# Configuring a site

This is an outline of the steps required to set up `radon-monitor` on a new computer.  These steps do not need to be followed precisely, but if we can keep the setup roughly the same at different sites it should make things easier for us later.


## Windows

### Entirely new computer

1. Install the ancillary software listed below
2. Install the Radon Monitor GUI from https://github.com/anstoradonlab/radon-monitor-gui (look for releases to find a Windows installer) 
3. Create the directory `c:\data`
4. Choose a site name, and a name for each radon detector.  Make sure that both the site name and detector name will uniquely identify the data stream in the event that data from many detectors is merged together.  Also, choose names which can be used as file names without surprises (use no whitespace, or special characters).  If there is only one radon detector at the site, it is Ok for both the site and detector name to be the same, e.g. `GunnPoint`. A more complex example is a site with a tower.  This would be Ok for Lucas Heights with radon detectors drawing air from 2m and 50m AGL:
    * site: LucasHeights
    * detector1: LH-2m
    * detector2: LH-50m
5. Create a configuration file `c:\data\rdm-config.ini` and edit it based on the template below
    * to work out which COM port the datalogger is connected to, use <kbd>Win</kbd> + <kbd>R</kbd> to run `devmgmt.msc`.  Expand the device tree to find out which COM port is associated with any USB-Serial convertor which you might be using.
        * alternatively, the list of COM ports is available in `RDM` under `View → System Information`
