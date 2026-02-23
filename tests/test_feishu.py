"""Unit tests for Feishu/Lark channel implementation."""

import json
import sys
import unittest
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

# Mock lark_oapi before importing feishu module
mock_lark = MagicMock()
mock_lark_api = MagicMock()
mock_lark_api_im_v1 = MagicMock()

# Create mock classes for lark_oapi
mock_lark.Client = MagicMock()
mock_lark.EventDispatcherHandler = MagicMock()
mock_lark.ws = MagicMock()
mock_lark.ws.Client = MagicMock()
mock_lark.LogLevel = MagicMock()
mock_lark.LogLevel.INFO = "INFO"

# Create mock request classes
mock_lark_api_im_v1.CreateFileRequest = MagicMock()
mock_lark_api_im_v1.CreateFileRequestBody = MagicMock()
mock_lark_api_im_v1.CreateImageRequest = MagicMock()
mock_lark_api_im_v1.CreateImageRequestBody = MagicMock()
mock_lark_api_im_v1.CreateMessageReactionRequest = MagicMock()
mock_lark_api_im_v1.CreateMessageReactionRequestBody = MagicMock()
mock_lark_api_im_v1.CreateMessageRequest = MagicMock()
mock_lark_api_im_v1.CreateMessageRequestBody = MagicMock()
mock_lark_api_im_v1.Emoji = MagicMock()
mock_lark_api_im_v1.GetMessageResourceRequest = MagicMock()
mock_lark_api_im_v1.P2ImMessageReceiveV1 = MagicMock()

mock_lark_api.im = MagicMock()
mock_lark_api.im.v1 = MagicMock()
mock_lark_api.im.v1.message_reaction = MagicMock()
mock_lark_api.im.v1.message_resource = MagicMock()
mock_lark_api.im.v1.image = MagicMock()
mock_lark_api.im.v1.file = MagicMock()
mock_lark_api.im.v1.message = MagicMock()

mock_lark_oapi = MagicMock()
mock_lark_oapi.api = mock_lark_api
mock_lark_oapi.api.im = mock_lark_api.im
mock_lark_oapi.api.im.v1 = mock_lark_api_im_v1
mock_lark_oapi.api.im.v1.CreateFileRequest = mock_lark_api_im_v1.CreateFileRequest
mock_lark_oapi.api.im.v1.CreateFileRequestBody = mock_lark_api_im_v1.CreateFileRequestBody
mock_lark_oapi.api.im.v1.CreateImageRequest = mock_lark_api_im_v1.CreateImageRequest
mock_lark_oapi.api.im.v1.CreateImageRequestBody = mock_lark_api_im_v1.CreateImageRequestBody
mock_lark_oapi.api.im.v1.CreateMessageReactionRequest = mock_lark_api_im_v1.CreateMessageReactionRequest
mock_lark_oapi.api.im.v1.CreateMessageReactionRequestBody = mock_lark_api_im_v1.CreateMessageReactionRequestBody
mock_lark_oapi.api.im.v1.CreateMessageRequest = mock_lark_api_im_v1.CreateMessageRequest
mock_lark_oapi.api.im.v1.CreateMessageRequestBody = mock_lark_api_im_v1.CreateMessageRequestBody
mock_lark_oapi.api.im.v1.Emoji = mock_lark_api_im_v1.Emoji
mock_lark_oapi.api.im.v1.GetMessageResourceRequest = mock_lark_api_im_v1.GetMessageResourceRequest
mock_lark_oapi.api.im.v1.P2ImMessageReceiveV1 = mock_lark_api_im_v1.P2ImMessageReceiveV1
mock_lark_oapi.Client = mock_lark.Client
mock_lark_oapi.EventDispatcherHandler = mock_lark.EventDispatcherHandler
mock_lark_oapi.ws = mock_lark.ws
mock_lark_oapi.ws.Client = mock_lark.ws.Client
mock_lark_oapi.LogLevel = mock_lark.LogLevel

# Patch sys.modules to mock lark_oapi
sys.modules["lark_oapi"] = mock_lark_oapi
sys.modules["lark_oapi.api"] = mock_lark_api
sys.modules["lark_oapi.api.im"] = mock_lark_api.im
sys.modules["lark_oapi.api.im.v1"] = mock_lark_api_im_v1

# Now import the feishu module after mocking
from nanobot.channels.feishu import (  # noqa: E402
    FeishuChannel,
    _extract_element_content,
    _extract_interactive_content,
    _extract_post_text,
    _extract_share_card_content,
)


