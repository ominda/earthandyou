output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "sg_alb_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "sg_backend_id" {
  description = "Backend ECS security group ID"
  value       = aws_security_group.backend.id
}

output "sg_frontend_id" {
  description = "Frontend ECS security group ID"
  value       = aws_security_group.frontend.id
}

output "sg_rds_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "sg_elasticache_id" {
  description = "ElastiCache security group ID"
  value       = aws_security_group.elasticache.id
}
