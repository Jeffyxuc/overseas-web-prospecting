#!/usr/bin/env bash
# macOS bootstrap. Run from a downloaded file so interactive installers retain stdin.
set -euo pipefail
check_only=false
case "${1:-}" in --check-only) check_only=true ;; '') ;; *) echo 'Usage: bash setup.sh [--check-only]' >&2; exit 2 ;; esac
[[ $(uname -s) == Darwin ]] || { echo 'Use setup.ps1 on Windows. This entry point is for macOS.' >&2; exit 2; }
[[ ${CODEX_HOME:-"$HOME/.codex"} == "$HOME/.codex" ]] || { echo 'For custom CODEX_HOME, follow references/setup.md.' >&2; exit 2; }
task_cache="$HOME/Library/Caches/overseas-web-prospecting/setup"
mkdir -p "$task_cache"
printf '%s\n' '{"status":"setup_in_progress","next_action":"Setup has not completed. Follow terminal instructions and rerun."}' > "$task_cache/environment-report.json"
echo '[1/6] Checking Homebrew'
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v brew >/dev/null; then
    $check_only && { echo '[NEEDS ACTION] Homebrew is missing.' >&2; exit 2; }
    curl --fail --location --show-error https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$task_cache/homebrew-install.sh"
    /bin/bash "$task_cache/homebrew-install.sh"
fi
install_formula() {
    $check_only && { echo "[NEEDS ACTION] Missing $1. Rerun without --check-only." >&2; exit 2; }
    brew install "$1"
}
echo '[2/6] Checking Python, Git and Node.js'
if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then install_formula python; fi
if ! command -v git >/dev/null || ! git --version >/dev/null 2>&1; then install_formula git; fi
if brew --prefix node@24 >/dev/null 2>&1; then export PATH="$(brew --prefix node@24)/bin:$PATH"; fi
if ! command -v node >/dev/null || ! node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=20)?0:1)'; then
    install_formula node@24
    export PATH="$(brew --prefix node@24)/bin:$PATH"
fi
echo '[3/6] Checking Docker Desktop'
export PATH="/Applications/Docker.app/Contents/Resources/bin:$HOME/.docker/bin:$PATH"
if ! command -v docker >/dev/null && [[ ! -d /Applications/Docker.app ]]; then
    $check_only && { echo '[NEEDS ACTION] Docker is missing.' >&2; exit 2; }
    brew install --cask docker-desktop
fi
if ! docker info >/dev/null 2>&1 && ! $check_only; then
    open -a Docker
    echo 'Finish Docker first-run prompts. If verification fails, wait until Docker is ready and rerun.'
fi
echo '[4/6] Checking Bash'
command -v bash >/dev/null
echo '[5/6] Installing both Codex skills (existing copies are backed up)'
if ! $check_only; then
    task_backup=$(mktemp -d "$task_cache/backup.XXXXXX")
    for task_skill in overseas-web-prospecting google-maps-scraper; do
        [[ ! -e "$HOME/.codex/skills/$task_skill" ]] || cp -R "$HOME/.codex/skills/$task_skill" "$task_backup/$task_skill"
    done
    for task_repo in Jeffyxuc/overseas-web-prospecting gosom/google-maps-scraper; do
        npx -y skills@1.7.0 add "$task_repo" -a codex -g --copy -y
    done
    echo "Existing skill backups: $task_backup"
fi
echo '[6/6] Validating Docker and a real, small Google Maps crawl'
curl --fail --location --show-error https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main/scripts/check_environment.py -o "$task_cache/check_environment.py"
task_args=(--skills-dir "$HOME/.codex/skills" --report-dir "$task_cache")
$check_only || task_args+=(--smoke-test)
python3 "$task_cache/check_environment.py" "${task_args[@]}"
