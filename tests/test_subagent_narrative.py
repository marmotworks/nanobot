"""
Tests for _extract_narrative function in nanobot/agent/subagent.py.

Tests cover:
1. Normal result - single paragraph returned as-is (up to 300 chars)
2. Empty string - returns ⚠️ prefixed message
3. None input - returns ⚠️ prefixed message
4. [INCOMPLETE] prefix - returns ⚠️ prefixed message
5. Long result (>300 chars) - truncated with ...
6. Multi-paragraph result - only first non-empty paragraph returned
7. Whitespace-only result - returns ⚠️ prefixed message
"""

from __future__ import annotations

from nanobot.agent.subagent import _extract_narrative


class TestExtractNarrative:
    """Tests for _extract_narrative function."""

    def test_normal_result_single_paragraph(self) -> None:
        """Test that a single paragraph is returned as-is."""
        result = _extract_narrative("This is a normal result with some text.")
        assert result == "This is a normal result with some text."

    def test_normal_result_under_300_chars(self) -> None:
        """Test that a short paragraph is returned unchanged."""
        short_text = "Short text."
        result = _extract_narrative(short_text)
        assert result == short_text

    def test_empty_string(self) -> None:
        """Test that empty string returns warning message."""
        result = _extract_narrative("")
        assert result == "⚠️ No result produced."

    def test_none_input(self) -> None:
        """Test that None input returns warning message."""
        result = _extract_narrative(None)
        assert result == "⚠️ No result produced."

    def test_incomplete_prefix(self) -> None:
        """Test that [INCOMPLETE] prefix returns warning message."""
        result = _extract_narrative("[INCOMPLETE] Task failed to complete.")
        assert result == "⚠️ Task completed with no output (incomplete)."

    def test_long_result_truncation(self) -> None:
        """Test that results over 300 characters are truncated with ..."""
        long_text = "A" * 350
        result = _extract_narrative(long_text)
        assert len(result) == 300
        assert result == "A" * 297 + "..."
        assert result.endswith("...")

    def test_long_result_exact_300_chars(self) -> None:
        """Test that exactly 300 character result is not truncated."""
        text_300 = "A" * 300
        result = _extract_narrative(text_300)
        assert result == text_300
        assert not result.endswith("...")

    def test_long_result_301_chars(self) -> None:
        """Test that 301 character result is truncated."""
        text_301 = "A" * 301
        result = _extract_narrative(text_301)
        assert len(result) == 300
        assert result == "A" * 297 + "..."

    def test_multi_paragraph_first_only(self) -> None:
        """Test that only the first non-empty paragraph is returned."""
        multi_paragraph = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        result = _extract_narrative(multi_paragraph)
        assert result == "First paragraph here."

    def test_multi_paragraph_with_whitespace(self) -> None:
        """Test multi-paragraph with whitespace between paragraphs."""
        multi_paragraph = "  First paragraph  \n\n   Second paragraph   \n\nThird"
        result = _extract_narrative(multi_paragraph)
        assert result == "First paragraph"

    def test_paragraph_with_newlines_within(self) -> None:
        """Test that newlines within a paragraph are preserved."""
        text_with_newlines = "Line 1\nLine 2\nLine 3"
        result = _extract_narrative(text_with_newlines)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_whitespace_only_returns_warning(self) -> None:
        """Test that whitespace-only input returns warning message."""
        result = _extract_narrative("   \n\t\n  ")
        assert result == "⚠️ No result produced."

    def test_whitespace_only_empty_string(self) -> None:
        """Test that empty string with spaces returns warning."""
        result = _extract_narrative("   ")
        assert result == "⚠️ No result produced."

    def test_paragraph_truncation_at_300_chars(self) -> None:
        """Test that truncation happens at exactly 300 chars with ellipsis."""
        # 297 chars + 3 chars for "..." = 300 total
        text = "X" * 350
        result = _extract_narrative(text)
        assert len(result) == 300
        assert result.endswith("...")

    def test_incomplete_with_extra_content(self) -> None:
        """Test [INCOMPLETE] prefix with additional content."""
        result = _extract_narrative("[INCOMPLETE] Some extra details here.")
        assert result == "⚠️ Task completed with no output (incomplete)."

    def test_normal_result_with_special_characters(self) -> None:
        """Test normal result with special characters."""
        text = "Result with quotes \"and\" symbols & more."
        result = _extract_narrative(text)
        assert result == text

    def test_multiline_first_paragraph_only(self) -> None:
        """Test that only first paragraph is extracted from multiline text."""
        text = "First line\nSecond line\n\nSecond paragraph starts here."
        result = _extract_narrative(text)
        assert result == "First line\nSecond line"

    def test_result_with_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is stripped from result."""
        text = "Some text   "
        result = _extract_narrative(text)
        assert result == "Some text"

    def test_result_with_leading_whitespace(self) -> None:
        """Test that leading whitespace is stripped from result."""
        text = "   Some text"
        result = _extract_narrative(text)
        assert result == "Some text"

    def test_empty_paragraph_between_content(self) -> None:
        """Test that empty paragraphs between content are skipped."""
        text = "First\n\n\n\nSecond"
        result = _extract_narrative(text)
        assert result == "First"
