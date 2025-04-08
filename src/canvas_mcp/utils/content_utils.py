"""
Utilities for content detection and processing.
"""


def detect_content_type(content: str | None) -> str:
    """
    Detect the content type from the given content string.

    Args:
        content: The content string to analyze

    Returns:
        String indicating the content type ('html', 'pdf_link', 'external_link', 'json', etc.)
    """
    if not content or not isinstance(content, str):
        return "html"  # Default for empty content

    # Strip whitespace for easier checks
    stripped_content = content.strip()
    content_lower = stripped_content.lower()

    # Check for empty content first
    if stripped_content in ["<p></p>", "<div></div>", ""]:
        return "empty"

    # Check for PDF links
    if ".pdf" in content_lower and (
        "<a href=" in content_lower or "src=" in content_lower
    ):
        return "pdf_link"

    # Check for external links (simple URLs with minimal formatting)
    if (
        content_lower.startswith("http://")
        or content_lower.startswith("https://")
        or (
            ("http://" in content or "https://" in content)
            and len(stripped_content) < 1000
            and content.count(" ") < 10
        )
    ):
        return "external_link"

    # Check for JSON content
    if stripped_content.startswith("{") and stripped_content.endswith("}"):
        try:
            import json

            json.loads(stripped_content)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass  # Not valid JSON

    # Check for XML/HTML content
    if (stripped_content.startswith("<") and stripped_content.endswith(">")) or (
        "<html" in content_lower or "<body" in content_lower or "<div" in content_lower
    ):
        return "html"

    # Default to HTML for anything else
    return "html"
