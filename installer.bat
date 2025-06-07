@echo off
setlocal

echo Checking for pip...
py -3.10 -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip not found. Attempting to install pip...
    py -3.10 -m ensurepip --upgrade >nul 2>&1
    if errorlevel 1 (
        echo Downloading get-pip.py...
        powershell -Command "Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py"
        py -3.10 get-pip.py
        if errorlevel 1 (
            echo Failed to install pip. Please install Python and pip manually.
            pause
            exit /b 1
        )
        del get-pip.py
    )
)

echo Installing Python dependencies...
py -3.10 -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo Python dependency install failed!
    pause
    exit /b 1
)

echo Installing npm dependencies...
cd frontend
if errorlevel 1 (
    echo frontend directory not found!
    pause
    exit /b 1
)
npm install
if errorlevel 1 (
    echo npm install failed!
    pause
    exit /b 1
)
cd ..
echo All dependencies installed!

echo Creating Spleeter virtual environment...
py -3.10 -m venv spleeter_venv
if errorlevel 1 (
    echo Failed to create Spleeter venv!
    pause
    exit /b 1
)
echo Installing Spleeter in its virtual environment...
spleeter_venv\Scripts\pip install spleeter
if errorlevel 1 (
    echo Failed to install Spleeter!
    pause
    exit /b 1
)

pause
endlocal