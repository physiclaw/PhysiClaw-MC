.PHONY: build test

build:
	uv run --locked tools/build.py

test:
	uv run --locked python -m unittest discover -s tests
