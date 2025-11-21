# Repository Guidelines

## Project Structure & Module Organization
- `kicandy_action.py` contains the main KiCad action that launches the icon picker dialog and writes board text items.
- `icon_fonts.py`, `icon_repository.py`, and `state_store.py` provide metadata, download/search logic, and dialog state persistence.
- `ui/` holds the wxPython dialog classes; add new widgets or layouts here.
- `tmp/` mirrors upstream KiCad SDK samples and should stay untouched.
- Tests should live beside the feature they exercise (e.g., `tests/test_icon_repository.py`).

## Build, Test, and Development Commands
- `uv run format` — run Ruff formatter over the entire tree.
- `uv run lint` — execute Ruff checks (preview mode) for lint issues.
- `uv run test` — run pytest; ideal for repository modules that are pure Python.
- `uv run check` — chain format check, lint, and pytest for CI parity.
- `uv run fix` — format and apply Ruff’s auto-fixes (unsafe; review output).

## Coding Style & Naming Conventions
- Follow Ruff’s defaults: 4-space indentation, max line length 100, and explicit imports.
- Use descriptive module-level names (`icon_repository`, not abbreviations).
- wxPython UI classes should end with `Dialog` or `Panel` to match current patterns.
- Persist user-visible strings in `README.md` or dedicated resources to keep code minimal.

## Testing Guidelines
- Pytest is the standard harness; name files `test_*.py` and functions `test_*`.
- Mock KiCad or network interactions using fixtures; do not hit remote URLs in unit tests.
- Strive for smoke coverage on repository helpers (parsers, caching) before touching UI logic.

## Commit & Pull Request Guidelines
- Keep commits scoped: “Add icon cache parser” over “Misc fixes”.
- Reference tracked issues in the commit body when applicable (`Fixes #12`).
- PRs should summarize behavior changes, list testing performed, and include screenshots/GIFs for UI tweaks.
- Ensure `uv run check` passes before requesting review; CI mirrors these scripts.
