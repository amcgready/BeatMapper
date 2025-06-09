#!/bin/bash
set -e

echo "Checking for pip..."
if ! command -v pip &> /dev/null; then
    echo "pip not found. Attempting to install pip..."
    if command -v python3 &> /dev/null; then
        python3 -m ensurepip --upgrade || curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py
    elif command -v python &> /dev/null; then
        python -m ensurepip --upgrade || curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python get-pip.py
    else
        echo "Python not found. Please install Python and rerun this script."
        exit 1
    fi
fi

echo "Installing Python dependencies..."
if command -v python3 &> /dev/null; then
    python3 -m pip install --upgrade pip
    python3 -m pip install -r backend/requirements.txt
else
    python -m pip install --upgrade pip
    python -m pip install -r backend/requirements.txt
fi

echo "Installing npm dependencies..."
cd frontend || { echo "frontend directory not found!"; exit 1; }
npm install || { echo "npm install failed!"; exit 1; }
cd ..

echo "Creating Spleeter virtual environment..."
python3 -m venv spleeter_venv
echo "Installing Spleeter in its virtual environment..."
./spleeter_venv/bin/pip install --upgrade pip
./spleeter_venv/bin/pip install spleeter

echo "All dependencies installed!"