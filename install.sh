
#!/usr/bin/env bash

set -euo pipefail
umask 077

VERSION="0.1.0"
IMAGE="ccv-core:${VERSION}"
BASE_IMAGE="python:3.13-slim"

CHECK_ONLY=false
ALLOW_PULL=false

info() {
    printf '[INFO] %s\n' "$*"
}

ok() {
    printf '[ OK ] %s\n' "$*"
}

fail() {
    printf '[FAIL] %s\n' "$*" >&2
    exit 1
}

case "${1:-}" in
    "")
        ;;
    --check)
        CHECK_ONLY=true
        ;;
    --allow-pull)
        ALLOW_PULL=true
        ;;
    --help|-h)
        printf '%s\n' \
            "CCV Core Deployment" \
            "./install.sh              Deploy using local images" \
            "./install.sh --check      Read-only compatibility check" \
            "./install.sh --allow-pull Authorize missing base image download"
        exit 0
        ;;
    *)
        fail "Unsupported argument: $1"
        ;;
esac

[[ "$#" -le 1 ]] || fail "Too many arguments."

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$APP_DIR"

printf '\nCCV Core Deployment - v%s\n' "$VERSION"
printf '%s\n\n' "======================================"

# 1. Existing environment only.

[[ "$(uname -s)" == "Linux" ]] \
    || fail "Linux is required."

[[ "$(uname -m)" == "x86_64" ]] \
    || fail "Architecture not qualified for this release."

for tool in git docker stat realpath; do
    command -v "$tool" >/dev/null 2>&1 \
        || fail "Required command unavailable: $tool"
done

[[ -f Dockerfile && -x ccv-core.sh ]] \
    || fail "Deployment files missing or invalid."

REVISION="$(git rev-parse HEAD)"

[[ -z "$(git status --porcelain)" ]] \
    || fail "Git working directory is not clean."

ok "Git source: $REVISION"

# Use the existing local Docker daemon.
# Environment changes apply only to this process.

unset DOCKER_CONTEXT
export DOCKER_HOST="unix:///var/run/docker.sock"

[[ -S /var/run/docker.sock ]] \
    || fail "Standard local Docker socket is unavailable."

docker info >/dev/null 2>&1 \
    || fail "Cannot access the existing Docker daemon."

DOCKER_VERSION="$(docker version --format '{{.Server.Version}}')"

ok "Docker Engine: $DOCKER_VERSION"

SECURITY="$(docker info --format '{{json .SecurityOptions}}')"

case "$SECURITY" in
    *rootless*|*userns*)
        fail "Docker ownership mapping requires separate qualification."
        ;;
esac

# 2. Protected runtime directory.

RUNTIME_PARENT="$(dirname "$APP_DIR")/ccv-runtime"
DEFAULT_DATA="${RUNTIME_PARENT}/core"

[[ ! -L "$RUNTIME_PARENT" && ! -L "$DEFAULT_DATA" ]] \
    || fail "Symbolic links in default runtime path are unsupported."

DATA_DIR="${CCV_CORE_DATA_DIR:-$DEFAULT_DATA}"

[[ ! -L "$DATA_DIR" ]] \
    || fail "Runtime directory must not be a symbolic link."

DATA_DIR="$(realpath -m -- "$DATA_DIR")"

