"""Wrap explicit scene components in native groups without moving any leaf shape."""
import argparse
import json
import os
import sys
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
for prefix, uri in {**NS, 'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}.items():
    ET.register_namespace(prefix, uri)

def tag(name):
    prefix, local = name.split(':')
    return '{'+NS[prefix]+'}'+local

DRAWINGS = {tag('p:sp'), tag('p:pic'), tag('p:cxnSp'), tag('p:graphicFrame'), tag('p:grpSp')}

def leaves(node):
    if node.tag == tag('p:grpSp'):
        return [leaf for child in node if child.tag in DRAWINGS for leaf in leaves(child)]
    return [node] if node.tag in DRAWINGS else []

def object_name(node):
    prop = node.find('./*/p:cNvPr', NS)
    if prop is None:
        raise ValueError('Drawing lacks cNvPr')
    return prop.get('name')

def bounds(node):
    xf = node.find('p:grpSpPr/a:xfrm', NS) if node.tag == tag('p:grpSp') else node.find('p:spPr/a:xfrm', NS)
    if xf is None:
        xf = node.find('p:xfrm', NS)
    if xf is None:
        raise ValueError('Drawing has no explicit transform: '+str(object_name(node)))
    off, ext = xf.find('a:off', NS), xf.find('a:ext', NS)
    if off is None or ext is None:
        raise ValueError('Incomplete transform')
    if xf.get('rot') not in {None, '0'}:
        raise ValueError('Rotated bounds need an explicit adapter')
    return int(off.get('x')), int(off.get('y')), int(ext.get('cx')), int(ext.get('cy'))

def wrap_slide(xml, groups):
    # Register source namespaces before serialization, including any Office extensions.
    import io
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(xml), events=('start-ns',)):
        if prefix and not prefix.startswith('ns'):
            ET.register_namespace(prefix, uri)
    root = ET.fromstring(xml)
    tree = root.find('p:cSld/p:spTree', NS)
    original = [leaf for child in tree for leaf in leaves(child)]
    before = [ET.tostring(leaf) for leaf in original]
    lookup = {object_name(leaf): leaf for leaf in original}
    if len(lookup) != len(original):
        raise ValueError('Non-unique drawing names')
    next_id = max(int(e.get('id')) for e in root.findall('.//p:cNvPr', NS)) + 1
    names = set(lookup)
    rows = []
    # Inner groups first; outer groups then wrap them as units. Never reorder.
    for group in sorted(groups, key=lambda g: len(g['members'])):
        members = set(group['members'])
        if len(members) < 2 or len(members) != len(group['members']):
            raise ValueError('Group needs at least two distinct objects: '+group['name'])
        if not members <= lookup.keys():
            raise ValueError('Missing members in '+group['name']+': '+str(members-lookup.keys()))
        if group['name'] in names:
            raise ValueError('Duplicate group name: '+group['name'])
        if any(lookup[n].find('.//p:ph', NS) is not None for n in members):
            raise ValueError('Placeholders must remain outside content groups')
        children = list(tree)
        selected = []
        for i, child in enumerate(children):
            child_names = {object_name(leaf) for leaf in leaves(child)}
            overlap = child_names & members
            if overlap and not child_names <= members:
                raise ValueError('Crossing groups: '+group['name'])
            if overlap:
                selected.append(i)
        if not selected or selected != list(range(selected[0], selected[-1]+1)):
            raise ValueError('Interleaved paint order; cannot safely group '+group['name'])
        chosen = children[selected[0]:selected[-1]+1]
        if {object_name(leaf) for child in chosen for leaf in leaves(child)} != members:
            raise ValueError('Member coverage mismatch')
        boxes = [bounds(child) for child in chosen]
        x, y = min(v[0] for v in boxes), min(v[1] for v in boxes)
        w, h = max(v[0]+v[2] for v in boxes)-x, max(v[1]+v[3] for v in boxes)-y
        w, h = max(1, w), max(1, h)
        wrapper = ET.Element(tag('p:grpSp'))
        nv = ET.SubElement(wrapper, tag('p:nvGrpSpPr'))
        ET.SubElement(nv, tag('p:cNvPr'), {'id': str(next_id), 'name': group['name']})
        ET.SubElement(nv, tag('p:cNvGrpSpPr'))
        ET.SubElement(nv, tag('p:nvPr'))
        xf = ET.SubElement(ET.SubElement(wrapper, tag('p:grpSpPr')), tag('a:xfrm'))
        # Identity map in slide coordinates: leaves retain their original xfrm.
        ET.SubElement(xf, tag('a:off'), {'x': str(x), 'y': str(y)})
        ET.SubElement(xf, tag('a:ext'), {'cx': str(w), 'cy': str(h)})
        ET.SubElement(xf, tag('a:chOff'), {'x': str(x), 'y': str(y)})
        ET.SubElement(xf, tag('a:chExt'), {'cx': str(w), 'cy': str(h)})
        wrapper.extend(chosen)
        tree[:] = children[:selected[0]] + [wrapper] + children[selected[-1]+1:]
        rows.append({'id': group['id'], 'name': group['name'], 'selector': group.get('selector'),
                     'leafObjects': len(members), 'textFrames': sum(lookup[n].find('p:txBody', NS) is not None for n in members),
                     'boundsEMU': [x, y, w, h]})
        next_id += 1
        names.add(group['name'])
    after = [ET.tostring(leaf) for child in tree for leaf in leaves(child)]
    if before != after:
        raise ValueError('Grouping changed leaf paint order or content')
    ids = [e.get('id') for e in root.findall('.//p:cNvPr', NS)]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate shape id')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True), rows

