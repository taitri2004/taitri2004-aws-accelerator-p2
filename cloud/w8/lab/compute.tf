# compute.tf - EC2 bootstrap for kind and the app

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  app_manifest = templatefile("${path.module}/templates/app.yaml.tftpl", {
    app_name  = var.name
    node_port = var.node_port
  })

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    node_port        = var.node_port
    app_manifest_b64 = base64encode(local.app_manifest)
  })
}

resource "aws_instance" "node" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ssm.name
  user_data              = local.user_data

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = { Name = "${var.name}-k8s-node" }
}