class TestModuleLevelFunctions(TestCase):
    """Tests for module-level extraction functions."""

    def test_extract_post_text_direct_format(self) -> None:
        """Test extracting text from direct format post content."""
        content = {
            "title": "Hello",
            "content": [
                [
                    {"tag": "text", "text": "world"},
                    {"tag": "at", "user_name": "alice"},
                ]
            ],
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "Hello world @alice")

    def test_extract_post_text_localized_format_zh_cn(self) -> None:
        """Test extracting text from localized format (zh_cn)."""
        content = {
            "zh_cn": {
                "title": "标题",
                "content": [
                    [
                        {"tag": "text", "text": "内容"},
                    ]
                ],
            }
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "标题 内容")

    def test_extract_post_text_localized_format_en_us(self) -> None:
        """Test extracting text from localized format (en_us)."""
        content = {
            "en_us": {
                "title": "Title",
                "content": [
                    [
                        {"tag": "text", "text": "Content"},
                    ]
                ],
            }
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "Title Content")

    def test_extract_post_text_localized_format_ja_jp(self) -> None:
        """Test extracting text from localized format (ja_jp)."""
        content = {
            "ja_jp": {
                "title": "タイトル",
                "content": [
                    [
                        {"tag": "text", "text": "コンテンツ"},
                    ]
                ],
            }
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "タイトル コンテンツ")

    def test_extract_post_text_fallback_order(self) -> None:
        """Test that extraction tries zh_cn, en_us, ja_jp in order."""
        content = {
            "zh_cn": None,
            "en_us": None,
            "ja_jp": {
                "title": "Japanese",
                "content": [[{"tag": "text", "text": "Text"}]],
            },
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "Japanese Text")

    def test_extract_post_text_no_content(self) -> None:
        """Test extraction when content is missing."""
        content = {}
        result = _extract_post_text(content)
        self.assertEqual(result, "")

    def test_extract_post_text_invalid_content(self) -> None:
        """Test extraction with invalid content structure."""
        content = {"title": "test", "content": "not a list"}
        result = _extract_post_text(content)
        self.assertEqual(result, "")

    def test_extract_post_text_empty_blocks(self) -> None:
        """Test extraction with empty content blocks."""
        content = {"title": "", "content": []}
        result = _extract_post_text(content)
        self.assertEqual(result, "")

    def test_extract_post_text_non_dict_content(self) -> None:
        """Test extraction with non-dict content."""
        content = {"content": "not a list"}
        result = _extract_post_text(content)
        self.assertEqual(result, "")

    def test_extract_post_text_non_list_content_blocks(self) -> None:
        """Test extraction with non-list content blocks."""
        content = {"title": "test", "content": "not a list"}
        result = _extract_post_text(content)
        self.assertEqual(result, "")

    def test_extract_post_text_empty_title_and_content(self) -> None:
        """Test extraction with empty title and content."""
        content = {"title": "", "content": [[]]}
        result = _extract_post_text(content)
        self.assertEqual(result, "")

    def test_extract_post_text_direct_format_with_a_tag(self) -> None:
        """Test extraction with 'a' tag in direct format."""
        content = {
            "title": "Title",
            "content": [
                [
                    {"tag": "a", "text": "link text", "href": "https://example.com"},
                ]
            ],
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "Title link text")

    def test_extract_post_text_direct_format_with_at_tag(self) -> None:
        """Test extraction with 'at' tag in direct format."""
        content = {
            "title": "Title",
            "content": [
                [
                    {"tag": "at", "user_name": "alice"},
                ]
            ],
        }
        result = _extract_post_text(content)
        self.assertEqual(result, "Title @alice")

    def test_extract_share_card_content_share_chat(self) -> None:
        """Test extracting share chat content."""
        content = {"chat_id": "chat123"}
        result = _extract_share_card_content(content, "share_chat")
        self.assertEqual(result, "[shared chat: chat123]")

    def test_extract_share_card_content_share_user(self) -> None:
        """Test extracting share user content."""
        content = {"user_id": "user456"}
        result = _extract_share_card_content(content, "share_user")
        self.assertEqual(result, "[shared user: user456]")

    def test_extract_share_card_content_interactive(self) -> None:
        """Test extracting interactive content."""
        content = {
            "title": "Card Title",
            "elements": [{"tag": "markdown", "content": "Card content"}],
        }
        result = _extract_share_card_content(content, "interactive")
        self.assertIn("title: Card Title", result)
        self.assertIn("Card content", result)

    def test_extract_share_card_content_share_calendar_event(self) -> None:
        """Test extracting share calendar event content."""
        content = {"event_key": "event789"}
        result = _extract_share_card_content(content, "share_calendar_event")
        self.assertEqual(result, "[shared calendar event: event789]")

    def test_extract_share_card_content_system(self) -> None:
        """Test extracting system message content."""
        content = {}
        result = _extract_share_card_content(content, "system")
        self.assertEqual(result, "[system message]")

    def test_extract_share_card_content_merge_forward(self) -> None:
        """Test extracting merge forward content."""
        content = {}
        result = _extract_share_card_content(content, "merge_forward")
        self.assertEqual(result, "[merged forward messages]")

    def test_extract_share_card_content_unknown_type(self) -> None:
        """Test extracting unknown message type."""
        content = {}
        result = _extract_share_card_content(content, "unknown_type")
        self.assertEqual(result, "[unknown_type]")

    def test_extract_interactive_content_string_json(self) -> None:
        """Test extracting from stringified JSON."""
        content = '{"title": "Test", "elements": []}'
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: Test"])

    def test_extract_interactive_content_dict_with_title(self) -> None:
        """Test extracting from dict with title."""
        content = {"title": {"content": "My Title"}}
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: My Title"])

    def test_extract_interactive_content_dict_with_text_title(self) -> None:
        """Test extracting from dict with text title."""
        content = {"title": {"text": "Text Title"}}
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: Text Title"])

    def test_extract_interactive_content_elements(self) -> None:
        """Test extracting from elements list."""
        content = {
            "elements": [
                {"tag": "markdown", "content": "Hello World"},
            ]
        }
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["Hello World"])

    def test_extract_interactive_content_nested_card(self) -> None:
        """Test extracting from nested card structure."""
        content = {
            "card": {
                "title": "Nested",
                "elements": [{"tag": "markdown", "content": "Content"}],
            }
        }
        result = _extract_interactive_content(content)
        self.assertIn("title: Nested", result)
        self.assertIn("Content", result)

    def test_extract_interactive_content_header(self) -> None:
        """Test extracting from header."""
        content = {
            "header": {
                "title": {"content": "Header Title"},
            }
        }
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: Header Title"])

    def test_extract_interactive_content_invalid_input(self) -> None:
        """Test extracting from invalid input."""
        result = _extract_interactive_content("not json")
        self.assertEqual(result, ["not json"])

    def test_extract_interactive_content_none_content(self) -> None:
        """Test extracting from None content."""
        result = _extract_interactive_content(None)
        self.assertEqual(result, [])

    def test_extract_interactive_content_empty_dict(self) -> None:
        """Test extracting from empty dict."""
        result = _extract_interactive_content({})
        self.assertEqual(result, [])

    def test_extract_interactive_content_title_string(self) -> None:
        """Test extracting from dict with string title."""
        content = {"title": "Simple Title"}
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: Simple Title"])

    def test_extract_interactive_content_card_nested(self) -> None:
        """Test extracting from nested card structure."""
        content = {
            "card": {
                "title": {"content": "Card Title"},
                "elements": [{"tag": "markdown", "content": "Card Content"}],
            }
        }
        result = _extract_interactive_content(content)
        self.assertIn("title: Card Title", result)
        self.assertIn("Card Content", result)

    def test_extract_interactive_content_header_title_dict(self) -> None:
        """Test extracting from header with dict title."""
        content = {
            "header": {
                "title": {"content": "Header Title"},
            }
        }
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: Header Title"])

    def test_extract_interactive_content_header_title_string(self) -> None:
        """Test extracting from header with string title."""
        content = {
            "header": {
                "title": "Header String Title",
            }
        }
        result = _extract_interactive_content(content)
        self.assertEqual(result, ["title: Header String Title"])

    def test_extract_interactive_content_elements_and_card(self) -> None:
        """Test extracting from both elements and card."""
        content = {
            "elements": [{"tag": "markdown", "content": "Main Element"}],
            "card": {
                "title": "Card Title",
                "elements": [{"tag": "markdown", "content": "Card Element"}],
            },
        }
        result = _extract_interactive_content(content)
        self.assertIn("Main Element", result)
        self.assertIn("title: Card Title", result)
        self.assertIn("Card Element", result)

    def test_extract_interactive_content_header_and_elements(self) -> None:
        """Test extracting from header and elements."""
        content = {
            "header": {"title": {"content": "Header Title"}},
            "elements": [{"tag": "markdown", "content": "Element Content"}],
        }
        result = _extract_interactive_content(content)
        self.assertIn("title: Header Title", result)
        self.assertIn("Element Content", result)

    def test_extract_interactive_content_non_dict_string(self) -> None:
        """Test extracting from non-dict string that is not JSON."""
        result = _extract_interactive_content("plain text")
        self.assertEqual(result, ["plain text"])

    def test_extract_interactive_content_empty_string(self) -> None:
        """Test extracting from empty string."""
        result = _extract_interactive_content("")
        self.assertEqual(result, [])

    def test_extract_interactive_content_whitespace_string(self) -> None:
        """Test extracting from whitespace-only string."""
        result = _extract_interactive_content("   ")
        self.assertEqual(result, [])

    def test_extract_element_content_markdown(self) -> None:
        """Test extracting from markdown element."""
        element = {"tag": "markdown", "content": "# Hello"}
        result = _extract_element_content(element)
        self.assertEqual(result, ["# Hello"])

    def test_extract_element_content_div_with_text(self) -> None:
        """Test extracting from div element with text."""
        element = {
            "tag": "div",
            "text": {"content": "Div text"},
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Div text"])

    def test_extract_element_content_div_with_text_str(self) -> None:
        """Test extracting from div element with string text."""
        element = {
            "tag": "div",
            "text": "Div string text",
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Div string text"])

    def test_extract_element_content_div_with_fields(self) -> None:
        """Test extracting from div element with fields."""
        element = {
            "tag": "div",
            "text": {"content": "Main text"},
            "fields": [
                {"text": {"content": "Field text"}},
            ],
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Main text", "Field text"])

    def test_extract_element_content_a_link(self) -> None:
        """Test extracting from link element."""
        element = {
            "tag": "a",
            "href": "https://example.com",
            "text": "Example",
        }
        result = _extract_element_content(element)
        self.assertIn("link: https://example.com", result)
        self.assertIn("Example", result)

    def test_extract_element_content_button_with_url(self) -> None:
        """Test extracting from button element with URL."""
        element = {
            "tag": "button",
            "text": {"content": "Click"},
            "url": "https://button.com",
        }
        result = _extract_element_content(element)
        self.assertIn("Click", result)
        self.assertIn("link: https://button.com", result)

    def test_extract_element_content_button_with_multi_url(self) -> None:
        """Test extracting from button element with multi_url."""
        element = {
            "tag": "button",
            "text": {"content": "Click"},
            "multi_url": {"url": "https://multi.com"},
        }
        result = _extract_element_content(element)
        self.assertIn("link: https://multi.com", result)

    def test_extract_element_content_img(self) -> None:
        """Test extracting from image element."""
        element = {
            "tag": "img",
            "alt": {"content": "Alt text"},
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Alt text"])

    def test_extract_element_content_img_without_alt(self) -> None:
        """Test extracting from image element without alt."""
        element = {
            "tag": "img",
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["[image]"])

    def test_extract_element_content_note(self) -> None:
        """Test extracting from note element."""
        element = {
            "tag": "note",
            "elements": [
                {"tag": "markdown", "content": "Note content"},
            ],
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Note content"])

    def test_extract_element_content_column_set(self) -> None:
        """Test extracting from column_set element."""
        element = {
            "tag": "column_set",
            "columns": [
                {"elements": [{"tag": "markdown", "content": "Column 1"}]},
            ],
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Column 1"])

    def test_extract_element_content_plain_text(self) -> None:
        """Test extracting from plain_text element."""
        element = {
            "tag": "plain_text",
            "content": "Plain text content",
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Plain text content"])

    def test_extract_element_content_unknown_tag(self) -> None:
        """Test extracting from unknown tag falls back to elements."""
        element = {
            "tag": "unknown",
            "elements": [
                {"tag": "markdown", "content": "Fallback content"},
            ],
        }
        result = _extract_element_content(element)
        self.assertEqual(result, ["Fallback content"])

    def test_extract_element_content_non_dict(self) -> None:
        """Test extracting from non-dict element."""
        result = _extract_element_content("not a dict")
        self.assertEqual(result, [])

    def test_extract_element_content_empty_dict(self) -> None:
        """Test extracting from empty dict element."""
        result = _extract_element_content({})
        self.assertEqual(result, [])


class TestFeishuChannelStaticMethods(TestCase):
    """Tests for FeishuChannel static and instance methods."""

    def test_parse_md_table_valid(self) -> None:
        """Test parsing a valid markdown table."""
        table_text = "| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        result = FeishuChannel._parse_md_table(table_text)
        self.assertIsNotNone(result)
        self.assertEqual(result["tag"], "table")
        self.assertEqual(len(result["columns"]), 2)
        self.assertEqual(result["columns"][0]["name"], "c0")
        self.assertEqual(result["columns"][0]["display_name"], "Header 1")
        self.assertEqual(len(result["rows"]), 1)

    def test_parse_md_table_minimal(self) -> None:
        """Test parsing minimal markdown table."""
        table_text = "| H1 |\n| --- |\n| C1 |"
        result = FeishuChannel._parse_md_table(table_text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["columns"]), 1)

    def test_parse_md_table_insufficient_rows(self) -> None:
        """Test parsing table with insufficient rows returns None."""
        table_text = "| Header 1 |\n| --- |"
        result = FeishuChannel._parse_md_table(table_text)
        self.assertIsNone(result)

    def test_parse_md_table_empty(self) -> None:
        """Test parsing empty table returns None."""
        result = FeishuChannel._parse_md_table("")
        self.assertIsNone(result)

    def test_parse_md_table_whitespace_only(self) -> None:
        """Test parsing whitespace-only table returns None."""
        result = FeishuChannel._parse_md_table("   \n   ")
        self.assertIsNone(result)

    def test_build_card_elements_with_table(self) -> None:
        """Test building card elements with markdown table."""
        content = "Before table\n\n| H1 | H2 |\n| --- | --- |\n| C1 | C2 |\n\nAfter table"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._build_card_elements(content)
        self.assertIsNotNone(result)
        # Should have markdown before, table, and markdown after
        self.assertTrue(len(result) >= 3)

    def test_build_card_elements_no_table(self) -> None:
        """Test building card elements without table."""
        content = "Just text\n\n## Heading\n\nMore text"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._build_card_elements(content)
        self.assertIsNotNone(result)

    def test_build_card_elements_empty(self) -> None:
        """Test building card elements from empty content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._build_card_elements("")
        self.assertEqual(result, [{"tag": "markdown", "content": ""}])

    def test_split_headings_with_markdown(self) -> None:
        """Test splitting content with headings."""
        content = "# Heading 1\n\nContent\n\n## Heading 2\n\nMore content"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        self.assertIsNotNone(result)
        # Should have: div for H1, markdown for Content, div for H2, markdown for More content
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["tag"], "div")
        self.assertEqual(result[1]["tag"], "markdown")
        self.assertEqual(result[2]["tag"], "div")
        self.assertEqual(result[3]["tag"], "markdown")

    def test_split_headings_no_headings(self) -> None:
        """Test splitting content without headings."""
        content = "Just plain text\n\nWith multiple lines"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        self.assertEqual(result, [{"tag": "markdown", "content": content}])

    def test_split_headings_with_code_block(self) -> None:
        """Test splitting content with code blocks preserved."""
        content = "# Heading\n\n```python\nprint('hello')\n```\n\nMore text"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        self.assertIsNotNone(result)
        # Find the markdown element and check code block is preserved
        code_found = False
        for el in result:
            if el.get("tag") == "markdown" and "```python" in el.get("content", ""):
                code_found = True
                break
        self.assertTrue(code_found, "Code block should be preserved")

    def test_split_headings_empty(self) -> None:
        """Test splitting empty content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings("")
        self.assertEqual(result, [{"tag": "markdown", "content": ""}])

    def test_split_headings_code_blocks_protected(self) -> None:
        """Test that code blocks are properly protected during heading split."""
        content = "Text before\n\n```\ncode block\n```\n\nText after"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        # Verify code blocks are preserved
        code_preserved = False
        for el in result:
            if el.get("tag") == "markdown" and "```" in el.get("content", ""):
                code_preserved = True
                break
        self.assertTrue(code_preserved)


class TestFeishuChannelChannelMethods(TestCase):
    """Tests for FeishuChannel async methods."""

    def test_send_no_client(self) -> None:
        """Test send method when client is not initialized."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = None
        msg = MagicMock()
        msg.content = "test"
        msg.media = []
        msg.chat_id = "oc_test"
        import asyncio
        asyncio.run(channel.send(msg))

    def test_send_empty_content_no_media(self) -> None:
        """Test send method with empty content and no media."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        msg = MagicMock()
        msg.content = ""
        msg.media = []
        msg.chat_id = "oc_test"
        import asyncio
        asyncio.run(channel.send(msg))

    def test_send_image_file_not_found(self) -> None:
        """Test send method with image file not found."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        msg = MagicMock()
        msg.content = "test"
        msg.media = ["/nonexistent/image.png"]
        msg.chat_id = "oc_test"
        import asyncio
        asyncio.run(channel.send(msg))

    def test_send_with_image_media(self) -> None:
        """Test send method with image media."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        msg = MagicMock()
        msg.content = "test"
        msg.media = ["/tmp/test.png"]
        msg.chat_id = "oc_test"
        import asyncio
        asyncio.run(channel.send(msg))

    def test_send_with_file_media(self) -> None:
        """Test send method with file media."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        msg = MagicMock()
        msg.content = "test"
        msg.media = ["/tmp/test.pdf"]
        msg.chat_id = "oc_test"
        import asyncio
        asyncio.run(channel.send(msg))

    def test_send_with_audio_media(self) -> None:
        """Test send method with audio media."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        msg = MagicMock()
        msg.content = "test"
        msg.media = ["/tmp/test.opus"]
        msg.chat_id = "oc_test"
        import asyncio
        asyncio.run(channel.send(msg))

    def test_stop_method(self) -> None:
        """Test stop method."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._ws_client = MagicMock()
        channel._running = True
        import asyncio
        asyncio.run(channel.stop())

    def test_stop_method_no_ws_client(self) -> None:
        """Test stop method when ws_client is None."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._ws_client = None
        channel._running = True
        import asyncio
        asyncio.run(channel.stop())

    def test_add_reaction_no_client(self) -> None:
        """Test add_reaction when client is None."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = None
        import asyncio
        asyncio.run(channel._add_reaction("msg123", "THUMBSUP"))

    def test_add_reaction_no_emoji(self) -> None:
        """Test add_reaction when Emoji is None."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        channel._add_reaction_sync = MagicMock()
        import asyncio
        asyncio.run(channel._add_reaction("msg123", "THUMBSUP"))

    def test_send_message_sync_failure(self) -> None:
        """Test _send_message_sync when request fails."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 400
        mock_response.msg = "Bad Request"
        mock_response.get_log_id.return_value = "log123"
        channel._client.im.v1.message.create.return_value = mock_response
        result = channel._send_message_sync("chat_id", "chat123", "text", "test")
        self.assertFalse(result)

    def test_send_message_sync_exception(self) -> None:
        """Test _send_message_sync when exception occurs."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        channel._client.im.v1.message.create.side_effect = Exception("Network error")
        result = channel._send_message_sync("chat_id", "chat123", "text", "test")
        self.assertFalse(result)

    def test_upload_image_sync_failure(self) -> None:
        """Test _upload_image_sync when request fails."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 400
        mock_response.msg = "Bad Request"
        channel._client.im.v1.image.create.return_value = mock_response
        result = channel._upload_image_sync("/tmp/test.png")
        self.assertIsNone(result)

    def test_upload_image_sync_exception(self) -> None:
        """Test _upload_image_sync when exception occurs."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        channel._client.im.v1.image.create.side_effect = Exception("Upload error")
        result = channel._upload_image_sync("/tmp/test.png")
        self.assertIsNone(result)

    def test_upload_file_sync_failure(self) -> None:
        """Test _upload_file_sync when request fails."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 400
        mock_response.msg = "Bad Request"
        channel._client.im.v1.file.create.return_value = mock_response
        result = channel._upload_file_sync("/tmp/test.pdf")
        self.assertIsNone(result)

    def test_upload_file_sync_exception(self) -> None:
        """Test _upload_file_sync when exception occurs."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        channel._client.im.v1.file.create.side_effect = Exception("Upload error")
        result = channel._upload_file_sync("/tmp/test.pdf")
        self.assertIsNone(result)

    def test_download_image_sync_failure(self) -> None:
        """Test _download_image_sync when request fails."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 400
        mock_response.msg = "Bad Request"
        channel._client.im.v1.message_resource.get.return_value = mock_response
        result = channel._download_image_sync("msg123", "img123")
        self.assertEqual(result, (None, None))

    def test_download_image_sync_exception(self) -> None:
        """Test _download_image_sync when exception occurs."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        channel._client.im.v1.message_resource.get.side_effect = Exception("Download error")
        result = channel._download_image_sync("msg123", "img123")
        self.assertEqual(result, (None, None))

    def test_download_file_sync_failure(self) -> None:
        """Test _download_file_sync when request fails."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 400
        mock_response.msg = "Bad Request"
        channel._client.im.v1.message_resource.get.return_value = mock_response
        result = channel._download_file_sync("msg123", "file123", "file")
        self.assertEqual(result, (None, None))

    def test_download_file_sync_exception(self) -> None:
        """Test _download_file_sync when exception occurs."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = MagicMock()
        channel._client.im.v1.message_resource.get.side_effect = Exception("Download error")
        result = channel._download_file_sync("msg123", "file123", "file")
        self.assertEqual(result, (None, None))

    def test_on_message_sync_with_loop(self) -> None:
        """Test _on_message_sync when loop is running."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._loop = MagicMock()
        channel._loop.is_running.return_value = True
        mock_data = MagicMock()
        channel._on_message = AsyncMock()
        channel._on_message_sync(mock_data)
        channel._loop.is_running.assert_called()

    def test_on_message_sync_without_loop(self) -> None:
        """Test _on_message_sync when loop is None."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._loop = None
        mock_data = MagicMock()
        channel._on_message_sync(mock_data)

    def test_on_message_deduplication(self) -> None:
        """Test _on_message message deduplication."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {"msg123": None}
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        # Should return early due to deduplication

    def test_on_message_skip_bot(self) -> None:
        """Test _on_message skips bot messages."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "bot"
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "text"
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))

    def test_on_message_text_content(self) -> None:
        """Test _on_message handles text content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        channel._handle_message = AsyncMock()
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "text"
        mock_message.content = '{"text": "Hello"}'
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        channel._handle_message.assert_called()

    def test_on_message_post_content(self) -> None:
        """Test _on_message handles post content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        channel._handle_message = AsyncMock()
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "post"
        mock_message.content = '{"title": "Test", "content": [[{"tag": "text", "text": "Body"}]]}'
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        channel._handle_message.assert_called()

    def test_on_message_image_content(self) -> None:
        """Test _on_message handles image content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        channel._handle_message = AsyncMock()
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "image"
        mock_message.content = '{"image_key": "img123"}'
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        channel._handle_message.assert_called()

    def test_on_message_share_chat_content(self) -> None:
        """Test _on_message handles share_chat content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        channel._handle_message = AsyncMock()
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "share_chat"
        mock_message.content = '{"chat_id": "shared123"}'
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        channel._handle_message.assert_called()

    def test_on_message_unknown_type(self) -> None:
        """Test _on_message handles unknown message type."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        channel._handle_message = AsyncMock()
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "unknown_type"
        mock_message.content = '{}'
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        channel._handle_message.assert_called()

    def test_on_message_empty_content_no_media(self) -> None:
        """Test _on_message returns early with empty content and no media."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        channel._handle_message = AsyncMock()
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "text"
        mock_message.content = '{}'
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))
        channel._handle_message.assert_not_called()

    def test_on_message_exception(self) -> None:
        """Test _on_message exception handling."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._processed_message_ids = {}
        mock_data = MagicMock()
        mock_event = MagicMock()
        mock_sender = MagicMock()
        mock_sender.sender_type = "user"
        mock_sender_id = MagicMock()
        mock_sender_id.open_id = "open123"
        mock_sender.sender_id = mock_sender_id
        mock_message = MagicMock()
        mock_message.message_id = "msg123"
        mock_message.chat_id = "chat123"
        mock_message.chat_type = "group"
        mock_message.message_type = "text"
        mock_message.content = None
        mock_event.sender = mock_sender
        mock_event.message = mock_message
        mock_data.event = mock_event
        import asyncio
        asyncio.run(channel._on_message(mock_data))


class TestFeishuChannelChannelMethodsExtra(TestCase):
    """Tests for FeishuChannel static and instance methods."""

    def test_parse_md_table_valid(self) -> None:
        """Test parsing a valid markdown table."""
        table_text = "| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        result = FeishuChannel._parse_md_table(table_text)
        self.assertIsNotNone(result)
        self.assertEqual(result["tag"], "table")
        self.assertEqual(len(result["columns"]), 2)
        self.assertEqual(result["columns"][0]["name"], "c0")
        self.assertEqual(result["columns"][0]["display_name"], "Header 1")
        self.assertEqual(len(result["rows"]), 1)

    def test_parse_md_table_minimal(self) -> None:
        """Test parsing minimal markdown table."""
        table_text = "| H1 |\n| --- |\n| C1 |"
        result = FeishuChannel._parse_md_table(table_text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["columns"]), 1)

    def test_parse_md_table_insufficient_rows(self) -> None:
        """Test parsing table with insufficient rows returns None."""
        table_text = "| Header 1 |\n| --- |"
        result = FeishuChannel._parse_md_table(table_text)
        self.assertIsNone(result)

    def test_parse_md_table_empty(self) -> None:
        """Test parsing empty table returns None."""
        result = FeishuChannel._parse_md_table("")
        self.assertIsNone(result)

    def test_parse_md_table_whitespace_only(self) -> None:
        """Test parsing whitespace-only table returns None."""
        result = FeishuChannel._parse_md_table("   \n   ")
        self.assertIsNone(result)

    def test_build_card_elements_with_table(self) -> None:
        """Test building card elements with markdown table."""
        content = "Before table\n\n| H1 | H2 |\n| --- | --- |\n| C1 | C2 |\n\nAfter table"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._build_card_elements(content)
        self.assertIsNotNone(result)
        # Should have markdown before, table, and markdown after
        self.assertTrue(len(result) >= 3)

    def test_build_card_elements_no_table(self) -> None:
        """Test building card elements without table."""
        content = "Just text\n\n## Heading\n\nMore text"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._build_card_elements(content)
        self.assertIsNotNone(result)

    def test_build_card_elements_empty(self) -> None:
        """Test building card elements from empty content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._build_card_elements("")
        self.assertEqual(result, [{"tag": "markdown", "content": ""}])

    def test_split_headings_with_markdown(self) -> None:
        """Test splitting content with headings."""
        content = "# Heading 1\n\nContent\n\n## Heading 2\n\nMore content"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        self.assertIsNotNone(result)
        # Should have div for H1, markdown content, div for H2, markdown content
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["tag"], "div")
        self.assertEqual(result[1]["tag"], "markdown")
        self.assertEqual(result[2]["tag"], "div")
        self.assertEqual(result[3]["tag"], "markdown")

    def test_split_headings_no_headings(self) -> None:
        """Test splitting content without headings."""
        content = "Just plain text\n\nWith multiple lines"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        self.assertEqual(result, [{"tag": "markdown", "content": content}])

    def test_split_headings_with_code_block(self) -> None:
        """Test splitting content with code blocks preserved."""
        content = "# Heading\n\n```python\nprint('hello')\n```\n\nMore text"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        self.assertIsNotNone(result)
        # Find the markdown element and check code block is preserved
        code_found = False
        for el in result:
            if el.get("tag") == "markdown" and "```python" in el.get("content", ""):
                code_found = True
                break
        self.assertTrue(code_found, "Code block should be preserved")

    def test_split_headings_empty(self) -> None:
        """Test splitting empty content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings("")
        self.assertEqual(result, [{"tag": "markdown", "content": ""}])

    def test_split_headings_code_blocks_protected(self) -> None:
        """Test that code blocks are properly protected during heading split."""
        content = "Text before\n\n```\ncode block\n```\n\nText after"
        channel = FeishuChannel(MagicMock(), MagicMock())
        result = channel._split_headings(content)
        # Verify code blocks are preserved
        code_preserved = False
        for el in result:
            if el.get("tag") == "markdown" and "```" in el.get("content", ""):
                code_preserved = True
                break
        self.assertTrue(code_preserved)


class TestFeishuChannelSend(IsolatedAsyncioTestCase):
    """Tests for FeishuChannel send functionality."""

    async def test_send_with_image_media(self) -> None:
        """Test sending message with image media."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.return_value = ("path", ".png")
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.image.create.return_value.success.return_value = True
            channel._client.im.v1.image.create.return_value.data.image_key = "image_key_123"
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/image.png"],
            )
            await channel.send(msg)

    async def test_send_with_file_media(self) -> None:
        """Test sending message with file media."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.return_value = ("path", ".pdf")
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.file.create.return_value.success.return_value = True
            channel._client.im.v1.file.create.return_value.data.file_key = "file_key_123"
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/file.pdf"],
            )
            await channel.send(msg)

    async def test_send_with_audio_media(self) -> None:
        """Test sending message with audio media (opus)."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.return_value = ("path", ".opus")
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.file.create.return_value.success.return_value = True
            channel._client.im.v1.file.create.return_value.data.file_key = "file_key_456"
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/audio.opus"],
            )
            await channel.send(msg)

    async def test_send_with_media_file_not_found(self) -> None:
        """Test sending message when media file is not found."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=False):
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/nonexistent.png"],
            )
            await channel.send(msg)

    async def test_send_without_client(self) -> None:
        """Test sending message when client is not initialized."""
        from nanobot.bus.events import OutboundMessage

        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = None

        msg = OutboundMessage(
            channel="feishu",
            chat_id="oc_123",
            content="Test message",
        )
        await channel.send(msg)

    async def test_send_with_content_only(self) -> None:
        """Test sending message with content only (no media)."""
        from nanobot.bus.events import OutboundMessage

        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message.create.return_value.success.return_value = True

        msg = OutboundMessage(
            channel="feishu",
            chat_id="oc_123",
            content="Test message content",
            media=[],
        )
        await channel.send(msg)

    async def test_send_with_multiple_media(self) -> None:
        """Test sending message with multiple media files."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.side_effect = [("/path", ".png"), ("/path", ".pdf")]
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.image.create.return_value.success.return_value = True
            channel._client.im.v1.image.create.return_value.data.image_key = "image_key_123"
            channel._client.im.v1.file.create.return_value.success.return_value = True
            channel._client.im.v1.file.create.return_value.data.file_key = "file_key_456"
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/image.png", "/path/to/file.pdf"],
            )
            await channel.send(msg)

    async def test_send_with_image_upload_failure(self) -> None:
        """Test sending message when image upload fails."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.return_value = ("path", ".png")
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.image.create.return_value.success.return_value = False
            channel._client.im.v1.image.create.return_value.code = 400
            channel._client.im.v1.image.create.return_value.msg = "Upload failed"
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/image.png"],
            )
            await channel.send(msg)

    async def test_send_with_file_upload_failure(self) -> None:
        """Test sending message when file upload fails."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.return_value = ("path", ".pdf")
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.file.create.return_value.success.return_value = False
            channel._client.im.v1.file.create.return_value.code = 400
            channel._client.im.v1.file.create.return_value.msg = "Upload failed"
            channel._client.im.v1.message.create.return_value.success.return_value = True

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/file.pdf"],
            )
            await channel.send(msg)

    async def test_send_with_message_send_failure(self) -> None:
        """Test sending message when message send fails."""
        from nanobot.bus.events import OutboundMessage

        with patch("os.path.isfile", return_value=True), patch("os.path.splitext") as mock_split:
            mock_split.return_value = ("path", ".png")
            channel = FeishuChannel(MagicMock(), MagicMock())
            channel._client = mock_lark.Client.return_value
            channel._client.im.v1.image.create.return_value.success.return_value = True
            channel._client.im.v1.image.create.return_value.data.image_key = "image_key_123"
            channel._client.im.v1.message.create.return_value.success.return_value = False
            channel._client.im.v1.message.create.return_value.code = 400
            channel._client.im.v1.message.create.return_value.msg = "Send failed"

            msg = OutboundMessage(
                channel="feishu",
                chat_id="oc_123",
                content="Test message",
                media=["/path/to/image.png"],
            )
            await channel.send(msg)


