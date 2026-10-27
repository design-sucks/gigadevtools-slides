"""Independent source-text, font, relationship and layout gates for HTML export."""
import collections
import io
import json
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main", "a": "http://schemas.openxmlformats.org/drawingml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
def normalized(text):
    return re.sub(r"\s", "", text)

def coordinates(root):
    for e in root.iter():
        local = e.tag.rsplit("}", 1)[-1]
        if local in {"off", "chOff"}:
            assert set(e.attrib) == {"x", "y"}, f"Invalid {local} coordinate attributes: {e.attrib}"
        if local in {"ext", "chExt"} and "uri" not in e.attrib and e.tag.startswith("{" + NS['a'] + "}"):
            assert set(e.attrib) == {"cx", "cy"}, f"Invalid {local} dimensions: {e.attrib}"

def verify(directory):
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_text())
    from pypdf import PdfReader
    pdf = PdfReader(report['pdf']) if report.get('pdf') else None
    if report.get('format', 'both') in {'pdf', 'both'}:
        assert pdf is not None, 'Requested viewing PDF missing'
    if pdf is not None:
        assert len(pdf.pages) == report['input']['count'], 'Source PDF page count differs from slide count'
        for page in pdf.pages:
            assert abs(float(page.mediabox.width)/float(page.mediabox.height)-report['input']['w']/report['input']['h']) < .0001, 'Source PDF aspect ratio changed'
    if report.get('format') == 'pdf':
        assert not (directory / 'scene.json').exists(), 'PDF-only mode unexpectedly reconstructed a PPTX scene'
        result = {'status':'pass','slides':[{'slide':i+1} for i in range(len(pdf.pages))], 'fonts':[], 'layouts':0, 'sourcePdfPages':len(pdf.pages), 'pdfMode':report['pdfMode'], 'visualVerification':'Viewing PDF; no editable PPTX or PowerPoint claim.'}
        (directory / 'verification.json').write_text(json.dumps(result, indent=2))
        return result
    from fontTools.ttLib import TTFont
    scenes = json.loads((directory / 'scene.json').read_text())
    output = Path(report['output'])
    rows, fonts = [], []
    with ZipFile(output) as z:
        names = set(z.namelist())
        for name in names:
            if name.endswith((".xml", ".rels")):
                root = ET.fromstring(z.read(name))
                coordinates(root)
                if name.endswith(".rels"):
                    folder = posixpath.dirname(name).replace("/_rels", "") if name != "_rels/.rels" else ""
                    for relation in root:
                        if relation.get("TargetMode") == "External":
                            continue
                        target = relation.get("Target")
                        part = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(folder, target))
                        assert part in names, f"Missing relationship target {name}: {part}"
        types = ET.fromstring(z.read("[Content_Types].xml"))
        for e in types:
            if e.tag.endswith("Override"):
                assert e.get("PartName").lstrip("/") in names, "Dangling content type"
        slide_names = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.search(r"slide(\d+)", n)[1]))
        assert len(slide_names) == len(scenes) == report["input"]["count"]
        for scene, name in zip(scenes, slide_names):
            root = ET.fromstring(z.read(name))
            ids = [e.get('id') for e in root.findall('.//p:cNvPr', NS)]
            assert len(ids) == len(set(ids)), f'Duplicate shape/media ids on slide {scene["number"]}'
            videos = root.findall('.//a:videoFile', NS)
            assert len(videos) == sum(bool(m.get('nativeVideo')) for m in scene['items']), 'Native video missing or duplicated'
            expected = normalized("".join(v["text"] for v in scene["inventory"]))
            measured = normalized("".join(r["text"] for m in scene["items"] if m["kind"] == "text" and m["source"] not in {"hud", "hidden-native-number"} for r in m["runs"]))
            assert collections.Counter(expected) == collections.Counter(measured), f"DOM text lost before serialization on slide {scene['number']}"
            fields = root.findall('.//a:fld[@type="slidenum"]', NS)
            assert len(fields) == 1, f"Native number field missing/ambiguous on {scene['number']}"
            assert fields[0].find("a:t", NS).text == str(scene["number"])
            assert root.find("p:cSld/p:bg", NS) is None, "Background must inherit from layout"
            groups = root.findall('.//p:grpSp', NS)
            expected_groups = scene.get('groups', [])
            assert len(groups) == len(expected_groups), 'Unexpected native group count'
            native_group_names = {}
            for g in groups:
                gn = g.find('p:nvGrpSpPr/p:cNvPr', NS).get('name')
                assert gn not in native_group_names, 'Duplicate group name'
                native_group_names[gn] = g
                xf = g.find('p:grpSpPr/a:xfrm', NS)
                assert xf.find('a:off', NS).attrib == xf.find('a:chOff', NS).attrib, 'Group offset changed content'
                assert xf.find('a:ext', NS).attrib == xf.find('a:chExt', NS).attrib, 'Group scale changed content'
                assert not g.findall('.//p:ph', NS), 'Placeholders moved inside a group'
            for expected_group in expected_groups:
                g = native_group_names[expected_group['name']]
                leaf_tags = {'{'+NS['p']+'}'+t for t in ['sp', 'pic', 'cxnSp', 'graphicFrame']}
                actual_names = {sp.find('./*/p:cNvPr', NS).get('name') for sp in g.iter() if sp.tag in leaf_tags}
                assert actual_names == set(expected_group['members']), 'Group membership changed'
            shapes = root.findall('.//p:sp', NS)
            for item in (m for m in scene["items"] if m["kind"] == "text"):
                target = "".join(r["text"] for r in item["runs"])
                if item.get("isNumber"):
                    found = fields[0].find("a:t", NS).text
                    target = str(scene["number"])
                else:
                    shape = next((s for s in shapes if s.find("p:nvSpPr/p:cNvPr", NS).get("name") == item["objectName"]), None)
                    assert shape is not None, f"Missing text object {item['objectName']}"
                    found = "".join(t.text or "" for t in shape.findall('.//a:t', NS))
                assert normalized(found) == normalized(target), f"Text changed in {item.get('objectName')}"
            rows.append({"slide": scene["number"], "sourceCharacters": len(expected), "missingCharacters": 0, "nativeNumber": True, "textBlocks": sum(m["kind"] == "text" for m in scene["items"]), "groups": len(groups)})
        presentation = ET.fromstring(z.read("ppt/presentation.xml"))
        size = presentation.find("p:sldSz", NS)
        expected_ratio = report["input"]["w"] / report["input"]["h"]
        assert abs(int(size.get("cx"))/int(size.get("cy"))-expected_ratio) < .00001, "Canvas aspect ratio changed"
        if report["fonts"]:
            assert presentation.get("embedTrueTypeFonts") in {"1", "true"}
            assert presentation.get("saveSubsetFonts") in {"0", "false"}
        for i, face in enumerate(report["fonts"], 1):
            source = TTFont(directory / "assets" / f"font-{i}.source")
            data = z.read(f"ppt/fonts/font{i-1}.fntdata")
            assert int.from_bytes(data[:4], 'little') == len(data)
            size = int.from_bytes(data[4:8], 'little')
            embedded = TTFont(io.BytesIO(data[-size:]))
            a, b = set(source.getBestCmap()), set(embedded.getBestCmap())
            assert a <= b, f"Missing source glyphs in {face['family']}"
            assert source['maxp'].numGlyphs == embedded['maxp'].numGlyphs
            assert source['OS/2'].fsType == embedded['OS/2'].fsType == int.from_bytes(data[32:34], 'little')
            assert not source['OS/2'].fsType & 0x206, "Font metadata disallows editable embedding"
            fonts.append({"family": face['family'], "glyphs": source['maxp'].numGlyphs, "sourceUnicode": len(a), "missingUnicode": len(a-b)})
        layouts = [n for n in names if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)]
        for name in layouts:
            assert ET.fromstring(z.read(name)).find("p:cSld/p:bg", NS) is not None
    result = {"status": "pass", "slides": rows, "fonts": fonts, "fontEmbeddingVerified": bool(report["fonts"]), "fontEmbeddingNote": None if report["fonts"] else "No embedded font source supplied; system fonts require target-device verification.", "layouts": len(layouts), "sourcePdfPages": len(pdf.pages) if pdf is not None else None, "windowsVerified": False, "visualVerification": "Requires the matching PowerPoint PDF and visual review; this gate is structural/text/font only."}
    (directory / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result

if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        bad = ET.fromstring('<a:chOff xmlns:a="'+NS['a']+'" x="0" cy="0"/>')
        try:
            coordinates(bad)
        except AssertionError:
            print('PASS: rejects the real PowerPoint repair regression (chOff cy instead of y).')
        else:
            raise AssertionError('Regression gate did not reject invalid coordinates')
    else:
        result = verify(sys.argv[1])
        print(json.dumps({"status": result['status'], "slides": len(result['slides']), "fonts": len(result['fonts']), "layouts": result['layouts']}))
