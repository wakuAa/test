$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $projectRoot

Write-Host "[info] projectRoot=$projectRoot"

function Test-PythonVersion310([string]$pythonExe) {
    try {
        $ver = & $pythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        return ($ver.Trim() -eq "3.10")
    } catch {
        return $false
    }
}

function Resolve-Python310 {
    # 1) 优先 py launcher
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $exe = & py -3.10 -c "import sys; print(sys.executable)"
            if ($exe -and (Test-PythonVersion310 $exe.Trim())) {
                return $exe.Trim()
            }
        } catch {
            # ignore
        }
    }

    # 2) 退化：PATH 里的 python（且必须是 3.10）
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            $exe = & python -c "import sys; print(sys.executable)"
            if ($exe -and (Test-PythonVersion310 $exe.Trim())) {
                return $exe.Trim()
            }
        } catch {
            # ignore
        }
    }

    return $null
}

function Try-InstallPython310 {
    # 尝试用 winget 自动安装（如果系统支持的话）
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        return $false
    }

    Write-Host "[env] Python 3.10 not found, trying to install via winget..."
    try {
        winget install -e --id Python.Python.3.10 --accept-source-agreements --accept-package-agreements
        return $true
    } catch {
        return $false
    }
}

function Find-CommonPython310Paths {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"),
        (Join-Path $env:ProgramFiles "Python310\python.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Python310\python.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }
    return $candidates
}

# 选择 Python 3.10：优先 py launcher；没有则尝试 winget 安装；仍失败则引导手动安装
$pythonExe = Resolve-Python310
if (-not $pythonExe) {
    $installed = Try-InstallPython310
    # 安装后：优先再次解析；否则去常见目录里找
    $pythonExe = Resolve-Python310
    if (-not $pythonExe) {
        foreach ($p in (Find-CommonPython310Paths)) {
            if (Test-PythonVersion310 $p) {
                $pythonExe = $p
                break
            }
        }
    }

    if (-not $pythonExe) {
        Write-Host ""
        Write-Host "[error] 找不到 Python 3.10，且自动安装失败或系统不支持 winget。"
        Write-Host "请手动安装 Python 3.10+（官方版），安装时勾选 Add python.exe to PATH，然后重新运行本脚本。"
        Start-Process "https://www.python.org/downloads/windows/"
        throw "Python 3.10 not available."
    }
}

Write-Host "[env] Using Python: $pythonExe"

$buildVenv = Join-Path $projectRoot ".build-venv"
$buildPython = Join-Path $buildVenv "Scripts\python.exe"

if (-not (Test-Path $buildPython)) {
    Write-Host "[env] creating build venv: $buildVenv"
    & $pythonExe -m venv $buildVenv
}

Write-Host "[env] upgrading pip"
& $buildPython -m pip install --upgrade pip

Write-Host "[env] installing runtime deps"
& $buildPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

Write-Host "[env] installing pyinstaller"
& $buildPython -m pip install pyinstaller

# 清理旧产物
foreach ($d in @("build", "dist", "release_windows_exe")) {
    $p = Join-Path $projectRoot $d
    if (Test-Path $p) {
        Remove-Item -Recurse -Force $p
    }
}

$entry = Join-Path $projectRoot "start_windows.py"
if (-not (Test-Path $entry)) {
    throw "缺少入口脚本：start_windows.py"
}

Write-Host "[build] running pyinstaller"
& $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name wechat_score_bot `
    --collect-all rapidocr_onnxruntime `
    --collect-all onnxruntime `
    $entry

$releaseDir = Join-Path $projectRoot "release_windows_exe"
New-Item -ItemType Directory -Path $releaseDir | Out-Null

Copy-Item -Recurse -Force (Join-Path $projectRoot "dist\wechat_score_bot") (Join-Path $releaseDir "wechat_score_bot")
Copy-Item -Force (Join-Path $projectRoot "run_windows.bat") $releaseDir
Copy-Item -Force (Join-Path $projectRoot "README_windows_exe.md") $releaseDir

$zipPath = Join-Path $projectRoot "wechat_score_bot_windows_exe.zip"
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Write-Host "[pack] creating zip: $zipPath"
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -Force

Write-Host "[ok] done. output=$zipPath"