case "$DATA_DIR" in
    "$APP_DIR"|"$APP_DIR"/*)
        fail "Runtime data must remain outside the Git repository."
        ;;
    *','*|*'"'*)
        fail "Unsupported runtime path characters."
        ;;
esac

if [[ -e "$DATA_DIR" ]]; then
    [[ -d "$DATA_DIR" ]] \
        || fail "Runtime path is not a directory."

    [[ "$(stat -c '%u:%g:%a' "$DATA_DIR")" == "10001:10001:700" ]] \
        || fail "Existing runtime directory permissions are incompatible."

    ok "Existing runtime directory validated"
else
    [[ "$DATA_DIR" == "$DEFAULT_DATA" ]] \
        || fail "Custom runtime directory must already exist."

    [[ "$EUID" -eq 0 ]] \
        || fail "Authorized administrator required to prepare runtime directory."

    info "Runtime directory will be created during deployment."
fi

# 3. Image preparation.

validate_image() {
    local revision metadata

    revision="$(docker image inspect "$IMAGE" \
        --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')"

    [[ "$revision" == "$REVISION" ]] \
        || fail "Existing image does not match this Git revision."

    metadata="$(docker image inspect "$IMAGE" \
        --format '{{.Os}} {{.Architecture}} {{.Config.User}} {{json .Config.Entrypoint}}')"

    [[ "$metadata" == 'linux amd64 10001:10001 ["python","-m","cc_vision_import.ccv"]' ]] \
        || fail "Existing image configuration is incompatible."

    ok "CCV Core image identity and configuration validated"
}

IMAGE_EXISTS=false

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    validate_image
    IMAGE_EXISTS=true
else
    if docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
        ok "Python base image available locally"
    elif [[ "$ALLOW_PULL" == true ]]; then
        info "Downloading explicitly authorized base image."

        docker pull "$BASE_IMAGE" \
            || fail "Download failed. Check approved proxy or image availability."
    else
        fail "Base image unavailable. Use an approved image upload or --allow-pull."
    fi
fi

# Read-only mode ends before creating directories,
# building images or starting containers.

if [[ "$CHECK_ONLY" == true ]]; then
    ok "Read-only preflight completed"
    exit 0
fi

if [[ "$IMAGE_EXISTS" == false ]]; then
    info "Building CCV Core image."

    BASE_ID="$(docker image inspect "$BASE_IMAGE" --format '{{.Id}}')"

    DOCKER_BUILDKIT=0 docker build \
        --pull=false \
        --network none \
        --target core \
        --label "org.opencontainers.image.version=$VERSION" \
        --label "org.opencontainers.image.revision=$REVISION" \
        --label "ccv.core.base-image=$BASE_ID" \
        --tag "$IMAGE" \
        . || fail "Container image build failed."

    validate_image
fi

# 4. Create only dedicated CCV Core directories.

if [[ ! -d "$DATA_DIR" ]]; then
    if [[ ! -d "$RUNTIME_PARENT" ]]; then
        mkdir -m 700 -- "$RUNTIME_PARENT"
    fi

    mkdir -m 700 -- "$DATA_DIR"
    chown 10001:10001 -- "$DATA_DIR"
fi

[[ "$(stat -c '%u:%g:%a' "$DATA_DIR")" == "10001:10001:700" ]] \
    || fail "Runtime directory validation failed."

ok "Protected runtime directory ready"

# 5. Offline runtime smoke test.

info "Validating isolated container runtime."

docker run --rm \
    --pull=never \
    --network none \
    --read-only \
    --user 10001:10001 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --tmpfs /tmp:rw,noexec,nosuid,size=16m,mode=1777 \
    --mount "type=bind,source=$DATA_DIR,target=/data" \
    --entrypoint python \
    "$IMAGE" \
    -c '
import os
import ssl
import tempfile

assert os.getuid() == 10001
assert os.getgid() == 10001

ssl.create_default_context()

with tempfile.TemporaryFile(dir="/data") as handle:
    handle.write(b"CCV Core runtime validation")
    handle.flush()

print("Runtime validation passed.")
' || fail "Container runtime validation failed."

# 6. Validate the actual application launcher.

export CCV_CORE_IMAGE="$IMAGE"
export CCV_CORE_DATA_DIR="$DATA_DIR"

CCV_ALLOW_INSECURE_TLS_EXCEPTION=false \
CCV_TRUSTED_CA="" \
    ./ccv-core.sh --help \
    || fail "Application launcher validation failed."

ok "Application launcher validated"

printf '\n%s\n' "======================================"
printf '%s\n' "CCV CORE DEPLOYMENT COMPLETED"
printf '%s\n' "======================================"
printf 'Version:  %s\n' "$VERSION"
printf 'Image:    %s\n' "$IMAGE"
printf 'Revision: %s\n' "$REVISION"
printf 'Data:     %s\n' "$DATA_DIR"
printf 'Mode:     Offline qualification\n'
printf '\nStart CCV Core:\n\n'
printf '  ./ccv-core.sh\n\n'