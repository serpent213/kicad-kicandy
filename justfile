# Help
help:
  @just --list

# Format all Python files with Ruff
format:
  uv run ruff format .

# Run Ruff preview checks for lint issues
lint:
  uv run ruff check --preview .

# Execute the pytest suite
# test:
#   uv run pytest

# Format, lint, and run tests sequentially
check:
  just format
  just lint
  @: # just test

# Format then apply Ruff auto-fixes (unsafe)
fix:
  just format
  uv run ruff check --preview --fix --unsafe-fixes .
