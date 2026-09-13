"""Bounded, evidence-preserving retries for provider-backed CI benchmarks.

This module belongs to CI orchestration rather than an adapter. Interactive
runtime calls must stay responsive; a benchmark job can instead wait for a
provider-advertised cooldown and retry from the exact same persisted state.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Sequence, TextIO


_RATE_LIMIT_MARKERS = (
    "all groq api keys on cooldown",
    "all keys on cooldown",
    "rate limit reached",
    "rate_limit_exceeded",
)
_SHORTEST_SECONDS = re.compile(r"shortest\s+(\d+)s", re.IGNORECASE)
_TRY_AGAIN = re.compile(
    r"try again in\s+(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s",
    re.IGNORECASE,
)


def is_provider_rate_limit(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in _RATE_LIMIT_MARKERS)


def provider_wait_seconds(output: str, default: int = 120) -> int:
    """Return the longest concrete provider cooldown found in command output."""
    waits = [int(value) for value in _SHORTEST_SECONDS.findall(output)]
    for minutes, seconds in _TRY_AGAIN.findall(output):
        waits.append(
            int(minutes or 0) * 60 + int(math.ceil(float(seconds)))
        )
    return max(waits) if waits else default


def _workspace_path(raw: str | Path, workspace: Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve()
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise ValueError(
            f"CI retry paths must be descendants of the workspace: {raw}"
        )
    return resolved


def _snapshot_state(state_paths: Sequence[Path], backup_root: Path) -> list[Path | None]:
    snapshots: list[Path | None] = []
    for index, state_path in enumerate(state_paths):
        if not state_path.exists():
            snapshots.append(None)
            continue
        if not state_path.is_dir():
            raise ValueError(f"Benchmark state path is not a directory: {state_path}")
        snapshot = backup_root / str(index)
        shutil.copytree(state_path, snapshot, symlinks=True)
        snapshots.append(snapshot)
    return snapshots


def _restore_state(
    state_paths: Sequence[Path], snapshots: Sequence[Path | None]
) -> None:
    for state_path, snapshot in zip(state_paths, snapshots):
        if state_path.exists():
            shutil.rmtree(state_path)
        if snapshot is not None:
            shutil.copytree(snapshot, state_path, symlinks=True)


def _preserve_failed_state(
    state_paths: Sequence[Path], failure_root: Path, attempt: int
) -> None:
    attempt_root = failure_root / f"attempt-{attempt}"
    if attempt_root.exists():
        shutil.rmtree(attempt_root)
    attempt_root.mkdir(parents=True)
    for index, state_path in enumerate(state_paths):
        if state_path.is_dir():
            shutil.copytree(
                state_path,
                attempt_root / f"{index}-{state_path.name}",
                symlinks=True,
            )


def _run_command(command: Sequence[str], log: TextIO) -> tuple[int, str]:
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    captured: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log.write(line)
        log.flush()
        captured.append(line)
    return process.wait(), "".join(captured)


def run_with_retry(
    command: Sequence[str],
    *,
    attempts: int = 2,
    max_wait_seconds: int = 900,
    retry_grace_seconds: int = 30,
    results_path: str | Path = "benchmark-results.txt",
    state_paths: Sequence[str | Path] = (".identity_store", ".identitybench"),
    failure_root: str | Path = "benchmark-failure-state",
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    if not command:
        raise ValueError("A benchmark command is required")
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if max_wait_seconds < 1:
        raise ValueError("max_wait_seconds must be positive")

    workspace = Path.cwd().resolve()
    states = [_workspace_path(path, workspace) for path in state_paths]
    results = _workspace_path(results_path, workspace)
    failures = _workspace_path(failure_root, workspace)
    results.parent.mkdir(parents=True, exist_ok=True)
    results.write_text("", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="identitybench-ci-retry-") as temp:
        snapshots = _snapshot_state(states, Path(temp))
        for attempt in range(1, attempts + 1):
            with results.open("a", encoding="utf-8") as log:
                header = f"\n[identitybench-ci] attempt {attempt}/{attempts}\n"
                print(header, end="", flush=True)
                log.write(header)
                return_code, output = _run_command(command, log)

            if return_code == 0:
                return 0

            _preserve_failed_state(states, failures, attempt)
            _restore_state(states, snapshots)
            if attempt == attempts or not is_provider_rate_limit(output):
                return return_code or 1

            provider_wait = provider_wait_seconds(output)
            wait_seconds = min(
                provider_wait + max(0, retry_grace_seconds),
                max_wait_seconds,
            )
            notice = (
                "[identitybench-ci] provider rate limit observed; "
                f"retrying from restored state in {wait_seconds}s\n"
            )
            print(notice, end="", flush=True)
            with results.open("a", encoding="utf-8") as log:
                log.write(notice)
            sleep_fn(wait_seconds)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a provider benchmark with bounded, clean-state retries."
    )
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--max-wait-seconds", type=int, default=900)
    parser.add_argument("--retry-grace-seconds", type=int, default=30)
    parser.add_argument("--results-path", default="benchmark-results.txt")
    parser.add_argument(
        "--state-path",
        action="append",
        dest="state_paths",
        help="Workspace-relative state directory to restore after a failed attempt.",
    )
    parser.add_argument("--failure-root", default="benchmark-failure-state")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    return run_with_retry(
        command,
        attempts=args.attempts,
        max_wait_seconds=args.max_wait_seconds,
        retry_grace_seconds=args.retry_grace_seconds,
        results_path=args.results_path,
        state_paths=args.state_paths or (".identity_store", ".identitybench"),
        failure_root=args.failure_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
