#!/usr/bin/env bash
# Build and deploy PII Shield to Google Cloud Run (works in Cloud Shell, Linux, macOS).
# Usage: ./deploy/cloud_run_deploy.sh <GCP_PROJECT_ID> [REGION]

set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy/cloud_run_deploy.sh <GCP_PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"
REPO="pii-shield"
SERVICE="pii-shield"

echo "1/5 Setting active GCP project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

echo "2/5 Enabling Cloud Run, Cloud Build, and Artifact Registry APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com

echo "3/5 Ensuring Artifact Registry repository '${REPO}' exists in ${REGION}..."
if ! gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="PII Shield container images"
fi

echo "4/5 Granting Cloud Build service account permissions..."
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
COMPUTE_SA="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for ROLE in \
  roles/artifactregistry.writer \
  roles/logging.logWriter \
  roles/storage.objectViewer \
  roles/run.admin \
  roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="${COMPUTE_SA}" --role="${ROLE}" --quiet >/dev/null
done

echo "5/5 Submitting Cloud Build & deploying '${SERVICE}' to Cloud Run..."
gcloud builds submit --config cloudbuild.yaml \
  --substitutions="_REGION=${REGION},_REPO=${REPO},_SERVICE=${SERVICE}" .

URL="$(gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)')"
echo "Deployed successfully! Live Cloud Run URL: ${URL}"
