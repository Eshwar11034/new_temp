#!/bin/bash

# --- Script Configuration ---
# This script should be run from the root directory of the extracted artifact.

# Docker image to pull from Docker Hub (ensure this is your final, tested x86_64 image)
DOCKER_IMAGE_TO_PULL="parsqp/europar2025:latest" 


# Tag for locally built image if pulling fails
LOCAL_BUILD_IMAGE_TAG="parsqp/europar2025-localbuild-$(date +%Y%m%d-%H%M%S)" # Unique local build tag

# Git Repositories - will be cloned into the current directory
PARQR_REPO_URL="https://github.com/PDCRL/ParQR.git"
PARQR_LOCAL_DIR_NAME="pdcrl-parqr"  # Cloned as ./pdcrl-parqr


# File to store the final Docker image name to be used by other scripts
# Will be created in the current directory.
DOCKER_IMAGE_NAME_FILE=".artifact_docker_image_name"


# --- Helper Functions ---
log_info() {
    echo "[SETUP INFO] $1"
}

log_warn() {
    echo "[SETUP WARN] $1"
}

log_error() {
    echo "[SETUP ERROR] $1" >&2
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

get_docker_platform() {
    local arch
    arch=$(uname -m)
    case $arch in
        x86_64) echo "linux/amd64" ;;
        aarch64) echo "linux/arm64" ;;
        arm64) echo "linux/arm64" ;;
        *) log_error "Unsupported host architecture for build: $arch"; return 1 ;;
    esac
    return 0
}

# --- Main Setup Logic ---

log_info "Starting Artifact Setup Script..."
log_info "Current working directory: $(pwd)"
log_info "This script will set up the artifact in the current directory."

# Step 0: Sudo check
if [ "$(id -u)" -ne 0 ]; then
    log_warn "This script uses 'sudo' for Docker commands. You might be prompted for your password."
    if ! sudo -n true 2>/dev/null; then
        log_info "Attempting to acquire sudo privileges..."
        if ! sudo true; then log_error "Failed to acquire sudo privileges."; exit 1; fi
    fi
fi

# Step 1: Check Prerequisites (Docker, Git)
log_info "Step 1: Checking prerequisites..."
if ! command_exists docker; then log_error "Docker command not found. Please install Docker."; exit 1; fi
if ! command_exists git; then log_error "Git command not found. Please install Git."; exit 1; fi
if ! command_exists uname; then log_error "'uname' command not found. Cannot determine host architecture."; exit 1; fi

log_info "Verifying Docker daemon access..."
if ! sudo docker info > /dev/null 2>&1; then
    log_error "Cannot access Docker daemon even with sudo. Ensure Docker is installed, running, and you have permissions."
    exit 1
fi
log_info "Prerequisites met. Docker daemon accessible."


# Step 2: Set up Docker image (Pull or Build)
log_info "Step 2: Setting up Docker image..."
IMAGE_TO_USE="" 

log_info "Attempting to pull Docker image: $DOCKER_IMAGE_TO_PULL..."
if sudo docker pull "$DOCKER_IMAGE_TO_PULL"; then
    log_info "Docker image '$DOCKER_IMAGE_TO_PULL' pulled successfully."
    IMAGE_TO_USE="$DOCKER_IMAGE_TO_PULL"

    PULLED_ARCH=$(sudo docker image inspect "$DOCKER_IMAGE_TO_PULL" --format '{{.Architecture}}' 2>/dev/null)
    HOST_ARCH_RAW=$(uname -m)
    HOST_ARCH_DOCKER_FORMAT=$(get_docker_platform | cut -d'/' -f2) 

    log_info "Pulled image architecture: $PULLED_ARCH. Host architecture effectively: $HOST_ARCH_DOCKER_FORMAT (raw: $HOST_ARCH_RAW)."
    if [[ "$PULLED_ARCH" != "$HOST_ARCH_DOCKER_FORMAT" ]]; then
        log_warn "----------------------------------------------------------------------------------";
        log_warn "POTENTIAL ARCHITECTURE MISMATCH: PULLED IMAGE ($PULLED_ARCH) vs HOST ($HOST_ARCH_DOCKER_FORMAT)!";
        log_warn "If host is ARM and image AMD64, ensure Docker emulation (Rosetta/QEMU) is active.";
        log_warn "If host is AMD64 and image is ARM, execution will likely fail.";
        log_warn "----------------------------------------------------------------------------------";
    fi
else
    log_warn "Failed to pull Docker image '$DOCKER_IMAGE_TO_PULL'. Attempting to build locally from Dockerfile."
    # Fall through to local build logic
fi

