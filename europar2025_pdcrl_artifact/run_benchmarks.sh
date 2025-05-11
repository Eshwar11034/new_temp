#!/bin/bash

# --- Script Configuration ---
PARQR_HOST_MAIN_DIR="pdcrl-parqr"
PARQR_CODE_SUBDIR="Dynamic-Task-Scheduling" 
ARTIFACT_SCRIPTS_DIR_HOST="scripts" 
DOCKER_IMAGE_NAME_FILE=".artifact_docker_image_name"

# Docker container paths
DOCKER_WORKSPACE="/workspace"
DOCKER_PARQR_MOUNT_NAME="parqr_code" 
DOCKER_ARTIFACT_SCRIPTS_MOUNT_NAME="artifact_scripts"

# --- Helper Functions ---
log_info() { echo "[BENCHMARK INFO] $1"; }
log_warn() { echo "[BENCHMARK WARN] $1"; }
log_error() { echo "[BENCHMARK ERROR] $1" >&2; }

# Function to execute a specific benchmark experiment
# Usage: execute_benchmark "Experiment Display Name" "experiment_arg_for_master_runner" "unique_container_suffix"
execute_benchmark() {
    local display_name="$1"
    local experiment_arg="$2" 
    local container_suffix="$3" # To make container names unique if run multiple times
    local timestamp=$(date +%Y%m%d-%H%M%S)

    log_info "--- Starting Benchmark: $display_name ---"
    
    local HOST_PARQR_CODE_PATH_ABS="$(cd "$PARQR_HOST_MAIN_DIR/$PARQR_CODE_SUBDIR" && pwd)"
    if [ -z "$HOST_PARQR_CODE_PATH_ABS" ]; then log_error "Path error for '$PARQR_HOST_MAIN_DIR/$PARQR_CODE_SUBDIR'."; return 1; fi
    local HOST_ARTIFACT_SCRIPTS_PATH_ABS="$(cd "$ARTIFACT_SCRIPTS_DIR_HOST" && pwd)"
    if [ -z "$HOST_ARTIFACT_SCRIPTS_PATH_ABS" ]; then log_error "Path error for '$ARTIFACT_SCRIPTS_DIR_HOST'."; return 1; fi

    local CONTAINER_PARQR_CODE_PATH="${DOCKER_WORKSPACE}/${DOCKER_PARQR_MOUNT_NAME}"
    local CONTAINER_ARTIFACT_SCRIPTS_PATH="${DOCKER_WORKSPACE}/${DOCKER_ARTIFACT_SCRIPTS_MOUNT_NAME}"
    local COMMAND_IN_DOCKER="python3 ${CONTAINER_ARTIFACT_SCRIPTS_PATH}/helper.py --experiment ${experiment_arg}"
    local CONTAINER_NAME="benchmark_runner_${container_suffix}_${timestamp}" # Unique container name

    log_info "Host ParQR code path: $HOST_PARQR_CODE_PATH_ABS (mounted to $CONTAINER_PARQR_CODE_PATH)"
    log_info "Host artifact scripts path: $HOST_ARTIFACT_SCRIPTS_PATH_ABS (mounted to $CONTAINER_ARTIFACT_SCRIPTS_PATH)"
    log_info "Container working directory: $CONTAINER_PARQR_CODE_PATH"
    log_info "Command to execute in Docker: bash -c \"$COMMAND_IN_DOCKER\""
    echo 

    local DOCKER_RUN_OUTPUT_FILE="benchmark_${experiment_arg}_${timestamp}_docker_output.log"
    local success=false

    # We need to use a named container to be able to cp from it, so --rm is removed initially.
    if sudo docker run -it \
        -v "${HOST_PARQR_CODE_PATH_ABS}:${CONTAINER_PARQR_CODE_PATH}" \
        -v "${HOST_ARTIFACT_SCRIPTS_PATH_ABS}:${CONTAINER_ARTIFACT_SCRIPTS_PATH}" \
        -w "${CONTAINER_PARQR_CODE_PATH}" \
        --name "${CONTAINER_NAME}" \
        "${IMAGE_TO_USE}" \
        bash -c "${COMMAND_IN_DOCKER}" > "$DOCKER_RUN_OUTPUT_FILE" 2>&1; then
        # Check the output file for success message from master_experiment_runner.py
        if grep -q "BENCHMARK_COMPLETED:${experiment_arg}" "$DOCKER_RUN_OUTPUT_FILE"; then
            log_info "--- Benchmark '$display_name' execution inside Docker reported completion. ---"
            success=true
        else
            log_error "--- Benchmark '$display_name' execution inside Docker FAILED to report completion. ---"
        fi
    else
        local exit_code=$?
        log_error "--- Benchmark '$display_name' FAILED (Docker run command failed with exit code $exit_code). ---"
    fi

    # Always print the log file location
    log_info "Detailed log from Docker run is in: $(pwd)/$DOCKER_RUN_OUTPUT_FILE"
    echo "--- Docker Run Log ($DOCKER_RUN_OUTPUT_FILE) ---"
    cat "$DOCKER_RUN_OUTPUT_FILE"
    echo "--- End Docker Run Log ---"


    if [ "$success" = true ]; then
        # Define where results will be copied on the host
        local HOST_RESULTS_TARGET_DIR="$(pwd)/results_${experiment_arg}_${timestamp}"
        mkdir -p "$HOST_RESULTS_TARGET_DIR"
        
        # Path to the results directory inside the container
        local CONTAINER_RESULTS_PATH="${CONTAINER_PARQR_CODE_PATH}/results" 

        log_info "Attempting to copy results from container '${CONTAINER_NAME}:${CONTAINER_RESULTS_PATH}' to host '${HOST_RESULTS_TARGET_DIR}'..."
        # docker cp <containerId>:<src_path> <dest_path>
        if sudo docker cp "${CONTAINER_NAME}:${CONTAINER_RESULTS_PATH}/." "${HOST_RESULTS_TARGET_DIR}/"; then
            log_info "Successfully copied results to: ${HOST_RESULTS_TARGET_DIR}"
            log_info "--- Benchmark '$display_name' PASSED and results copied. ---"
        else
            log_error "Failed to copy results using 'docker cp'. The results might still be available via the mounted volume at:"
            log_error "  ${HOST_PARQR_CODE_PATH_ABS}/results/"
            log_error "This 'docker cp' step is an explicit confirmation; primary access is via volume mount."
            # Even if cp fails, the main run might have been okay.
        fi
    fi

    # Clean up the container
    log_info "Removing container '${CONTAINER_NAME}'..."
    sudo docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || log_warn "Could not remove container ${CONTAINER_NAME}. It might have already been removed or failed to start."
    
    if [ "$success" = true ]; then
        return 0
    else
        return 1
    fi
}


