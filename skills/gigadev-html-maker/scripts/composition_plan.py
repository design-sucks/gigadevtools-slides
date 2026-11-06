"""Validate explicit, per-slide composition decisions; does not judge visual quality."""
from pathlib import Path
import argparse
import json
import hashlib

ACTIONS = {'preserve', 'adapt', 'redesign'}
FIELDS = ('sourceId', 'purpose', 'emphasis', 'readingOrder', 'groups', 'density',
          'editability', 'works', 'problem', 'capacity', 'technicalRisk')


def validate(deck, plan, plan_dir, require_visual=False, project_sha256=None):
    records = plan.get('slides') if isinstance(plan, dict) else None
    if not isinstance(records, list):
        raise ValueError('Composition plan must contain a slides list')
    input_kind = plan.get('inputKind', 'slides')
    if input_kind not in ('slides', 'outline'):
        raise ValueError('Composition plan inputKind must be slides or outline')
    if input_kind == 'outline' and Path((deck.get('source') or {}).get('name') or '').suffix.lower() in ('.pptx', '.pdf'):
        raise ValueError('A slide source requires source render evidence; outline mode is for new decks.')
    evidence_field = 'sourceOutline' if input_kind == 'outline' else 'sourceRender'
    wanted = deck.get('order') or [s['id'] for s in deck.get('slides', [])]
    seen = set()
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get('slideId'), str):
            raise ValueError('Each composition decision needs a slideId')
        sid = item['slideId']
        if sid in seen or sid not in wanted:
            raise ValueError('Duplicate or unknown plan slide: ' + sid)
        seen.add(sid)
        for field in (*FIELDS, evidence_field):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f'{sid}: missing or empty {field}')
        if item.get('decision') not in ACTIONS:
            raise ValueError(f'{sid}: decision must be preserve, adapt or redesign')
        if item['decision'] == 'redesign' and not str(item.get('reference', '')).strip():
            raise ValueError(f'{sid}: redesign requires a reference or documented custom composition')
        evidence = (plan_dir / item[evidence_field]).resolve()
        if not evidence.is_file():
            raise ValueError(f'{sid}: {evidence_field} does not exist: {evidence}')
        if require_visual:
            review = item.get('visualReview')
            if not isinstance(review, dict) or review.get('reviewed') is not True or not str(review.get('observation', '')).strip():
                raise ValueError(f'{sid}: final build requires a recorded visual review and observation')
            if not isinstance(review.get('candidateRender'), str) or not review['candidateRender'].strip():
                raise ValueError(f'{sid}: final build requires candidateRender')
            frame = (plan_dir / review['candidateRender']).resolve()
            if not frame.is_file():
                raise ValueError(f'{sid}: candidateRender does not exist: {frame}')
            data=frame.read_bytes()
            if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')):
                raise ValueError(f'{sid}: candidateRender must be a PNG or JPEG')
            if review.get('candidateRenderSha256') != hashlib.sha256(data).hexdigest():
                raise ValueError(f'{sid}: candidateRender SHA-256 differs')
            if not project_sha256 or review.get('projectSha256') != project_sha256:
                raise ValueError(f'{sid}: visual review must match the current project SHA-256')
    missing = [sid for sid in wanted if sid not in seen]
    if missing:
        raise ValueError('Missing composition decisions: ' + ', '.join(missing))
    return {'status':'valid', 'slides':len(seen), 'visualApproval':False,
            'note':'Completeness only; claims, source fidelity, capacity and visual quality require review.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deck', type=Path)
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.deck.read_text()), json.loads(args.plan.read_text()), args.plan.parent)
    except (OSError, ValueError, KeyError) as e:
        parser.exit(1, 'composition plan: ' + str(e) + '\n')
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
