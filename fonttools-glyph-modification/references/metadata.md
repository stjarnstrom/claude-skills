# Name table and OFL compliance

## Before anything: may you rename it at all?

Check the source's OFL for a **Reserved Font Name**. If the licence reserves the
name, a derivative may not use it *or* anything confusingly similar — and the
check is the licence text, not the family name. Neither Sora nor DM Sans reserves
one, so `Tromb Grotesque` from Sora is fine. Ship `OFL.txt` with the output
either way, and keep every upstream copyright notice.

When you combine two OFL families, **both** notices travel with the result:

```python
notices = [f['name'].getName(0, 3, 1, 1033).toUnicode() for f in (host, donor)]
name.setName('Copyright 2026 You. ' + '  '.join(notices), 0, 3, 1, 1033)
```

## Which nameIDs to write

| nameID | Field | Rule |
|--------|-------|------|
| 0 | Copyright | **Additive** — yours first, every original retained |
| 1, 4, 6 | Family / Full / PostScript | Replace |
| 3 | Unique ID | `version;VENDOR;PSName` |
| 9 | Designer | `"Original Authors; modified by You"` |
| 10 | Description | Say what the derivative is. Survives scrubbing |
| 13, 14 | Licence / URL | The OFL text and `openfontlicense.org` |
| 16, 17 | Typographic Family / Subfamily | **Must overwrite** — Figma reads these, not 1/2 |
| 25 | Variations PS Prefix | **Must overwrite** — variable font PostScript name |

Empty fields do not clear themselves. `removeNames(nameID=...)` or the original
value survives.

## RIBBI, and why nameID 2 is not the style name

For static fonts nameID 2 may only be `Regular`, `Italic`, `Bold`, or
`Bold Italic`. Any other weight bakes into nameID 1 — family `"MyFont Medium"`,
subfamily `"Regular"` — while 16/17 hold the real grouping (`"MyFont"` /
`"Medium"`). Get this wrong and the family fragments into separate entries in
every font menu.

For a **variable** font, nameID 2 and 17 must match the fvar default axis value.
If the default `wght` is 300, the style is `Light`, not `Regular`. Read it off
the matching named instance rather than assuming.

Bold: set `OS/2.fsSelection` bit 5, clear bit 6, set `head.macStyle` bit 0.
Vendor: `OS/2.achVendID` to your 4-character tag.

## Scrubbing

After writing your names, walk every record and remove any that still mentions
the source family — skipping 0 and 10, which keep the credit deliberately.

High nameIDs (256+) are where the source's own PostScript names hide: fvar
instance names and STAT axis value labels. Rewriting fvar instances means
clearing those IDs and issuing fresh ones from 256 up. If STAT still points at
IDs you deleted, deleting the STAT table is cleaner than half-repairing it —
apps fall back to fvar instances.

## Figma

- Figma reads nameID 16/17 for the family menu. Always set both.
- An `MVAR` table can crash Figma's variable-axes panel. `del font['MVAR']` if
  you do not need metrics variation.
- Figma caches hard. To see a change: delete the old font, restart Figma, close
  and reopen the file, re-upload.
