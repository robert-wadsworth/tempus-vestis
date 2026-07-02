terraform {
  backend "gcs" {
    bucket = "rw-portfolio-tfstate"
    prefix = "tempus-vestis/state"
  }
}
