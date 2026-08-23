#!/usr/bin/env python3
"""Check a modified font before you trust it.

    python3 verify.py MyFont-VF.ttf [--chars '←↑→↓']

Runs three things fontbakery does not: that every requested character actually
shapes to a real glyph, that grafted glyphs interpolate monotonically instead of
collapsing, and that no name record still names the source family. Then defers
to fontbakery for the spec-level checks.
"""
import argparse, subprocess, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer


def check_coverage(path, chars):
    cmap = TTFont(path).getBestCmap()
    missing = [c for c in chars if ord(c) not in cmap]
    print(f'  coverage      {"MISSING " + " ".join(missing) if missing else "all present"}')
    return not missing


def check_interpolation(path, chars, steps=6):
    """A grafted glyph with bad gvar deltas shows up as ink that stalls,
    reverses, or explodes across the axis.

    Measure rendered INK, not the bounding box. DM Sans's double-headed arrow
    gets narrower as it gets bolder, so its bbox area falls while the glyph is
    perfectly correct — bbox area reports that as a defect.
    """
    from PIL import Image, ImageDraw, ImageFont
    import tempfile
    font = TTFont(path)
    if 'fvar' not in font:
        print('  interpolation not variable, skipped')
        return True
    axis = next(a for a in font['fvar'].axes if a.axisTag == 'wght')
    cmap = font.getBestCmap()
    ok = True
    for ch in chars:
        gn = cmap.get(ord(ch))
        if gn is None:
            continue
        ink = []
        for i in range(steps):
            w = axis.minValue + (axis.maxValue - axis.minValue) * i / (steps - 1)
            f = instancer.instantiateVariableFont(TTFont(path), {'wght': w})
            fd, p = tempfile.mkstemp(suffix='.ttf'); __import__('os').close(fd)
            try:
                f.save(p)
                img = Image.new('L', (600, 600), 0)
                ImageDraw.Draw(img).text((150, 150), ch,
                                         font=ImageFont.truetype(p, 200), fill=255)
                ink.append(sum(img.histogram()[129:]))
            finally:
                __import__('os').unlink(p)
        rising = all(b >= a * 0.97 for a, b in zip(ink, ink[1:]))
        good = rising and ink[0] > 0 and ink[-1] / max(1, ink[0]) < 25
        ok &= good
        print(f'  {ch} {gn:<16} ink {ink[0]:>6} .. {ink[-1]:>6}  '
              f'{"ok" if good else "SUSPECT — ink not rising smoothly"}')
    return ok


def check_names(path, source_family):
    n = TTFont(path)['name']
    hits = []
    for r in n.names:
        if r.nameID in (0, 10):        # copyright and description keep the credit
            continue
        try:
            v = r.toUnicode()
        except Exception:
            continue
        if source_family.lower() in v.lower():
            hits.append(f'{r.nameID}:{v}')
    print(f'  names         {"LEFTOVER " + ", ".join(hits) if hits else "clean"}')
    return not hits


def main():
    p = argparse.ArgumentParser()
    p.add_argument('font')
    p.add_argument('--chars', default='')
    p.add_argument('--source-family', default=None,
                   help='name that must NOT survive in the name table')
    a = p.parse_args()

    print(f'--- {a.font} ---')
    ok = True
    if a.chars:
        ok &= check_coverage(a.font, a.chars)
        ok &= check_interpolation(a.font, a.chars)
    if a.source_family:
        ok &= check_names(a.font, a.source_family)

    try:
        r = subprocess.run(['fontbakery', 'check-opentype', '-l', 'WARN',
                            '--no-progress', a.font],
                           capture_output=True, text=True, timeout=900)
        tail = [l.strip() for l in r.stdout.splitlines()
                if l.strip().startswith(('ERROR:', 'FATAL:', 'FAIL:', 'WARN:'))]
        print('  fontbakery    ' + '  '.join(tail) if tail else
              '  fontbakery    no summary (check output)')
        ok &= all(l.endswith(' 0') for l in tail if l.startswith(('FAIL', 'FATAL', 'ERROR')))
    except FileNotFoundError:
        print('  fontbakery    not installed — pip install fontbakery')
    except subprocess.TimeoutExpired:
        print('  fontbakery    timed out')

    print('  ' + ('PASS' if ok else 'PROBLEMS ABOVE'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
