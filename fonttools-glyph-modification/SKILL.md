---
name: fonttools-glyph-modification
description: Use when modifying TrueType font glyphs with fontTools - replacing contours, decomposing composites, updating variable font gvar deltas, or managing OFL font metadata. Symptoms - destroyed curves, wrong dot shapes, broken variable font interpolation, leftover original font names in metadata.
---

# fontTools TrueType Glyph Modification

## Overview
Reference for surgically modifying TrueType glyph outlines with fontTools. Covers the non-obvious pitfalls in coordinate reading, contour reconstruction, composite handling, variable font delta recomputation, and OFL metadata compliance.

## Quick Reference

| API | Returns | Pitfall |
|-----|---------|---------|
| `glyph.getCoordinates(glyf_table)` | `(coords, endPtsOfContours, flags)` — **3-tuple** | Flags are at index **2**, not 1 |
| `flags[i] & 1` | `1` = on-curve, `0` = off-curve (quadratic control point) | Using `lineTo` for off-curve points destroys curves |
| `glyph.isComposite()` | Whether glyph references other glyphs | Must decompose composites to modify individual contours |
| `gvar.variations[name]` | List of `TupleVariation` with normalized axis coords | Deltas include 4 phantom points at end |

## Reading Glyph Data

```python
coords, _, flags = glyph.getCoordinates(glyf_table)  # NOT [0:2]
```

Split into contours using `endPtsOfContours`:
```python
start = 0
for end_idx in glyph.endPtsOfContours:
    pts = coords[start:end_idx + 1]
    part_flags = flags[start:end_idx + 1]
    start = end_idx + 1
```

## Reconstructing Contours with TTGlyphPen

**Curve-preserving** (for stems, letter bodies):
```python
pen.moveTo(tuple(pts[0]))
idx = 1
while idx < len(pts):
    if flags[idx] & 1:  # on-curve
        pen.lineTo(tuple(pts[idx])); idx += 1
    else:  # collect off-curve run → qCurveTo
        off = []
        while idx < len(pts) and not (flags[idx] & 1):
            off.append(tuple(pts[idx])); idx += 1
        off.append(tuple(pts[idx]) if idx < len(pts) else tuple(pts[0]))
        if idx < len(pts): idx += 1
        pen.qCurveTo(*off)
pen.closePath()
```

**Hard-edge** (all lineTo, makes curves angular): Use for comma tails, shapes where you want straight edges but original geometry preserved.

**Square replacement** (4 lineTo points): For dots, tittles. Compute bounds, center, desired size.

## Composite Glyphs

Some glyphs (e.g., `i` = `dotlessi` + `uni0307`) are composites. `isComposite()` returns True, and `glyph.components` gives references. To modify individual contours, decompose by reading each component's base glyph and applying the component offset:
```python
for comp in glyph.components:
    base_coords, _, base_flags = glyf_table[comp.glyphName].getCoordinates(glyf_table)
    shifted = [(c[0] + comp.x, c[1] + comp.y) for c in base_coords]
```

## Variable Font gvar Recomputation

When you change glyph point count (e.g., 12-point circle → 4-point square), gvar deltas become invalid. Pattern:

1. Instantiate at default weight → modify → get `default_coords`
2. For each gvar tuple peak: instantiate at that weight → modify → get `peak_coords`
3. New delta = `peak_coords - default_coords` per point
4. Append original phantom point deltas (last 4 entries from original tuple)

**avar inversion**: gvar uses internal normalized values. If avar table exists, invert it before converting to user-space:
```python
from fontTools.varLib.models import piecewiseLinearMap
inv_avar = {v: k for k, v in avar_segments.items()}
user_norm = piecewiseLinearMap(gvar_norm, inv_avar)
```

## OFL Metadata Compliance

| nameID | Field | Rule |
|--------|-------|------|
| 0 | Copyright | **Additive**: prepend yours, retain original |
| 1, 4, 6 | Family/Full/PS | Replace with new name |
| 3 | Unique ID | `version;VENDOR;PSName` |
| 9 | Designer | `"Original Authors; modified by You"` |
| 16, 17 | Typographic Family/Sub | **Must overwrite** — Figma reads these |
| 25 | Variations PS Prefix | **Must overwrite** — variable font PS name |

**Bold metadata**: Set `OS/2.fsSelection` bit 5 (BOLD), clear bit 6 (REGULAR). Set `head.macStyle` bit 0.

**Scrub leftovers**: After setting your names, scan all name entries and remove any still referencing the original font name (except nameID 0 copyright and 10 description).

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `coords, flags = getCoordinates(...)` | Use `coords, _, flags = ...` (3-tuple) |
| `lineTo` for all points | Check `flags[i] & 1`, use `qCurveTo` for off-curve runs |
| Skip composite glyphs | Decompose with component offsets for precise control |
| Modify glyf only in variable font | Must recompute gvar deltas at each variation peak |
| Linear norm→user conversion | Invert avar table first if present |
| Set nameID 1 only | Also set 16, 17, 25 — apps like Figma read these |
| Empty metadata fields leave originals | Use `removeNames()` to clear, not just skip |
