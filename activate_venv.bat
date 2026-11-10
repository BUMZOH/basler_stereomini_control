@echo off
cd /d "%~dp0"

call ".venv\Scripts\activate.bat"

doskey p=python $*
doskey pi=python -m pip install $*
doskey pl=python -m pip list

echo.
echo Virtual environment activated.
echo Aliases: p, pi, pl
echo.

cmd /k