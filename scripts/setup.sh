#!/usr/bin/env bash
# macOS bootstrap; use a downloaded file to retain interactive stdin.
set -euo pipefail
check_only=false
network=auto
proxy_file=''
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check-only) check_only=true; shift ;;
        --direct) network=direct; shift ;;
        --proxy-file) [[ $# -ge 2 ]] || { echo 'Missing proxy file path'; exit 2; }; proxy_file=$2; shift 2 ;;
        *) echo 'Usage: bash setup.sh [--check-only] [--direct | --proxy-file PATH]' >&2; exit 2 ;;
    esac
done
[[ $(uname -s) == Darwin ]] || { echo 'Use setup.ps1 on Windows. This entry point is for macOS.' >&2; exit 2; }
task_state="${CODEX_HOME:-$HOME/.codex}/overseas-web-prospecting"
mkdir -p "$task_state"
printf '%s\n' '{"status":"setup_in_progress","next_action":"Follow terminal instructions and rerun."}' > "$task_state/environment-report.json"
echo '[1/6] Checking Homebrew'
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v brew >/dev/null; then
    $check_only && { echo '[NEEDS ACTION] Homebrew is missing.' >&2; exit 2; }
    curl -fLSs https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$task_state/homebrew-install.sh"
    /bin/bash "$task_state/homebrew-install.sh"
fi
install_formula() {
    $check_only && { echo "[NEEDS ACTION] Missing $1. Rerun without --check-only." >&2; exit 2; }
    brew install "$1"
}
echo '[2/6] Checking Python, Git and Node.js'
if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then install_formula python; fi
if ! command -v git >/dev/null || ! git --version >/dev/null 2>&1; then install_formula git; fi
if brew --prefix node@24 >/dev/null 2>&1; then export PATH="$(brew --prefix node@24)/bin:$PATH"; fi
if ! command -v node >/dev/null || ! node -e 'process.exit(Number(process.versions.node.split(".")[0])>=22?0:1)'; then
    install_formula node@24
    export PATH="$(brew --prefix node@24)/bin:$PATH"
fi
echo '[3/6] Preparing Docker Desktop'
export PATH="/Applications/Docker.app/Contents/Resources/bin:$HOME/.docker/bin:$PATH"
if ! command -v docker >/dev/null && [[ ! -d /Applications/Docker.app ]]; then
    $check_only && { echo '[NEEDS ACTION] Docker is missing.' >&2; exit 2; }
    brew install --cask docker-desktop
fi
if ! docker info >/dev/null 2>&1 && ! $check_only; then
    open -a Docker
    echo 'Finish Docker first-run prompts. Waiting up to two minutes for the engine.'
    for ((task_i=0;task_i<24;task_i++)); do
        docker info >/dev/null 2>&1 && break
        sleep 5
    done
fi
echo '[4/6] Installing both skills from archives with original line endings'
if ! $check_only; then
    curl -fLSs https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main/scripts/install_bundle.py -o "$task_state/install_bundle.py"
    python3 "$task_state/install_bundle.py" --state-dir "$task_state"
fi
[[ -f "$task_state/installation.json" ]] || { echo 'Rerun without --check-only to install skills.' >&2; exit 2; }
task_skills=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["skills_dir"])' "$task_state/installation.json")
task_scripts="$task_skills/overseas-web-prospecting/scripts"
echo '[5/6] Saving local runtime and network settings'
if ! $check_only; then
    task_config=(--skills-dir "$task_skills" --state-dir "$task_state" --engine desktop --network "$network")
    [[ -z "$proxy_file" ]] || task_config+=(--proxy-file "$proxy_file")
    for task_dir in "$(dirname "$(command -v node)")" "$(dirname "$(command -v python3)")" /opt/homebrew/bin /usr/local/bin /Applications/Docker.app/Contents/Resources/bin "$HOME/.docker/bin"; do
        task_config+=(--native-path-prefix "$task_dir")
    done
    python3 "$task_scripts/runtime_config.py" "${task_config[@]}"
fi
echo '[6/6] Validating the saved environment and a real Google Maps crawl'
task_args=(--profile "$task_state/runtime.json" --skills-dir "$task_skills" --report-dir "$task_state")
$check_only || task_args+=(--smoke-test)
python3 "$task_scripts/check_environment.py" "${task_args[@]}"