6. Run RDM, from the Windows start menu
7. Ensure RDM is set as a startup program, according to [Microsoft's instructions](https://support.microsoft.com/en-us/windows/add-an-app-to-run-automatically-at-startup-in-windows-10-150da165-dcd9-7230-517b-cf3c295d89dd):
    * Select the Start button <kbd>Win</kbd> and scroll to find the app you want to run at startup.
    * Right-click the app, select More, and then select Open file location. This opens the location where the shortcut to the app is saved. If there isn't an option for Open file location, it means the app can't run at startup.
    * With the file location open, press the Windows logo key <kbd>Win</kbd> + <kbd>R</kbd>, type shell:startup, then select OK. This opens the Startup folder.
    * Copy and paste the shortcut to the app from the file location to the Startup folder.


### Conversion from a site running the VisualBasic version of RDM

1. Stop the old Radon Monitor software and remove it from the list of startup programs
2. Backup all data (the datalogger memory is going to be wiped in this procedure)
3. Follow steps 1-5 for a new install.  If you want to keep producing CSV files in the same format as the old logging system, pay attention to the `csv_file_pattern` section of the configuration file. It might also be helpful to use the short code from the old logger as the detector name, e.g. short codes like "GP", "CG", in the past. 
4. Using `Device Configuration Utility`, modify the datalogger code, as detailed below (in Appendix 2). This is optional, but will make the data more useful.
5. Also using `Device Configuration Utility`, set the datalogger clock to UTC.
6. Run RDM, from the Windows start menu
    * Go to `File → Load Configuration` and choose `c:\data\rdm-config.ini`
        * (expect logging to begin now)
    * Go to `View → Calibration` and enable scheduled calibrations
7. Ensure RDM is set as a startup program (TODO: check this works)


## Linux
    * `TODO:` write some instructions.  Basically, one approach, is:
        1. create a new user profile for the logging the radon data, say `/home/radonmonitor`, or `/home/atmdata` if the user will be controlling a 
        2. install a miniconda Python environment for that user (one which activates)
        3. install the radon-monitor CLI into that environment using `pip install`
        4. use cron to schedule calibrations/backgrounds
        4. TODO: set up RDM as a system service

## Linux, Raspberry Pi

TODO: fixme

If we're using a Raspberry Pi, we're likely to have a dedicated machine. In this case, it's probably fine to use the system installation of Python.

1. Perform a clean install of the RPi operating system
2. Install the radon-monitor command line client:
    `pip install --user git+https://github.com/anstoradonlab/radon-monitor.git`
3. Install the Labjack exodriver:
```sh
sudo apt install build-essential libusb-1.0-0-dev
git clone https://github.com/labjack/exodriver.git
cd exodriver
sudo ./install.sh
```
4. create a configuration file
5. integrate with the system (cheat by using cron jobs)
6. When new versions of `radon-monitor` get released, upgrade using this command:
   `pip install --user --upgrade git+https://github.com/anstoradonlab/radon-monitor.git`


## Basic Troubleshooting ideas

* Some odd problems occur if the logger is not set to UTC.  If you know that the clock on the PC is set correctly, you can force the logger to sync to the PC clock using `Device Configuration Utility` or by using the `View → System Information` dialog in RDM.
* Data locations may need to exist and be writable by the RDM user
* Sometimes we have seen a crash where the COM port has stayed locked, meaning that RDM is unable to access it after it is reopened.  Try rebooting the computer.
* Under the `View → System Information`


## Appendix 1: Sample configuration file

This is a simple configuration file intended for a site with one radon detector.  The detector is called `TEST` and the datalogger is assumed to be connected to `COM3`.

```ini
# Configuration for ANSTO two filter radon detector
# Save this file to c:\data\rdm-config.ini
# Settings which will need changing are:
#   * detector name
#   * detector COM port
#   * radon source information
#   * uncomment FTP section, if you want to try using FTP backup
#      * set the FTP upload directory
#
# Basic config, one 1500 L detector
[data]
data_dir=c:\data
logfile=c:\data\radon_monitor_messages.log
# allowed log levels (from least output through to most output):
# "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"
#loglevel="DEBUG"
loglevel= INFO
# If True, this option adds an "ApproxRadon" to the legacy format
# csv output (optional, True by default)
# legacy_file_write_approx_radon=True

# detector_kind sets the type of radon detector.  Options are:
#  "L1500" - standard 1500 litre detector
#  "L700" - standard 700 litre detector
#  "L200" - standard 200 litre detector
#  "mock" - used for testing without a connected radon detector
[detector1]
kind=L1500
serial_port=COM3
# suggested template: 
# [SITECODE]
# or (if there is more than one detector here)
# [SITECODE]_[InletHeight or Detector Name or other identifier]
name=TEST
csv_file_pattern=height02/{NAME}{MONTH}{YEAR}.CSV
datalogger_serial=-1

# add more detectors like this
# [detector2]
# kind=mock
# serial_port=COM6
# name=TEST_050M
# datalogger_serial=-1
# csv_file_pattern=height50/{NAME}{MONTH}{YEAR}.CSV


[calbox]
# there are different kinds of calibration units.  These are
# - `none`: no calibration unit attached, e.g. for manual calibrations
# - `generic`: single detector, built around a Labjack connected over USB
# - `CapeGrim`: two detectors, built around a Labjack connected over USB
# - `BurkertModel1`: one or two detectors, a new system available from Jan 2023.
#                    This is interfaced over ethernet, with a Burkert ME43 gateway
# - `BurkertModel1-2b`: one or two detectors including two background control,
#                    The default for new installations from 2024 onwards
#                    This is interfaced over ethernet, with a Burkert ME43 gateway`
# There is also a kind called "mock" which can be used for testing the software
# but which doesn't try to connect to hardware.
kind=BurkertModel1-2b
# Activity of the radon source (activity of radon's parent, radium-226), 
# in decays per second (Bq)
radon_source_activity_bq=10e3

# The labjack ID can be set in software.  A special value of -1 means
# to use the first labjack found, which only makes sense if there is
# only ever one labjack connected to the PC (only applies to Labjack-based devices)
labjack_id=-1
# Only use the labjack with the serial number specifed here.  A special
# value of -1 means to ignore the serial number.
# (only applies to Labjack-based devices)
labjack_serial=-1
# Flushing duration to use during calibrations (seconds)
flush_duration_sec=3600
# Radon injection duration to use during calibrations (seconds)
inject_duration_sec=3600
# Duration to switch to background mode for background charactisation (seconds)
background_duration_sec=3600
# ip address of the Burkert ME43 gateway (only applies when kind=BurkertModel1)
me43_ip_address=192.168.0.100
# flow rate setpoint on the calibration unit's mass flow controller during source flushing (units of standard l/min)
# (only applies when kind=BurkertModel1, optional, default=0.5)
flush_flow_rate=0.5 
# flow rate setpoint on the calibration unit's mass flow controller during injection (units of standard l/min)
# (only applies when kind=BurkertModel1, optional, default=0.5)
inject_flow_rate=0.5 



#[ftp]
#server=server.domain.name.com
#user=XXXXXX
#passwd=XXXXXX
## use this template: /rdm10/[sitename]
#directory=/rdm10/TEST
```

## Appendix 2: Logger firmware, required changes

The new RDM can take advantage of 10-second noise counts (`ULD`) and air temperature (`AirT`) from the `RTV` table (RTV is an abbreviation for Real Time Values), so we add these parameters to the `RTV` table.  We also ask the logger to keep 30 minutes' of 10-second values in logger memory (so that the main heads-up dispaly can populate immediately when RDM starts, and we don't lose any 10-second data during PC restarts).

```diff
diff --git a/logger-firmware/CR800_MAR08.CR8 b/logger-firmware/CR800_MAR08.CR8
index d4a0490..f59ff54 100644
--- a/logger-firmware/CR800_MAR08.CR8
+++ b/logger-firmware/CR800_MAR08.CR8
@@ -4,6 +4,7 @@ Detector: BareDatalogger,
 'Last modified: Scott Chambers, Feb-2007
 'Added RTV table: S.Werczynski, Feb-2007
 'Added RH/Temp and barometer sensors
+'Added more variables (ULD, AirT) to RTV, and retained RTV for 30 minutes: Alan Griffiths, Apr 2022

 '----- DECLARATIONS
 PreserveVariables
@@ -48,16 +49,18 @@ DataTable(Results,true,-1)

 EndTable

-DataTable(RTV,true,1)
+DataTable(RTV,true,180)
   OpenInterval
   DataInterval(0,10,Sec,10)
   Sample(1, ExFlow,FP2)
   Sample (1, InFlow, FP2)
   Sample(1, LLD,IEEE4)
+  Sample(1, ULD,IEEE4)
   Sample(1, Pres,FP2)
   Sample (1, TankP,FP2)
   Sample (1, HV,FP2)
   Sample (1, RelHum, FP2)
+  Sample (1, AirT, FP2)
 EndTable

 '----- MAIN PROGRAM
```

A copy of a generic version of the logger software is included in the [git repository](../logger-firmware/).

## Appendix 3: Ancillary software to install

All are free to use.  With the exception of Device Configuration Utility, all of these are also open-source.

### Campbell Scientific's free logger communications software

Device Configuration Utility:
https://www.campbellsci.com.au/devconfig 

### SQLite database viewer

DB Browser for SQLite:
https://download.sqlitebrowser.org/DB.Browser.for.SQLite-3.12.2-win64.msi


### A resonable text editor

Notepad++:
https://notepad-plus-plus.org/downloads/

### Some kind of period backup solution (optional)

WinSCP: https://winscp.net/ with a guide at https://winscp.net/eng/docs/guide_schedule

On Linux, rsync might be suitable.

For cloud storage, try rclone: https://rclone.org/

### Spreadsheet (optional)

LibreOffice:
https://www.libreoffice.org/download/download/?type=win-x86&version=7.3.1&lang=en-US


### Remote desktop (optional)

RustDesk:
https://rustdesk.com/
