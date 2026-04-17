# Aidez-vous du TP 2


variable "git_repo" {
  type = string
  default = "https://github.com/Aichadia/postagram_ensai.git" # Url de notre dépôt git
}

########################################
# Launch Template
########################################

resource "aws_launch_template" "ubuntu_template" {
  name_prefix   = "postagram-"
  image_id      = "ami-0ec10929233384c7f" # Ubuntu 24.04 LTS us-east-1 comme dans TP1 
  instance_type = "t3.micro"
  key_name      = "vockey"
  iam_instance_profile {
    #arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:instance-profile/LabRole" # <- NE PAS MODIFIER -- modif de l'arguement name en arn
    name = "LabInstanceProfile"
    } 

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    git_repo = var.git_repo
    dynamo_table = aws_dynamodb_table.basic-dynamodb-table.name
    bucket = aws_s3_bucket.bucket.bucket
    })) # ajout du base64 encoder 

  vpc_security_group_ids = [aws_security_group.web_sg.id]

  block_device_mappings {
    device_name = "/dev/sda1"

    ebs {
      volume_size = 8
      volume_type = "gp3"
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "postagram-instance"
    }
  }
  tags = {
    Name = "TP noté"
  }
}

########################################
# Auto Scaling Group
########################################
resource "aws_autoscaling_group" "web_asg" {
  desired_capacity     = 1
  max_size             = 4
  min_size             = 1
  vpc_zone_identifier  = data.aws_subnets.default.ids
  health_check_type    = "EC2"
  target_group_arns    = [aws_lb_target_group.web_tg.arn]

  launch_template {
    id      = aws_launch_template.ubuntu_template.id
    version = "$Latest"
    }

  tag {
    key                 = "Name"
    value               = "web-asg-instance"
    propagate_at_launch = true
    }
  }

########################################
# Load Balancer (ALB)
########################################
resource "aws_lb" "web_alb" {
  name               = "web-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web_sg.id]
  subnets            = data.aws_subnets.default.ids

  tags = {
    Name = "web-alb"
    }
  }

########################################
# Target Group (pour le Load Balancer)
########################################
resource "aws_lb_target_group" "web_tg" {
  name     = "web-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id


  tags = {
    Name = "web-tg"
    }
  }

########################################
# Listener pour le Load Balancer
########################################
resource "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_lb.web_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web_tg.arn
    }
  }

########################################
# Outputs
########################################
output "load_balancer_dns_name" {
  description = "Nom DNS du load balancer"
  value       = aws_lb.web_alb.dns_name
}

