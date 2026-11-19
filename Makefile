.PHONY: build check test

build:
	uv run --locked python tools/build.py

check:
	uv run --locked python -m unittest discover -s tests

test: check
