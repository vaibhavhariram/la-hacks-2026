PYTHON := $(shell test -f venv/bin/python && echo venv/bin/python || echo python3)

.PHONY: install test stub simulate simulate-full simulate-no-post agent lint

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

stub:
	$(PYTHON) -m uvicorn stub.backend_stub:app --port 8001 --reload

simulate:
	$(PYTHON) scripts/run_demo.py --steps 4 --dt-minutes 30

simulate-full:
	$(PYTHON) scripts/run_demo.py --steps 12 --dt-minutes 30

simulate-no-post:
	$(PYTHON) scripts/run_demo.py --steps 12 --dt-minutes 30 --no-post

agent:
	$(PYTHON) agents/field_unit_agent.py

lint:
	$(PYTHON) -m py_compile gis/firms_pipeline.py gis/noaa_wind.py gis/fire_spread.py agents/gemma_parser.py agents/field_unit_agent.py stub/backend_stub.py scripts/run_demo.py && echo "syntax OK"
