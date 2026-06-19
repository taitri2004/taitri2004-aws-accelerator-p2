provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      week       = "w10"
      component  = "homework-macie-cdo-security"
      managed_by = "terraform"
    }
  }
}
