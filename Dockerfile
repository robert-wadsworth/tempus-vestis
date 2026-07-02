# Phase 1 (PORT-18/PORT-22): token-gated proxy + UI only.
# Deliberately does NOT install the LangGraph/FAISS stack from pyproject.toml —
# that's Phase 2. See app/requirements.txt for the Phase 1 dependency set.
FROM python:3.11-slim

WORKDIR /srv

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ app/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
