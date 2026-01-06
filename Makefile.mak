# ============================
# Django Project Makefile
# ============================

.PHONY: help setup install migrate run shell clean

PYTHON := python
VENV := .venv
PIP := $(VENV)/bin/pip
DJANGO := $(VENV)/bin/python manage.py

help:
	@echo ""
	@echo "Available commands:"
	@echo "  make setup      Create venv, install deps, run migrations"
	@echo "  make install    Install Python dependencies"
	@echo "  make migrate    Create and apply database migrations"
	@echo "  make run        Start the development server"
	@echo "  make shell      Open Django shell"
	@echo "  make clean      Remove venv and compiled files"
	@echo ""

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)

install: $(VENV)/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

migrate:
	$(DJANGO) makemigrations
	$(DJANGO) migrate

setup: install migrate

run:
	$(DJANGO) runserver

shell:
	$(DJANGO) shell

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
