PYTHON := $(shell test -f venv/bin/python && echo venv/bin/python || echo python3)
NPM := npm

.PHONY: install test stub demo-data simulate simulate-full simulate-no-post agent lint frontend-build backend-smoke demo-smoke demo-replay

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

stub:
	$(PYTHON) -m uvicorn stub.backend_stub:app --port 8001 --reload

demo-data:
	AEGIS_DATA_MODE=real $(PYTHON) -m gis.firms_pipeline
	AEGIS_DATA_MODE=real $(PYTHON) -m gis.noaa_wind
	AEGIS_DATA_MODE=auto $(PYTHON) scripts/run_demo.py --steps 2 --dt-minutes 30 --no-post

simulate:
	$(PYTHON) scripts/run_demo.py --steps 4 --dt-minutes 30

simulate-full:
	$(PYTHON) scripts/run_demo.py --steps 12 --dt-minutes 30

simulate-no-post:
	$(PYTHON) scripts/run_demo.py --steps 12 --dt-minutes 30 --no-post

frontend-build:
	cd frontend && test -d node_modules || $(NPM) ci
	cd frontend && $(NPM) run build

backend-smoke:
	$(PYTHON) scripts/backend_smoke.py

demo-smoke: lint test simulate-no-post
	$(PYTHON) scripts/backend_smoke.py --optional

demo-replay:
	BACKEND_URL=http://127.0.0.1:8000 AEGIS_DATA_MODE=fixture $(PYTHON) scripts/run_demo.py --steps 2 --dt-minutes 30

agent:
	$(PYTHON) agents/field_unit_agent.py

lint:
	$(PYTHON) -m py_compile gis/firms_pipeline.py gis/noaa_wind.py gis/fire_spread.py agents/gemma_parser.py agents/field_unit_agent.py backend/routing_engine.py stub/backend_stub.py scripts/run_demo.py scripts/backend_smoke.py && echo "syntax OK"
