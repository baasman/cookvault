.PHONY: dev install-dev

# Start all development services
dev:
	.venv/bin/honcho start -f Procfile.dev

# Install development dependencies
install-dev:
	uv sync --extra dev
	cd frontend && npm install
