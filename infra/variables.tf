variable "project" {}

variable "region" {
  default = "us-central1"
}

variable "zone" {
  default = "us-central1-a"
}

# OpenAI API key for the LangGraph/RAG pipeline (PORT-28). Supplied via
# terraform.tfvars (gitignored) — never commit the value. Once applied it lives
# in the Secret Manager secret version AND in Terraform state, same exposure
# profile as any TF-managed secret; the state bucket is already the trust
# boundary for that.
variable "openai_api_key" {
  type      = string
  sensitive = true
}
