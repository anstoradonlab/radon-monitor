REM TODO: update version info file before running pyinstaller

pyinstaller --name RDM --noupx --log-level INFO --noconfirm ^
  --icon ..\..\icons\Icon.ico ^
  --version-file ..\..\scripts\file_version_info.txt ^
  --distpath ..\dist ^
  --specpath ..\dist\PyInstaller ^
  --workpath ..\dist\PyInstaller ^
  --add-binary ..\..\resources\windows\ljackuw.dll;. ^
  ..\src\ansto_radon_monitor\main.py

rem  --debug all ^


