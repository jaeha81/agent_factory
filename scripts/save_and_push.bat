@echo off
setlocal
cd /d %~dp0\..

:: Check for changes
git diff --quiet --exit-code 2>nul && git diff --cached --quiet --exit-code 2>nul && (
    for /f %%i in ('git ls-files --others --exclude-standard') do goto HAS_CHANGES
    echo No changes to commit.
    goto :EOF
)

:HAS_CHANGES
:: Build commit message
if "%~1"=="" (
    for /f "tokens=*" %%a in ('powershell -command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set TIMESTAMP=%%a
    set MSG=WIP: %TIMESTAMP%
) else (
    set MSG=%*
)

echo Committing: %MSG%
git add -A
git commit -m "%MSG%"
git push

echo Done.
endlocal
