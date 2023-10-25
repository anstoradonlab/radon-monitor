REM TODO: update version info file before running pyinstaller

@REM spec file was generated with something like this command line
@REM pyinstaller --name RDM --noupx --log-level INFO --noconfirm ^
@REM   --icon ..\..\icons\Icon.ico ^
@REM   --version-file ..\..\scripts\file_version_info.txt ^
@REM   --distpath ..\dist ^
@REM   --specpath ..\dist\PyInstaller ^
@REM   --workpath ..\dist\PyInstaller ^
@REM   --add-binary ..\..\resources\windows\ljackuw.dll;. ^
@REM   ..\src\ansto_radon_monitor\main.py


cd ..
pyinstaller --noconfirm src\RDM.spec
cd scripts
