# tkgis startup script for Windows
# Auto-detects python environment and launches tkgis.

$ConfigDir = Join-Path $HOME ".tkgis"
$ConfigFile = Join-Path $ConfigDir "config.yml"
$PythonExe = ""

# 1. Check config file for saved preference
if (Test-Path $ConfigFile) {
    $content = Get-Content $ConfigFile
    $match = $content | Select-String "^python_path:\s*(.*)"
    if ($match) {
        $PythonExe = $match.Matches.Groups[1].Value.Trim().Trim('"').Trim("'")
    }
}

# 2. Auto-detect if no preference saved
if (-not $PythonExe) {
    # Check for .venv in current directory
    if (Test-Path ".venv\Scripts\python.exe") {
        $PythonExe = Join-Path (Get-Location) ".venv\Scripts\python.exe"
    } 
    # Check for conda environment named 'tkgis'
    elseif (Get-Command conda -ErrorAction SilentlyContinue) {
        $condaEnvs = conda info --envs
        $tkgisEnv = $condaEnvs | Select-String "^tkgis\s+"
        if ($tkgisEnv) {
            $path = (-split $tkgisEnv)[-1]
            $PythonExe = Join-Path $path "python.exe"
        }
    }
    
    # Check if 'tkgis' is importable in default python
    if (-not $PythonExe) {
        try {
            python -c "import tkgis" -ErrorAction Stop > $null
            $PythonExe = (Get-Command python).Source
        } catch {
            # try python3
            try {
                python3 -c "import tkgis" -ErrorAction Stop > $null
                $PythonExe = (Get-Command python3).Source
            } catch {}
        }
    }
}

# 3. Prompt user if still not found
if (-not $PythonExe) {
    Write-Host "Python or virtual environment for tkgis not found." -ForegroundColor Yellow
    $UserInput = Read-Host "Please enter the path to the python executable or virtual environment directory"
    
    if (Test-Path $UserInput) {
        if (Test-Path (Join-Path $UserInput "Scripts\python.exe")) {
            $PythonExe = Join-Path $UserInput "Scripts\python.exe"
        } elseif (Test-Path (Join-Path $UserInput "bin\python")) {
            $PythonExe = Join-Path $UserInput "bin\python"
        } elseif ($UserInput.EndsWith("python.exe") -or $UserInput.EndsWith("python")) {
            $PythonExe = $UserInput
        } else {
            $PythonExe = $UserInput # Assume it's the executable itself
        }
    } else {
        $PythonExe = $UserInput
    }

    # Save the preference
    if ($PythonExe) {
        if (-not (Test-Path $ConfigDir)) { 
            New-Item -ItemType Directory -Path $ConfigDir | Out-Null 
        }
        
        if (Test-Path $ConfigFile) {
            $content = Get-Content $ConfigFile
            if ($content -match "^python_path:") {
                # Update existing line
                $content = $content -replace "^python_path:.*", "python_path: `"$PythonExe`""
                $content | Set-Content $ConfigFile
            } else {
                # Append to existing file
                Add-Content $ConfigFile "`npython_path: `"$PythonExe`""
            }
        } else {
            # Create new file
            "python_path: `"$PythonExe`"" | Set-Content $ConfigFile
        }
        Write-Host "Saved python_path to $ConfigFile" -ForegroundColor Green
    }
}

if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    Write-Error "Error: Valid python executable not found."
    exit 1
}

# Launch
Write-Host "Launching tkgis using $PythonExe ..." -ForegroundColor Cyan
& $PythonExe -m tkgis $args
