.PHONY: dev install-dev docs-serve docs-build

# Start all development services
#
# DYLD_FALLBACK_LIBRARY_PATH is needed on macOS so WeasyPrint can dlopen the
# Homebrew-installed pango/cairo/glib dylibs (their on-disk filenames don't
# match the bare names ctypes.util.find_library looks for). Harmless on Linux,
# which ignores DYLD_* and has the libs on the standard loader path anyway.
dev:
	DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$$DYLD_FALLBACK_LIBRARY_PATH \
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
