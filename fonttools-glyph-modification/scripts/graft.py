#!/usr/bin/env python3
"""Graft glyphs from one font family into another, matched by size and weight.

    python3 graft.py --host 'Sora[wght].ttf' --donor DMSans.ttf \
        --glyphs arrowleft,arrowup,arrowright,arrowdown \
        --codepoints 2190=arrowleft,2191=arrowup,2192=arrowright,2193=arrowdown \
        --match cap_stem --probe '→' --donor-axes opsz=20 --out TrombGrotesque-VF.ttf

Also importable: cap_scale, match_donor_weight, transfer, build_gvar_deltas,
append_single_subst_feature.
"""
import argparse, os, sys, tempfile
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.transform import Identity
from fontTools.ttLib.tables._g_v_a_r import TupleVariation
from fontTools.ttLib.tables import otTables as ot

PPEM = 400


# --- measuring -------------------------------------------------------------

def stem_width(font, glyph='H'):
    """Width of a plain vertical stem, off the outline. Right for H, n, l."""
    gs = font.getGlyphSet()
    rp = DecomposingRecordingPen(gs)
    gs[glyph].draw(rp)
    xs = sorted({round(p[0]) for op, a in rp.value for p in a if isinstance(p, tuple)})
    return xs[1] - xs[0]


def shaft_thickness(font, char, at=0.12):
    """Thickness of a NON-vertical stroke, by rasterising and scanning one
    column of pixels `at` this fraction across the ink box.

    Do not read this off the coordinate list. On an arrow the two lowest y
    values are the chevron's tips, not the shaft — that misreports an 88-unit
    shaft as 62. Rendering is slower and indifferent to how the glyph is drawn.
    """
    from PIL import Image, ImageDraw, ImageFont
    fd, path = tempfile.mkstemp(suffix='.ttf'); os.close(fd)
    try:
        font.save(path)
        fnt = ImageFont.truetype(path, PPEM)
        img = Image.new('L', (PPEM * 3, PPEM * 3), 0)
        ImageDraw.Draw(img).text((PPEM, PPEM), char, font=fnt, fill=255)
        box = img.getbbox()
        if box is None:
            return None
        x0, y0, x1, y1 = box
        col, px = round(x0 + (x1 - x0) * at), img.load()
        run = best = 0
        for y in range(y0, y1 + 1):
            run = run + 1 if px[col, y] > 128 else 0
            best = max(best, run)
        return best * font['head'].unitsPerEm / PPEM
    finally:
        os.unlink(path)


def cap_scale(host, donor):
    """Uniform scale that puts the donor at the host's cap height. Because it is
    about the origin, vertical placement follows proportionally — no nudge."""
    return host['OS/2'].sCapHeight / donor['OS/2'].sCapHeight


def match_donor_weight(donor_path, target, scale, fixed_axes, measure,
                       lo=None, hi=None, iters=14):
    """Bisect the donor's wght until measure(donor) * scale == target.

    Match the stroke you actually care about. Matching the donor's H to the
    host's H only preserves the DONOR's arrow-to-stem relationship, which is
    not the same as belonging in the host. Returns (wght, achieved, clamped).
    """
    axis = next(a for a in TTFont(donor_path)['fvar'].axes if a.axisTag == 'wght')
    lo = axis.minValue if lo is None else lo
    hi = axis.maxValue if hi is None else hi

    def scaled(w):
        f = instancer.instantiateVariableFont(TTFont(donor_path),
                                             {**fixed_axes, 'wght': w})
        return measure(f) * scale

    lo_s, hi_s = scaled(lo), scaled(hi)
    if target >= hi_s:
        return hi, hi_s, True
    if target <= lo_s:
        return lo, lo_s, True
    a, b = lo, hi
    for _ in range(iters):
        mid = (a + b) / 2
        if scaled(mid) < target:
            a = mid
        else:
            b = mid
    w = round((a + b) / 2, 1)
    return w, scaled(w), False


# --- transferring ----------------------------------------------------------

