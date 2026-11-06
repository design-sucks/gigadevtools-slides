# RC16 — section-aware navigation without heading duplication

An author-reviewed navigationRole: divider (or explicit divider composition) supplies the following section from its visible heading. Full section membership stays in metadata; the top breadcrumb omits heading duplicates, and empty topics stay empty through runtime/save/export. Distinct reviewed context remains. Sidebar labels remain usable and accept concise author-written navigationLabel. Source title/body/labels are not rewritten by this resolver.

Section metadata resolves in deck.slides source order and stays bound to stable IDs during reorder or excluding a divider. Automatic speculative divider classification and semantic summarization are not performed: the authoring agent reviews actual source slides and marks dividers during preparation. Existing prebuilt HTML requires rebuilding with the reviewed metadata to adopt the change.

Qualified by nine resolver tests and one local five-slide trial covering two section dividers, duplicate removal, distinct topic, short sidebar label, unchanged body, presentation/export, save/reopen, reorder and exclusion. Standard shell check15/15 passed. Large deck and native PowerPoint runs were not repeated. RC15 inactive navigation transparency and one-theme behavior remain unchanged.
