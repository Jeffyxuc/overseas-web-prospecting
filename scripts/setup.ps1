# Windows PowerShell 5.1+. Local settings stay outside installed skills.
[CmdletBinding()]
param([switch]$CheckOnly, [string]$Distro = 'Ubuntu',
      [ValidateSet('Wsl','Desktop')][string]$Engine = 'Wsl',
      [ValidateSet('auto','direct')][string]$Network = 'auto', [string]$ProxyFile)
$ErrorActionPreference = 'Stop'
if ($Distro -notmatch '^[A-Za-z0-9._-]+$' -or $Distro -eq 'docker-desktop') { throw 'Choose a user WSL distribution, such as Ubuntu.' }
$taskCodex = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$taskState = Join-Path $taskCodex 'overseas-web-prospecting'
New-Item -ItemType Directory -Force -Path $taskState | Out-Null
$taskRaw = 'https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main'
@{status='setup_in_progress'; next_action='Follow terminal instructions and rerun the same installer.'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskState 'environment-report.json') -Encoding UTF8
function Install-TaskPackage([string]$Id) {
    if ($CheckOnly) { throw "[NEEDS ACTION] Missing $Id. Rerun without -CheckOnly." }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Install App Installer, reopen PowerShell and rerun: https://aka.ms/getwinget' }
    & winget.exe install --id $Id --exact --source winget --accept-source-agreements
    $taskExit = $LASTEXITCODE
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User') + ';' + $env:Path
    if ($taskExit -in @(1641,3010)) { throw '[NEEDS RESTART] Restart Windows and rerun this command.' }
    if ($taskExit -ne 0) { throw "Installation did not finish ($taskExit). Resolve the displayed issue and rerun." }
}
function Find-TaskPython {
    foreach ($taskCandidate in @('python.exe','python3.exe','py.exe')) {
        if (Get-Command $taskCandidate -ErrorAction SilentlyContinue) {
            & $taskCandidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $taskCandidate }
        }
    }
    return $null
}
Write-Host '[1/6] Checking Windows Python and Node.js'
$taskPython = Find-TaskPython
if (-not $taskPython) { Install-TaskPackage 'Python.Python.3.12'; $taskPython = Find-TaskPython }
if (-not $taskPython) { throw 'Reopen PowerShell to load Python, then rerun.' }
$taskNodeOK = $false
if (Get-Command node.exe -ErrorAction SilentlyContinue) {
    & node.exe -e 'process.exit(Number(process.versions.node.split(String.fromCharCode(46))[0])>=22?0:1)'
    $taskNodeOK = $LASTEXITCODE -eq 0
}
if (-not $taskNodeOK) { Install-TaskPackage 'OpenJS.NodeJS.LTS' }
Write-Host '[2/6] Checking WSL 2 and Ubuntu/Debian tools'
$taskDistros = @()
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    $taskDistros = @((& wsl.exe --list --quiet 2>$null) -replace "`0", '' | ForEach-Object { $_.Trim() })
}
if ($taskDistros -notcontains $Distro) {
    throw "[NEEDS ACTION] In Administrator PowerShell run: wsl --install -d $Distro . Finish Ubuntu first-run setup, restart if requested, then rerun here."
}
& wsl.exe -d $Distro --exec true
if ($LASTEXITCODE -ne 0) { throw 'Open your Linux distribution, finish its first-run setup, and rerun.' }
& wsl.exe -d $Distro --exec sh -c 'command -v bash && command -v node && command -v python3 && command -v curl && command -v git' *> $null
if ($LASTEXITCODE -ne 0 -and -not $CheckOnly) {
    & wsl.exe -d $Distro -u root --exec apt-get update
    if ($LASTEXITCODE -ne 0) { throw 'Linux package index update failed. Check Linux network access and rerun.' }
    & wsl.exe -d $Distro -u root --exec apt-get install -y bash nodejs npm python3 curl git ca-certificates
    if ($LASTEXITCODE -ne 0) { throw 'Linux tools installation failed. Resolve the displayed error and rerun.' }
}
Write-Host '[3/6] Preparing the selected Docker engine'
if ($Engine -eq 'Wsl' -and -not $CheckOnly) {
    & wsl.exe -d $Distro --exec sh -c 'command -v dockerd' *> $null
    if ($LASTEXITCODE -ne 0) {
        & wsl.exe -d $Distro --exec docker info *> $null
        if ($LASTEXITCODE -eq 0) { throw 'This distribution already uses another Docker engine. Rerun with -Engine Desktop to reuse it, or choose a separate Ubuntu distribution.' }
        & wsl.exe -d $Distro -u root --exec apt-get update
        if ($LASTEXITCODE -ne 0) { throw 'Linux package index update failed.' }
        & wsl.exe -d $Distro -u root --exec apt-get install -y docker.io
        if ($LASTEXITCODE -ne 0) { throw 'Docker Engine installation failed. Ubuntu/Debian with docker.io is required.' }
    }
    & wsl.exe -d $Distro -u root --exec systemctl enable --now docker
    if ($LASTEXITCODE -ne 0) { throw 'Enable systemd in this WSL 2 distribution, restart WSL after saving other work, then rerun. See references/setup.md.' }
    & wsl.exe -d $Distro --exec docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        $taskLinuxUser = (& wsl.exe -d $Distro --exec id -un).Trim()
        if ($taskLinuxUser -notmatch '^[a-z_][a-z0-9_-]*[$]?$') { throw 'Could not determine the Linux account.' }
        Write-Host 'Adding the Linux account to the Docker group (root-equivalent Docker access).'
        & wsl.exe -d $Distro -u root --exec usermod -aG docker $taskLinuxUser
        if ($LASTEXITCODE -ne 0) { throw 'Could not grant Docker access.' }
        & wsl.exe -d $Distro --exec docker info *> $null
        if ($LASTEXITCODE -ne 0) { throw 'Docker group membership needs a fresh Linux session. Save Linux work, restart this distribution, then rerun.' }
    }
} elseif ($Engine -eq 'Desktop' -and -not $CheckOnly) {
    & wsl.exe -d $Distro --exec docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Start Docker Desktop, finish first-run prompts and enable WSL integration for $Distro, then rerun with -Engine Desktop. Install Docker Desktop first if absent." }
}
Write-Host '[4/6] Installing both skills from archives with original line endings'
$taskReceipt = Join-Path $taskState 'installation.json'
if (-not $CheckOnly) {
    $taskInstaller = Join-Path $taskState 'install_bundle.py'
    Invoke-WebRequest -UseBasicParsing "$taskRaw/scripts/install_bundle.py" -OutFile $taskInstaller
    & $taskPython $taskInstaller --state-dir $taskState
    if ($LASTEXITCODE -ne 0) { throw 'Skill installation failed. Previous copies are preserved or restored.' }
}
if (-not (Test-Path -LiteralPath $taskReceipt)) { throw 'No installation receipt. Rerun without -CheckOnly.' }
$taskSkills = (Get-Content -Raw -LiteralPath $taskReceipt | ConvertFrom-Json).skills_dir
$taskScripts = Join-Path $taskSkills 'overseas-web-prospecting/scripts'
Write-Host '[5/6] Saving local runtime and network settings'
if (-not $CheckOnly) {
    $taskConfigArgs = @((Join-Path $taskScripts 'runtime_config.py'),'--skills-dir',$taskSkills,'--state-dir',$taskState,'--wsl-distro',$Distro,'--engine',$Engine.ToLowerInvariant(),'--network',$Network)
    if ($ProxyFile) { $taskConfigArgs += @('--proxy-file',$ProxyFile) }
    & $taskPython @taskConfigArgs
    if ($LASTEXITCODE -ne 0) { throw 'Network configuration incomplete. Follow the message above; proxy values were not printed.' }
}
Write-Host '[6/6] Validating the saved environment and a real Google Maps crawl'
$taskArgs = @((Join-Path $taskScripts 'check_environment.py'),'--profile',(Join-Path $taskState 'runtime.json'),'--skills-dir',$taskSkills,'--report-dir',$taskState)
if (-not $CheckOnly) { $taskArgs += '--smoke-test' }
& $taskPython @taskArgs
if ($LASTEXITCODE -ne 0) { throw "Environment is not ready. Read $taskState/environment-report.json, resolve the indicated issue and rerun." }
