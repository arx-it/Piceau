@echo off
set "input=C:/PROGRA~1/QGIS3~1.4"
echo %input%

@echo ON

cd /d %~dp0

call py3-env.bat "%input%"

python3 -m pip install --upgrade pip
python3 -m pip install -r python_modules.txt