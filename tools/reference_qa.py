#!/usr/bin/env python3
"""Strict full-resolution reference-vs-Android-screenshot visual regression check.

Does not resize, crop, recolour or vectorize source files. Compares composited
sRGB sample values (not a substitute for colour-managed print calibration).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgb(path, bg):
    with Image.open(path) as image:
        if image.format != 'PNG':
            raise ValueError(f'Only PNG inputs are supported: {path}')
        rgba = image.convert('RGBA')
        backdrop = Image.new('RGBA', rgba.size, (*bg, 255))
        return np.asarray(Image.alpha_composite(backdrop, rgba).convert('RGB'), dtype=np.uint8)


def parse_background(value):
    color = value.lstrip('#')
    if len(color) != 6 or any(c not in '0123456789abcdefABCDEF' for c in color):
        raise ValueError('Background must be a six-digit RGB hex value, e.g. #FFFFFF')
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))


def load_mask(path, width, height):
    mask = np.zeros((height, width), dtype=bool)
    if path is None:
        return mask
    settings = json.loads(Path(path).read_text(encoding='utf-8'))
    if set(settings) != {'ignore_regions'} or not isinstance(settings['ignore_regions'], list):
        raise ValueError('Mask JSON requires only an ignore_regions array')
    for region in settings['ignore_regions']:
        if set(region) != {'x', 'y', 'width', 'height'} or any(
            type(region[k]) is not int for k in ('x', 'y', 'width', 'height')
        ):
            raise ValueError('Each mask region needs integer x, y, width, height')
        x, y, w, h = (region[k] for k in ('x', 'y', 'width', 'height'))
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
            raise ValueError(f'Mask region outside screenshot: {region}')
        mask[y:y+h, x:x+w] = True
    if np.count_nonzero(mask) > mask.size * 0.20:
        raise ValueError('Mask covers over 20% of the screen; review it instead of hiding the design')
    return mask


def save_report(outdir, report):
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = [
        '# Android reference visual QA',
        '',
        f"**Status:** {report['status']}",
        f"**Reference:** `{report['reference']}` ({report['reference_size'][0]}×{report['reference_size'][1]})",
        f"**Actual:** `{report['actual']}` ({report['actual_size'][0]}×{report['actual_size'][1]})",
    ]
    if 'changed_percent' in report:
        summary.extend([
            f"**Changed pixels:** {report['changed_percent']:.4f}%",
            f"**Maximum allowed:** {report['max_changed_percent']:.4f}%",
            f"**Ignored pixels:** {report['ignored_percent']:.4f}%",
            f"**Mean absolute channel difference:** {report['mean_absolute_channel_difference']:.4f}/255",
            f"**Maximum channel difference:** {report['maximum_channel_difference']}/255",
            '', 'Inspect `diff.png` and `overlay.png` from the workflow artifact.',
        ])
    else:
        summary.append('Screenshots must have exactly equal pixel dimensions; no automatic scaling is performed.')
    (outdir / 'summary.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')


def compare(reference, actual, outdir, tolerance=2, max_changed_percent=0.5,
            background='#FFFFFF', mask_file=None):
    bg = parse_background(background)
    ref = load_rgb(reference, bg)
    act = load_rgb(actual, bg)
    h, w = ref.shape[:2]
    ah, aw = act.shape[:2]
    report = {
        'reference': str(reference), 'actual': str(actual),
        'reference_size': [w, h], 'actual_size': [aw, ah],
        'tolerance': tolerance, 'max_changed_percent': max_changed_percent,
    }
    if (w, h) != (aw, ah):
        report['status'] = 'dimension_mismatch'
        save_report(outdir, report)
        return 2
    mask = load_mask(mask_file, w, h)
    delta = np.abs(ref.astype(np.int16) - act.astype(np.int16))
    valid = ~mask
    changed = (delta.max(axis=2) > tolerance) & valid
    count = int(np.count_nonzero(valid))
    fraction = float(np.count_nonzero(changed) / count * 100) if count else 0
    selected = delta[valid]
    maxdelta = int(selected.max()) if selected.size else 0
    mean_delta = float(selected.mean()) if selected.size else 0.0
    bounds = None
    ys, xs = np.where(changed)
    if xs.size:
        bounds = [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]
    status = 'matches' if fraction <= max_changed_percent else 'different'
    report.update({
        'status': status, 'changed_pixels': int(changed.sum()),
        'compared_pixels': count, 'changed_percent': round(fraction, 6),
        'ignored_percent': round(float(mask.mean() * 100), 6),
        'mean_absolute_channel_difference': round(mean_delta, 6),
        'maximum_channel_difference': maxdelta, 'changed_bounds': bounds,
    })
    outdir.mkdir(parents=True, exist_ok=True)
    diff = (act // 3).copy()
    diff[changed] = (255, 40, 40)
    diff[mask] = (120, 120, 120)
    Image.fromarray(diff, 'RGB').save(outdir / 'diff.png', optimize=True)
    Image.blend(Image.fromarray(ref, 'RGB'), Image.fromarray(act, 'RGB'), 0.5).save(
        outdir / 'overlay.png', optimize=True)
    save_report(outdir, report)
    return 0 if status == 'matches' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('reference', type=Path, help='Approved reference PNG')
    parser.add_argument('actual', type=Path, help='Screenshot from real app or emulator PNG')
    parser.add_argument('--out-dir', type=Path, default=Path('visual-qa-report'))
    parser.add_argument('--tolerance', type=int, default=2, help='Ignored per-channel delta (0..255)')
    parser.add_argument('--max-changed-percent', type=float, default=0.5,
                        help='Maximum percentage of changed unmasked pixels (0..100)')
    parser.add_argument('--background', default='#FFFFFF', help='RGB backdrop for transparent PNGs')
    parser.add_argument('--mask', type=Path, help='Optional JSON with small ignored rectangles')
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.tolerance <= 255:
            raise ValueError('Tolerance must be between 0 and 255')
        if not 0 <= args.max_changed_percent <= 100:
            raise ValueError('Maximum changed percent must be between 0 and 100')
        code = compare(args.reference, args.actual, args.out_dir, args.tolerance,
                       args.max_changed_percent, args.background, args.mask)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f'reference-qa: {error}', file=sys.stderr)
        return 2
    print((args.out_dir / 'summary.md').read_text(encoding='utf-8'))
    return code


if __name__ == '__main__':
    sys.exit(main())
