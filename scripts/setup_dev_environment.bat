Rem Delete old virtual environment
cd ..
del /f /Q /S venv

Rem create a minimal environment containing Python and some dev. extensions
call conda create -y --prefix ./venv python=3.6 pip nsis=3 black isort

Rem Activate the packaging environment
call conda activate ./venv

Rem Install the local copy of this package and dependencies
python -m pip install -e .[gui,pyinstaller]

cd scripts