# --- Main Script ---
log_info "Starting Benchmark Runner Script..."

log_info "Step 1: Verifying setup components..."
if [ ! -f "$DOCKER_IMAGE_NAME_FILE" ]; then log_error "File '$DOCKER_IMAGE_NAME_FILE' not found. Run 'setup_artifact.sh'."; exit 1; fi
IMAGE_TO_USE=$(cat "$DOCKER_IMAGE_NAME_FILE")
if [ -z "$IMAGE_TO_USE" ]; then log_error "Image name empty in '$DOCKER_IMAGE_NAME_FILE'. Re-run setup."; exit 1; fi
log_info "Using Docker image: $IMAGE_TO_USE"

if [ ! -d "$PARQR_HOST_MAIN_DIR/$PARQR_CODE_SUBDIR" ]; then log_error "Dir '$PARQR_HOST_MAIN_DIR/$PARQR_CODE_SUBDIR' not found. Run setup."; exit 1; fi
if [ ! -d "$ARTIFACT_SCRIPTS_DIR_HOST" ] || [ ! -f "$ARTIFACT_SCRIPTS_DIR_HOST/helper.py" ]; then log_error "Script '$ARTIFACT_SCRIPTS_DIR_HOST/helper.py' not found."; exit 1; fi
log_info "Required directories and scripts found."

while true; do
    echo
    log_info "--------------------------------------------------------------------"
    log_info "Select a Benchmark Experiment to Run:"
    log_info " (Results will be volume-mounted and also explicitly copied to a timestamped directory on host)"
    log_info "--------------------------------------------------------------------"
    log_info "  [1] Parameter Tuning (Generates Fig 2 style data)"
    log_info "  [2] Scalability Analysis (Generates Fig 4a, 4b style data)"
    log_info "  [3] Throughput Evaluation (Generates Fig 5 style data)"
    log_info "  [4] Run ALL Benchmarks (1, 2, and 3)"
    log_info "  [0] Exit Benchmark Runner"
    log_info "--------------------------------------------------------------------"
    read -p "Enter your choice: " choice
    echo

    case $choice in
        1) execute_benchmark "Parameter Tuning" "param_tuning" "param" ;;
        2) execute_benchmark "Scalability Analysis" "scalability" "scale" ;;
        3) execute_benchmark "Throughput Evaluation" "throughput" "thru" ;;
        4) 
            log_info "Running ALL Benchmarks..."
            execute_benchmark "Parameter Tuning" "param_tuning" "param_all" && \
            execute_benchmark "Scalability Analysis" "scalability" "scale_all" && \
            execute_benchmark "Throughput Evaluation" "throughput" "thru_all"
            log_info "All benchmarks attempted." ;;
        0) log_info "Exiting Benchmark Runner."; break ;;
        *) log_warn "Invalid choice. Please try again." ;;
    esac
done

exit 0
