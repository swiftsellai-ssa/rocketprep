# ============================================================
# RocketPrep Simulator — Makefile (Windows GnuWin32)
# Usage: make <target>
# ============================================================

.DEFAULT_GOAL := help
.PHONY: help install dev test test-unit test-integration test-cov \
        lint format fix check clean reset docs

# ── Help ──────────────────────────────────────────────────────────────────────────

help:
	@echo RocketPrep Simulator - available commands
	@echo ==========================================
	@echo make install          - Install all dependencies
	@echo make dev              - Start dev server with hot reload
	@echo make test             - Run all tests
	@echo make test-unit        - Run unit tests only
	@echo make test-integration - Run integration tests only
	@echo make test-cov         - Run tests with coverage report
	@echo make lint             - Check code with Ruff (no fixes)
	@echo make format           - Format code with Ruff
	@echo make fix              - Auto-fix lint issues and format
	@echo make clean            - Remove caches and generated files
	@echo make reset            - Full reset, clean + reinstall deps
	@echo make docs             - Open API docs in browser

# ── Setup ─────────────────────────────────────────────────────────────────────────

install:
	uv sync

# ── Development ───────────────────────────────────────────────────────────────────

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docs:
	start http://localhost:8000/docs

# ── Testing ───────────────────────────────────────────────────────────────────────

test:
	uv run pytest

test-unit:
	uv run pytest -m unit

test-integration:
	uv run pytest -m integration

test-cov:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

# ── Linting & formatting ──────────────────────────────────────────────────────────

lint:
	uv run ruff check .

format:
	uv run ruff format .

fix:
	uv run ruff check . --fix
	uv run ruff format .

check: lint

# ── Maintenance ───────────────────────────────────────────────────────────────────

clean:
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist .coverage del .coverage
	@echo Cleaned.

reset: clean
	@if exist .venv rmdir /s /q .venv
	uv sync
	@echo Reset complete.
