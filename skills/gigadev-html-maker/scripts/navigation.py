"""Resolve reviewed slide sections and non-redundant navigation without editing slide copy."""
import re
import unicodedata
from html.parser import HTMLParser


class Heading(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.done = False
        self.parts = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if not self.done and tag in ('h1', 'h2'):
            self.active = True
        if self.active and tag == 'br':
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if self.active and tag in ('h1', 'h2'):
            self.active = False
            self.done = True

    def handle_data(self, value):
        if self.active:
            self.parts.append(value)


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def normalize_prefix(value, slide):
    value = clean(value)
    slash = re.match(r'^\d{1,2}\s*/\s*(.+)$', value)
    prefix = re.match(r'^(\d{1,3})\s*[.·:)—-]\s*(.+)$', value)
    if slash:
        return slash.group(1).strip()
    if prefix and slide.get('sourceNumber') and int(prefix.group(1)) == int(slide['sourceNumber']):
        return prefix.group(2).strip()
    return value


def equivalent(first, second):
    # Typography and case are cosmetic. Words and numerical values remain significant.
    def key(value):
        return tuple(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', clean(value)).casefold().replace('ё', 'е')))
    return bool(key(first)) and key(first) == key(second)


def resolve(slides):
    current = ''
    origin = None
    result = {}
    for index, slide in enumerate(slides):
        for field in ('navigationLabel', 'navigationTopic', 'navigationSection', 'section'):
            if field in slide and not isinstance(slide[field], str):
                raise ValueError(f'{field} must be a string on {slide["id"]}')
        role = slide.get('navigationRole', 'divider' if slide.get('composition', {}).get('id') == 'divider' else 'content')
        if role not in ('content', 'divider'):
            raise ValueError(f'Invalid navigationRole on {slide["id"]}')
        parsed = Heading(slide.get('html', ''))
        title = normalize_prefix(''.join(parsed.parts) or slide.get('title') or slide.get('label'), slide)
        if role == 'divider':
            current = clean(slide.get('navigationSection', slide.get('section') or title))
            if not current:
                raise ValueError(f'Divider requires a section title on {slide["id"]}')
            origin = slide['id']
        section = clean(slide['navigationSection']) if 'navigationSection' in slide else clean(slide.get('section')) or current
        topic = clean(slide['navigationTopic']) if 'navigationTopic' in slide else normalize_prefix(slide.get('topic') or slide.get('label') or title, slide)
        removed = []
        if equivalent(topic, title):
            topic = ''
            removed.append('topic-repeats-heading')
        if equivalent(section, title):
            header_section = ''
            removed.append('section-repeats-heading')
        else:
            header_section = section
        if equivalent(header_section, topic):
            topic = ''
            removed.append('topic-repeats-section')
        label = clean(slide.get('navigationLabel')) or normalize_prefix(slide.get('label') or slide.get('topic') or title, slide) or f'Слайд {index + 1}'
        result[slide['id']] = {'section': header_section, 'navigationSection': section, 'topic': topic, 'label': label,
                               'role': role, 'sectionSourceId': origin if current and section == current else None,
                               'removedDuplicates': removed}
    return result
