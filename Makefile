.PHONY: test lint tree

test:
	python -m compileall src

lint:
	python -m py_compile $(shell find src -name '*.py')

tree:
	find . -maxdepth 3 | sort
