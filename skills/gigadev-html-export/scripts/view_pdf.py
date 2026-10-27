"""Build a viewing PDF; raster mode reuses lossless references and URL overlays."""
import json
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter

directory, output, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
w, h, count = map(int, sys.argv[4:7])
if mode == 'browser':
    pages = sorted((directory / 'assets').glob('page-*.pdf'))
    assert len(pages) == count, 'Unexpected browser PDF page count'
    writer = PdfWriter()
    for path in pages:
        assert len(PdfReader(path).pages) == 1, 'Expected one page per slide'
        writer.append(str(path))
    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    writer.write(output)
else:
    import pymupdf
    links = json.loads((directory / 'pdf-links.json').read_text())
    doc = pymupdf.open()
    for i in range(count):
        page = doc.new_page(width=w * .75, height=h * .75)
        page.insert_image(page.rect, filename=str(directory / 'assets' / f'reference-{i+1:03}.png'))
        for link in links[i]:
            if link['href'].startswith(('https://', 'http://')) and link['w'] > 0 and link['h'] > 0:
                r = pymupdf.Rect(link['x']*.75, link['y']*.75, (link['x']+link['w'])*.75, (link['y']+link['h'])*.75)
                page.insert_link({'kind': pymupdf.LINK_URI, 'from': r, 'uri': link['href']})
    doc.save(output, garbage=4, deflate=True)
    doc.close()
pdf = PdfReader(output)
assert len(pdf.pages) == count
assert all(abs(float(p.mediabox.width)/float(p.mediabox.height)-w/h) < .0001 for p in pdf.pages)
