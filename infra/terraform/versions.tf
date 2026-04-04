terraform {
  required_version = ">= 1.5"

  required_providers {
    vultr = {
      source  = "vultr/vultr"
      version = "~> 2.0"
    }
  }

  # Remote state in Vultr Object Storage (S3-compatible).
  # Bucket created manually: vultr-cli object-storage create --label halo-tfstate --region lhr --cluster 1
  # State locking not available with S3 backend without DynamoDB.
  # Acceptable at single-operator scale — Kai is the only one running apply.
  backend "s3" {
    bucket = "halo-tfstate"
    key    = "halo/terraform.tfstate"
    region = "us-east-1"  # Dummy — Vultr ignores this but S3 backend requires it

    # Vultr Object Storage endpoint — set via env or backend config.
    # endpoint, access_key, secret_key provided via backend-config file
    # or environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
    use_path_style              = true
  }
}

provider "vultr" {
  api_key = var.vultr_api_key
}
