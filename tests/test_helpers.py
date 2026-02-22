"""Tests for nanobot.utils.helpers."""

from pathlib import Path
from unittest.mock import patch

import pytest

from nanobot.utils.helpers import (
    ensure_dir,
    get_data_path,
    get_sessions_path,
    get_skills_path,
    get_workspace_path,
    parse_session_key,
    safe_filename,
    timestamp,
    truncate_string,
)


class TestEnsureDir:
    """Tests for ensure_dir function."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        """ensure_dir creates the directory if it doesn't exist."""
        path = tmp_path / "new_dir"
        result = ensure_dir(path)

        assert result == path
        assert path.is_dir()

    def test_returns_path(self, tmp_path: Path) -> None:
        """ensure_dir returns the path object."""
        path = tmp_path / "another_dir"
        result = ensure_dir(path)

        assert isinstance(result, Path)
        assert result == path

    def test_existing_directory(self, tmp_path: Path) -> None:
        """ensure_dir works on existing directory."""
        path = tmp_path / "existing_dir"
        path.mkdir()

        result = ensure_dir(path)

        assert result == path
        assert path.is_dir()

    def test_parent_directories_created(self, tmp_path: Path) -> None:
        """ensure_dir creates parent directories if needed."""
        path = tmp_path / "level1" / "level2" / "level3"
        result = ensure_dir(path)

        assert result == path
        assert path.is_dir()


class TestGetWorkspacePath:
    """Tests for get_workspace_path function."""

    @patch("nanobot.utils.helpers.Path.mkdir")
    @patch("nanobot.utils.helpers.Path.home")
    def test_default_path(self, mock_home: Path, mock_mkdir: Path) -> None:
        """get_workspace_path returns ~/.nanobot/workspace by default."""
        mock_home.return_value = Path("/home/user")
        mock_mkdir.return_value = None

        result = get_workspace_path()

        assert result == Path("/home/user/.nanobot/workspace")
        mock_mkdir.assert_called_once()

    @patch("nanobot.utils.helpers.Path.mkdir")
    def test_custom_path(self, mock_mkdir: Path) -> None:
        """get_workspace_path uses custom path when provided."""
        mock_mkdir.return_value = None

        result = get_workspace_path("/tmp/myws")

        assert result == Path("/tmp/myws")
        mock_mkdir.assert_called_once()

    @patch("nanobot.utils.helpers.Path.mkdir")
    def test_custom_path_expands_user(self, mock_mkdir: Path) -> None:
        """get_workspace_path expands ~ in custom path."""
        mock_mkdir.return_value = None

        result = get_workspace_path("~/myws")

        assert result == Path.home() / "myws"
        mock_mkdir.assert_called_once()


class TestGetDataPath:
    """Tests for get_data_path function."""

    @patch("nanobot.utils.helpers.Path.mkdir")
    @patch("nanobot.utils.helpers.Path.home")
    def test_returns_data_path(self, mock_home: Path, mock_mkdir: Path) -> None:
        """get_data_path returns ~/.nanobot."""
        mock_home.return_value = Path("/home/user")
        mock_mkdir.return_value = None

        result = get_data_path()

        assert result == Path("/home/user/.nanobot")
        mock_mkdir.assert_called_once()


class TestGetSessionsPath:
    """Tests for get_sessions_path function."""

    @patch("nanobot.utils.helpers.Path.mkdir")
    @patch("nanobot.utils.helpers.get_data_path")
    def test_returns_sessions_path(self, mock_get_data: Path, mock_mkdir: Path) -> None:
        """get_sessions_path returns ~/.nanobot/sessions."""
        mock_get_data.return_value = Path("/home/user/.nanobot")
        mock_mkdir.return_value = None

        result = get_sessions_path()

        assert result == Path("/home/user/.nanobot/sessions")
        mock_mkdir.assert_called_once()


