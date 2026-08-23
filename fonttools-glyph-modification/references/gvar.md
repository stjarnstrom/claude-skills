# Variable font deltas after you change outlines

`glyf` holds the default instance. Every other point on the axis comes from
`gvar` deltas. Change an outline and leave `gvar` alone and the font interpolates
from your new default toward the *old* shape — usually visible as a glyph that
distorts as the axis moves rather than one that is obviously broken.

## Reading what is there

```python
for tv in font['gvar'].variations['H']:
    print(tv.axes)          # {'wght': (start, peak, end)} in normalized coords
    print(len(tv.coordinates))   # numPoints + 4
```

The peaks tell you where the masters are. Two masters at the extremes gives
tents `{'wght': (-1.0, -1.0, 0.0)}` and `{'wght': (0.0, 1.0, 1.0)}`; the default
sits at 0.0 and has no tuple of its own. Normalized ∓1 map to the axis min and
max in `fvar`.

The **last four coordinates are phantom points** — left, right, top, bottom.
Left and right carry the advance and side bearing variations. They are not
optional: a tuple with `numPoints` entries instead of `numPoints + 4` is
malformed.

## Modifying an existing glyph

Point count unchanged: the existing deltas still apply, and moving the default
outline moves every instance with it. Often that is what you want.

Point count changed (a 12-point circle squared to 4 points, say): the deltas are
invalid and must be rebuilt.

1. Instantiate at the default → apply your modification → record `default_coords`
2. For each master peak: instantiate there → apply the same modification →
   record `peak_coords`
3. Delta per point = `peak_coords[i] - default_coords[i]`
4. Reuse the original tuple's last four phantom deltas

## Adding a glyph that was never there

Same as above, except step 4 has nothing to reuse. Write four zero deltas — the
advance then holds steady across the axis, which is right for a symbol and
acceptable for most else. Vary it deliberately if you need to.

All masters must have **identical point counts and order**. They will if they
come from one interpolatable source instanced at different weights. Assert it
rather than trusting it — a mismatch here produces a font that loads and renders
garbage at every position except the default.

## HVAR outranks gvar

If `HVAR` is present it supplies advance variations and gvar's phantom points are
ignored. It is indexed by glyph ID, so glyphs appended after the fact fall
outside its mapping. When gvar already carries the phantom deltas, deleting HVAR
is correct rather than lossy:

```python
if 'HVAR' in font:
    del font['HVAR']
```

## avar

`gvar` peaks are in the font's *internal* normalized space. With an `avar` table
present, invert it before treating a peak as a user-space axis value:

```python
from fontTools.varLib.models import piecewiseLinearMap
user_norm = piecewiseLinearMap(gvar_norm, {v: k for k, v in avar_segments.items()})
```

## After adding any glyph

```python
glyph.recalcBounds(font['glyf'])          # maxp.recalc reads xMin; else AttributeError
font.setGlyphOrder(font['glyf'].glyphOrder)   # TTFont caches its own order
font['maxp'].recalc(font)
font.recalcBBoxes = True
```
