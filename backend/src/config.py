import os
from google.cloud import secretmanager

class Config:
    SECRET_MANAGER_CLIENT = secretmanager.SecretManagerServiceClient()

    @staticmethod
    def get_secret(secret_name):
        try:
            response = Config.SECRET_MANAGER_CLIENT.access_secret_version(request={"name": secret_name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Failed to retrieve secret: {e}")
            raise

    SQLALCHEMY_DATABASE_URI = get_secret("projects/multi-cloud-platform/secrets/database-uri/versions/latest")
    JWT_SECRET_KEY = get_secret("projects/multi-cloud-platform/secrets/jwt-secret-key/versions/latest")
