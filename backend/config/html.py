"""Allowlist HTML sanitiser for rich-text fields.

Rich text produced by the admin editor is stored as HTML, so it has to be
filtered before it reaches the database: the API is the only write path but it
is authenticated, not admin-only. Only the tags and attributes below survive;
everything else (scripts, styles, iframes, event handlers, javascript: URLs)
is dropped. Implemented on the standard library so no extra dependency is
needed.
"""
import re
from html.parser import HTMLParser

ALLOWED_TAGS = {
    'p', 'br', 'div', 'span', 'b', 'strong', 'i', 'em', 'u', 's', 'strike',
    'sup', 'sub', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
    'blockquote', 'pre', 'code', 'hr', 'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
}

ALLOWED_ATTRS = {
    'a': {'href', 'target', 'rel'},
    'img': {'src', 'alt', 'width', 'height'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan', 'scope'},
}

# Inline style properties an author is allowed to set: font, size, colour and
# alignment. Anything else (position, z-index, url() backgrounds) is dropped.
ALLOWED_STYLE_PROPS = {
    'color', 'background-color',
    'font-family', 'font-size', 'font-weight', 'font-style', 'font-variant',
    'text-align', 'text-decoration', 'text-decoration-line', 'text-indent',
    'text-transform', 'letter-spacing', 'line-height',
    'margin-left', 'margin-right',
}

ALIGN_VALUES = {
    'left': 'left', 'center': 'center', 'centre': 'center',
    'right': 'right', 'justify': 'justify',
}

VOID_TAGS = {'br', 'hr', 'img'}

DROP_CONTENT_TAGS = {'script', 'style', 'iframe', 'object', 'embed', 'noscript'}

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_DATA_IMAGE = re.compile(r'^data:image/(png|jpe?g|gif|webp);base64,[a-z0-9+/=]+$', re.I)
_ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*(?:=\s*("[^"]*"|\'[^\']*\'|[^\s"\'>]+))?')
_STYLE_PROP_RE = re.compile(r'^-?[a-z][a-z0-9-]*$')
_UNSAFE_STYLE_RE = re.compile(r'url\s*\(|expression\s*\(|javascript:|@import|[<>\\;{}]', re.I)


def _is_safe_url(value, allow_data_image=False):
    url = _CONTROL_CHARS.sub('', value).strip()
    url = re.sub(r'\s+', '', url)
    if not url:
        return False
    if re.match(r'^(https?:|mailto:|tel:)', url, re.I):
        return True
    if re.match(r'(^/|^#|^\./|^\.\./)', url):
        return True
    if allow_data_image and _DATA_IMAGE.match(url):
        return True
    return False


def _escape_attr(value):
    return (
        value.replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def _sanitize_style(value):
    """Keep only allowlisted declarations, dropping the rest of the block."""
    kept = []
    for declaration in value.split(';'):
        prop, sep, val = declaration.partition(':')
        if not sep:
            continue
        prop = prop.strip().lower()
        val = val.strip()
        if not _STYLE_PROP_RE.match(prop) or prop not in ALLOWED_STYLE_PROPS:
            continue
        if not val or _UNSAFE_STYLE_RE.search(val):
            continue
        kept.append('%s: %s' % (prop, val))
    return '; '.join(kept)


class _Sanitiser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.skip_depth = 0
        self.skip_tag = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.skip_depth:
            if tag == self.skip_tag:
                self.skip_depth += 1
            return
        if tag in DROP_CONTENT_TAGS:
            self.skip_tag = tag
            self.skip_depth = 1
            return
        if tag not in ALLOWED_TAGS:
            return

        allowed = ALLOWED_ATTRS.get(tag, set())
        rendered = []
        for name, value in attrs:
            name = name.lower()
            if name == 'style':
                # Inline styles carry the author's font, size, colour and alignment.
                style = _sanitize_style(value or '')
                if style:
                    rendered.append('style="%s"' % _escape_attr(style))
                continue
            if name == 'align':
                # Word and older editors write align="center" instead of a style.
                text_align = ALIGN_VALUES.get((value or '').strip().lower())
                if text_align:
                    rendered.append('style="text-align: %s"' % text_align)
                continue
            if name not in allowed:
                continue
            if name in ('href', 'src'):
                if not value or not _is_safe_url(value, name == 'src'):
                    continue
                rendered.append('%s="%s"' % (name, _escape_attr(value)))
            elif name == 'target':
                rendered.append('target="_blank"')
            elif name == 'rel':
                rendered.append('rel="noopener noreferrer"')
            else:
                rendered.append('%s="%s"' % (name, _escape_attr(value or '')))

        attr_text = (' ' + ' '.join(rendered)) if rendered else ''
        self.parts.append('<%s%s>' % (tag, attr_text))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self.skip_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            self.handle_starttag(tag, attrs)
            return
        self.handle_starttag(tag, attrs)
        self.parts.append('</%s>' % tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip_depth:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if not self.skip_depth:
                    self.skip_tag = None
            return
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.parts.append('</%s>' % tag)

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.parts.append(
            data.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        )

    def handle_entityref(self, name):
        if not self.skip_depth:
            self.parts.append('&%s;' % name)

    def handle_charref(self, name):
        if not self.skip_depth:
            self.parts.append('&#%s;' % name)

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        pass

    def handle_pi(self, data):
        pass

    def unknown_decl(self, data):
        pass

    def result(self):
        return ''.join(self.parts)


def sanitize_html(value):
    """Return `value` with every tag outside the allowlist removed."""
    if not value:
        return ''
    if '<' not in value and '&' not in value:
        return value
    parser = _Sanitiser()
    parser.feed(value)
    parser.close()
    return parser.result()
