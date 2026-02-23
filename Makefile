.PHONY: dev install-dev docs-serve docs-build

# Start all development services
dev:
	.venv/bin/honcho start -f Procfile.dev

# Install development dependencies
install-dev:
	uv sync --extra dev
	cd frontend && npm install

# Serve documentation locally
docs-serve:
	uv run --extra docs mkdocs serve -a localhost:8007

# Build documentation
docs-build:
	uv run --extra docs mkdocs build
