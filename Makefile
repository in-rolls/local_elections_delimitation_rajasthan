PYTHON ?= python3

.PHONY: check lint test reproduce ci-docker

check: lint test

lint:
	$(PYTHON) -m black --check pipeline.py tests
	$(PYTHON) -m isort --check-only pipeline.py tests
	$(PYTHON) -m flake8 pipeline.py tests

test:
	$(PYTHON) -m pytest

reproduce:
	$(PYTHON) pipeline.py

ci-docker:
	docker run --rm -v "$(CURDIR):/work:ro" -w /tmp/project python:3.14 bash -c 'cp -a /work/. . && python -m pip install -r requirements.txt && make check PYTHON=python'