if [ -z "$IMAGE_TO_USE" ]; then # If pull failed
    log_info "Proceeding with local Docker build..."
    if [ ! -f Dockerfile ]; then # Dockerfile should be in the current directory
        log_error "Dockerfile not found in the current directory ($(pwd)). Cannot build image locally."
        exit 1
    fi

    TARGET_DOCKER_PLATFORM=$(get_docker_platform)
    if [ $? -ne 0 ]; then log_error "Cannot determine target platform for local build."; exit 1; fi
    log_info "Determined Target Docker Platform for local build: $TARGET_DOCKER_PLATFORM"

    log_info "Building Docker image '$LOCAL_BUILD_IMAGE_TAG' locally for platform '$TARGET_DOCKER_PLATFORM'..."
    if sudo DOCKER_BUILDKIT=1 docker build --platform "$TARGET_DOCKER_PLATFORM" -t "$LOCAL_BUILD_IMAGE_TAG" .; then # "." for current dir
        log_info "Docker image '$LOCAL_BUILD_IMAGE_TAG' built successfully locally."
        IMAGE_TO_USE="$LOCAL_BUILD_IMAGE_TAG"
        BUILT_ARCH=$(sudo docker image inspect "$LOCAL_BUILD_IMAGE_TAG" --format '{{.Architecture}}' 2>/dev/null)
        EXPECTED_ARCH_SHORT=$(echo "$TARGET_DOCKER_PLATFORM" | cut -d'/' -f2)
        log_info "Locally built image architecture: $BUILT_ARCH."
        if [[ "$BUILT_ARCH" != "$EXPECTED_ARCH_SHORT" ]]; then
            log_warn "Warning: Locally built image architecture '$BUILT_ARCH' might not match requested platform '$EXPECTED_ARCH_SHORT'."
        fi
    else
        log_error "Failed to build Docker image locally. Please check Dockerfile, Docker setup, and error messages."
        exit 1
    fi
fi

if [ -z "$IMAGE_TO_USE" ]; then
    log_error "CRITICAL: Failed to obtain a usable Docker image. Setup cannot continue."
    exit 1
fi
log_info "Using Docker image: $IMAGE_TO_USE for subsequent steps."
echo "$IMAGE_TO_USE" > "$DOCKER_IMAGE_NAME_FILE" # Create this file in the current directory
if [ $? -ne 0 ]; then
    log_error "Failed to write Docker image name to $DOCKER_IMAGE_NAME_FILE file in $(pwd)."
    exit 1
else
    log_info "Docker image name '$IMAGE_TO_USE' saved to $(pwd)/$DOCKER_IMAGE_NAME_FILE"
fi


# Step 3: Clone the required repositories (into the current directory)
log_info "Step 3: Cloning Git repositories into $(pwd)..."

if [ -d "$PARQR_LOCAL_DIR_NAME/.git" ]; then log_info "Repo '$PARQR_LOCAL_DIR_NAME' exists.";
elif [ -d "$PARQR_LOCAL_DIR_NAME" ]; then log_warn "'$PARQR_LOCAL_DIR_NAME' exists but not Git repo. Remove/rename."; exit 1;
else
    log_info "Cloning ParQR ($PARQR_REPO_URL)..."
    if git clone "$PARQR_REPO_URL" "$PARQR_LOCAL_DIR_NAME"; then log_info "ParQR cloned to './$PARQR_LOCAL_DIR_NAME'.";
    else log_error "Failed to clone ParQR."; exit 1; fi
fi


# Step 4: Final Instructions
log_info "Step 4: Setup Complete!"
echo
log_info "--------------------------------------------------------------------"
log_info "Artifact Setup Summary:"
log_info "1. All operations performed in the current directory: $(pwd)"
log_info "   This directory should contain Dockerfile, this setup script, run_minimal_test.sh, run_benchmarks.sh,"
log_info "   config/, scripts/ (containing helper.py),"
log_info "   and now also .artifact_docker_image_name, $PARQR_LOCAL_DIR_NAME/, and $PARSQP_LOCAL_DIR_NAME/."
log_info "2. Docker image ready for use: $IMAGE_TO_USE"
log_info "   (Image name also stored in $(pwd)/$DOCKER_IMAGE_NAME_FILE)"
log_info "3. ParQR repository in: $(pwd)/$PARQR_LOCAL_DIR_NAME"
log_info "--------------------------------------------------------------------"
echo
log_info "Next Steps (run from this directory: $(pwd)):"
log_info "1. To run a quick minimal test:"
log_info "   ./run_minimal_test.sh"
log_info "2. To run full benchmarks:"
log_info "   ./run_benchmarks.sh"
log_info "--------------------------------------------------------------------"

exit 0