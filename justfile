[private]
default:
    @just --list

# Crawl championship data (interactive prompt if no championship given)
[group("bvbb")]
crawl *args:
    uv run bvbb-crawl {{ args }}

# Run the Streamlit frontend
[group("bvbb")]
frontend:
    uv run streamlit run src/bvbb/frontend/app.py

# Install all dependencies
[group("dev")]
setup:
    uv sync
    uv run prek install

# Run all tests
[group("test")]
test *args:
    uv run python -m pytest {{ args }}

# Lint with ruff
[group("dev")]
lint:
    uv run ruff check src/ tests/

# Format with ruff
[group("dev")]
fmt:
    uv run ruff format src/ tests/

# Lint and auto-fix
[group("dev")]
fix:
    uv run ruff check --fix src/ tests/

# Check formatting without modifying
[group("dev")]
fmt-check:
    uv run ruff format --check src/ tests/

# Run pre-commit hooks
[group("dev")]
pre-commit:
    uv run prek run --all-files

# Run tests with coverage
[group("test")]
cov *args:
    uv run python -m pytest --cov=bvbb --cov-report=html {{ args }}

# Run all checks (lint + format check + tests)
[group("dev")]
check: lint fmt-check test

# Tail the log file
[group("utils")]
logs:
    tail -f logs/bvbb.log

# Clean generated files
[group("utils")]
clean:
    rm -rf data/ logs/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache .ruff_cache dist build *.egg-info
