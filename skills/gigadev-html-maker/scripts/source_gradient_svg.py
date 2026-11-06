"""Narrow OOXML circle-gradient evidence and source-derived SVG rendering.

This supports only the observed point-focus / tileRect combinations.
"""
from dataclasses import dataclass, asdict
from math import hypot
import posixpath
import re
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from source_dispositions import NS


def need(ok, message):
    if not ok:
        raise ValueError(message)


def local(node):
    return node.tag.rsplit('}', 1)[-1]


def related(z, part, kind):
    rel = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    root = ET.fromstring(z.read(rel))
    hits = [e for e in root if e.get('Type', '').endswith('/' + kind) and e.get('TargetMode') != 'External']
    need(len(hits) == 1, 'unresolved relationship: ' + kind)
    target = hits[0].get('Target', '')
    need(bool(target), 'empty relationship target')
    return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part), target))


@dataclass(frozen=True)
class Stop:
    position: int                 # OOXML percent, 100000 = 100%
    rgb: str                      # resolved RRGGBB
    alpha: int                    # OOXML percent


@dataclass(frozen=True)
class GradientShape:
    source_id: str
    slide_part: str
    theme_part: str
    box_emu: tuple                # x, y, width, height
    canvas_emu: tuple             # width, height
    radius_emu: float
    stops: tuple                  # tuple[Stop, ...], sorted by position
    fill_to_rect: tuple           # l,t,r,b OOXML percentages
    tile_rect: tuple              # l,t,r,b OOXML percentages; preserve exact source
    stroke_rgb: str
    stroke_alpha: int
    stroke_width_emu: int
    status: str = 'source-derived-pixel-review-required'

    def to_dict(self):
        return asdict(self)


