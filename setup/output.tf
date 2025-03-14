# Output the DATABASE_URI and JWT secret key
output "database_uri" {
  value = google_secret_manager_secret_version.database_uri_secret_version.secret_data
  sensitive = true
}

output "jwt_secret_key" {
  value = google_secret_manager_secret_version.jwt_secret_key_version.secret_data
  sensitive = true
}