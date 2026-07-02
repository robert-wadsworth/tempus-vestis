# FAISS vectorstore bucket (PORT-27). The wardrobe knowledge index is data, not
# code — the container downloads it on startup rather than baking it into the
# image, so `data/wardrobe_rules.txt` can change and be re-seeded (via
# scripts/seed_vectorstore.py) without an image rebuild.
resource "google_storage_bucket" "vectorstore" {
  name     = "rw-portfolio-tempus-vestis-vectorstore"
  location = var.region

  # Uniform (not per-object ACLs) + enforced public-access prevention: this is
  # private data read only by the Cloud Run service account, never the browser.
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # The index is fully reproducible from data/wardrobe_rules.txt via the seed
  # script, so allowing `terraform destroy` to remove it (even non-empty) is
  # safe and avoids a manual-empty step. Nothing irreplaceable lives here.
  force_destroy = true
}