def resolve(verifier, slide_number, object_id):
    """Resolve supported direct shapes; unknown inputs fail closed with ValueError."""
    need(isinstance(slide_number, int) and isinstance(object_id, str) and re.fullmatch(r'[1-9][0-9]*', object_id), 'invalid source identity')
    part, shape = verifier.shape(slide_number, object_id)
    z = verifier.zip
    layout = related(z, part, 'slideLayout')
    master = related(z, layout, 'slideMaster')
    theme = related(z, master, 'theme')
    for name in (part, layout):
        root = ET.fromstring(z.read(name))
        override = root.find('p:clrMapOvr', NS)
        need(override is None or (len(override) == 1 and local(override[0]) == 'masterClrMapping'), 'color map override unsupported')
    master_root = ET.fromstring(z.read(master))
    clrmap = master_root.find('p:clrMap', NS)
    root = ET.fromstring(z.read(theme))
    scheme = root.find('.//a:clrScheme', NS)
    lines = root.find('.//a:fmtScheme/a:lnStyleLst', NS)
    need(clrmap is not None and scheme is not None and lines is not None, 'theme incomplete')
    def color(node):
        kind = local(node)
        if kind == 'schemeClr':
            val = node.get('val')
            need(val is not None and val != 'phClr', 'placeholder color unsupported')
            entry = scheme.find('a:' + clrmap.get(val, val), NS)
            need(entry is not None and len(entry) == 1 and local(entry[0]) == 'srgbClr' and len(entry[0]) == 0, 'theme color unsupported')
            rgb = entry[0].get('val', '')
        elif kind == 'srgbClr':
            rgb = node.get('val', '')
        else:
            raise ValueError('color type unsupported')
        need(re.fullmatch(r'[0-9a-fA-F]{6}', rgb) is not None, 'invalid RGB')
        need(set(node.attrib) == {'val'} and len(node) == 1 and local(node[0]) == 'alpha' and set(node[0].attrib) == {'val'} and len(node[0]) == 0, 'color transforms unsupported')
        try: alpha = int(node[0].get('val', ''))
        except ValueError: raise ValueError('invalid alpha')
        need(0 <= alpha <= 100000, 'invalid alpha')
        return rgb.upper(), alpha
    sp = shape.find('p:spPr', NS)
    style = shape.find('p:style', NS)
    need(sp is not None and style is not None and shape.find('p:nvSpPr/p:nvPr/p:ph', NS) is None, 'shape style or placeholder unsupported')
    need(not sp.attrib and [local(x) for x in sp] == ['xfrm', 'prstGeom', 'gradFill', 'ln'], 'shape properties unsupported')
    xf = sp.find('a:xfrm', NS)
    need(not xf.attrib and [local(x) for x in xf] == ['off', 'ext'], 'transformed geometry unsupported')
    try:
        off, ext = list(xf)
        need(set(off.attrib) == {'x','y'} and set(ext.attrib) == {'cx','cy'} and not len(off) and not len(ext), 'geometry attributes unsupported')
        x,y,w,h = int(off.get('x')),int(off.get('y')),int(ext.get('cx')),int(ext.get('cy'))
    except (TypeError, ValueError): raise ValueError('invalid geometry')
    need(w > 0 and h > 0, 'empty geometry')
    geom = sp.find('a:prstGeom', NS)
    gd = geom.findall('a:avLst/a:gd', NS)
    need(geom.attrib == {'prst':'roundRect'} and len(geom) == 1 and local(geom[0]) == 'avLst' and len(geom[0]) == 1 and len(gd) == 1 and gd[0].get('name') == 'adj' and re.fullmatch(r'val [0-9]+', gd[0].get('fmla','')), 'roundRect geometry unsupported')
    adj = int(gd[0].get('fmla').split()[1]); need(0 <= adj <= 50000, 'invalid radius')
    grad = sp.find('a:gradFill', NS)
    need(set(grad.attrib) <= {'flip','rotWithShape'} and grad.get('flip','none') == 'none' and grad.get('rotWithShape','1') in ('1','true'), 'gradient transform unsupported')
    need([local(a) for a in grad] in (['gsLst','path'], ['gsLst','path','tileRect']), 'gradient structure unsupported')
    gs = grad.find('a:gsLst', NS)
    need(not gs.attrib and len(gs) == 2 and all(local(s) == 'gs' and set(s.attrib) == {'pos'} and len(s) == 1 for s in gs), 'gradient stops unsupported')
    stops=[]
    for s in gs:
        try: pos = int(s.get('pos',''))
        except ValueError: raise ValueError('invalid stop')
        need(0 <= pos <= 100000, 'invalid stop position')
        rgb, alpha = color(s[0]); stops.append(Stop(pos, rgb, alpha))
    need(sorted((s.position, s.alpha) for s in stops) == [(38000,49889),(100000,19814)], 'gradient stop pattern unsupported')
    path = grad.find('a:path', NS)
    need(path.attrib == {'path':'circle'} and len(path) == 1 and local(path[0]) == 'fillToRect', 'gradient path unsupported')
    def rect(node):
        if node is None: return (0,0,0,0)
        need(not len(node) and set(node.attrib) <= set('ltrb'), 'rectangle attributes unsupported')
        try: return tuple(int(node.get(k,'0')) for k in 'ltrb')
        except ValueError: raise ValueError('invalid rectangle')
    focus, tile = rect(path[0]), rect(grad.find('a:tileRect', NS))
    allowed = {((0,100000,100000,0),(0,0,0,0)), ((100000,0,0,100000),(0,-100000,-100000,0)), ((0,0,100000,100000),(-100000,-100000,0,0))}
    need((focus,tile) in allowed, 'fillToRect/tileRect combination unsupported')
    ef = style.find('a:effectRef', NS); ref = style.find('a:lnRef', NS)
    need(ef is not None and ef.get('idx') == '0' and ref is not None and ref.get('idx') == '2' and len(lines) >= 2, 'effect or theme line reference unsupported')
    themed = lines[1]
    need(themed.get('cap','flat') == 'flat' and themed.get('cmpd','sng') == 'sng' and themed.get('algn','ctr') == 'ctr' and [local(a) for a in themed] == ['solidFill','prstDash','miter'] and themed.find('a:prstDash', NS).get('val') == 'solid', 'theme line unsupported')
    try: width = int(themed.get('w',''))
    except ValueError: raise ValueError('invalid line width')
    need(width > 0, 'invalid line width')
    line = sp.find('a:ln', NS)
    need(not line.attrib and len(line) == 1 and local(line[0]) == 'solidFill' and not line[0].attrib and len(line[0]) == 1, 'local line unsupported')
    stroke, alpha = color(line[0][0])
    return GradientShape(f's{slide_number}-o{object_id}', part, theme, (x,y,w,h), (verifier.canvas['width'],verifier.canvas['height']), min(w,h)*adj/100000, tuple(sorted(stops,key=lambda s:s.position)), focus,tile,stroke,alpha,width)