class TestGetSkillsPath:
    """Tests for get_skills_path function."""

    @patch("nanobot.utils.helpers.Path.mkdir")
    @patch("nanobot.utils.helpers.get_workspace_path")
    def test_default_workspace(self, mock_get_ws: Path, mock_mkdir: Path) -> None:
        """get_skills_path uses default workspace when not provided."""
        mock_get_ws.return_value = Path("/home/user/.nanobot/workspace")
        mock_mkdir.return_value = None

        result = get_skills_path()

        assert result == Path("/home/user/.nanobot/workspace/skills")
        mock_mkdir.assert_called_once()

    @patch("nanobot.utils.helpers.Path.mkdir")
    def test_custom_workspace(self, mock_mkdir: Path) -> None:
        """get_skills_path uses custom workspace when provided."""
        mock_mkdir.return_value = None
        custom_ws = Path("/custom/workspace")

        result = get_skills_path(custom_ws)

        assert result == Path("/custom/workspace/skills")
        mock_mkdir.assert_called_once()


class TestTimestamp:
    """Tests for timestamp function."""

    def test_returns_iso_format(self) -> None:
        """timestamp returns valid ISO datetime string."""
        result = timestamp()

        # Should be parseable as ISO format
        from datetime import datetime

        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)


class TestTruncateString:
    """Tests for truncate_string function."""

    def test_short_string_no_truncation(self) -> None:
        """Short string returned unchanged."""
        result = truncate_string("hello", max_len=100)

        assert result == "hello"

    def test_exact_length_no_truncation(self) -> None:
        """String of exact length returned unchanged."""
        result = truncate_string("hello", max_len=5)

        assert result == "hello"

    def test_over_length_truncated(self) -> None:
        """String over length is truncated with suffix."""
        result = truncate_string("hello world", max_len=10)

        assert result == "hello w..."

    def test_custom_suffix(self) -> None:
        """Custom suffix is used when provided."""
        result = truncate_string("hello world", max_len=10, suffix=">>>")

        assert result == "hello w>>>"

    def test_truncation_with_custom_suffix(self) -> None:
        """Truncation accounts for custom suffix length."""
        result = truncate_string("this is a long string", max_len=15, suffix="!!!")

        # 15 - 3 = 12 characters, then add suffix
        assert result == "this is a lo!!!"


class TestSafeFilename:
    """Tests for safe_filename function."""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("file<name", "file_name"),
            ("file>name", "file_name"),
            ("file:name", "file_name"),
            ('file"name', "file_name"),
            ("file/name", "file_name"),
            ("file\\name", "file_name"),
            ("file|name", "file_name"),
            ("file?name", "file_name"),
            ("file*name", "file_name"),
        ],
    )
    def test_unsafe_chars_replaced(self, input_str: str, expected: str) -> None:
        """All unsafe characters are replaced with underscore."""
        result = safe_filename(input_str)

        assert result == expected

    def test_all_unsafe_chars(self) -> None:
        """All unsafe characters in one string."""
        result = safe_filename('<>:"/\\|?*')

        assert result == "_________"

    def test_leading_trailing_spaces_stripped(self) -> None:
        """Leading and trailing spaces are removed."""
        result = safe_filename("  filename  ")

        assert result == "filename"

    def test_spaces_and_unsafe_chars(self) -> None:
        """Spaces and unsafe chars are handled."""
        result = safe_filename("  file<name  ")

        assert result == "file_name"


class TestParseSessionKey:
    """Tests for parse_session_key function."""

    def test_valid_key(self) -> None:
        """Valid key splits into channel and chat_id."""
        result = parse_session_key("discord:12345")

        assert result == ("discord", "12345")

    def test_key_with_multiple_colons(self) -> None:
        """Key with multiple colons splits on first only."""
        result = parse_session_key("discord:chat:extra")

        assert result == ("discord", "chat:extra")

    def test_no_colon_raises_error(self) -> None:
        """Key without colon raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_session_key("no_colon_here")

        assert "Invalid session key" in str(exc_info.value)

    def test_empty_string_raises_error(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_session_key("")

        assert "Invalid session key" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
