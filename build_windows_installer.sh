#!/bin/bash
#
# build windows app
#

# create minimal environment to get the right version of Python

if [[ ! -d ./minenv ]]
then
    conda create -y --prefix ./minenv
fi

conda env update --prefix ./minenv --file minimal-env.yml  --prune

## - if git isn't working within conda, try running git-for-windows (bash)
## - and activating the environment within
source /c/data/sw/Miniconda3/Scripts/activate

# or, if running under cmd.exe
c:\data\sw\Miniconda3\Scripts\activate .\minenv

# create a virtual environment and install dependencies using pip
conda activate ./minenv

python -m venv venv
venv/Scripts/activate
python -m pip install -r requirements/windows.txt

# debug/release build
fbs freeze --debug
#fbs freeze

# installer
fbs installer


# NOTE:
# pyzmq error.  See: https://stackoverflow.com/questions/66054625/pyinstaller-error-running-script-with-pyzmq-dependency


#
# ... future TODO:
#
# Investigate using github actions: https://github.com/trappitsch/fbs-release-github-actions
# or build on linux using docker:
# https://github.com/marketplace/actions/pyinstaller-windows
# https://github.com/cdrx/docker-pyinstaller
