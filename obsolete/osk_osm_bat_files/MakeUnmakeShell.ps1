# Automatically get the absolute path of the folder where this script is saved
$scriptFolder = Split-Path -Parent $MyInvocation.MyCommand.Path

# Build the dynamic absolute path to the launcher
$customShellPath = Join-Path $scriptFolder "MeridianLauncher.exe"

$registryPath = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
$valueName = "Shell"
$shouldLogOut = $false

# Check if the custom shell property already exists in the registry
if (Get-ItemProperty -Path $registryPath -Name $valueName -ErrorAction SilentlyContinue) {
    # Revert to default Windows desktop
    Remove-ItemProperty -Path $registryPath -Name $valueName -ErrorAction SilentlyContinue
    Write-Host "Success: Reverted to default Windows desktop shell." -ForegroundColor Yellow
    $shouldLogOut = $true
} else {
    # Verify the launcher file actually exists in this local folder
    if (Test-Path $customShellPath) {
        if (-not (Test-Path $registryPath)) {
            New-Item -Path $registryPath -Force | Out-Null
        }
        # Apply the dynamically generated absolute path
        Set-ItemProperty -Path $registryPath -Name $valueName -Value $customShellPath
        Write-Host "Success: Custom shell set to $customShellPath." -ForegroundColor Green
        $shouldLogOut = $true
    } else {
        Write-Error "Error: 'MeridianLauncher.exe' was not found in the same folder as this script ($scriptFolder)."
    }
}

# If a registry change occurred, prompt the user and log out
if ($shouldLogOut) {
    Write-Host "`nYou will be logged out to apply changes. Save your work first!" -ForegroundColor Cyan
    Write-Host "Press any key to sign out..." -NoNewline
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    # Trigger an immediate Windows sign-out
    shutdown.exe /l
}
