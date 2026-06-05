# W8 Lab - K8s on AWS, Terraform 1-Click

> Challenge: create one EC2 instance, run kind inside it, deploy a small HTML app,
> expose the app through an AWS ALB, and build everything with one Terraform apply.

## Architecture

```text
Internet
  -> ALB :80
     -> Target Group: instance port 30080
        -> EC2 Ubuntu 22.04
           -> IAM role + SSM Agent for admin access
           -> Docker
              -> kind single-node Kubernetes cluster
                 -> Service web NodePort 30080
                    -> Deployment web, 2 nginx replicas
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

`random_id.suffix.hex` feeds into `aws_lb`, `aws_lb_target_group`, `aws_iam_role` and `aws_iam_instance_profile` names, so the two providers share one dependency graph in a single apply.

## Run

```bash
terraform init
terraform apply -auto-approve
terraform output alb_url
```

After apply, wait about 3-5 minutes for EC2 bootstrap and ALB health checks. Then open `alb_url` in a browser.

## SSM Access

The EC2 instance does not expose port 22. Use SSM Session Manager:

```bash
aws ssm start-session --target $(terraform output -raw instance_id) --region ap-southeast-1
```

To verify the app is running inside Kubernetes:

```bash
aws ssm send-command \
  --instance-ids $(terraform output -raw instance_id) \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["KUBECONFIG=/root/.kube/config kubectl get pods,svc -o wide"]'
```

## Cleanup

```bash
terraform destroy -auto-approve
```

EC2 and ALB are billed while running, so destroy the lab after collecting evidence.

## Acceptance Map

- [x] One Terraform apply creates the infrastructure and deploys the app
- [x] The app runs inside Kubernetes kind, not directly on EC2
- [x] The app is reachable from the Internet through ALB
- [x] Two Terraform providers are wired in the same configuration: `aws` and `random`
- [x] EC2 does not expose SSH; admin access uses SSM
- [x] Destroy removes the lab resources
