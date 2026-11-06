"""Source evidence for authored PPTX compositions."""
from collections import defaultdict
from xml.etree import ElementTree as ET

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'
NS = {'p': P, 'a': A}


def xml_evidence(node):
    return ET.tostring(node, encoding='unicode') if node is not None else None


def table_layout(table):
    return {
        'columnsEMU': [int(col.get('w')) for col in table.findall('a:tblGrid/a:gridCol', NS)],
        'propertiesXml': xml_evidence(table.find('a:tblPr', NS)),
        'rows': [
            {
                'heightEMU': int(row.get('h')) if row.get('h') else None,
                'cells': [
                    {
                        'attributes': cell.attrib,
                        'propertiesXml': xml_evidence(cell.find('a:tcPr', NS)),
                    }
                    for cell in row.findall('a:tc', NS)
                ],
            }
            for row in table.findall('a:tr', NS)
        ],
    }


def media_timing(tree):
    """Retain observed conditions/commands by target without inferring autoplay."""
    evidence = defaultdict(lambda: {'conditions': [], 'commands': [], 'settings': []})
    timing = tree.find('p:timing', NS)
    if timing is None:
        return evidence
    for tag, field in [('cond', 'conditions'), ('cmd', 'commands'), ('cMediaNode', 'settings')]:
        for node in timing.findall(f'.//p:{tag}', NS):
            value = dict(node.attrib)
            if tag == 'cMediaNode':
                timing_node = node.find('p:cTn', NS)
                if timing_node is not None:
                    value['timeline'] = dict(timing_node.attrib)
            for target in node.findall('./p:tgtEl/p:spTgt', NS):
                if target.get('spid') is not None:
                    evidence[target.get('spid')][field].append(value)
    return evidence


def picture_media(node, rels):
    """Identify a media picture by its explicit audio/video relationship."""
    for file_tag, media_type in [('videoFile', 'video'), ('audioFile', 'audio')]:
        file_node = node.find(f'.//a:{file_tag}', NS)
        if file_node is None:
            continue
        media = node.find(f'.//{{{P14}}}media')
        embedded = media.get(f'{{{R}}}embed') if media is not None else None
        linked = file_node.get(f'{{{R}}}link')
        rids = [rid for rid in (embedded, linked) if rid]
        selected = next((rid for rid in rids if rid in rels and not rels[rid]['external']), None)
        if selected is None:
            selected = next((rid for rid in rids if rid in rels), None)
        return media_type, selected, rids
    return None