class TestFeishuChannelMessageHandling(IsolatedAsyncioTestCase):
    """Tests for FeishuChannel message handling (_on_message)."""

    async def test_on_message_text_content(self) -> None:
        """Test handling incoming text message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"text": "Hello World"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "text"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_post_content(self) -> None:
        """Test handling incoming post message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({
            "title": "Post Title",
            "content": [[{"tag": "text", "text": "Post content"}]],
        })
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "post"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_image_content(self) -> None:
        """Test handling incoming image message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True
        channel._client.im.v1.message_resource.get.return_value.success.return_value = True
        channel._client.im.v1.message_resource.get.return_value.file = MagicMock()
        channel._client.im.v1.message_resource.get.return_value.file.read.return_value = b"image_data"
        channel._client.im.v1.message_resource.get.return_value.file_name = "image_key_123.png"

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"image_key": "image_key_123"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "image"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_share_chat_content(self) -> None:
        """Test handling incoming share_chat message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"chat_id": "shared_chat_123"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "share_chat"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_share_user_content(self) -> None:
        """Test handling incoming share_user message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"user_id": "shared_user_123"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "share_user"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_interactive_content(self) -> None:
        """Test handling incoming interactive message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({
            "title": "Interactive Card",
            "elements": [{"tag": "markdown", "content": "Card content"}],
        })
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "interactive"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_audio_content(self) -> None:
        """Test handling incoming audio message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True
        channel._client.im.v1.message_resource.get.return_value.success.return_value = True
        channel._client.im.v1.message_resource.get.return_value.file = MagicMock()
        channel._client.im.v1.message_resource.get.return_value.file.read.return_value = b"audio_data"
        channel._client.im.v1.message_resource.get.return_value.file_name = "file_key_123.opus"

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"file_key": "file_key_123"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "audio"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_file_content(self) -> None:
        """Test handling incoming file message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True
        channel._client.im.v1.message_resource.get.return_value.success.return_value = True
        channel._client.im.v1.message_resource.get.return_value.file = MagicMock()
        channel._client.im.v1.message_resource.get.return_value.file.read.return_value = b"file_data"
        channel._client.im.v1.message_resource.get.return_value.file_name = "file_key_123.pdf"

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"file_key": "file_key_123"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "file"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_merge_forward_content(self) -> None:
        """Test handling incoming merge_forward message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "merge_forward"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_system_content(self) -> None:
        """Test handling incoming system message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "system"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_share_calendar_event_content(self) -> None:
        """Test handling incoming share_calendar_event message."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"event_key": "event_123"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "share_calendar_event"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_deduplication(self) -> None:
        """Test message deduplication."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"text": "First"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "text"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        # First call should process
        await channel._on_message(data)

        # Second call with same message_id should be skipped
        await channel._on_message(data)

    async def test_on_message_bot_message(self) -> None:
        """Test that bot messages are skipped."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"text": "Bot message"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "text"
        event.sender = MagicMock()
        event.sender.sender_type = "bot"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "bot_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_empty_content(self) -> None:
        """Test handling message with empty content."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = ""
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "text"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_unknown_message_type(self) -> None:
        """Test handling unknown message type."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "unknown_type"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)

    async def test_on_message_user_open_id(self) -> None:
        """Test handling message with user open_id (not oc_ prefix)."""
        channel = FeishuChannel(MagicMock(), MagicMock())
        channel._client = mock_lark.Client.return_value
        channel._client.im.v1.message_reaction.create.return_value.success.return_value = True
        channel._client.im.v1.message.create.return_value.success.return_value = True

        message_id = "msg_123"
        event = MagicMock()
        event.message = MagicMock()
        event.message.message_id = message_id
        event.message.content = json.dumps({"text": "Hello"})
        event.message.chat_id = "chat_123"
        event.message.chat_type = "group"
        event.message.message_type = "text"
        event.sender = MagicMock()
        event.sender.sender_type = "user"
        event.sender.sender_id = MagicMock()
        event.sender.sender_id.open_id = "user_456"

        data = MagicMock()
        data.event = event

        await channel._on_message(data)


if __name__ == "__main__":
    unittest.main()
