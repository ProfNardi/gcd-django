from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from django import template
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()

ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}
VOID_TAGS = {"br", "hr"}


def _safe_href(value):
    value = value.strip()
    if any(ord(char) < 32 for char in value):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return not parsed.scheme or parsed.scheme.lower() in {"http", "https", "mailto"}


class MarkdownSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        rendered_attrs = []
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value and _safe_href(value):
                    rendered_attrs.append(f'href="{escape(value, quote=True)}"')
                elif name == "title" and value:
                    rendered_attrs.append(f'title="{escape(value, quote=True)}"')
            rendered_attrs.extend(['rel="nofollow ugc noopener"', 'target="_blank"'])
        suffix = f" {' '.join(rendered_attrs)}" if rendered_attrs else ""
        self.output.append(f"<{tag}{suffix}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        self.output.append(escape(data))


@register.filter
def safe_markdown(value):
    """Render Markdown and allow only a small, safe subset of generated HTML."""
    sanitizer = MarkdownSanitizer()
    sanitizer.feed(str(markdownify(escape(value or ""))))
    sanitizer.close()
    return mark_safe("".join(sanitizer.output))


@register.filter
def reply_count(post_count):
    try:
        return max(int(post_count) - 1, 0)
    except (TypeError, ValueError):
        return 0


@register.filter
def tag_classes(color_code):
    # Literal utilities are discoverable by Tailwind; never interpolate CSS.
    return {
        "#4F46E5": "bg-indigo-100 text-indigo-800",
        "#059669": "bg-emerald-100 text-emerald-800",
        "#D97706": "bg-amber-100 text-amber-800",
        "#DC2626": "bg-red-100 text-red-800",
    }.get(str(color_code).upper(), "bg-slate-100 text-slate-700")
