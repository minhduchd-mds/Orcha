@echo off
setlocal
call "%~dp0_python.cmd" "%~dp0..\app\kimik3_lite.py" --self-test
if errorlevel 1 exit /b 1
call "%~dp0_python.cmd" -m py_compile "%~dp0..\app\studio_server.py" "%~dp0..\app\workflow_engine.py"
if errorlevel 1 exit /b 1
echo PASS: Desktop Studio Python core.
exit /b 0