@dataclass(frozen=True)
class GradientGeometry:
    tile_box_emu: tuple            # x, y, width, height, relative to the shape
    center_emu: tuple              # center of circumscribed circle
    focus_emu: tuple               # point specified by fillToRect
    radius_emu: float


def gradient_geometry(shape):
    """Resolve the observed circle-gradient geometry in local EMU units."""
    need(isinstance(shape, GradientShape), 'GradientShape required')
    _, _, w, h = shape.box_emu
    l, t, r, b = shape.tile_rect
    x, y = w*l/100000, h*t/100000
    tw, th = w*(1-(l+r)/100000), h*(1-(t+b)/100000)
    need(tw > 0 and th > 0, 'invalid gradient tile')
    fl, ft, fr, fb = shape.fill_to_rect
    need(fl+fr == 100000 and ft+fb == 100000, 'non-point focus unsupported')
    center = (x+tw/2, y+th/2)
    focus = (w*fl/100000, h*ft/100000)
    radius = hypot(tw, th)/2
    need(hypot(focus[0]-center[0],focus[1]-center[1]) <= radius*(1+1e-12), 'focus outside gradient circle')
    return GradientGeometry((x,y,tw,th),center,focus,radius)


def render_svg(shape):
    """Render source-derived circle fill and solid line; retain HTML text separately.

    Intermediate stops reproduce PowerPoint's premultiplied color interpolation
    in renderers that interpolate SVG stop colors independently of opacity.
    """
    g = gradient_geometry(shape)
    _,_,w,h = shape.box_emu
    ident = 'g-' + re.sub(r'[^a-zA-Z0-9_-]', '', shape.source_id)
    first,last=shape.stops
    ca=tuple(int(first.rgb[i:i+2],16) for i in (0,2,4))
    cb=tuple(int(last.rgb[i:i+2],16) for i in (0,2,4))
    aa,ab=first.alpha/100000,last.alpha/100000
    parts=[]
    for i in range(129):
        u=i/128
        opacity=aa*(1-u)+ab*u
        rgb=tuple(round((ca[j]*aa*(1-u)+cb[j]*ab*u)/opacity) if opacity else 0 for j in range(3))
        pos=first.position+(last.position-first.position)*u
        parts.append(f'<stop offset="{pos/1000:.6f}%" stop-color="rgb({rgb[0]},{rgb[1]},{rgb[2]})" stop-opacity="{opacity:.6f}"/>')
    cx,cy=g.center_emu; fx,fy=g.focus_emu
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="none" overflow="visible" aria-hidden="true" data-source-shape-for="{escape(shape.source_id)}">'
            f'<defs><radialGradient id="{ident}" gradientUnits="userSpaceOnUse" cx="{cx:.6f}" cy="{cy:.6f}" r="{g.radius_emu:.6f}" fx="{fx:.6f}" fy="{fy:.6f}">{''.join(parts)}</radialGradient></defs>'
            f'<rect x="0" y="0" width="{w}" height="{h}" rx="{shape.radius_emu:g}" fill="url(#{ident})" stroke="#{shape.stroke_rgb}" stroke-opacity="{shape.stroke_alpha/100000:g}" stroke-width="{shape.stroke_width_emu}"/></svg>')
