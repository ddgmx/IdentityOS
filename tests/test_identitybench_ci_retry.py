from __future__ import annotations

from pathlib import Path
import sys

import pytest

from scripts import benchmark_ci_retry as ci_retry


def test_provider_wait_uses_longest_advertised_cooldown() -> None:
    output = """
    Rate limited on key 0, cooldown 865s
    All keys on cooldown (shortest 473s). Falling through.
    Please try again in 7m53.472s.
    All keys on cooldown (shortest 60s). Falling through.
    """

    assert ci_retry.is_provider_rate_limit(output) is True
    assert ci_retry.provider_wait_seconds(output) == 474
    assert ci_retry.is_provider_rate_limit("schema validation failed") is False


def test_rate_limit_retry_restores_state_and_preserves_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    identity_state = tmp_path / ".identity_store"
    benchmark_state = tmp_path / ".identitybench"
    identity_state.mkdir()
    benchmark_state.mkdir()
    (identity_state / "baseline.txt").write_text("identity-baseline")
    (benchmark_state / "baseline.txt").write_text("benchmark-baseline")
    calls = 0
    waits: list[float] = []

    def fake_run(command, log):
        nonlocal calls
        calls += 1
        assert command == ["identitybench", "run"]
        if calls == 1:
            (identity_state / "partial.txt").write_text("failed identity mutation")
            (benchmark_state / "failed.json").write_text("failed run evidence")
            output = "All keys on cooldown (shortest 7s). Falling through.\n"
            log.write(output)
            return 1, output
        assert not (identity_state / "partial.txt").exists()
        assert not (benchmark_state / "failed.json").exists()
        assert (identity_state / "baseline.txt").read_text() == "identity-baseline"
        (benchmark_state / "success.json").write_text("verified run")
        log.write("completed\n")
        return 0, "completed\n"

    monkeypatch.setattr(ci_retry, "_run_command", fake_run)

    result = ci_retry.run_with_retry(
        ["identitybench", "run"],
        attempts=2,
        max_wait_seconds=30,
        retry_grace_seconds=2,
        sleep_fn=waits.append,
    )

    assert result == 0
    assert calls == 2
    assert waits == [9]
    assert (benchmark_state / "success.json").read_text() == "verified run"
    failure = (
        tmp_path
        / "benchmark-failure-state"
        / "attempt-1"
        / "1-.identitybench"
        / "failed.json"
    )
    assert failure.read_text() == "failed run evidence"
    results = (tmp_path / "benchmark-results.txt").read_text()
    assert "attempt 1/2" in results
    assert "retrying from restored state in 9s" in results
    assert "attempt 2/2" in results


def test_non_rate_limit_failure_is_not_retried_and_state_is_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    state = tmp_path / ".identitybench"
    state.mkdir()
    (state / "baseline.txt").write_text("baseline")
    calls = 0

    def fake_run(command, log):
        nonlocal calls
        calls += 1
        (state / "invalid.json").write_text("invalid")
        log.write("tool schema validation failed\n")
        return 3, "tool schema validation failed\n"

    monkeypatch.setattr(ci_retry, "_run_command", fake_run)

    result = ci_retry.run_with_retry(
        ["identitybench", "run"],
        attempts=2,
        state_paths=(".identitybench",),
        sleep_fn=lambda _: pytest.fail("non-rate-limit failure must not wait"),
    )

    assert result == 3
    assert calls == 1
    assert (state / "baseline.txt").read_text() == "baseline"
    assert not (state / "invalid.json").exists()


def test_real_subprocess_recovers_from_one_transient_provider_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    state = tmp_path / ".identitybench"
    state.mkdir()
    (state / "baseline.txt").write_text("baseline")
    helper = tmp_path / "transient_provider.py"
    helper.write_text(
        """from pathlib import Path
counter = Path("attempt-count.txt")
attempt = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(attempt))
if attempt == 1:
    Path(".identitybench/partial.json").write_text("partial")
    print("All keys on cooldown (shortest 1s). Falling through.")
    raise SystemExit(1)
assert not Path(".identitybench/partial.json").exists()
assert Path(".identitybench/baseline.txt").read_text() == "baseline"
Path(".identitybench/completed.json").write_text("completed")
print("provider benchmark completed")
"""
    )
    waits: list[float] = []

    result = ci_retry.run_with_retry(
        [sys.executable, str(helper)],
        attempts=2,
        max_wait_seconds=5,
        retry_grace_seconds=0,
        state_paths=(".identitybench",),
        sleep_fn=waits.append,
    )

    assert result == 0
    assert waits == [1]
    assert (tmp_path / "attempt-count.txt").read_text() == "2"
    assert (state / "completed.json").read_text() == "completed"
    assert (
        tmp_path
        / "benchmark-failure-state"
        / "attempt-1"
        / "0-.identitybench"
        / "partial.json"
    ).read_text() == "partial"


def test_retry_rejects_state_paths_outside_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="descendants of the workspace"):
        ci_retry.run_with_retry(
            ["identitybench", "run"],
            state_paths=(tmp_path.parent,),
        )
