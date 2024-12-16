#!/bin/bash
poetry run pytest tests -v --cov=orchestrator --cov-report=term-missing
