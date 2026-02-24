@echo off
cd /d %~dp0
call conda activate xiaozhi-esp32-server
uvicorn api:api --host 0.0.0.0 --port 9880 --reload