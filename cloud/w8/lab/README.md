# W8 Lab - K8s on AWS, Terraform 1-Click

> Challenge: create one EC2 instance, run kind inside it, deploy a small HTML demo app,
> expose the app through an AWS ALB, and build everything with one Terraform apply.

## Architecture

```text
                           AWS Region: ap-southeast-1

        +----------------------------- VPC 10.0.0.0/16 -----------------------------+
        |                                                                            |
Internet|  Public Subnet A                         Public Subnet B                   |
   |    |  +----------------------+                +----------------------+          |
   +------> Application Load      |                | ALB second subnet    |          |
        |  | Balancer :80         |                | attachment           |          |
        |  +----------+-----------+                +----------------------+          |
        |             |                                                              |
        |             v                                                              |
        |  +----------------------+                                                  |
        |  | EC2 Ubuntu 22.04     |                                                  |
        |  | - SSM Agent          |                                                  |
        |  | - Docker             |                                                  |
        |  | - kind cluster       |                                                  |
        |  |   Service NodePort   |                                                  |
        |  |   Deployment nginx   |                                                  |
        |  +----------------------+                                                  |
        |                                                                            |
        +----------------------------------------------------------------------------+
```

Network:

- VPC `10.0.0.0/16`
- 2 public subnets in 2 AZs
- Internet Gateway and public route table
- ALB security group allows HTTP 80 from Internet
- EC2 security group allows NodePort `30080` only from the ALB security group
- EC2 has no inbound SSH rule; admin access uses AWS SSM Session Manager

Traffic path:

```text
Browser -> ALB:80 -> EC2:30080 -> kind extraPortMapping -> Service NodePort -> nginx Pod
```

## Provider Wiring

| Provider | Role |
|---|---|
| `hashicorp/aws` | VPC, subnet, IGW, SG, EC2, IAM role/profile, ALB, target group, listener |
| `hashicorp/random` | Generates a unique suffix so globally-unique names (ALB, target group, IAM role, instance profile) do not collide on repeated or parallel applies |

The wiring is in `naming.tf` and the AWS resources: the `random` output is an input to `aws` resource names.

```hcl
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_lb" "this" {
  name = "${var.name}-alb-${random_id.suffix.hex}"
}
```

## Run

```bash
terraform init
terraform apply -auto-approve
terraform output alb_url
```

After apply, wait about 3-5 minutes for EC2 bootstrap and ALB health checks. Then open `alb_url` in a browser to view the presentation/demo page.

## Cleanup

```bash
terraform destroy -auto-approve
```
