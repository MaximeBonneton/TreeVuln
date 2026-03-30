"""Tests for uploaded filename sanitization."""

import pytest

from app.filename_validation import sanitize_filename


class TestSanitizeFilename:
    """Validation of sanitize_filename against common attack vectors."""

    # --- Nominal cases ---

    def test_normal_filename(self):
        assert sanitize_filename("data.csv") == "data.csv"

    def test_normal_json(self):
        assert sanitize_filename("assets_export.json") == "assets_export.json"

    def test_filename_with_spaces(self):
        assert sanitize_filename("my file.csv") == "my file.csv"

    def test_filename_with_hyphens_underscores(self):
        assert sanitize_filename("my-file_2024.csv") == "my-file_2024.csv"

    # --- Empty values / None ---

    def test_none_returns_none(self):
        assert sanitize_filename(None) is None

    def test_empty_string_returns_none(self):
        assert sanitize_filename("") is None

    def test_whitespace_only_returns_none(self):
        assert sanitize_filename("   ") is None

    # --- Path traversal ---

    def test_path_traversal_unix(self):
        assert sanitize_filename("../../../etc/passwd") == "passwd"

    def test_path_traversal_windows(self):
        assert sanitize_filename("..\\..\\..\\windows\\system32\\config") == "config"

    def test_absolute_path_unix(self):
        assert sanitize_filename("/etc/passwd") == "passwd"

    def test_absolute_path_windows(self):
        assert sanitize_filename("C:\\Users\\admin\\data.csv") == "data.csv"

    def test_mixed_separators(self):
        assert sanitize_filename("path/to\\file.csv") == "file.csv"

    def test_dot_dot_only(self):
        """A name consisting only of '..' must be rejected."""
        assert sanitize_filename("..") is None

    def test_single_dot(self):
        """A name consisting of a single '.' must be rejected (empty hidden file)."""
        assert sanitize_filename(".") is None

    # --- Hidden files (dot-prefix) ---

    def test_hidden_file(self):
        assert sanitize_filename(".htaccess") == "htaccess"

    def test_hidden_file_with_path(self):
        assert sanitize_filename("/var/www/.env") == "env"

    # --- Null bytes and control characters ---

    def test_null_byte_injection(self):
        result = sanitize_filename("file.csv\x00.exe")
        assert result == "file.csv.exe"
        assert "\x00" not in result

    def test_control_characters(self):
        result = sanitize_filename("file\x01\x02\x03.csv")
        assert result == "file.csv"

    def test_tab_and_newline(self):
        result = sanitize_filename("file\t\n.csv")
        assert result == "file.csv"

    # --- Dangerous special characters ---

    def test_angle_brackets(self):
        """Protects against HTML injection in headers."""
        result = sanitize_filename("<script>alert(1)</script>.csv")
        assert "<" not in result
        assert ">" not in result

    def test_pipe_and_question(self):
        result = sanitize_filename("file|name?.csv")
        assert "|" not in result
        assert "?" not in result

    def test_double_quotes(self):
        """Protects against injection in Content-Disposition."""
        result = sanitize_filename('file"name.csv')
        assert '"' not in result

    def test_colon(self):
        result = sanitize_filename("file:name.csv")
        assert ":" not in result

    def test_asterisk(self):
        result = sanitize_filename("file*name.csv")
        assert "*" not in result

    # --- Length ---

    def test_very_long_filename_truncated(self):
        long_name = "a" * 300 + ".csv"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_normal_length_preserved(self):
        name = "a" * 100 + ".csv"
        assert sanitize_filename(name) == name

    # --- Combined cases ---

    def test_traversal_with_null_byte(self):
        result = sanitize_filename("../../\x00file.csv")
        assert result == "file.csv"

    def test_traversal_with_special_chars(self):
        result = sanitize_filename('../<script>"alert.csv')
        assert result == "scriptalert.csv"

    def test_extension_preserved_after_sanitization(self):
        """The extension must remain intact for format detection."""
        assert sanitize_filename("../data.csv").endswith(".csv")
        assert sanitize_filename("..\\data.json").endswith(".json")
