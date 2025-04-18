@echo off
echo Network Traffic Monitor Launcher
echo ==============================

SET PROJECT_ROOT=%~dp0
SET BACKEND_PATH=%PROJECT_ROOT%backend
SET FRONTEND_PATH=%PROJECT_ROOT%frontend

echo Starting backend server with administrator privileges...
cd /d "%BACKEND_PATH%"
powershell -Command "Start-Process cmd -ArgumentList '/k cd /d \"%BACKEND_PATH%\" && python app2.py' -Verb RunAs"

echo Waiting for backend to initialize (10 seconds)...
timeout /t 10

echo Starting frontend application...
cd /d "%FRONTEND_PATH%"
start cmd /k "npm start"

echo Startup complete! Check the opened windows for application status.
