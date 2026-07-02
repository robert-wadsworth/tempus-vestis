"""Build the FAISS wardrobe vectorstore locally and upload it to GCS (PORT-27).

Manual, run-when-`data/wardrobe_rules.txt`-changes step — deliberately NOT part
of the deploy pipeline. The vectorstore is data, not code: the Cloud Run
container downloads these two files on startup instead of baking them into the
image, so the knowledge base can be updated without an image rebuild.

Usage (from the repo root):

    uv run python scripts/seed_vectorstore.py

Requires OPENAI_API_KEY (embeddings are computed once here, at build time) and
Application Default Credentials with write access to the bucket, e.g.
`gcloud auth application-default login`.
"""

import os
import sys
from pathlib import Path

# The seed script builds against the *local* index, never the container's /tmp
# copy — pin VECTORSTORE_PATH before importing core.rag so an env var meant for
# the deployed service can't redirect the build somewhere unexpected.
_LOCAL_VECTORSTORE_PATH = "data/vectorstore"
os.environ["VECTORSTORE_PATH"] = _LOCAL_VECTORSTORE_PATH

# Make src/ importable when run as a plain script (mirrors pyproject's pytest
# pythonpath) so this works without relying on an editable install.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
from google.cloud import storage  # noqa: E402

from core.rag import get_or_create_vectorstore  # noqa: E402

BUCKET_NAME = os.getenv("VECTORSTORE_BUCKET", "rw-portfolio-tempus-vestis-vectorstore")
_INDEX_FILES = ("index.faiss", "index.pkl")


def main() -> None:
    load_dotenv(_REPO_ROOT / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit(
            "OPENAI_API_KEY is not set — needed to embed the knowledge base. "
            "Add it to .env or the environment and re-run."
        )

    # Builds and saves to data/vectorstore/ if absent; loads it if already there.
    print(f"Building/loading local FAISS index at {_LOCAL_VECTORSTORE_PATH}/ ...")
    get_or_create_vectorstore()

    local_dir = _REPO_ROOT / _LOCAL_VECTORSTORE_PATH
    missing = [f for f in _INDEX_FILES if not (local_dir / f).exists()]
    if missing:
        sys.exit(f"Expected index files not found after build: {missing}")

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    for name in _INDEX_FILES:
        blob = bucket.blob(name)
        print(f"Uploading {name} -> gs://{BUCKET_NAME}/{name} ...")
        blob.upload_from_filename(str(local_dir / name))

    print("Done. Vectorstore is seeded in GCS.")


if __name__ == "__main__":
    main()
