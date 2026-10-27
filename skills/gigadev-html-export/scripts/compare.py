"""All-page native PDF diagnostics; local regions expose small missing details."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata
import pymupdf
from PIL import Image, ImageDraw, ImageChops, ImageStat


def normal(text):
    return re.sub(r'\s', '', unicodedata.normalize('NFKC', text))


def metrics(a, b):
    diff = ImageChops.difference(a, b)
    channels = diff.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    histogram = maximum.histogram()
    return {'mae': round(sum(ImageStat.Stat(diff).mean)/3, 4),
            'fractionOver20': round(sum(histogram[21:])/(a.width*a.height), 5)}


def crop_box(item, width, height, padding=4):
    x, y, w, h = [float(item.get(k, 0)) for k in ('x', 'y', 'w', 'h')]
    return (max(0, int(x-padding)), max(0, int(y-padding)),
            min(width, int(x+w+padding+1)), min(height, int(y+h+padding+1)))


def diagnose(ref, native, scene, words):
    w, h = ref.size
    tiles = []
    for y in range(0, h, 64):
        for x in range(0, w, 64):
            box = (x, y, min(w, x+64), min(h, y+64))
            m = metrics(ref.crop(box), native.crop(box))
            if m['mae'] >= 12 and m['fractionOver20'] >= .025:
                tiles.append({'box': box, **m})
    regions = []
    for item in scene['items']:
        text = item.get('kind') == 'text'
        graphic = item.get('kind') == 'shape' and item.get('tag') in {'path', 'line', 'polyline', 'polygon'}
        if not (text or graphic) or item.get('isNumber'):
            continue
        box = crop_box(item, w, h)
        if box[0] >= box[2] or box[1] >= box[3]:
            continue
        m = metrics(ref.crop(box), native.crop(box))
        row = {'object': item.get('objectName', item.get('id')), 'kind': item['kind'], 'box': box, **m, 'reasons': []}
        if text:
            expected = ''.join(r['text'] for r in item.get('runs', []))
            inside = [v for v in words if box[0] <= (v[0]+v[2])/2 <= box[2] and box[1] <= (v[1]+v[3])/2 <= box[3]]
            actual = ''.join(v[4] for v in inside)
            target = normal(expected)
            missing = sum((Counter(target)-Counter(normal(actual))).values())
            source_lines = item.get('lineCount') or len(item.get('baselines', []))
            actual_lines = len({(v[5], v[6]) for v in inside})
            row.update(text=expected[:100], estimatedMissingCharacters=missing,
                       expectedLines=source_lines, nativeLinesInRegion=actual_lines)
            if len(target) >= 4 and missing > max(2, len(target)*.2):
                row['reasons'].append('text-coverage-candidate')
            if source_lines and actual_lines and actual_lines != source_lines:
                row['reasons'].append('line-wrap-candidate')
        if m['mae'] >= 18 and m['fractionOver20'] >= .05:
            row['reasons'].append('regional-pixel-change')
        if row['reasons']:
            regions.append(row)
    regions.sort(key=lambda x: ('text-coverage-candidate' in x['reasons'], x['mae']), reverse=True)
    tiles.sort(key=lambda x: x['mae'], reverse=True)
    return regions, tiles


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True, help='Converter output directory')
    p.add_argument('--powerpoint-pdf', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--baseline-pdf', help='Previously accepted native PDF; prioritise regressions against it')
    p.add_argument('--only-outliers', action='store_true', help='Write image pairs for candidate pages only; compute every page')
    a = p.parse_args()
    source, out = Path(a.source), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((source/'scene.json').read_text())
    pdf = pymupdf.open(a.powerpoint_pdf)
    assert len(pdf) == len(scenes), 'PowerPoint page count differs from source'
    baseline = pymupdf.open(a.baseline_pdf) if a.baseline_pdf else None
    if baseline is not None:
        assert len(baseline) == len(scenes), 'Accepted baseline page count differs'
    rows, detail = [], []
    for i, (page, scene) in enumerate(zip(pdf, scenes), 1):
        w, h = scene['size']['w'], scene['size']['h']
        assert abs(page.rect.width/page.rect.height-w/h) < .002, 'PowerPoint canvas ratio changed'
        sx, sy = w/page.rect.width, h/page.rect.height
        pix = page.get_pixmap(matrix=pymupdf.Matrix(sx, sy), alpha=False)
        im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        if im.size != (w, h):
            im = im.resize((w, h), Image.Resampling.LANCZOS)
        ref = Image.open(source/'assets'/f'reference-{i:03}.png').convert('RGB')
        words = [(v[0]*sx, v[1]*sy, v[2]*sx, v[3]*sy, *v[4:]) for v in page.get_text('words')]
        diagnostic_ref = ref
        baseline_drift = None
        if baseline is not None:
            bp = baseline[i-1]
            assert abs(bp.rect.width/bp.rect.height-w/h) < .002, 'Accepted baseline canvas ratio changed'
            pix = bp.get_pixmap(matrix=pymupdf.Matrix(w/bp.rect.width, h/bp.rect.height), alpha=False)
            diagnostic_ref = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            if diagnostic_ref.size != (w, h):
                diagnostic_ref = diagnostic_ref.resize((w, h), Image.Resampling.LANCZOS)
            baseline_drift = metrics(diagnostic_ref, im)['mae']
        unchanged = baseline is not None and ImageChops.difference(diagnostic_ref, im).getbbox() is None
        regions, tiles = ([], []) if unchanged else diagnose(diagnostic_ref, im, scene, words)
        if baseline is not None:
            regions = [v for v in regions if v['mae'] > .05]
        whole = metrics(ref, im)
        candidate = bool(regions or tiles)
        rows.append({'slide': i, 'pixelMAE': whole['mae'], 'baselineDriftMAE': baseline_drift,
                     'unchangedFromAcceptedBaseline': unchanged, 'reviewCandidate': candidate,
                     'regionCandidates': len(regions), 'tileCandidates': len(tiles),
                     'topRegions': regions[:3], 'topTiles': tiles[:3]})
        detail.append({'slide': i, 'regions': regions, 'tiles': tiles})
        if not a.only_outliers or candidate:
            im.save(out/f'powerpoint-{i:03}.png')
            pair = Image.new('RGB', (w*2, h+32), '#202020')
            pair.paste(ref, (0, 32)); pair.paste(im, (w, 32))
            d = ImageDraw.Draw(pair)
            d.text((8, 8), 'Source HTML', fill='white'); d.text((w+8, 8), 'PowerPoint PDF', fill='white')
            pair.save(out/f'pair-{i:03}.jpg', quality=92)
    candidates = [r['slide'] for r in rows if r['reviewCandidate']]
    meaning = ('Diagnostics nominate review candidates, not failures or visual approval. '
               'Text-region estimates can overlap neighbouring frames; OOXML text verification remains mandatory. '
               'Native counters and video-player chrome may intentionally differ; account for every page. '
               'With an explicitly accepted baseline, unchanged pages/regions reuse prior visual acceptance.')
    result = {'slides': rows, 'reviewSlides': candidates, 'meaning': meaning,
              'thresholds': {'tileMAE':12, 'regionMAE':18, 'channelDelta':20},
              'powerpointPdf': str(Path(a.powerpoint_pdf).resolve()),
              'acceptedBaseline':str(Path(a.baseline_pdf).resolve()) if a.baseline_pdf else None}
    (out/'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (out/'region-details.json').write_text(json.dumps(detail, ensure_ascii=False, indent=2))
    summary = {'pages':len(rows), 'meanPixelMAE':sum(r['pixelMAE'] for r in rows)/len(rows),
               'reviewSlides':candidates, 'report':str((out/'comparison.json').resolve()), 'visualApproval':False}
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
