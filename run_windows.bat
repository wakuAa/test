@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG_FILE=%~dp0run_windows.log"
if exist "%LOG_FILE%" del /f /q "%LOG_FILE%" >nul 2>nul

set "EXE1=%~dp0wechat_score_bot\wechat_score_bot.exe"
set "EXE2=%~dp0dist\wechat_score_bot\wechat_score_bot.exe"

if exist "%EXE1%" (
    echo [info] Using packaged exe>"%LOG_FILE%"
    "%EXE1%" %* >>"%LOG_FILE%" 2>&1
    set "EXIT_CODE=%ERRORLEVEL%"
) else if exist "%EXE2%" (
    echo [info] Using packaged exe (dist)>"%LOG_FILE%"
    "%EXE2%" %* >>"%LOG_FILE%" 2>&1
    set "EXIT_CODE=%ERRORLEVEL%"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        echo [info] Using py launcher>"%LOG_FILE%"
        py -3 "%~dp0start_windows.py" %* >>"%LOG_FILE%" 2>&1
        set "EXIT_CODE=%ERRORLEVEL%"
    ) else (
        where python >nul 2>nul
        if %errorlevel%==0 (
            echo [info] Using python.exe>"%LOG_FILE%"
            python "%~dp0start_windows.py" %* >>"%LOG_FILE%" 2>&1
            set "EXIT_CODE=%ERRORLEVEL%"
        ) else (
            >"%LOG_FILE%" echo [error] Python was not found, and no exe was found. Please use the exe zip package, or install Python 3.10+ and add it to PATH.
            set "EXIT_CODE=9009"
        )
    )
)

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Script failed. Full log:
    echo ------------------------------
    type "%LOG_FILE%"
    echo ------------------------------
    echo Saved log: "%LOG_FILE%"
    pause
)

