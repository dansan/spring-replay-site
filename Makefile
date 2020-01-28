.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

PY_MODULES := infolog_upload lobbyauth setup spring_replay_site srs
PY_PATHS := manage.py $(PY_MODULES)
PY_FILES := $(shell find $(PY_PATHS) -name '*.py')
ISORT_SKIP := --skip spring_replay_site/settings.py --skip srs/contrib/argparse.py --skip srs/contrib/pyCURLTransport.py --skip srs/SpringStatsViewer
EXCLUDE_BLACK := --exclude srs/SpringStatsViewer

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

format: ## format source code
	isort --apply --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --recursive  --project srs $(ISORT_SKIP) $(PY_PATHS)
	black --target-version py38 $(EXCLUDE_BLACK) $(PY_PATHS)

lint-isort:
	isort --check-only --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --recursive  --project srs $(ISORT_SKIP) $(PY_PATHS)

lint-black:
	black --check --target-version py38 $(EXCLUDE_BLACK) $(PY_PATHS)

lint-flake8:
	flake8 --max-line-length=105 --ignore=W503 $(PY_PATHS)

lint: lint-isort lint-black lint-flake8 ## check source code style

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	pip3 install -e .
