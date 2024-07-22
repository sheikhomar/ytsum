#!/bin/bash

# This script creates two things:
# 1. An Azure resource group in the specified region.
# 2. A service principal with Contributor access to the resource group, because we want
#    our GitHub Actions to be able to deploy Azure resources in the resource group.
#    The credentials are saved to a file in the `.secrets` directory.

set -e

# Function to log errors
log_error() {
    echo "ERROR: $1" >&2
}

# Function to log warnings
log_warning() {
    echo "WARNING: $1" >&2
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if required commands exist
for cmd in az jq; do
    if ! command_exists "$cmd"; then
        log_error "$cmd is required but not installed. Aborting."
        exit 1
    fi
done

# Check if logged in to Azure
if ! az account show >/dev/null 2>&1; then
    log_error "Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

# Set variables
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RESOURCE_GROUP_NAME="bb-ytsum-weu-dev-rg"
SERVICE_PRINCIPAL_NAME="bb-ytsum-weu-dev-sp"
REGION="westeurope"
OUTPUT_FILE=".secrets/service-principal-credentials.json"

# Create resource group
echo "Creating resource group ${RESOURCE_GROUP_NAME}..."
if ! az group create -n "${RESOURCE_GROUP_NAME}" -l "${REGION}"; then
    log_error "Failed to create resource group."
    exit 1
fi

# Create a service principal that allows our GitHub Actions to deploy Azure resources in
# the ${RESOURCE_GROUP_NAME}. The minimum required permissions are Contributor access to
# the resource group..
echo "Creating service principal ${SERVICE_PRINCIPAL_NAME}..."
SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "${SERVICE_PRINCIPAL_NAME}" \
    --role contributor \
    --scopes "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_NAME}" \
    --json-auth 2>&1)

SP_EXIT_CODE=$?

if [ $SP_EXIT_CODE -ne 0 ]; then
    log_error "Failed to create service principal. Exit code: ${SP_EXIT_CODE}"
    log_error "Error output: ${SP_OUTPUT}"
    exit 1
fi

# Validate JSON output
if ! echo "${SP_OUTPUT}" | jq empty > /dev/null 2>&1; then
    log_error "Invalid JSON output from service principal creation."
    log_error "Raw output: ${SP_OUTPUT}"
    log_warning "Attempting to extract JSON from the output..."
    
    # Attempt to extract JSON from the output
    EXTRACTED_JSON=$(echo "${SP_OUTPUT}" | sed -n '/^{/,/^}/p')
    
    if echo "${EXTRACTED_JSON}" | jq empty > /dev/null 2>&1; then
        log_warning "Valid JSON extracted. Proceeding with extracted JSON."
        SP_OUTPUT="${EXTRACTED_JSON}"
    else
        log_error "Unable to extract valid JSON. Please check the Azure CLI version and try again."
        exit 1
    fi
fi

# Save output to file
echo "Saving service principal credentials to ${OUTPUT_FILE}..."
mkdir -p "$(dirname "${OUTPUT_FILE}")"
if ! echo "${SP_OUTPUT}" > "${OUTPUT_FILE}"; then
    log_error "Failed to write credentials to file."
    exit 1
fi

# Set restrictive permissions on the file
if ! chmod 600 "${OUTPUT_FILE}"; then
    log_error "Failed to set restrictive permissions on ${OUTPUT_FILE}."
    exit 1
fi

echo "Service principal created successfully. Output saved to ${OUTPUT_FILE}"
echo "Please ensure this file is kept secure and not shared."

# Display the contents of the file
echo "File contents:"
cat "${OUTPUT_FILE}"

echo "Remember to securely store these credentials and delete this file when no longer needed."
