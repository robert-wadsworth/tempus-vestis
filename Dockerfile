# Phase 2 (PORT-30): the image now carries the full pipeline. This supersedes
# the Phase 1 "app/ isolated from src/" decision (knowledge/decisions.md):
# POST /recommend runs the LangGraph/FAISS/OpenAI stack, so app/ and src/ share
# one dependency tree now. Installing `.[web]` resolves the pipeline deps
# (pyproject [project].dependencies) and the web layer (the `web` extra)
# together in a single pip pass — and installs the src/ package itself so
# `core`/`tools` are importable.
#
# The FAISS index is NOT baked in — it's downloaded from GCS on startup
# (PORT-27), so data/wardrobe_rules.txt is intentionally absent from the image.
FROM python:3.11-slim

WORKDIR /srv

COPY pyproject.toml pyproject.toml
COPY src/ src/
RUN pip install --no-cache-dir .[web]

COPY app/ app/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
