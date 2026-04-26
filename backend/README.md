# Backend

## Run locally

From the repo root:

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Add your MongoDB settings to `.env` before starting the server if you want database writes enabled.

The API will start at:

- `http://localhost:8000`
- `http://localhost:8000/health`
- `http://localhost:8000/docs`

If you already have a virtual environment, just activate it, `cd backend`, install requirements, and run:

```bash
uvicorn main:app --reload
```
