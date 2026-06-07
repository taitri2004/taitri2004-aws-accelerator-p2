provider "aws" {
  region = var.region
  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      component  = "final-project"
      env        = "dev"
      managed_by = "terraform"
    }
  }
}

provider "random" {}
