# providers.tf - provider configuration
# Cost Explorer (ce) la dich vu GLOBAL, API chi o us-east-1 -> region us-east-1.
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "aws-accelerator-p2"
      week       = "w10"
      component  = "day-c-cost-anomaly"
      managed_by = "terraform"
    }
  }
}
