REM Run this from inside the build environment
REM (see setup_build_environment.bat)

REM Note that some paths are relative to the --specpath

cd ..
pyinstaller --name RDM --noupx --log-level INFO --noconfirm ^
   --workpath .\dist\PyInstaller ^
   --distpath .\dist ^
   --specpath .\src ^
   --icon icons\Icon.ico ^
   --version-file file_version_info.txt ^
   --add-binary resources\windows\ljackuw.dll;. ^
   --add-binary icons\Icon.ico;. ^
   .\src\ansto_radon_monitor\main.py
cd scripts
