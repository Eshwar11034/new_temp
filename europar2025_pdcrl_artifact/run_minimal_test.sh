#!/bin/bash

# --- Script Configuration ---
# These paths are relative to this script's location (the main artifact workspace, 
# e.g., europar2025_pdcrl_artifact_workspace/ or europar2025_pdcrl_artifact/ as per your setup.sh)


PARQR_HOST_MAIN_DIR="pdcrl-parqr" # This is a subdirectory in the current workspace
# Subdirectory within ParQR containing the Makefile, C++ sources for experiments
PARQR_CODE_SUBDIR="Dynamic-Task-Scheduling"

# Location of scripts and configs to be mounted into Docker
# These are also subdirectories in the current workspace
ARTIFACT_SCRIPTS_DIR_HOST="scripts"       # Contains helper.py
ARTIFACT_CONFIG_DIR_HOST="config"         # Contains minimal_test_config.json
MINIMAL_TEST_CONFIG_FILE="minimal_test_config.json"
PYTHON_MASTER_SCRIPT_NAME="helper.py"     # Actual name of your Python script

# Docker container paths
DOCKER_WORKSPACE="/workspace"
# Name for the mounted ParQR code's Dynamic-Task-Scheduling dir inside workspace
DOCKER_PARQR_DTS_MOUNT_NAME="parqr_dts_code" 
DOCKER_ARTIFACT_SCRIPTS_MOUNT_NAME="artifact_scripts"
DOCKER_CONFIG_MOUNT_NAME="config"

# File storing the Docker image name 
DOCKER_IMAGE_NAME_FILE=".artifact_docker_image_name"

# --- Helper Functions ---
log_info() {
    echo "[MINIMAL_TEST INFO] $1"
}

log_error() {
    echo "[MINIMAL_TEST ERROR] $1" >&2
}

# --- Main Test Logic ---

log_info "Starting Minimal Test Script..."
log_info "Current working directory: $(pwd)"

# Step 1: Check for necessary files and directories from setup
log_info "Step 1: Verifying setup components..."
if [ ! -f "$DOCKER_IMAGE_NAME_FILE" ]; then
    log_error "Docker image name file ('$DOCKER_IMAGE_NAME_FILE') not found in $(pwd)."
    log_error "Please run 'setup.sh' (or your main setup script) first from the parent directory."
    exit 1
fi
IMAGE_TO_USE=$(cat "$DOCKER_IMAGE_NAME_FILE")
if [ -z "$IMAGE_TO_USE" ]; then
    log_error "Docker image name is empty in '$DOCKER_IMAGE_NAME_FILE'."
    log_error "Please re-run setup."
    exit 1
fi
log_info "Using Docker image: $IMAGE_TO_USE"

PARQR_DTS_HOST_PATH="${PARQR_HOST_MAIN_DIR}/${PARQR_CODE_SUBDIR}"
if [ ! -d "$PARQR_DTS_HOST_PATH" ]; then
    log_error "ParQR code directory ('$PARQR_DTS_HOST_PATH') not found in $(pwd)."
    log_error "Ensure ParQR repository was cloned correctly by setup."
    exit 1
fi
log_info "ParQR code directory found: ./$PARQR_DTS_HOST_PATH"

if [ ! -d "$ARTIFACT_SCRIPTS_DIR_HOST" ] || [ ! -f "$ARTIFACT_SCRIPTS_DIR_HOST/$PYTHON_MASTER_SCRIPT_NAME" ]; then
    log_error "Artifact scripts directory ('./$ARTIFACT_SCRIPTS_DIR_HOST') or Python script ('$PYTHON_MASTER_SCRIPT_NAME') not found."
    exit 1
fi
log_info "Artifact Python script found: ./$ARTIFACT_SCRIPTS_DIR_HOST/$PYTHON_MASTER_SCRIPT_NAME"

if [ ! -d "$ARTIFACT_CONFIG_DIR_HOST" ] || [ ! -f "$ARTIFACT_CONFIG_DIR_HOST/$MINIMAL_TEST_CONFIG_FILE" ]; then
    log_error "Artifact config directory ('./$ARTIFACT_CONFIG_DIR_HOST') or config file ('$MINIMAL_TEST_CONFIG_FILE') not found."
    exit 1
fi
log_info "Minimal test configuration file found: ./$ARTIFACT_CONFIG_DIR_HOST/$MINIMAL_TEST_CONFIG_FILE"

# Step 2: Define paths for Docker volumes and commands
# Absolute path to the ParQR Dynamic-Task-Scheduling directory on the host
HOST_PARQR_DTS_PATH_ABS="$(cd "$PARQR_DTS_HOST_PATH" && pwd)"
if [ -z "$HOST_PARQR_DTS_PATH_ABS" ]; then
    log_error "Could not resolve absolute path for '$PARQR_DTS_HOST_PATH'."
    exit 1
fi

