# Keyboard commands

Viewing: arrows, PageUp/PageDown, Space/Enter, Home/End. HID clickers emitting PageUp/PageDown or arrows follow this path; physical hardware compatibility must be checked separately. Exercise rapid presses and reversal.

Outside typing/showing: E editor, F showing, G slide number, S save form, O organizer, J journal, C screen controls, T theme (only with two themes), N slide list, M animation. M also works during showing; N stays in reading. Other tool panels must not open during showing. Cmd/Ctrl+S commits editing and opens the existing save form without silent submission/download.

Route commands through the existing button handlers; include tooltip labels and aria-keyshortcuts. Do not add duplicate buttons or help panels. Use physical KeyboardEvent.code for letters across language layouts. Ordinary letters, including N/M, must remain typing in inputs, contenteditable, search and media controls. Preserve undo/redo/browser combinations, block tools behind forms, ignore repeat and IME composition.

Escape closes screen controls before a workspace, and exits showing/editing as before. Closing windows/forms, including native Escape/cancel, returns focus synchronously to the toolbar trigger via closeWindow. A hidden focused input must not suppress the next command.

The default demo's slide 03 and navigation topic are «Хоткеи», including N and M. Separate unrelated topics and keep paragraphs readable rather than shrinking all text. Run `check_shortcuts.mjs` on the bundled demo when bindings or focus guards change, not for every content edit. It checks M during showing and N/M typing protection as well as navigation and other bindings.
