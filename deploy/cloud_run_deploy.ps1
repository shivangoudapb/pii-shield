<#
.SYNOPSIS
  Build and deploy PII Shield to Google Cloud Run (keeps Modal untouched).
.EXAMPLE
  .\deploy\cloud_run_deploy.ps1 -ProjectId "pii-shield-shivu"
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectId,
  [string]$Region = "us-central1",
  [string]$Repo = "pii-shield",
  [string]$Service = "pii-shield"
)

$GcloudCmd = (Get-Command gcloud.cmd -ErrorAction SilentlyContinue).Source
if (-not $GcloudCmd) {
  $SdkBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
  if (Test-Path "$SdkBin\gcloud.cmd") {
    $env:PATH = "$SdkBin;$env:PATH"
    $GcloudCmd = "$SdkBin\gcloud.cmd"
  } else {
    Write-Error "gcloud.cmd not found. Install Google.CloudSDK first."
    exit 1
  }
}

function Invoke-Gcloud {
  & $GcloudCmd @args
  if ($LASTEXITCODE -ne 0) {
    throw "gcloud command failed with exit code $LASTEXITCODE"
  }
}

Write-Host "1/5 Setting active GCP project to $ProjectId..."
Invoke-Gcloud config set project $ProjectId

Write-Host "2/5 Enabling Cloud Run, Cloud Build, and Artifact Registry APIs..."
Invoke-Gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  compute.googleapis.com

Write-Host "3/5 Ensuring Artifact Registry repository '$Repo' exists in $Region..."
& $GcloudCmd artifacts repositories describe $Repo --location=$Region --quiet 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
  Invoke-Gcloud artifacts repositories create $Repo `
    --repository-format=docker `
    --location=$Region `
    --description="PII Shield container images"
}

Write-Host "4/5 Granting Cloud Build service account permissions for Artifact Registry & Cloud Run..."
$ProjectNumber = (& $GcloudCmd projects describe $ProjectId --format="value(projectNumber)").Trim()
$ComputeSa = "serviceAccount:${ProjectNumber}-compute@developer.gserviceaccount.com"
foreach ($Role in @(
  "roles/artifactregistry.writer",
  "roles/logging.logWriter",
  "roles/storage.objectViewer",
  "roles/run.admin",
  "roles/iam.serviceAccountUser"
)) {
  Invoke-Gcloud projects add-iam-policy-binding $ProjectId --member=$ComputeSa --role=$Role --quiet 1>$null
}

Write-Host "5/5 Submitting Cloud Build & deploying '$Service' to Cloud Run..."
Invoke-Gcloud builds submit --config cloudbuild.yaml `
  --substitutions="_REGION=$Region,_REPO=$Repo,_SERVICE=$Service" .

$Url = (& $GcloudCmd run services describe $Service --region=$Region --format="value(status.url)").Trim()
Write-Host "`nDeployed successfully! Live Cloud Run URL: $Url"