def transfer(donor, host, src, dst, scale):
    """Copy one glyph, scaled, into host['glyf'] with hmtx. Composites are
    decomposed, so the result is always simple and self-contained."""
    dgs, hgs = donor.getGlyphSet(), host.getGlyphSet()
    rp = DecomposingRecordingPen(dgs)
    dgs[src].draw(rp)
    pen = TTGlyphPen(hgs)
    rp.replay(TransformPen(pen, Identity.scale(scale, scale)))
    glyph = pen.glyph()
    glyph.recalcBounds(host['glyf'])       # maxp.recalc() reads xMin; without
    host['glyf'][dst] = glyph              # this it raises AttributeError
    adv = round(donor['hmtx'][src][0] * scale)
    bp = BoundsPen(hgs)
    glyph.draw(bp, host['glyf'])
    host['hmtx'][dst] = (adv, round(bp.bounds[0]) if bp.bounds else 0)
    return adv


def outline_points(host, name):
    return [tuple(p) for p in host['glyf'][name].getCoordinates(host['glyf'])[0]]


def build_gvar_deltas(host, name, masters, default_coords):
    """masters: {normalized_peak: Glyph}. Writes one TupleVariation per peak
    with the 4 phantom points appended as zero deltas, holding the advance
    steady across the axis.

    New glyphs have no original tuple to copy phantom deltas from — that is the
    case the usual recipe omits.
    """
    tvs = []
    for peak, glyph in masters.items():
        mc = [tuple(p) for p in glyph.getCoordinates(host['glyf'])[0]]
        if len(mc) != len(default_coords):
            raise ValueError(f'{name}: {len(mc)} points at peak {peak} vs '
                             f'{len(default_coords)} at default — not interpolatable')
        deltas = [(round(m[0] - d[0]), round(m[1] - d[1]))
                  for m, d in zip(mc, default_coords)]
        deltas += [(0, 0)] * 4                 # left, right, top, bottom
        axes = {'wght': (-1.0, -1.0, 0.0)} if peak < 0 else {'wght': (0.0, 1.0, 1.0)}
        tvs.append(TupleVariation(axes, deltas))
    host['gvar'].variations[name] = tvs


def append_single_subst_feature(font, tag, mapping):
    """Add a feature to an existing GSUB without destroying what is there.

    feaLib's addOpenTypeFeatures(font, fea, tables=['GSUB']) REPLACES the table.
    On Sora that silently dropped liga, frac, ss01 and eleven more.
    """
    gsub = font['GSUB'].table
    st = ot.SingleSubst(); st.mapping = dict(mapping)
    lk = ot.Lookup(); lk.LookupType = 1; lk.LookupFlag = 0
    lk.SubTable = [st]; lk.SubTableCount = 1
    gsub.LookupList.Lookup.append(lk)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    idx = len(gsub.LookupList.Lookup) - 1

    feat = ot.Feature(); feat.FeatureParams = None
    feat.LookupListIndex = [idx]; feat.LookupCount = 1
    rec = ot.FeatureRecord(); rec.FeatureTag = tag; rec.Feature = feat
    recs = gsub.FeatureList.FeatureRecord
    pos = next((i for i, r in enumerate(recs) if r.FeatureTag > tag), len(recs))
    recs.insert(pos, rec)                      # FeatureRecords must stay sorted
    gsub.FeatureList.FeatureCount = len(recs)

    for sr in gsub.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]:
            if ls is None:
                continue
            ls.FeatureIndex = sorted(
                [i + 1 if i >= pos else i for i in ls.FeatureIndex] + [pos])
            ls.FeatureCount = len(ls.FeatureIndex)


def finalise(host):
    """Everything that has to happen after adding glyphs, in order."""
    if 'HVAR' in host:
        # HVAR outranks gvar's phantom points and has no entries for glyphs
        # added after the fact. gvar already carries advance variations.
        del host['HVAR']
    if 'DSIG' in host:
        del host['DSIG']
    host.setGlyphOrder(host['glyf'].glyphOrder)   # TTFont caches its own order
    host['maxp'].recalc(host)
    host.recalcBBoxes = True


