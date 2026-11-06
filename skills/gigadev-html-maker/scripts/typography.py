"""Conservative Russian typography for plain, source-bound slide text."""
import html
import re
from html.parser import HTMLParser

CYR = 'А-Яа-яЁё'
QUOTE = re.compile(r'(?<![\w/])"([' + CYR + r'][' + CYR + r' ,.!?:;]*[' + CYR + r'.!?]|[' + CYR + r'])"(?![\w/])')
DASH = re.compile(r'(?<=[' + CYR + r'»]) +[-–] +(?=(?:это|значит|вот)\b)', re.I)
DASH_SPACING = re.compile(r'(?<=[' + CYR + r'»]) +— +(?=(?:это|значит|вот)\b)', re.I)
SPACES = re.compile(r'(?<=[' + CYR + r'»]) {2,}(?=[' + CYR + r'])')
BEFORE_PUNCT = re.compile(r'([A-Za-zА-Яа-яЁё»]) +([,;:!?\.])(?=\s|$)')
PROTECTED_TEXT = re.compile(r'(?:[a-z]+://|www\.|\S+@\S+|[<>/\\`_={}\[\]])', re.I)

BLOCKS = {'p', 'h1', 'h2', 'h3', 'h4', 'li', 'figcaption', 'blockquote'}
PROTECTED_TAGS = {'a', 'code', 'pre', 'kbd', 'samp', 'script', 'style', 'svg', 'math', 'textarea'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


def normalize(text):
    if PROTECTED_TEXT.search(text):
        return text
    text = QUOTE.sub(r'«\1»', text)
    text = DASH.sub(' — ', text)
    text = DASH_SPACING.sub(' — ', text)
    text = SPACES.sub(' ', text)
    text = BEFORE_PUNCT.sub(r'\1\2', text)
    return re.sub(r'(?<![\w])([ВвКкСсУуОоИиАа]) (?=[А-Яа-яЁё])', r'\1' + '\u00a0', text)


class PlainBlocks(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.line_offsets = [0] + [m.end() for m in re.finditer('\n', markup)]
        self.stack = []
        self.targets = []
        self.feed(markup)
        self.close()

    def source_position(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        inherited = self.stack[-1][1] if self.stack else False
        lang = attrs.get('lang') or 'ru'
        protected = inherited or tag in PROTECTED_TAGS or attrs.get('data-gd-typography') == 'off' or lang.lower().split('-')[0] != 'ru'
        if tag not in VOID:
            source = attrs.get('data-source-id') if tag in BLOCKS and not protected else None
            self.stack.append((tag, protected, source, self.source_position() + len(self.get_starttag_text())))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            name, _, source, start = self.stack[index]
            if tag == name:
                if source and index == len(self.stack) - 1:
                    self.targets.append((source, start, self.source_position()))
                del self.stack[index:]
                break


def prepare(markup, excluded, apply, include=None):
    changes = []
    replacements = []
    for source, start, end in PlainBlocks(markup).targets:
        raw = markup[start:end]
        if source in excluded or (include is not None and source not in include) or '\n' in raw or '\r' in raw:
            continue
        parts = re.split(r'(<[^>]*>)', raw)
        if any(not re.fullmatch(r'</?(?:strong|em|b|i|span)(?:\s+[^<>]*)?/?>', part, re.I) for part in parts[1::2]):
            continue
        before = ''.join(html.unescape(part) for part in parts[::2])
        normalized = [html.escape(normalize(html.unescape(part)), quote=False) if index % 2 == 0 else part for index, part in enumerate(parts)]
        after = ''.join(html.unescape(part) for part in normalized[::2])
        if before == after:
            continue
        changes.append({'sourceId': source, 'before': before, 'after': after})
        replacements.append((start, end, ''.join(normalized)))
    if apply:
        for start, end, value in reversed(replacements):
            markup = markup[:start] + value + markup[end:]
    return markup, changes
