"""Argument parsing must follow the host OS without a shell."""

import os
import subprocess
import sys

from core.capabilities.command_exec import _split_command


def test_quoted_argument_and_shell_punctuation_stay_literal():
    command = subprocess.list2cmdline([sys.executable, "-c", "import sys; print(sys.argv[1])", "a b;$(echo bad)"])
    argv = _split_command(command)
    assert argv[0] == sys.executable
    assert argv[-1] == "a b;$(echo bad)"
    result = subprocess.run(argv, shell=False, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "a b;$(echo bad)"


def test_windows_backslashes_survive_native_parsing():
    if os.name != "nt":
        return
    arguments = [r"C:\Program Files\IdentityOS\tool.exe", r"C:\Users\name\file with spaces.txt"]
    assert _split_command(subprocess.list2cmdline(arguments)) == arguments
