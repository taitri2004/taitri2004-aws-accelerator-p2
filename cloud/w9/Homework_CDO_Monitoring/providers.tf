# providers.tf - provider configuration
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      week       = "w9"
      component  = "homework-cloudwatch-monitoring"
      managed_by = "terraform"
    }
  }
}
