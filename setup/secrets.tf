# Create a secret in Secret Manager for the DATABASE_URI
resource "google_secret_manager_secret" "database_uri_secret" {
  secret_id = "projects/multi-cloud-platform/secrets/database-uri/versions/latest"

  replication {
    automatic = true
  }
}

# Store the DATABASE_URI in the secret
resource "google_secret_manager_secret_version" "database_uri_secret_version" {
  secret = google_secret_manager_secret.database_uri_secret.id

  secret_data = "postgresql://${google_sql_user.postgres_user.name}:${google_sql_user.postgres_user.password}@${google_sql_database_instance.postgres_instance.public_ip_address}/${google_sql_database.postgres_database.name}"
}


# Create a secret in Secret Manager for the JWT secret key
resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "projects/multi-cloud-platform/secrets/jwt-secret-key/versions/latest"

  replication {
    automatic = true
  }
}

# Generate a random JWT secret key
resource "random_password" "jwt_secret_key" {
  length  = 32
  special = true
}

# Store the JWT secret key in the secret
resource "google_secret_manager_secret_version" "jwt_secret_key_version" {
  secret = google_secret_manager_secret.jwt_secret_key.id

  secret_data = random_password.jwt_secret_key.result
}