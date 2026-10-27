# Style references

Separate shell UI from slide styling. assets/ui.css and the controller are reusable product behavior; theme JSON and slide.html define the deck's visual system. Do not copy the full source SalesKit CSS/media into every new deck.

Best input: a filled PPTX design reference with a cover, section divider, dense text, table, data chart and image slide. A POTX can provide theme/master/layout evidence, but may not show real compositions. HTML references reveal CSS and components; images give approximate visual direction. Request exact font files only if needed for fidelity and portability.

Compile a small theme JSON: name, themes (['dark'] / ['light'] / ['dark','light']), primary, font CSS stack, colors by available theme (bg/ink/muted/accent/line in #RRGGBB), optional fonts [{family,weight,path}] and css. The file can sit anywhere; asset/font paths resolve relative to the deck project. A one-theme style must not expose an unusable theme switch. Screen calibration operates the five semantic palette tokens; custom hard-coded SVG/CSS colors do not automatically inherit it.

A full style also needs layout choices in slide.html: grids, text scale, white space, framing, image treatment and graphical language. Changing color tokens alone is not a new style. Store those choices in a short project-specific style guide, not in shell JS. Dense material needs a reading-first composition; do not default every slide to a three-card grid.

Show representative slides before propagating a genuinely new style. Preserve facts and supplied wording. Do not add decorative charts with invented data. Keep the existing v25 transition as the baseline; additional choreography is a separate requested pass. Validate static final states before motion.

Default typography is embedded SB Sans Text Regular/Semibold for UI/body and SB Sans Display Regular/Semibold for headings. theme.font changes body; theme.displayFont changes headings (falling back to an explicitly supplied body font for other styles). Set builtinFonts:false to omit the bundled SB pack; supply authorized project font files as needed. Custom fonts with the same family/weight replace their bundled declaration. Original binary metadata is preserved; default source hashes/glyph counts/fsType are in assets/fonts/manifest.json.

Default dark colors match the source v25 computed fills: one continuous bg/shell #050709 across the whole presentation. A supplied style can override both; omitted shell falls back to that style bg. The navigation rail is transparent, with no separate sidebar panel. Its selection fits the active row, including padding, after fonts load and on navigation/reorder/resize. Keep clear hover/current/focus states.

## UI accent and selection roles

The shell uses mint --sk-accent (#9deda5) as a fill in both themes. --sk-on-accent is dark ink (#173923). In the light theme, --sk-accent-text (#2d6b44) supplies readable green accent text and thin indicators; never put the pale mint fill color into small text on white. Neutral --sk-selected-fill/--sk-selected-ink identify selected mode controls by fill contrast. --sk-focus-ring is reserved for keyboard focus; do not add persistent selection strokes. Checkbox and radio states share size, stroke and palette; Composition cards remain neutral; the marked radio identifies their state. Keep non-accent surfaces and hovers grayscale. Empty checkbox/radio boundaries and keyboard focus indicators are functional exceptions to the no-decorative-stroke rule.

Window placement uses an icon toolbar, with four-corner maximize glyphs. Card layout uses named List/Tile segments. Keep their roles visually distinct. For changes to UI colors or states, run scripts/check_ui_contrast.mjs against a generated Maker HTML and a new QA directory. It measures enabled button text/icons and selected-state boundaries in normal/hover/keyboard-focus states for the journal/organizer shell; it does not certify an entire document's accessibility. Inspect real screenshots as well.

Stateful mode switches change ink and fill together without color interpolation; transient interpolation can erase selected-state contrast. Keep slide motion independent.

The neutral default light slide style also uses achromatic background, primary/secondary ink and dividers; green belongs to the accent token. Preserve explicitly supplied brand styles rather than recoloring reference decks automatically.
