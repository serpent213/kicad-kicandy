# KiCandy Icon Picker

KiCandy is a KiCad 9 Python action plugin that inserts Material Symbols glyphs as
free silkscreen text. Instead of typing a Unicode character manually, you get a
searchable gallery of icons grouped by font style (Outlined, Rounded, Sharp).

## Features

- Search-as-you-type filtering with live updates as you toggle icon sets.
- Persistent dialog state so the plugin remembers the last search text, enabled
  icon sets, and chosen layer.

## Usage

1. Load a PCB in KiCad 9 and run the **Insert Icon Text** action.
2. Type to search or toggle the icon family checkboxes. The list updates as you
   type; enabling at least one font is required.
3. Select the target silkscreen layer, highlight an icon, and press **Add Icon**
   (or double-click the row).
4. A `BoardText` item containing the glyph is created and pushed into an
   interactive move session so you can place it immediately.

### Notes

- The plugin expects the Material Symbols fonts to be available on the host OS.
  Only the codepoint metadata is downloaded today, but the metadata in
  `icon_fonts.py` already includes the TTF/WOFF2 URLs so font installation can
  be added later.
- Codepoint files are cached under `cache/` within the plugin directory. Delete
  the folder if you need to force a refresh.
- Dialog state is stored in `cache/kicandy_state.json` (or the KiCad plugin
  cache directory when `KICAD_CACHE_HOME` is set).
- wxPython version during development: 4.2.2a1 osx-cocoa (phoenix) wxWidgets 3.2.8

### Profiling

- Add `pyinstrument>=5.1.1` to `requirements.txt` (for KiCad to pick it up) to
  enable the optional startup profiler.
- When present, invoking the plugin writes PyInstrument output to
  `/tmp/kicandy_profile.txt` (text) and `/tmp/kicandy_profile.html` (HTML) after
  the dialog closes, making it easy to analyze slow launches.

## Extending

To add new icon sets, append entries to `ICON_FONTS` in `icon_fonts.py`. Provide
the human-readable name, style label, system font family, and download URLs for
both the codepoint file and any font binaries you want to expose later. The
dialog builds its checkbox list directly from this metadata so new sets will
appear automatically.
