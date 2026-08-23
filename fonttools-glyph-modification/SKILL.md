---
name: fonttools-glyph-modification
description: Use when building a derivative typeface from an open-source font with fontTools — modifying or replacing glyph outlines, borrowing glyphs from another family, keeping variable font interpolation intact, renaming and relicensing, or exporting statics and woff2. Symptoms - destroyed curves, glyphs that distort along the axis, arrows or symbols at the wrong weight, lost OpenType features, leftover original font names, Figma showing the old family.
---

# fontTools glyph modification

Surgically changing a TrueType font: outlines, borrowed glyphs, variable font
deltas, name table, export. Every trap in here was hit for real.

## Order of work

1. **Check the licence first.** Reserved Font Name in the source OFL means you
   may not rename it. `references/metadata.md`.
2. **Get the source.** `raw.githubusercontent.com/google/fonts/main/ofl/<family>/`
   works from a sandbox where `fonts.googleapis.com` and `fonts.gstatic.com` are
   blocked, and it is the canonical upstream anyway.
3. **Work on the variable font, not the statics.** Modify the VF, fix its gvar,
   then instance the statics from it. Modifying eight statics separately
   guarantees they drift apart.
4. **Look at the result.** Pillow rasterizes a specimen in a dozen lines. Numbers
   agreeing is not the same as the glyph being right.
5. **Verify.** `python3 scripts/verify.py FONT.ttf --chars '←↑→' --source-family Sora`
   — coverage, interpolation, name leftovers, then fontbakery. Expect 0 FAIL.

## Borrowing glyphs from another family

The common case: a typeface you like is missing glyphs that another draws well.
Copying the outlines across gives you glyphs at the wrong size and the wrong
weight for their new home. Three corrections, in order:

**Size** — scale by the cap-height ratio. A uniform scale about the origin
carries vertical placement along proportionally, so no separate baseline nudge.

**Weight** — bisect the donor's `wght` axis until the *donor glyph's own stroke*,
once scaled, equals the host's stem. Matching H stem to H stem only preserves the
donor's internal relationship, which is a different thing from belonging in the
host. Choose which host stem is the reference: its cap stem (the symbol carries
like a capital) or its lowercase stem (it recedes into the text). Watch for
clamping — the donor may not be able to draw a stroke light or heavy enough for
the host's extremes, and a clamp is worth reporting rather than swallowing.

**Interpolation** — match at every host master and write real gvar deltas, so the
graft moves along the axis like everything else. `references/gvar.md`.

```bash
python3 scripts/graft.py --host 'Sora[wght].ttf' --donor DMSans.ttf \
  --glyphs arrowleft,arrowright --codepoints 2190=arrowleft,2192=arrowright \
  --match cap_stem --probe '→' --donor-axes opsz=20 --out Out-VF.ttf
```

`--probe` raster-measures that character's stroke instead of reading the
outline — required for anything not a plain vertical stem. `--alternate-set ss08`
also brings over `.ss08` variants and wires them to a real feature.

## The five that cost the most time

| | |
|---|---|
| `coords, flags = glyph.getCoordinates(...)` | It is a **3-tuple**. Flags are index 2 |
| `addOpenTypeFeatures(..., tables=['GSUB'])` | **Replaces** GSUB. Dropped 14 features from Sora. Append by hand |
| `HVAR` present | Outranks gvar phantom points and has no entry for glyphs you add. Delete it |
| Stroke width off the coordinate list | Lies for anything diagonal or horizontal. Rasterize and scan a column |
| nameID 1 set, 16/17/25 not | Figma reads 16/17. The family fragments in every font menu |

## Reference

- `references/outlines.md` — coordinate reading, contour rebuilding, composites,
  copying glyphs across fonts, boolean ops, measuring strokes, GSUB surgery
- `references/gvar.md` — deltas after modifying or adding glyphs, phantom points,
  masters, HVAR, avar, and the post-add incantation
- `references/metadata.md` — Reserved Font Names, which nameIDs to write, RIBBI,
  scrubbing high nameIDs, Figma

## Environment

`fontTools` is usually preinstalled. `pip install --break-system-packages
fontmake skia-pathops ufo2ft glyphsLib uharfbuzz brotli fontbakery` covers the
rest; all of it works in an ephemeral cloud sandbox. There is no GUI font editor,
so everything here is programmatic — a script you keep beats a session you
cannot repeat.