def convert(source, scene_path, output):
    scenes = json.loads(Path(scene_path).read_text())
    changed, rows = {}, []
    with ZipFile(source) as archive:
        for scene in scenes:
            groups = scene.get('groups', [])
            if not groups:
                continue
            part = f"ppt/slides/slide{scene['number']}.xml"
            changed[part], stats = wrap_slide(archive.read(part), groups)
            rows.append({'slide': scene['number'], 'groups': stats})
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.group-', suffix='.pptx', dir=output.parent)
        os.close(fd)
        try:
            with ZipFile(temp, 'w') as target:
                for info in archive.infolist():
                    target.writestr(info, changed.get(info.filename, archive.read(info.filename)))
            os.replace(temp, output)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    return {'status': 'pass', 'groupCount': sum(len(s['groups']) for s in rows), 'slides': rows,
            'invariants': 'leaf geometry/style/text/order unchanged; identity group transforms; no rasterization'}

def self_test():
    shapes = ''.join(f'<p:sp><p:nvSpPr><p:cNvPr id="{i+2}" name="{name}"/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{i*100}" y="0"/><a:ext cx="90" cy="90"/></a:xfrm></p:spPr><p:txBody><a:p><a:r><a:t>{name}</a:t></a:r></a:p></p:txBody></p:sp>' for i, name in enumerate('ABC'))
    xml = ('<p:sld xmlns:p="'+NS['p']+'" xmlns:a="'+NS['a']+'"><p:cSld><p:spTree>'+shapes+'</p:spTree></p:cSld></p:sld>').encode()
    def g(name, members):
        return {'id': name, 'name': name, 'members': list(members)}
    result, _ = wrap_slide(xml, [g('Outer', 'ABC'), g('Inner', 'AB')])
    assert len(ET.fromstring(result).findall('.//p:grpSp', NS)) == 2
    for plan, reason in [([g('Interleaved', 'AC')], 'Interleaved'), ([g('One', 'AB'), g('Two', 'BC')], 'Crossing')]:
        try:
            wrap_slide(xml, plan)
        except ValueError as exc:
            assert reason in str(exc)
        else:
            raise AssertionError('Unsafe grouping accepted')
    print('PASS: nested groups preserve leaf content/order; interleaved and crossing groups are rejected.')

if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        self_test()
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.scene, args.output)))
