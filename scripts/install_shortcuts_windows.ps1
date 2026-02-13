# install_shortcuts_windows.ps1
# Creates desktop shortcuts for JH Agent Factory

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktop  = [Environment]::GetFolderPath("Desktop")
$wsh      = New-Object -ComObject WScript.Shell

# --- Shortcut 1: Run API + AutoSave ---
$lnkPath1 = Join-Path $desktop "AgentFactory - Run(API+AutoSave).lnk"
$sc1 = $wsh.CreateShortcut($lnkPath1)
$sc1.TargetPath       = Join-Path $repoRoot "scripts\run_api_auto_save.bat"
$sc1.WorkingDirectory  = $repoRoot
$sc1.Description       = "Start JH Agent Factory API server with auto-save on exit"
$sc1.Save()
Write-Host "[OK] Created: $lnkPath1"

# --- Shortcut 2: Save + Push ---
$lnkPath2 = Join-Path $desktop "AgentFactory - Save+Push.lnk"
$sc2 = $wsh.CreateShortcut($lnkPath2)
$sc2.TargetPath       = Join-Path $repoRoot "scripts\save_and_push.bat"
$sc2.WorkingDirectory  = $repoRoot
$sc2.Description       = "Git add, commit, and push all changes"
$sc2.Save()
Write-Host "[OK] Created: $lnkPath2"

Write-Host ""
Write-Host "Desktop shortcuts installed successfully."
