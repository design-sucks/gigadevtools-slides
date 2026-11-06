"""Map observed PPTX list levels to valid HTML list nesting without phantom items."""


def normalize_list_levels(paragraphs, kind_of):
    """Return per-paragraph (zero-based depth, opens-list), or None for non-list text.

    Source levels are relative evidence, not required absolute HTML nesting: the first
    observed level is the root; a later deeper level nests under the preceding item.
    Missing intermediate levels are not represented by fabricated list items.
    """
    stack = []  # observed source level and list kind for each real HTML container
    result = []
    for paragraph in paragraphs:
        kind = kind_of(paragraph)
        if kind not in ('ul', 'ol'):
            stack.clear()
            result.append(None)
            continue
        level = paragraph.get('level', 0)
        if not isinstance(level, int) or level < 0:
            level = 0
        while stack and stack[-1][0] > level:
            stack.pop()
        opens = not stack or stack[-1][0] != level or stack[-1][1] != kind
        if opens:
            if stack and stack[-1][0] == level:
                stack.pop()
            stack.append((level, kind))
        result.append((len(stack) - 1, opens))
    return result
