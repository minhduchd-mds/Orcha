@echo off
setlocal
call "%~dp0_python.cmd" "%~dp0..\app\kimik3_lite.py" --self-test
if errorlevel 1 exit /b 1
call "%~dp0_python.cmd" -m py_compile "%~dp0..\app\studio_server.py" "%~dp0..\app\studio_server_v64.py" "%~dp0..\app\studio_server_v65.py" "%~dp0..\app\studio_server_v66.py" "%~dp0..\app\parallel_agent.py" "%~dp0..\app\uiux_design_agent.py" "%~dp0..\app\workflow_engine.py"
if errorlevel 1 exit /b 1
call "%~dp0_python.cmd" "%~dp0..\app\uiux_design_agent.py"
if errorlevel 1 exit /b 1
call "%~dp0_python.cmd" "%~dp0..\app\parallel_agent.py"
if errorlevel 1 exit /b 1
node --check "%~dp0..\studio\design-agent.js"
if errorlevel 1 exit /b 1
node --check "%~dp0..\studio\parallel-agents.js"
if errorlevel 1 exit /b 1
echo PASS: Desktop Studio v6.6 Parallel Agents core.
exit /b 0
