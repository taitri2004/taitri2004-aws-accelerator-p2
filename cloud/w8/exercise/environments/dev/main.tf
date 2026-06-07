resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name = "${var.name}-${random_id.suffix.hex}"
}

module "vpc" {
  source   = "../../modules/vpc"
  name     = local.name
  vpc_cidr = var.vpc_cidr
}

module "ec2" {
  source        = "../../modules/ec2"
  name          = local.name
  vpc_id        = module.vpc.vpc_id
  subnet_id     = module.vpc.public_subnet_ids[0]
  instance_type = var.instance_type
}

module "rds" {
  source                = "../../modules/rds"
  name                  = local.name
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  web_security_group_id = module.ec2.security_group_id
  db_password           = var.db_password
}

module "s3" {
  source      = "../../modules/s3"
  bucket_name = "${local.name}-assets"
}
