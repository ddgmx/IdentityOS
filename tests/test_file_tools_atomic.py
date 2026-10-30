"""File writes must preserve the last complete version on failure."""

from unittest.mock import patch

from core.capabilities.file_tools import FileToolsCapability


def test_write_reports_encoded_bytes_and_replace(tmp_path):
    tool = FileToolsCapability({"allowed_roots": [str(tmp_path)]})
    target = tmp_path / "note.txt"
    first = tool._write_file(str(target), "é")
    assert first["status"] == "created"
    assert first["bytes_written"] == 2
    second = tool._write_file(str(target), "new")
    assert second["status"] == "created"  # Existing response contract.
    assert second["operation"] == "replaced"
    assert target.read_text(encoding="utf-8") == "new"


def test_failed_replace_keeps_original_and_cleans_temporary_file(tmp_path):
    tool = FileToolsCapability({"allowed_roots": [str(tmp_path)]})
    target = tmp_path / "note.txt"
    target.write_text("original", encoding="utf-8")
    with patch("core.capabilities.file_tools.os.replace", side_effect=OSError("disk failure")):
        result = tool.call("file_tools.write_file", path=str(target), content="new")
    assert not result.success
    assert target.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [target]


def test_failed_flush_keeps_original_and_cleans_temporary_file(tmp_path):
    tool = FileToolsCapability({"allowed_roots": [str(tmp_path)]})
    target = tmp_path / "note.txt"
    target.write_text("original", encoding="utf-8")
    with patch("core.capabilities.file_tools.os.fsync", side_effect=OSError("disk full")):
        result = tool.call("file_tools.write_file", path=str(target), content="new")
    assert not result.success
    assert target.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [target]
