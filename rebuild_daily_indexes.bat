@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0rebuild_daily_indexes.ps1" %*
