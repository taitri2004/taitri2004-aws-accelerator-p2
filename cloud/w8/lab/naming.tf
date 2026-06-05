# naming.tf - random suffix for AWS resource names

resource "random_id" "suffix" {
  byte_length = 4
}
