-- Mac only. Caller supplies an exact QA-copy path and a NEW PDF output path.
-- No operation is addressed to the active/frontmost presentation.
on exactDeck(deckPath)
 tell application "Microsoft PowerPoint"
  set matchedDecks to {}
  repeat with presentationRef in (get presentations)
   if (get full name of presentationRef) is deckPath then set matchedDecks to matchedDecks & {contents of presentationRef}
  end repeat
  if (count of matchedDecks) > 1 then error "Ambiguous QA-copy identity; no export performed"
  if (count of matchedDecks) is 1 then return item 1 of matchedDecks
 end tell
 return missing value
end exactDeck
on assertPath(targetDeck, deckPath)
 tell application "Microsoft PowerPoint"
  if (get full name of targetDeck) is not deckPath then error "QA-copy path changed; stopping without save/close"
 end tell
end assertPath
on run argv
 if (count of argv) < 2 then error "Usage: osascript native_export.applescript ABS_QA_COPY.pptx ABS_NEW_PROOF.pdf [close]"
 set deckPath to item 1 of argv
 set pdfPath to item 2 of argv
 if deckPath does not start with "/" or pdfPath does not start with "/" then error "Both paths must be absolute"
 if deckPath is pdfPath then error "Proof output must differ from input"
 set deckFile to POSIX file deckPath
 set inputInfo to info for deckFile
 if folder of inputInfo then error "Input must be a PPTX file"
 set outputExists to false
 try
  set outputInfo to info for (POSIX file pdfPath)
  set outputExists to true
 end try
 if outputExists then error "Use a new native-proof output path"
 set targetDeck to my exactDeck(deckPath)
 if targetDeck is missing value then
  -- A cancelled/failed open does not authorize any operation on another document.
  tell application "Microsoft PowerPoint" to open deckFile
  set targetDeck to my exactDeck(deckPath)
 end if
 if targetDeck is missing value then error "Exact QA copy did not open; stopping without save/close"
 my assertPath(targetDeck, deckPath)
 tell application "Microsoft PowerPoint"
  set slideCount to count of slides of targetDeck
  save targetDeck in pdfPath as save as PDF
 end tell
 my assertPath(targetDeck, deckPath)
 if (count of argv) > 2 and item 3 of argv is "close" then
  tell application "Microsoft PowerPoint"
   if not (saved of targetDeck) then error "QA copy has unsaved changes; leaving it open"
  end tell
  my assertPath(targetDeck, deckPath)
  tell application "Microsoft PowerPoint" to close targetDeck saving no
 end if
 return (slideCount as text) & " slides; confirmed QA copy: " & deckPath & "; native proof: " & pdfPath
end run
