resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db-subnet"
  subnet_ids = var.private_subnet_ids
  tags       = { Name = "${var.name}-db-subnet" }
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db-sg"
  description = "MySQL 3306 from web SG only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "MySQL from web server"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [var.web_security_group_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.name}-db-sg" }
}

resource "aws_db_instance" "this" {
  identifier             = "${var.name}-mysql"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = var.instance_class
  allocated_storage      = 20
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]

  publicly_accessible = false
  skip_final_snapshot = true
  storage_encrypted   = true

  tags = { Name = "${var.name}-mysql" }
}
