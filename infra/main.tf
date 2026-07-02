terraform {
  required_providers {
    google = {
      source  = "hashicorp/google",
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
  zone    = var.zone
}

data "terraform_remote_state" "common" {
  backend = "gcs"

  config = {
    bucket = "rw-portfolio-tfstate"
    prefix = "shared-infra/state"
  }
}

data "terraform_remote_state" "auth" {
  backend = "gcs"

  config = {
    bucket = "rw-portfolio-tfstate"
    prefix = "authentication/state"
  }
}
