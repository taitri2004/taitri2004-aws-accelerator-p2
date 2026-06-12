# compute.tf - EC2 (Amazon Linux 2023) tu cai + chay CloudWatch Agent
# Khong khai bao subnet/SG -> dung default VPC + default SG cua account

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

locals {
  # Giu nguyen file (khong qua templatefile) de ${aws:InstanceId} cua agent
  # khong bi Terraform dien.
  agent_config_b64 = base64encode(file("${path.module}/templates/cw_agent_config.json"))

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    agent_config_b64 = local.agent_config_b64
  })
}

resource "aws_instance" "this" {
  ami                  = data.aws_ami.al2023.id
  instance_type        = var.instance_type
  iam_instance_profile = aws_iam_instance_profile.ec2.name
  user_data            = local.user_data

  tags = { Name = "${var.name}-ec2" }
}
