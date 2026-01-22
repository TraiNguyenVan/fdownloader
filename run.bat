@echo off
SETLOCAL

IF "%~1"=="" (
    echo Usage: run.bat "https://www.facebook.com/..."
    GOTO :EOF
)

echo Building/Starting Docker container...
docker-compose run --rm fdownloader python main.py "%~1"

ENDLOCAL
