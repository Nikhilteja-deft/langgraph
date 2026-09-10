

provider "google" {
  project = var.project
  region  = var.region
  zone    = var.zone
}


resource "google_artifact_registry_repository" "my-repo" {
  location      = "us-central1"
  repository_id = "${local.prefix}-repository"
  description   = "store the docker images"
  format        = "DOCKER"
}


resource "google_cloud_run_service" "default" {
  name     = "${local.prefix}-cloudrun"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "us-central1-docker.pkg.dev/${var.project}/langgraph-dev-repository/app:latest"
        ports {
          container_port = 8080
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Allow unauthenticated invocation (public HTTP access)
resource "google_cloud_run_service_iam_member" "noauth" {
  location = google_cloud_run_service.default.location
  project  = google_cloud_run_service.default.project
  service  = google_cloud_run_service.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

