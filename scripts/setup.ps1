# Windows PowerShell 5.1+; downloads public scripts, never reads credentials.
[CmdletBinding()]
param([switch]$CheckOnly, [string]$Distro = 'Ubuntu')
$ErrorActionPreference = 'Stop'
if ($Distro -notmatch '^[A-Za-z0-9._-]+$' -or $Distro -eq 'docker-desktop') { throw 'Choose a user WSL distribution, such as Ubuntu.' }
$taskCodex = Join-Path $env:USERPROFILE '.codex'
if ($env:CODEX_HOME -and ([IO.Path]::GetFullPath($env:CODEX_HOME) -ne [IO.Path]::GetFullPath($taskCodex))) { throw 'This installer uses the default Codex directory. For custom CODEX_HOME, follow references/setup.md.' }
$taskCache = Join-Path $env:LOCALAPPDATA 'overseas-web-prospecting\setup'
New-Item -ItemType Directory -Force -Path $taskCache | Out-Null
$taskRaw = 'https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main'
@{ status = 'setup_in_progress'; checked_at = [DateTime]::UtcNow.ToString('o'); next_action = 'Setup has not completed. Follow terminal instructions and rerun.' } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskCache 'environment-report.json') -Encoding UTF8
function Refresh-TaskPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:Path
}
function Install-TaskPackage([string]$Id) {
    if ($CheckOnly) { throw "[NEEDS ACTION] Missing $Id. Run again without -CheckOnly to install." }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Install Microsoft App Installer (winget), reopen PowerShell, then run this command again: https://aka.ms/getwinget' }
    Write-Host "[INSTALL] $Id - follow any system prompts."
    & winget.exe install --id $Id --exact --source winget --accept-source-agreements
    $taskExit = $LASTEXITCODE
    Refresh-TaskPath
    if ($taskExit -in @(1641, 3010)) { throw '[NEEDS RESTART] Restart Windows, reopen PowerShell and rerun the same command.' }
    if ($taskExit -ne 0) { throw "Package installation did not finish ($taskExit). Follow the message above and rerun." }
}
function Find-TaskPython {
    foreach ($taskCandidate in @('python.exe', 'python3.exe', 'py.exe')) {
        if (Get-Command $taskCandidate -ErrorAction SilentlyContinue) {
            & $taskCandidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $taskCandidate }
        }
    }
    return $null
}
Write-Host '[1/6] Checking Python, Git and Node.js on Windows'
$taskPython = Find-TaskPython
if (-not $taskPython) { Install-TaskPackage 'Python.Python.3.12'; $taskPython = Find-TaskPython }
if (-not $taskPython) { throw 'Python is not available yet. Reopen PowerShell and rerun.' }
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { Install-TaskPackage 'Git.Git' }
$taskNodeOK = $false
if (Get-Command node.exe -ErrorAction SilentlyContinue) {
    & node.exe -e 'const [a,b]=process.versions.node.split(String.fromCharCode(46)).map(Number);process.exit(a>22||(a===22&&b>=20)?0:1)'
    $taskNodeOK = $LASTEXITCODE -eq 0
}
if (-not $taskNodeOK) { Install-TaskPackage 'OpenJS.NodeJS.LTS' }
if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) { throw 'Reopen PowerShell to load Node.js, then rerun.' }
Write-Host '[2/6] Checking WSL and the selected Linux distribution'
$taskDistros = @()
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    $taskDistros = @((& wsl.exe --list --quiet 2>$null) -replace "`0", '' | ForEach-Object { $_.Trim() })
    if ($LASTEXITCODE -ne 0) { $taskDistros = @() }
}
if ($taskDistros -notcontains $Distro) {
    if ($CheckOnly) { throw "[NEEDS ACTION] WSL distribution $Distro is missing." }
    Write-Host "Run in an Administrator PowerShell: wsl --install -d $Distro"
    throw 'Complete WSL installation and its first username/password setup; restart if requested, then rerun this installer in your normal PowerShell.'
}
& wsl.exe -d $Distro -- true
if ($LASTEXITCODE -ne 0) { throw 'Open the selected Linux distribution and finish its initial setup, then rerun.' }
Write-Host '[3/6] Checking Docker Desktop'
$taskDockerApps = @((Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'), (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe'))
# A non-default installation (for example D:) must not be mistaken for an absent app.
foreach ($taskRegistryRoot in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
    foreach ($taskApp in @(Get-ItemProperty -Path $taskRegistryRoot -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq 'Docker Desktop' })) {
        if ($taskApp.InstallLocation) { $taskDockerApps += Join-Path $taskApp.InstallLocation 'Docker Desktop.exe' }
    }
}
$taskDockerProcess = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($taskDockerProcess -and $taskDockerProcess.Path) { $taskDockerApps += $taskDockerProcess.Path }
$taskDockerApp = $taskDockerApps | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
# A working WSL daemon is sufficient, even if Docker was installed in another location.
& wsl.exe -d $Distro -- docker info *> $null
$taskDockerReady = $LASTEXITCODE -eq 0
if (-not $taskDockerReady -and -not $taskDockerApp) {
    Install-TaskPackage 'Docker.DockerDesktop'
    $taskDockerApp = $taskDockerApps | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $taskDockerReady -and $taskDockerApp -and -not $CheckOnly) { Start-Process -FilePath $taskDockerApp -WindowStyle Hidden }
