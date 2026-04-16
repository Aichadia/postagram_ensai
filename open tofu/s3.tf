# Aidez-vous du TP 4

resource "aws_s3_bucket" "bucket" {
   bucket_prefix = "postagram-"
   force_destroy = true
}

# A décommenter seulement quand le bucket est défini
 output "bucketname" {
   description = "The postagram bucket name"
   value       = aws_s3_bucket.bucket.bucket
 }

# A décommenter seulement quand le bucket est défini
 resource "aws_s3_bucket_cors_configuration" "cors_bucket" {
   bucket = aws_s3_bucket.bucket.id

   cors_rule {
     allowed_headers = ["*"]
     allowed_methods = ["GET", "HEAD", "PUT"]
     allowed_origins = ["*"]
   }
 }