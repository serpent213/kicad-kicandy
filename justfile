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
test:
  uv run -m pytest

# Execute the pytest suite with downloads
test-dl:
  uv run -m pytest --run-download

# Format, lint, and run tests sequentially
check:
  just format
  just lint
  just test

# Run format check, lint and full tests
ci:
  uv run --group ci --no-default-groups ruff format --check .
  uv run --group ci --no-default-groups ruff check --preview .
  uv run --group ci --no-default-groups -m pytest --run-download

# Format then apply Ruff auto-fixes (unsafe)
fix:
  just format
  uv run ruff check --preview --fix --unsafe-fixes .
