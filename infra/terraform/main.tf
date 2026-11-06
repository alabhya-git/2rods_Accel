# Udyam Digital on Google Cloud, Mumbai (asia-south1). One codebase, two environments:
#   environment = "demo"  judge demo: own project, seeded synthetic data, judge mode on, 1 warm instance
#   environment = "prod"  production shape: judge mode off, HA database, staff accounts from Secret Manager
# Everything stateful stays in India; backups are copied to Delhi (asia-south2).

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

variable "project" { type = string }
variable "region" {
  type    = string
  default = "asia-south1"
}
variable "environment" {
  type    = string
  default = "demo"
  validation {
    condition     = contains(["demo", "prod"], var.environment)
    error_message = "environment is demo or prod"
  }
}
variable "image" {
  type        = string
  description = "asia-south1-docker.pkg.dev/PROJECT/udyam/app:TAG, pushed by CI"
}
variable "public_url" {
  type    = string
  default = ""
}
variable "llm_api_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "sarvam_api_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "staff_accounts" {
  type      = string
  sensitive = true
  default   = ""
}

locals {
  name   = "udyam-${var.environment}"
  is_prod = var.environment == "prod"
  services = ["run.googleapis.com", "sqladmin.googleapis.com", "secretmanager.googleapis.com", "cloudkms.googleapis.com",
              "artifactregistry.googleapis.com", "storage.googleapis.com", "iam.googleapis.com"]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# ---- identity: the service runs as its own least-privilege account, no key files ----
resource "google_service_account" "app" {
  account_id   = "${local.name}-app"
  display_name = "Udyam Digital ${var.environment} runtime"
}

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "udyam"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# ---- keys: Cloud KMS wraps the vault master key; secrets live in Secret Manager ----
resource "google_kms_key_ring" "ring" {
  name       = "${local.name}-ring"
  location   = var.region
  depends_on = [google_project_service.apis]
}

resource "google_kms_crypto_key" "vault" {
  name            = "vault-master"
  key_ring        = google_kms_key_ring.ring.id
  rotation_period = "7776000s" # 90 days
  lifecycle { prevent_destroy = false }
}

resource "google_kms_crypto_key" "storage" {
  name            = "documents"
  key_ring        = google_kms_key_ring.ring.id
  rotation_period = "7776000s"
}

resource "random_bytes" "master" { length = 32 }

resource "google_secret_manager_secret" "s" {
  for_each  = toset(["master-key", "llm-key", "staff-accounts", "sarvam-key", "whatsapp-token", "whatsapp-app-secret", "database-url"])
  secret_id = "${local.name}-${each.value}"
  replication {
    user_managed {
      replicas { location = var.region }
    }
  }
  depends_on = [google_project_service.apis]
}

# keys passed in as sensitive variables (never in the repo); a secret with no value is not mounted
locals {
  secret_values = { for k, v in {
    "llm-key" = var.llm_api_key, "sarvam-key" = var.sarvam_api_key, "staff-accounts" = var.staff_accounts
  } : k => v if v != "" }
  mounted = merge(
    { MASTER_KEY_B64 = "master-key", DATABASE_URL = "database-url" },
    var.llm_api_key != "" ? { LLM_API_KEY = "llm-key" } : {},
    var.sarvam_api_key != "" ? { SARVAM_API_KEY = "sarvam-key" } : {},
    var.staff_accounts != "" ? { STAFF_ACCOUNTS = "staff-accounts" } : {},
  )
}

resource "google_secret_manager_secret_version" "given" {
  for_each    = nonsensitive(toset(keys(local.secret_values)))
  secret      = google_secret_manager_secret.s[each.value].id
  secret_data = local.secret_values[each.value]
}

resource "google_secret_manager_secret_version" "master" {
  secret      = google_secret_manager_secret.s["master-key"].id
  secret_data = random_bytes.master.base64
}

resource "google_secret_manager_secret_iam_member" "read" {
  for_each  = google_secret_manager_secret.s
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}

# ---- documents: private bucket in Mumbai, customer-managed key, deleted on schedule ----
data "google_storage_project_service_account" "gcs" {}

resource "google_kms_crypto_key_iam_member" "gcs" {
  crypto_key_id = google_kms_crypto_key.storage.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_storage_project_service_account.gcs.email_address}"
}

