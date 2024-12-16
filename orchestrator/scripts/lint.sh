#!/bin/bash
poetry run black src tests
poetry run isort src tests
poetry run flake8 src tests
poetry run mypy src
