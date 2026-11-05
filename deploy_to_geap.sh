#!/usr/bin/env bash
# Deploy Contract Review Agent to Google Enterprise Agent Platform (GEAP / Vertex AI Agent Engine)

set -e

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-assist-463118}}"
REGION="${2:-${GOOGLE_CLOUD_REGION:-us-central1}}"
STAGING_BUCKET="${3:-gs://${PROJECT_ID}-geap-staging}"
DISPLAY_NAME="geap-contract-compliance-reviewer"

echo "================================================================================"
echo "    DEPLOYING CONTRACT REVIEW AGENT TO GEAP / VERTEX AI AGENT ENGINE"
echo "================================================================================"
echo "  Google Cloud Project:  ${PROJECT_ID}"
echo "  Deployment Region:     ${REGION}"
echo "  Staging GCS Bucket:    ${STAGING_BUCKET}"
echo "  Agent Display Name:    ${DISPLAY_NAME}"
echo "================================================================================"

# 1. Ensure staging bucket exists or create it
echo "[1/3] Ensuring staging bucket exists in ${REGION}..."
if ! gsutil ls -b "${STAGING_BUCKET}" >/dev/null 2>&1; then
  echo "Creating GCS staging bucket ${STAGING_BUCKET}..."
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "${STAGING_BUCKET}" || true
fi

# 2. Deploy via Google ADK / agents CLI to Agent Engine
echo "[2/3] Deploying agent application via agents CLI to Agent Engine..."
agents deploy agent_engine \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --staging_bucket="${STAGING_BUCKET}" \
  --display_name="${DISPLAY_NAME}" \
  --description="GEAP 18-Point Legal Contract Compliance Reviewer with cross-reference tools" \
  contract_review_agent

# 3. Complete
echo "[3/3] Deployment initiated successfully!"
echo "You can evaluate the deployed agent using:"
echo "  agents eval contract_review_agent contract_review_agent/eval_set.json"
