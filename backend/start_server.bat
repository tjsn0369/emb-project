@echo off
chcp 65001
set PYTHONIOENCODING=utf-8
uvicorn main:app --reload --port 8001
pause