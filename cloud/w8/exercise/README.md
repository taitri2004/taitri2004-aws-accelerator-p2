# Final Project - Web App on AWS

Terraform project for a basic AWS web application architecture:

- VPC with public and private subnets
- EC2 web server in a public subnet
- RDS MySQL in private subnets
- S3 bucket for static assets
- Security groups that allow only required inbound traffic

## Architecture

```text
Internet
  -> EC2 web server, public subnet, HTTP 80
     -> RDS MySQL, private subnets, MySQL 3306 from web SG only

S3 bucket:
  private static assets bucket, versioned and encrypted

Terraform state:
  S3 backend with native S3 lockfile
```

The project does not create a NAT Gateway. The EC2 web server is in a public subnet and can reach the Internet through the Internet Gateway. RDS is in private subnets and does not need outbound Internet access for this lab.

## Structure

```text
exercise/
  bootstrap/
  modules/
    vpc/
    ec2/
    rds/
    s3/
  environments/dev/
```

## Run

Bootstrap the remote state bucket once:

```bash
cd bootstrap
terraform init
terraform apply
terraform output state_bucket
```

Deploy the dev environment:

```bash
cd ../environments/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output web_url
```

Clean up:

```bash
terraform destroy
```

## Local Validation

To validate without initializing the S3 backend:

```bash
cd environments/dev
terraform init -backend=false
terraform validate
```
