@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0stop_web.ps1" %*
