@echo off
chcp 65001 >nul
cd /d "C:\Users\PC\求职工作台"

echo ================================
echo   求职工作台 v2.0
echo ================================
echo.

REM 检查前端是否已构建
if not exist "server\static\index.html" (
    echo [!] 前端未构建，请先运行: cd web ^&^& npm run build
    echo     或跳过前端，仅启动后端 API
    echo.
)

REM 启动后端 (0.0.0.0 允许局域网访问)
echo [*] 启动服务 http://localhost:7788
echo [*] 停止请按 Ctrl+C
echo.

.venv\Scripts\python.exe -m uvicorn server.main:app --host 0.0.0.0 --port 7788
pause
