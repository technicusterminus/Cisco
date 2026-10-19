terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

resource "aws_vpc" "lab" {
  cidr_block = "10.50.0.0/16"
  tags       = { Name = "lab-vpc" }
}

resource "aws_subnet" "users" {
  vpc_id     = aws_vpc.lab.id
  cidr_block = "10.50.10.0/24"
}

output "vpc_id" {
  value = aws_vpc.lab.id
}
