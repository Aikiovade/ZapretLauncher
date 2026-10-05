#requires -Version 5.1
<#
.SYNOPSIS
    Удаление ZapretLauncher и связанных компонентов.
.DESCRIPTION
    Останавливает и удаляет службы zapret/WinDivert, завершает процессы winws/TgWsProxy,
    удаляет автозапуск (ярлык в Startup и запись HKCU Run "TgWsProxy"),
    затем каталоги данных. Сам .exe удаляется вручную.
.PARAMETER KeepData
    Сохранить каталоги данных (C:\ZapretLauncher и legacy %LOCALAPPDATA%\ZapretLauncher).
.PARAMETER PurgeTgProxy
    Дополнительно удалить конфиг и логи TgWsProxy (%APPDATA%\TgWsProxy).
.PARAMETER DryRun
    Показать действия без их выполнения (безопасная проверка).
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\uninstall.ps1 -DryRun
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\uninstall.ps1 -KeepData
#>
param(
    [switch]$KeepData,
    [switch]$PurgeTgProxy,
    [switch]$DryRun
)

$ErrorActionPreference = "SilentlyContinue"

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Action {
    param([string]$Desc, [scriptblock]$Action)
    if ($DryRun) {
        Write-Host "  [dry-run] $Desc"
    } else {
        & $Action
    }
}

if (-not $DryRun -and -not (Test-Admin)) {
    Write-Host "Требуются права администратора — перезапуск с UAC..."
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    if ($KeepData) { $argList += "-KeepData" }
    if ($PurgeTgProxy) { $argList += "-PurgeTgProxy" }
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

Write-Host "=== Удаление ZapretLauncher ==="
if ($DryRun) { Write-Host "(режим dry-run: изменения не вносятся)" }

Write-Host "[1/4] Службы..."
foreach ($svc in @("zapret", "WinDivert", "WinDivert14")) {
    Invoke-Action "net stop $svc" { & net stop $svc 2>$null | Out-Null }
    Invoke-Action "sc delete $svc" { & sc.exe delete $svc 2>$null | Out-Null }
}

Write-Host "[2/4] Процессы..."
foreach ($proc in @("winws", "TgWsProxy_windows", "Zapret", "ZapretWeb")) {
    Invoke-Action "taskkill /F /IM $proc.exe" { & taskkill /F /IM "$proc.exe" 2>$null | Out-Null }
}

Write-Host "[3/4] Автозапуск..."
$startup = [Environment]::GetFolderPath("Startup")
Invoke-Action "Remove-Item '$startup\Zapret.lnk'" { Remove-Item -LiteralPath (Join-Path $startup "Zapret.lnk") -Force }
Invoke-Action "Remove HKCU Run: TgWsProxy" {
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "TgWsProxy"
}

Write-Host "[4/4] Данные..."
if ($KeepData) {
    Write-Host "  Каталоги данных сохранены (-KeepData)."
} else {
    $dataDirs = @(
        (Join-Path $env:ProgramData "ZapretLauncher"),
        (Join-Path $env:SystemDrive "ZapretLauncher"),
        (Join-Path $env:LOCALAPPDATA "ZapretLauncher")
    )
    foreach ($dir in $dataDirs) {
        Invoke-Action "Remove-Item -Recurse '$dir'" { Remove-Item -LiteralPath $dir -Recurse -Force }
    }
}
if ($PurgeTgProxy) {
    Invoke-Action "Remove-Item -Recurse '$env:APPDATA\TgWsProxy'" {
        Remove-Item -LiteralPath (Join-Path $env:APPDATA "TgWsProxy") -Recurse -Force
    }
}

# Ярлыки (если скрипт запущен отдельно от деинсталлятора Inno)
$desktopLnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "ZapretLauncher.lnk"
Invoke-Action "Remove-Item '$desktopLnk'" { Remove-Item -LiteralPath $desktopLnk -Force }
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\ZapretLauncher"
Invoke-Action "Remove-Item -Recurse '$startMenuDir'" { Remove-Item -LiteralPath $startMenuDir -Recurse -Force }

Write-Host "Готово. Файлы Zapret.exe / ZapretWeb.exe удалите вручную."
