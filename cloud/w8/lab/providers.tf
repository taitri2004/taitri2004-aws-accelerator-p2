# providers.tf - provider configuration
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      week       = "w8"
      component  = "lab-k8s-on-aws"
      managed_by = "terraform"
    }
  }
}

provider "random" {}
