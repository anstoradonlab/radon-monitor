echo this isn't working, run the steps individually.

echo off
rem
rem build windows app from scratch
rem

call setup_build_environment.bat
call run_pyinstaller.bat
call run_nsis.bat



rem NOTE:
rem pyzmq error.  See: https://stackoverflow.com/questions/66054625/pyinstaller-error-running-script-with-pyzmq-dependency


rem
rem ... future TODO:
rem
rem Investigate using github actions: 
rem or build on linux using docker:
rem https://github.com/marketplace/actions/pyinstaller-windows
rem https://github.com/cdrx/docker-pyinstaller