# Absolute path to the artifact scripts directory (containing helper.py) on the host
HOST_ARTIFACT_SCRIPTS_PATH_ABS="$(cd "$ARTIFACT_SCRIPTS_DIR_HOST" && pwd)"
if [ -z "$HOST_ARTIFACT_SCRIPTS_PATH_ABS" ]; then
    log_error "Could not resolve absolute path for '$ARTIFACT_SCRIPTS_DIR_HOST'."
    exit 1
fi

# Absolute path to the config directory on the host
HOST_CONFIG_PATH_ABS="$(cd "$ARTIFACT_CONFIG_DIR_HOST" && pwd)"
if [ -z "$HOST_CONFIG_PATH_ABS" ]; then
    log_error "Could not resolve absolute path for '$ARTIFACT_CONFIG_DIR_HOST'."
    exit 1
fi

# Paths inside the Docker container
CONTAINER_PARQR_DTS_CODE_PATH="${DOCKER_WORKSPACE}/${DOCKER_PARQR_DTS_MOUNT_NAME}"
CONTAINER_ARTIFACT_SCRIPTS_PATH="${DOCKER_WORKSPACE}/${DOCKER_ARTIFACT_SCRIPTS_MOUNT_NAME}"
CONTAINER_CONFIG_PATH="${DOCKER_WORKSPACE}/${DOCKER_CONFIG_MOUNT_NAME}"
CONTAINER_MINIMAL_TEST_CONFIG_FILE_PATH="${CONTAINER_CONFIG_PATH}/${MINIMAL_TEST_CONFIG_FILE}"

# Command to run the Python master script inside Docker
COMMAND_IN_DOCKER="python3 ${CONTAINER_ARTIFACT_SCRIPTS_PATH}/${PYTHON_MASTER_SCRIPT_NAME} --config ${CONTAINER_MINIMAL_TEST_CONFIG_FILE_PATH}"

# Step 3: Run the minimal test inside Docker
log_info "Step 3: Running minimal test inside Docker container..."
log_info "Host ParQR DTS path: $HOST_PARQR_DTS_PATH_ABS (mounted to $CONTAINER_PARQR_DTS_CODE_PATH)"
log_info "Host artifact scripts path: $HOST_ARTIFACT_SCRIPTS_PATH_ABS (mounted to $CONTAINER_ARTIFACT_SCRIPTS_PATH)"
log_info "Host config path: $HOST_CONFIG_PATH_ABS (mounted to $CONTAINER_CONFIG_PATH)"
log_info "Container working directory set to: $CONTAINER_PARQR_DTS_CODE_PATH"
log_info "Command to execute in Docker: bash -c \"$COMMAND_IN_DOCKER\""
echo # Blank line for clarity

DOCKER_RUN_OUTPUT_FILE="minimal_test_docker_output.log"
# Using sudo for docker command
# -it: Interactive TTY
# --rm: Remove container after exit
# -v: Mount volumes
# -w: Set working directory inside container
if sudo docker run -it --rm \
    -v "${HOST_PARQR_DTS_PATH_ABS}:${CONTAINER_PARQR_DTS_CODE_PATH}" \
    -v "${HOST_ARTIFACT_SCRIPTS_PATH_ABS}:${CONTAINER_ARTIFACT_SCRIPTS_PATH}" \
    -v "${HOST_CONFIG_PATH_ABS}:${CONTAINER_CONFIG_PATH}" \
    -w "${CONTAINER_PARQR_DTS_CODE_PATH}" \
    "${IMAGE_TO_USE}" \
    bash -c "${COMMAND_IN_DOCKER}" | tee "$DOCKER_RUN_OUTPUT_FILE"; then
    
    if grep -q "MINIMAL_TEST_PASSED" "$DOCKER_RUN_OUTPUT_FILE"; then
        log_info "--- Minimal Test PASSED successfully! ---"
        log_info "Detailed log from Docker run is in: $(pwd)/$DOCKER_RUN_OUTPUT_FILE"
        log_info "If the test produces files, they would be within: $HOST_PARQR_DTS_PATH_ABS (e.g., in a 'results' or 'testcase' subdirectory)"
        exit 0
    else
        log_error "--- Minimal Test FAILED. ---"
        log_error "The script inside Docker did not report MINIMAL_TEST_PASSED."
        log_error "Please check the output above and in: $(pwd)/$DOCKER_RUN_OUTPUT_FILE"
        exit 1
    fi
else
    exit_code=$? # Capture exit code of the docker run command itself
    log_error "--- Minimal Test FAILED (Docker run command failed with exit code $exit_code). ---"
    log_error "Please check the output above and in: $(pwd)/$DOCKER_RUN_OUTPUT_FILE"
    if [ $exit_code -eq 126 ] || [ $exit_code -eq 127 ]; then
         log_error "Exit code $exit_code often indicates 'Command invoked cannot execute' or 'Command not found'."
         log_error "This might suggest an issue with bash, python3, or the script path inside the container, or an architecture mismatch if emulation isn't working."
    fi
    exit 1
fi