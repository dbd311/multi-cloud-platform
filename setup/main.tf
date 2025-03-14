provider "google" {
  project = "multi-cloud-multi-tenant"
  region  = "europe-west6" # gcp region in zurich
}

# gcloud compute regions list 


# Create a Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "postgres_instance" {
  name             = "my-postgres-instance"
  database_version = "POSTGRES_13"
  region           = "europe-west6"

  settings {
    tier = "db-f1-micro"  # Choose a suitable tier
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0" # adapt networks accordingly for security
      }
    }
  }
}

# Create a database
resource "google_sql_database" "postgres_database" {
  name     = "multi-cloud-database"
  instance = google_sql_database_instance.postgres_instance.name
}

# Create a user
resource "google_sql_user" "postgres_user" {
  name     = "multicloud"
  instance = google_sql_database_instance.postgres_instance.name
  password = "to_be_changed"
}





