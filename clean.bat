@echo off

REM ɾ��JGSL\__pycache__Ŀ¼�µ������ļ�
if exist "JGSL\__pycache__" (
    for /f "delims=" %%i in ('dir /b "JGSL\__pycache__" ^| findstr /v "\.gitkeep"') do (
        del /f /q "JGSL\__pycache__\%%i"
    )
)

REM ɾ��LogsĿ¼�µ������ļ�
if exist "Logs" (
    for /f "delims=" %%i in ('dir /b "Logs" ^| findstr /v "\.gitkeep"') do (
        del /f /q "Logs\%%i"
    )
)

echo ������ɣ�
pause