Rem Delete old virtual environment
cd ..
del /f /Q /S installervenv

Rem create a minimal environment containing just Python
call conda create -y --prefix ./installervenv python=3.11 pip nsis=3

Rem Activate the packaging environment
call conda activate ./installervenv

Rem Install the local copy of this package and dependencies
python -m pip install .[gui,pyinstaller]

Rem Copy the labjack dll into the environment where it can be discovered by ctypes
copy src\resources\windows\ljackuw.dll installervenv

cd scripts

