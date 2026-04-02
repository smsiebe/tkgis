#!/bin/bash

# tkgis startup script for Linux
# Auto-detects python environment and launches tkgis.

CONFIG_DIR="$HOME/.tkgis"
CONFIG_FILE="$CONFIG_DIR/config.yml"
PYTHON_EXE=""

# 1. Check config file for saved preference
if [ -f "$CONFIG_FILE" ]; then
    # Simple grep to avoid yq dependency
    PYTHON_EXE=$(grep "^python_path:" "$CONFIG_FILE" | head -n 1 | cut -d' ' -f2- | tr -d '"' | tr -d "'")
fi

# 2. Auto-detect if no preference saved
if [ -z "$PYTHON_EXE" ]; then
    # Check for .venv in current directory
    if [ -f ".venv/bin/python" ]; then
        PYTHON_EXE="$(pwd)/.venv/bin/python"
    # Check for conda environment named 'tkgis'
    elif command -v conda >/dev/null 2>&1 && conda info --envs | grep -q "^tkgis "; then
        PYTHON_EXE=$(conda info --envs | grep "^tkgis " | awk '{print $NF}')/bin/python
    # Check if 'tkgis' is importable in default python3
    elif command -v python3 >/dev/null 2>&1 && python3 -c "import tkgis" >/dev/null 2>&1; then
        PYTHON_EXE=$(which python3)
    # Check if 'tkgis' is importable in default python
    elif command -v python >/dev/null 2>&1 && python -c "import tkgis" >/dev/null 2>&1; then
        PYTHON_EXE=$(which python)
    fi
fi

# 3. Prompt user if still not found
if [ -z "$PYTHON_EXE" ]; then
    echo "Python or virtual environment for tkgis not found."
    echo "Please enter the path to the python executable or virtual environment directory:"
    read -r USER_INPUT
    
    # If user provided a directory, look for python inside
    if [ -d "$USER_INPUT" ]; then
        if [ -f "$USER_INPUT/bin/python" ]; then
            PYTHON_EXE="$USER_INPUT/bin/python"
        elif [ -f "$USER_INPUT/Scripts/python.exe" ]; then
            # Maybe they pointed to a windows venv from WSL or similar
            PYTHON_EXE="$USER_INPUT/Scripts/python.exe"
        else
            echo "Error: Could not find python in $USER_INPUT"
            exit 1
        fi
    else
        PYTHON_EXE="$USER_INPUT"
    fi
    
    # Save the preference
    if [ ! -z "$PYTHON_EXE" ]; then
        mkdir -p "$CONFIG_DIR"
        if [ -f "$CONFIG_FILE" ] && grep -q "^python_path:" "$CONFIG_FILE"; then
            # Update existing line
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^python_path:.*|python_path: \"$PYTHON_EXE\"|" "$CONFIG_FILE"
            else
                sed -i "s|^python_path:.*|python_path: \"$PYTHON_EXE\"|" "$CONFIG_FILE"
            fi
        else
            # Append or create
            echo "python_path: \"$PYTHON_EXE\"" >> "$CONFIG_FILE"
        fi
        echo "Saved python_path to $CONFIG_FILE"
    fi
fi

if [ -z "$PYTHON_EXE" ] || [ ! -f "$PYTHON_EXE" ]; then
    echo "Error: Valid python executable not found."
    exit 1
fi

# Launch
echo "Launching tkgis using $PYTHON_EXE ..."
"$PYTHON_EXE" -m tkgis "$@"
