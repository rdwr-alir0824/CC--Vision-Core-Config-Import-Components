#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077

repository="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
temporary=""
token=""
helper_name=""
operation_name=""
operation_pid=""
cleanup_failed=0

fail() { printf 'CC-Vision: %s\n' "$1" >&2; exit "${2:-2}"; }

remove_owned_container() {
    local name="$1" label
    [[ -n "$name" ]] || return 0
    if ! label="$(docker container inspect --format '{{ index .Config.Labels "ccv.launcher.run" }}' "$name" 2>/dev/null)"; then
        if [[ "$name" == "$operation_name" && -n "$operation_pid" ]]; then
            printf 'Warning: interrupted container could not be inspected; confirm cleanup with the administrator: %s\n' "$name" >&2
            cleanup_failed=1
        fi
        return 0
    fi
    if [[ "$label" == "$token" ]]; then
        if ! docker container rm --force "$name" >/dev/null 2>&1; then
            printf 'Warning: could not remove this launcher container; administrator cleanup required: %s\n' "$name" >&2
            cleanup_failed=1
        fi
    fi
}

cleanup() {
    local status=$?
    trap - EXIT INT TERM
    unset ccv_username ccv_password
    remove_owned_container "$operation_name"
    remove_owned_container "$helper_name"
    if [[ -n "$operation_pid" ]] && kill -0 "$operation_pid" 2>/dev/null; then
        kill -TERM "$operation_pid" 2>/dev/null || true
        wait "$operation_pid" 2>/dev/null || true
    fi
    if [[ -n "$temporary" ]]; then
        # Only known files in our uniquely created directory, never administrator secrets.
        if ! rm -f -- "$temporary/credentials.json" "$temporary/ca.pem" "$temporary/tls-exception.json" \
            "$temporary/stdout" "$temporary/stderr"; then
            printf 'Warning: temporary-file cleanup failed; administrator action required: %s\n' "$temporary" >&2
            cleanup_failed=1
        fi
        if ! rmdir -- "$temporary"; then
            printf 'Warning: temporary directory remains: %s\n' "$temporary" >&2
            cleanup_failed=1
        fi
    fi
    if [[ "$status" == "0" && "$cleanup_failed" == "1" ]]; then status=3; fi
    exit "$status"
}
trap cleanup EXIT
trap 'printf "\nInterrupted; cleaning this run only.\n" >&2; exit 130' INT
trap 'printf "\nTerminated; cleaning this run only.\n" >&2; exit 143' TERM

qualify_default_root=0
single_site_mode=""
site_batch_mode=""
single_site_arguments=()
if [[ "${1:-}" == "--help" ]]; then
    printf 'Usage: ./ccv.sh [--qualify-default-root]\n       ./ccv.sh --single-site-dry-run|--single-site-create --input /incoming/... --comparison /reports/... --destination-snapshot /reports/... --site-reference source:node-N\n       ./ccv.sh --sites-dry-run|--sites-execute|--sites-resume --input /incoming/... --comparison /reports/... --destination-snapshot /reports/... [--target-version VERSION] [--operation-delay SECONDS] [--readback-interval SECONDS] [--readback-attempts COUNT]\nSelect menu choice 2 for explicit Site modes. Writes require separate interactive authorization; batch authorization covers only the reviewed list and destination.\nRequires Bash, Docker Compose v2 and the existing shared image/runtime directories.\n'
    exit 0
