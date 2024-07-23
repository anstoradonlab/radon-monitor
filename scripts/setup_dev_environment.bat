Rem Delete old virtual environment
cd ..
del /f /Q /S venv

Rem create a minimal environment containing Python and some dev. extensions
call conda create -y --prefix ./venv python=3.11 pip nsis=3 black isort

Rem Activate the environment
call conda activate ./venv

Rem Install the local copy of this package and dependencies
python -m pip install -e .[gui,pyinstaller]

Rem Copy the labjack dll into the environment where it can be discovered by ctypes
copy src\resources\windows\ljackuw.dll venv

cd scripts

