# Navigation editor (RC19)

The organizer has one pencil per slide. It opens one raised popover with a list name and show section/topic, followed by apply, cancel and restore-original icons. There is no duplicate preview line. Lists/cards do not expand; the popover works above docked and modal organizers. Labels are plain text, never interpreted as HTML.

- Apply or Enter in an input commits all available fields. Enter on a button activates that button; Escape cancels only the popover. Outside click, organizer scroll and resize dismiss uncommitted input.
- The list name updates the sidebar, organizer/search, progress label and journal. It does not edit body headings or the show context.
- The show section/topic update canonical presentation and static-export metadata for the selected slide. Empty show fields are allowed; no orphan separator remains. Counter and header mode remain automatic/existing. Fields are disabled when that slide's header is hidden or number-only.
- Restore returns all three generated values. It does not re-extract source wording, change another slide's section or restore the whole deck. Global reset returns the opened file's state.
- Pending input is committed on explicit save while the popover is still active; outside-click dismissal remains cancellation. Apply before switching windows when the edit should be kept.

## Stored state and project rebuilds

Project fields are optional and backwards-compatible:

```json
{
  "id":"s2",
  "navigationLabelOverride":"Short list name",
  "showNavigationOverride":{"section":"Section","topic":"Specific context"}
}
```

The builder validates lengths/types, normalizes whitespace and applies explicit manual values **after** automatic heading/section deduplication. This preserves human intent while retaining generated defaults for restore. The browser stores overrides by stable slide ID in work/bundle HTML and local drafts. Work retains excluded records; bundle contains only chosen slides. Resetting or clearing history does not erase committed values in a saved file.

After browser edits, use the saved **work** HTML as the authoritative source. Synchronize before authoring/rebuilding:

```sh
node scripts/reconcile_edits.mjs Baseline.html Saved_Work.html project/deck.json project/next.json
python3 scripts/build.py project/next.json Rebuilt.html --theme project/theme.json
```

Reconciliation compares baseline, saved and current project values per slide and per field. An independent field can merge; a conflicting edit to the same field or changed generated default is rejected without writing a project. Repeating the merge is safe. Work serialization allows the checker to inspect detached/excluded source slides too. A bundle omits excluded content and is not a substitute for the full saved work/project.

```sh
python3 scripts/test_navigation_overrides.py
node scripts/test_navigation_editor.mjs EMPTY_QA_DIRECTORY
```

The browser regression uses three small authored slides and checks keyboard/cancel, source preservation, excluded records, local drafts, real work/bundle saves, show/export, three-way merge/rebuild, conflicts, independent fields and restoration. This is not broad arbitrary-deck or native PowerPoint qualification. For a new real deck still run normal delivery/source/layout QA.