fi
if [[ $# -eq 1 && "$1" == "--qualify-default-root" ]]; then
    qualify_default_root=1
    shift
fi
while [[ $# -gt 0 ]]; do
    case "$1" in
        --single-site-dry-run|--single-site-create)
            [[ -z "$single_site_mode" && -z "$site_batch_mode" ]] || fail "Select only one single-Site mode."
            single_site_mode="${1#--single-site-}"
            shift
            ;;
        --sites-dry-run|--sites-execute|--sites-resume)
            [[ -z "$single_site_mode" && -z "$site_batch_mode" ]] || fail "Select only one Site mode."
            site_batch_mode="${1#--sites-}"
            shift
            ;;
        --input|--comparison|--destination-snapshot|--site-reference|--target-version|--operation-delay|--readback-interval|--readback-attempts)
            [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || fail "Missing single-Site argument value."
            single_site_arguments+=("$1" "$2")
            shift 2
            ;;
        *) fail "Use ./ccv.sh --help for supported arguments." ;;
    esac
done
[[ ${#single_site_arguments[@]} -eq 0 || -n "$single_site_mode" || -n "$site_batch_mode" ]] ||
    fail "Single-Site arguments require an explicitly selected mode."
[[ $# -eq 0 ]] || fail "Use ./ccv.sh without arguments, or --help."

printf '\nCC-Vision Master\n\n1. Source Vision - Full Supported Backup\n2. Destination CC - Read-Only Site Discovery\n3. Destination CC - Validate Transferred Backup\n4. Exit\n'
if [[ -n "$single_site_mode" ]]; then
    printf 'Explicit override for choice 2: single-Site %s. Create still requires separate in-session authorization.\n' "$single_site_mode"
fi
if [[ -n "$site_batch_mode" ]]; then
    [[ "$qualify_default_root" == "0" ]] || fail "Root qualification and batch Site modes are separate."
    printf 'Explicit override for choice 2: full hierarchical Sites %s. Execution/resume requires one separate batch authorization.\n' "$site_batch_mode"
fi
IFS= read -r -p 'Select operation: ' selection || fail "No operation selected."
[[ "$selection" == "4" ]] && exit 0
[[ "$selection" =~ ^[123]$ ]] || fail "Select 1, 2, 3 or 4."
[[ "$qualify_default_root" == "0" || "$selection" == "2" ]] ||
    fail "--qualify-default-root requires menu choice 2."
[[ -z "$single_site_mode" || "$selection" == "2" ]] || fail "Single-Site mode requires menu choice 2."
[[ -z "$site_batch_mode" || "$selection" == "2" ]] || fail "Site batch mode requires menu choice 2."

command -v docker >/dev/null 2>&1 || fail "Docker is missing; ask the administrator to install/configure Docker."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is missing or unavailable."
[[ -f "$repository/compose.yaml" ]] || fail "compose.yaml is missing; use the approved application checkout."
compose=(docker compose --project-directory "$repository" -f "$repository/compose.yaml")
configuration="$("${compose[@]}" --profile source --profile destination --profile destination-discovery config --format json 2>/dev/null)" ||
    fail "Compose configuration failed; ask the administrator to check the checkout and private settings."
# Resolve image/path overrides through Compose itself, including its private .env.
image_list="$("${compose[@]}" --profile source --profile destination --profile destination-discovery config --images 2>/dev/null)" ||
    fail "Cannot resolve the shared Compose image."
mapfile -t images <<< "$image_list"
image="${images[0]}"
[[ -n "$image" && "$image" != -* && "$image" != *[[:space:]]* ]] || fail "Invalid shared image reference."
for candidate in "${images[@]}"; do
    [[ "$candidate" == "$image" ]] || fail "All Compose roles must use the same approved image."
done
docker image inspect "$image" >/dev/null 2>&1 ||
    fail "Shared image is unavailable; ask the administrator to build/load the approved image."

temporary="$(mktemp -d "${TMPDIR:-/tmp}/ccv-launcher.XXXXXXXXXX")" || fail "Cannot create a private temporary directory."
temporary="$(cd -- "$temporary" && pwd -P)"
token="${temporary##*/}"
helper_name="$token-helper"
operation_name="$token-operation"
[[ "$temporary" != "$repository/"* && "$temporary" != *,* && "$temporary" != *$'\n'* && "$temporary" != *$'\r'* ]] ||
    fail "Temporary credentials require a dedicated temporary location outside the checkout, without commas."

offline() {
    docker run --pull never --rm -i --name "$helper_name" --label "ccv.launcher.run=$token" \
        --network none --user 10001:10001 --read-only --cap-drop ALL \
        --security-opt no-new-privileges:true \
        --mount "type=bind,source=$temporary,target=/run/setup" \
        "${helper_mounts[@]}" --entrypoint python "$image" -B -m cc_vision_import.launcher_helper "$@"
}
helper_mounts=()
settings="$(printf '%s' "$configuration" | offline settings "$selection" 2>"$temporary/stderr")" ||
    fail "Image/configuration mismatch; rebuild the approved shared image and verify Compose settings."
unset configuration
mapfile -t paths <<< "$settings"
[[ ${#paths[@]} -eq 5 && "${paths[0]}" == "$image" ]] ||
    fail "Configured Compose image differs from the inspected shared image; use the same CC_VISION_IMAGE on both hosts."
output="${paths[1]}"
config_directory="${paths[2]}"
requested_ca="${paths[3]}"
allow_exceptions="${paths[4]}"
[[ "$allow_exceptions" =~ ^(true|false)$ ]] || fail "Invalid administrator TLS restriction; rebuild the shared image."
[[ -d "$output" ]] || fail "Required runtime directory is missing; administrator must provision: $output"

run_operation() {
    local status summary_status exception_used=0 answer
    while true; do
        status=0
        "${compose[@]}" --profile "$profile" run --rm --no-deps -T \
            --name "$operation_name" --label "ccv.launcher.run=$token" "$service" "$@" \
            >"$temporary/stdout" 2>"$temporary/stderr" &
        operation_pid=$!
        wait "$operation_pid" || status=$?
        operation_pid=""
        summary_status=0
        helper_mounts=()
        offline summary "$selection" "$status" "$output" "$report_name" \
            <"$temporary/stdout" 2>"$temporary/stderr" || summary_status=$?
        if [[ "$status" == "1" && "$summary_status" == "11" && "$exception_used" == "0" ]]; then
            [[ "$allow_exceptions" == "true" ]] ||
                fail "Certificate verification failed. This deployment prohibits insecure exceptions; ask the administrator to correct CA trust/certificate SAN." 1
            printf 'WARNING: Controller identity cannot be authenticated; an attacker could impersonate the controller and intercept credentials. HTTPS encryption alone does not establish identity.\n' >&2
            answer=""
            printf 'Untrusted/self-signed certificate. Continue without certificate verification for this session only? [y/N] ' >&2
            IFS= read -r answer || answer=""
            [[ "$answer" == "y" || "$answer" == "Y" || "$answer" == "yes" || "$answer" == "YES" ]] ||
                fail "TLS exception declined; stopped without unverified authentication." 1
            printf '%s' "$origin" | offline approve-exception "$allow_exceptions" 2>"$temporary/stderr" ||
                fail "Could not prepare a private TLS exception; no unverified authentication attempted."
            exception_used=1
            if [[ "$selection" == "1" ]]; then
                export CCV_TLS_VERIFY=false CCV_TRUSTED_CA=""
            else
                export CCV_DESTINATION_TLS_VERIFY=false CCV_DESTINATION_TRUSTED_CA=""
            fi
            printf 'WARNING: Controller identity is NOT VERIFIED; exception applies only to the selected origin and current execution.\n' >&2
            continue
        fi
        if [[ "$status" == "1" && "$summary_status" == "10" ]]; then exit 1; fi
        if [[ "$summary_status" != "0" ]]; then
            [[ "$status" != "0" ]] || status=3
            fail "Application/Docker output was not a valid result (exit $status). Check administrator TLS, permissions and image configuration; raw output is not displayed." "$status"
        fi
        if [[ "$status" == "0" && ( "$site_batch_mode" == "execute" || "$site_batch_mode" == "resume" ) ]]; then
            printf 'Starting fresh authenticated batch session; authorization applies only to the reviewed list and destination.\n'
            status=0
            "${compose[@]}" --profile "$profile" run --rm --no-deps -it \
                --name "$operation_name" --label "ccv.launcher.run=$token" "$service" \
                "sites-$site_batch_mode" "${single_site_arguments[@]}" || status=$?
            exit "$status"
        fi
        if [[ "$status" == "0" && "$single_site_mode" == "create" ]]; then
            printf 'Starting fresh controlled preflight; authorization will be requested inside the same session before one create.\n'
            status=0
            "${compose[@]}" --profile "$profile" run --rm --no-deps -it \
                --name "$operation_name" --label "ccv.launcher.run=$token" "$service" \
                site-create "${single_site_arguments[@]}" || status=$?
            exit "$status"
        fi
        exit "$status"
    done
}
report_name=""
if [[ "$selection" == "3" ]]; then
    [[ -d "$config_directory" ]] || fail "Incoming directory is missing; transfer the complete backup folder first."
    helper_mounts=(--mount "type=bind,source=$config_directory,target=/incoming,readonly")
    folders="$(offline backups </dev/null 2>"$temporary/stderr")" ||
        fail "Cannot list incoming backups; check UID 10001 permissions and transfer completeness."
    [[ -n "$folders" ]] || fail "No incoming Vision backup folders found; transfer a complete folder first."
    mapfile -t available <<< "$folders"
    for index in "${!available[@]}"; do printf '%d. %s\n' "$((index + 1))" "${available[$index]}"; done
    IFS= read -r -p 'Select backup: ' choice || fail "No backup selected."
    [[ "$choice" =~ ^[1-9][0-9]{0,4}$ ]] && (( choice <= ${#available[@]} )) ||
        fail "Select a displayed backup number."
    backup="${available[$((choice - 1))]}"
    offline check-backup "$backup" </dev/null 2>"$temporary/stderr" ||
        fail "Backup is missing/incomplete or unsafe; transfer all six module directories and summary.json, then verify integrity."
    report_name="$token-sites.json"
    profile=destination
    service=ccv-destination
    run_operation --operation tree-readiness-preview --site-readiness --report-format json \
        --input "/incoming/$backup/organization-tree/tree.json" --output "/reports/$report_name"
fi

[[ -d "$config_directory" ]] || fail "Administrator CA directory is missing: $config_directory"
touch "$temporary/credentials.json" "$temporary/ca.pem" "$temporary/tls-exception.json"
chmod 0600 "$temporary/credentials.json" "$temporary/ca.pem" "$temporary/tls-exception.json"
if [[ "$(id -u)" == "10001" && "$(id -g)" == "10001" ]]; then
    chmod 0700 "$temporary"
else
    if [[ "$(id -u)" == "0" ]]; then
        chgrp 10001 "$temporary"
        chown 10001:10001 "$temporary/credentials.json" "$temporary/ca.pem" "$temporary/tls-exception.json"
    else
        command -v sudo >/dev/null 2>&1 || fail "Approved sudo is required to provision UID/GID 10001 temporary files."
        sudo -v || fail "Sudo authorization was not granted; no credentials collected."
        sudo -n chgrp 10001 "$temporary" || fail "Cannot provision temporary directory group."
        sudo -n chown 10001:10001 "$temporary/credentials.json" "$temporary/ca.pem" "$temporary/tls-exception.json" ||
            fail "Cannot provision temporary credential ownership."
    fi
    # Container group may traverse, not list/write; the operator can always unlink files.
    chmod 0710 "$temporary"
fi
printf 'Use only an authorized controller/account. HTTPS certificate verification is enabled initially.\n'
if [[ "$selection" == "2" ]]; then
    printf 'Administrator-restricted CC HTTPS egress is required; this launcher does not change firewall rules.\n'
fi
IFS= read -r -p 'Controller IP or hostname (not URL): ' controller || fail "Controller address is required."
helper_mounts=(--mount "type=bind,source=$config_directory,target=/run/admin,readonly")
origin="$(printf '%s' "$controller" | offline prepare "$selection" "$requested_ca" 2>"$temporary/stderr")" ||
    fail "Invalid address, temporary permissions, or CA trust configuration; no credentials collected."
[[ "$origin" == https://* && "$origin" != *$'\n'* && "$origin" != *$'\r'* ]] ||
    fail "Invalid HTTPS preparation result; rebuild the shared image."
unset controller
unset ccv_username ccv_password
IFS= read -r -p 'Username: ' ccv_username || fail "Username is required."
IFS= read -r -s -p 'Password: ' ccv_password || fail "Password input was interrupted."
printf '\n' >&2
printf '%s\0%s\0' "$ccv_username" "$ccv_password" | offline credentials 2>"$temporary/stderr" ||
    fail "Credential input is invalid; values were not logged."
unset ccv_username ccv_password
if [[ "$selection" == "1" ]]; then
    profile=source
    service=ccv-source
    export CCV_VISION_URL="$origin" CCV_TLS_VERIFY=true CCV_SOURCE_SECRETS_DIR="$temporary"
    export CCV_ALLOW_INSECURE_TLS_EXCEPTION="$allow_exceptions" CCV_TRUSTED_CA=/run/secrets/ca.pem
    run_operation backup
else
    profile=destination-discovery
    service=ccv-destination-discovery
    export CCV_DESTINATION_URL="$origin" CCV_DESTINATION_SECRETS_DIR="$temporary"
    export CCV_DESTINATION_TLS_VERIFY=true CCV_ALLOW_INSECURE_TLS_EXCEPTION="$allow_exceptions"
    export CCV_DESTINATION_TRUSTED_CA=/run/secrets/ca.pem
    if [[ -n "$site_batch_mode" ]]; then
        run_operation sites-dry-run "${single_site_arguments[@]}"
    elif [[ -n "$single_site_mode" ]]; then
        run_operation site-dry-run "${single_site_arguments[@]}"
    elif [[ "$qualify_default_root" == "1" ]]; then
        run_operation discover-sites --qualify-default-root
    else
        run_operation discover-sites
    fi
fi
