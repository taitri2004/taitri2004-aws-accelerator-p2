terraform {
  required_version = ">= 1.10"

  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }

  backend "s3" {
    bucket       = "taitri2004-tfstate-w8"
    key          = "w8/exercise/dev/terraform.tfstate"
    region       = "ap-southeast-1"
    use_lockfile = true
    encrypt      = true
  }
}
