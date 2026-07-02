Rem Delete old virtual environment
cd ..
del /f /Q /S venv

Rem create a minimal environment containing Python and some dev. extensions
Rem For the devel environment, it works better to use the conda PyQt
Rem package, so get this here too...
call conda create -y --prefix ./venv python=3.11 pip nsis=3 black isort pyqt~=5.9 pyqtgraph pywin32

Rem Activate the environment
call conda activate ./venv

Rem Install the local copy of this package and dependencies
python -m pip install -e .[gui,pyinstaller,testing]

Rem Copy the labjack dll into the environment where it can be discovered by ctypes
copy src\resources\windows\ljackuw.dll venv

cd scripts