Write-Host "Docker must be running with WSL 2 integration enabled for $Distro (Settings > Resources > WSL Integration)."
Write-Host '[4/6] Checking tools inside WSL (Windows tools do not count)'
& wsl.exe -d $Distro -- sh -c 'command -v bash && command -v node && command -v python3 && command -v curl && command -v git && command -v npx' *> $null
if ($LASTEXITCODE -ne 0) {
    if ($CheckOnly) { throw '[NEEDS ACTION] WSL tools are missing. Rerun without -CheckOnly.' }
    # Uses Ubuntu/Debian packages in the chosen user distribution, never docker-desktop.
    & wsl.exe -d $Distro -- sudo apt-get update
    if ($LASTEXITCODE -ne 0) { throw 'WSL package index update failed. Fix the displayed error and rerun.' }
    & wsl.exe -d $Distro -- sudo apt-get install -y bash nodejs npm python3 curl git ca-certificates
    if ($LASTEXITCODE -ne 0) { throw 'WSL package installation failed. Fix the displayed error and rerun.' }
}
Write-Host '[5/6] Installing both Codex skills (existing copies are backed up)'
if (-not $CheckOnly) {
    $taskBackup = Join-Path $taskCache ('backup-' + [guid]::NewGuid().ToString('N'))
    foreach ($taskSkill in @('overseas-web-prospecting', 'google-maps-scraper')) {
        $taskExisting = Join-Path $taskCodex "skills\$taskSkill"
        if (Test-Path -LiteralPath $taskExisting) {
            New-Item -ItemType Directory -Force -Path $taskBackup | Out-Null
            Copy-Item -LiteralPath $taskExisting -Destination (Join-Path $taskBackup $taskSkill) -Recurse
        }
    }
    foreach ($taskRepo in @('Jeffyxuc/overseas-web-prospecting', 'gosom/google-maps-scraper')) {
        & npx.cmd -y skills@1.7.0 add $taskRepo -a codex -g --copy -y
        if ($LASTEXITCODE -ne 0) { throw "Skill installation failed: $taskRepo" }
    }
    Write-Host "Existing skill backups, if any: $taskBackup"
}
Write-Host '[6/6] Validating Docker and a real, small Google Maps crawl'
$taskValidator = Join-Path $taskCache 'check_environment.py'
Invoke-WebRequest -UseBasicParsing "$taskRaw/scripts/check_environment.py" -OutFile $taskValidator
$taskArgs = @($taskValidator, '--wsl-distro', $Distro, '--skills-dir', (Join-Path $taskCodex 'skills'), '--report-dir', $taskCache)
if (-not $CheckOnly) { $taskArgs += '--smoke-test' }
& $taskPython @taskArgs
if ($LASTEXITCODE -ne 0) { throw "Environment is not ready. See $taskCache\environment-report.json, complete the indicated step, then rerun." }
