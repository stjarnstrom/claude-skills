# Reading and rebuilding contours

## The API traps

| Call | Returns | Trap |
|------|---------|------|
| `glyph.getCoordinates(glyf)` | `(coords, endPtsOfContours, flags)` — a **3-tuple** | Flags are at index **2**. `coords, flags = ...` silently binds flags to the contour ends |
| `flags[i] & 1` | 1 on-curve, 0 off-curve (quadratic control) | `lineTo` on an off-curve point flattens the curve |
| `glyph.isComposite()` | glyph references others | `i` is often `dotlessi` + `uni0307`; you cannot touch one contour without decomposing |
| `glyph.numberOfContours` | `-1` for composite, `0` for blank | A space is not a bug |

Split into contours with `endPtsOfContours`:

```python
coords, end_pts, flags = glyph.getCoordinates(glyf)
start = 0
for end in end_pts:
    pts, part_flags = coords[start:end + 1], flags[start:end + 1]
    start = end + 1
```

## Rebuilding with TTGlyphPen

Curve-preserving — for stems, bowls, anything that should stay smooth:

```python
pen.moveTo(tuple(pts[0]))
idx = 1
while idx < len(pts):
    if flags[idx] & 1:
        pen.lineTo(tuple(pts[idx])); idx += 1
    else:
        off = []
        while idx < len(pts) and not (flags[idx] & 1):
            off.append(tuple(pts[idx])); idx += 1
        off.append(tuple(pts[idx]) if idx < len(pts) else tuple(pts[0]))
        if idx < len(pts):
            idx += 1
        pen.qCurveTo(*off)
pen.closePath()
```

All-`lineTo` gives hard edges — right for a comma tail you want angular, wrong
everywhere else. Four `lineTo` points replace a dot with a square: compute the
contour's bounds, its centre, and the size you want.

## Copying a glyph wholesale

`DecomposingRecordingPen` → `TransformPen` → `TTGlyphPen` handles composites,
scaling, and skewing in one pass, and yields a simple self-contained glyph:

```python
rp = DecomposingRecordingPen(donor.getGlyphSet())
donor.getGlyphSet()[src].draw(rp)
pen = TTGlyphPen(host.getGlyphSet())
rp.replay(TransformPen(pen, Identity.scale(s, s)))
host['glyf'][dst] = pen.glyph()
```

`Identity.skew(-0.20, 0)` slants the **wrong way** — the sign convention leans
left. Use a positive value for a forward italic slant, and set
`post.italicAngle` to the negative of the angle you drew.

For boolean cleanup after skewing or overlapping, `skia-pathops`:

```python
sk = pathops.Path()
rp.replay(TransformPen(sk.getPen(), xform))
sk.simplify(fix_winding=True, keep_starting_points=False)
sk.draw(TTGlyphPen(gs))
```

## Measuring a stroke

Off the coordinate list, for a plain vertical stem — sort the distinct x values
and take the gap between the first two. Correct for `H`, `n`, `l`.

**Not** for anything diagonal or horizontal. On an arrow the two lowest y values
are the chevron's tips, not the shaft: that reports 62 units where the shaft is
actually 88. Rasterise instead and scan one pixel column through a part of the
glyph you know is plain stroke — `scripts/graft.py:shaft_thickness`.

Likewise, when checking that a variable glyph interpolates, measure **rendered
ink**, not bounding-box area. DM Sans's `↔` narrows as it gets bolder, so its
bbox shrinks while the glyph is entirely correct.

## GSUB: extend, never rebuild

```python
addOpenTypeFeatures(font, fea, tables=['GSUB'])   # REPLACES the table
```

On Sora that silently dropped `liga`, `frac`, `ss01` and eleven more. Build the
lookup by hand — `scripts/graft.py:append_single_subst_feature`. Two things it
gets right that are easy to miss: `FeatureRecord`s must stay in alphabetical
order by tag, and inserting one shifts every later index, so each langsys
`FeatureIndex` needs remapping.

To bake a feature in permanently instead — making alternates the default — remap
`cmap` through the feature's substitution mapping:

```python
for t in font['cmap'].tables:
    for cp, gn in list(t.cmap.items()):
        if gn in subs:
            t.cmap[cp] = subs[gn]
```
