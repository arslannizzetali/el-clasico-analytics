# Common tasks. `make help` lists them.
# The reference Clásico pipeline needs only Python; everything else uses the virtualenv and PostgreSQL in Docker.

PY      ?= .venv/bin/python
# load scope: all | league | clasico | ucl_finals
SCOPE   ?= all

.PHONY: help setup db download load quality dbt dagster pipeline analysis site run test clean

help:  ## list targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup:  ## create .venv and install requirements
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements-pipeline.txt

db:  ## start PostgreSQL (localhost:5434) and wait until it accepts connections
	docker compose up -d
	@until docker compose exec -T db pg_isready -U clasico -d clasico >/dev/null 2>&1; do sleep 1; done
	@echo "PostgreSQL ready"

download:  ## download raw StatsBomb files for SCOPE (all = ~2.5 GB)
	$(PY) scripts/download.py $(SCOPE)

load: db  ## load SCOPE into PostgreSQL (idempotent: only missing matches)
	$(PY) scripts/load_db.py $(SCOPE)

quality:  ## data quality checks on the loaded database (fails on errors)
	$(PY) scripts/check_quality.py

dbt:  ## dbt models and their tests (staging -> intermediate -> marts)
	cd dbt && ../.venv/bin/dbt build --profiles-dir .

dagster:  ## run the whole pipeline as the Dagster job full_pipeline (SCOPE sets the load scope)
	mkdir -p .dagster_home && touch .dagster_home/dagster.yaml
	DAGSTER_HOME=$(CURDIR)/.dagster_home CLASICO_SCOPE=$(SCOPE) .venv/bin/dagster job execute -m orchestration.clasico_pipeline -j full_pipeline

pipeline:  ## reference Clásico pipeline -> data/processed (standard library only)
	python3 pipeline.py

analysis:  ## league tables, intervals, BI and Parquet export -> data/league, data/bi, data/parquet
	$(PY) analysis/league.py > /dev/null
	$(PY) analysis/intervals.py
	$(PY) analysis/export_bi.py
	$(PY) analysis/export_parquet.py

site:  ## rebuild docs/index.html and the README charts
	python3 site/build_site.py
	python3 site/readme_charts.py

run: pipeline load quality dbt analysis site  ## everything, in order

test:  ## all tests (database tests skip if PostgreSQL is not loaded)
	$(PY) -W error::ResourceWarning -m unittest discover -s tests -v

clean:  ## stop PostgreSQL (data is kept in the Docker volume)
	docker compose stop