resource "google_storage_bucket" "docs" {
  name                        = "${var.project}-${local.name}-docs"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  encryption { default_kms_key_name = google_kms_crypto_key.storage.id }
  lifecycle_rule {
    condition { age = 45 } # backstop: the app deletes photos 30 days after verification
    action { type = "Delete" }
  }
  depends_on = [google_kms_crypto_key_iam_member.gcs]
}

resource "google_storage_bucket_iam_member" "docs" {
  bucket = google_storage_bucket.docs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app.email}"
}

# ---- database: Cloud SQL for Postgres 16, private to the app, point-in-time recovery ----
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_sql_database_instance" "pg" {
  name                = "${local.name}-pg"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = local.is_prod
  settings {
    edition           = "ENTERPRISE" # Postgres 16 defaults to Enterprise Plus, which has no small tiers
    tier              = local.is_prod ? "db-custom-2-7680" : "db-f1-micro"
    availability_type = local.is_prod ? "REGIONAL" : "ZONAL"
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      location                       = "asia-south2" # backups copied to Delhi
      transaction_log_retention_days = 7
    }
    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "500"
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "app" {
  name     = "udyam"
  instance = google_sql_database_instance.pg.name
}

resource "google_sql_user" "app" {
  name     = "udyam"
  instance = google_sql_database_instance.pg.name
  password = random_password.db.result
}

resource "google_secret_manager_secret_version" "db" {
  secret      = google_secret_manager_secret.s["database-url"].id
  secret_data = "postgresql+psycopg://udyam:${random_password.db.result}@/udyam?host=/cloudsql/${google_sql_database_instance.pg.connection_name}"
}

resource "google_project_iam_member" "sql" {
  project = var.project
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# ---- the app: Cloud Run, autoscaled, one warm instance for the judge demo ----
resource "google_cloud_run_v2_service" "app" {
  name     = local.name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  template {
    service_account                  = google_service_account.app.email
    max_instance_request_concurrency = 80
    timeout                          = "300s"
    scaling {
      min_instance_count = local.is_prod ? 2 : 1
      max_instance_count = local.is_prod ? 100 : 10
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.pg.connection_name] }
    }
    containers {
      image = var.image
      resources {
        limits            = { cpu = "1", memory = "1Gi" }
        startup_cpu_boost = true
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "JUDGE_MODE"
        value = local.is_prod ? "false" : "true"
      }
      env {
        name  = "MOCK_ADAPTERS_ALLOWED"
        value = local.is_prod ? "false" : "true"
      }
      env {
        name  = "LLM_PROVIDER"
        value = "anthropic"
      }
      env {
        name  = "STORAGE_BACKEND"
        value = "gcs"
      }
      env {
        name  = "STORAGE_BUCKET"
        value = google_storage_bucket.docs.name
      }
      env {
        name  = "PUBLIC_URL"
        value = var.public_url
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.public_url == "" ? "https://${local.name}.run.app" : var.public_url
      }
      dynamic "env" {
        for_each = nonsensitive(local.mounted)
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.s[env.value].secret_id
              version = "latest"
            }
          }
        }
      }
      startup_probe {
        http_get { path = "/api/health" }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 24
      }
      liveness_probe {
        http_get { path = "/api/health" }
        period_seconds = 30
      }
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.read, google_project_iam_member.sql, google_secret_manager_secret_version.given, google_secret_manager_secret_version.db]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "url" { value = google_cloud_run_v2_service.app.uri }
output "docs_bucket" { value = google_storage_bucket.docs.name }
output "kms_vault_key" { value = google_kms_crypto_key.vault.id }