# --- driver ----------------------------------------------------------------

def graft(host_path, donor_path, glyphs, codepoints, match='cap_stem',
          probe=None, donor_axes=None, alternate_set=None, verbose=True):
    donor_axes = donor_axes or {}
    host = TTFont(host_path)
    scale = cap_scale(host, TTFont(donor_path))
    ref = {'cap_stem': 'H', 'lc_stem': 'n'}[match]

    if probe:
        def measure(f):
            return shaft_thickness(f, probe)
    else:
        def measure(f):
            return stem_width(f, ref)

    axis = next(a for a in host['fvar'].axes if a.axisTag == 'wght')
    peaks = {}
    for tv in host['gvar'].variations.get('H', []):
        lo, pk, hi = tv.axes['wght']
        peaks[pk] = axis.minValue if pk < 0 else axis.maxValue
    locations = {0.0: axis.defaultValue, **peaks}

    picks = {}
    for peak, host_w in locations.items():
        inst = instancer.instantiateVariableFont(TTFont(host_path), {'wght': host_w})
        target = stem_width(inst, ref)
        w, got, clamped = match_donor_weight(donor_path, target, scale,
                                            donor_axes, measure)
        picks[peak] = w
        if verbose:
            note = '  CLAMPED — donor cannot reach it' if clamped else ''
            print(f'  host wght {host_w:>4.0f}  {ref} stem {target:>4}  ->  donor '
                  f'wght {w:>6.1f}  stroke {got:>5.1f}{note}')

    donors = {p: instancer.instantiateVariableFont(TTFont(donor_path),
                                                   {**donor_axes, 'wght': w})
              for p, w in picks.items()}

    for src in glyphs:
        transfer(donors[0.0], host, src, src, scale)
        default_coords = outline_points(host, src)
        masters = {}
        for peak in peaks:
            scratch = TTFont(host_path)
            transfer(donors[peak], scratch, src, src, scale)
            masters[peak] = scratch['glyf'][src]
        if masters:
            build_gvar_deltas(host, src, masters, default_coords)

    for t in host['cmap'].tables:
        if t.isUnicode():
            for cp, gn in codepoints.items():
                t.cmap[cp] = gn

    if alternate_set:
        alts = [g + '.' + alternate_set for g in glyphs]
        for src in alts:
            if src in donors[0.0].getGlyphSet():
                transfer(donors[0.0], host, src, src, scale)
        append_single_subst_feature(
            host, alternate_set,
            {g: g + '.' + alternate_set for g in glyphs
             if g + '.' + alternate_set in host['glyf']})

    finalise(host)
    return host


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--host', required=True, help='variable font to graft INTO')
    p.add_argument('--donor', required=True, help='variable font to take glyphs FROM')
    p.add_argument('--glyphs', required=True, help='comma-separated donor glyph names')
    p.add_argument('--codepoints', default='', help='hex=glyphname,... to map in cmap')
    p.add_argument('--match', default='cap_stem', choices=['cap_stem', 'lc_stem'],
                   help='which host stem the graft should weigh the same as')
    p.add_argument('--probe', default=None,
                   help='a character to raster-measure; required for non-vertical strokes')
    p.add_argument('--donor-axes', default='', help='tag=value,... pinned on the donor')
    p.add_argument('--alternate-set', default=None,
                   help='also graft .<tag> alternates and wire them to that feature')
    p.add_argument('--out', required=True)
    a = p.parse_args()

    def kv(s, cast=float):
        return {k: cast(v) for k, v in
                (item.split('=') for item in s.split(',') if item)}

    print(f'--- grafting {a.glyphs.count(",") + 1} glyphs ---')
    font = graft(a.host, a.donor, a.glyphs.split(','),
                 {int(k, 16): v for k, v in kv(a.codepoints, str).items()},
                 a.match, a.probe, kv(a.donor_axes), a.alternate_set)
    font.save(a.out)
    print(f'  -> {a.out}')
    print('  now run: python3 verify.py ' + a.out)


if __name__ == '__main__':
    sys.exit(main())
