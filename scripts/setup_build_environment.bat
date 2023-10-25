Rem Delete old virtual environment
cd ..
del /f /Q /S installervenv

Rem create a minimal environment containing just Python
call conda create -y --prefix ./installervenv python=3.6 pip nsis=3

Rem Activate the packaging environment
call conda activate ./installervenv

Rem Install the local copy of this package and dependencies
python -m pip install .[gui,pyinstaller]

cd scripts

