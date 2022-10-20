=========
Changelog
=========

Version 10.0
============
18 August 2022

- First release, alpha quality


Version 10.1
============
10 October 2022

- Allow Campbell loggers to be set to non-UTC
- Store some persistent state to database
- Only communicate through a single thread with LabJack (that is, stop assuming
  that there's no thread-local state in the labjack driver)
- Switch to using forked cr1000 communication library
- Handle multi-head detector and test at Cape Grim
- No longer create Views in database
- Add configuration option for backup time of day

    [data]
    backup_time_of_day=10:15


Version 10.2
============
XX Relese Date XX

- Repeated attempts to re-connect to a datalogger or calibration box happen at increasing 
  intervals (starting at 30 seconds delay increasing to 5 minutes)
- Reconnection to data logger is more error-tolerant
- Certain tasks (e.g. syncing time and downloading files from datalogger) are allowed to take
  much longer before they are identifed as having hung
- Provide more detail in log message diagnostics
- Fix external flow rate display (now showing mean flow rate over the last 30 minutes)
- Users can trigger a backup/csv sync from the File menu
- A banner display is shown at the top of the app during calibration or background
- Write a summary message to LogMessages at the end of a complete calibration or background, e.g.

  {"EventType": "Calibration", 
  "FlushStart": "2022-10-20 22:46:15+00:00", 
  "Start": "2022-10-20 22:46:15+00:00", 
  "Stop": "2022-10-20 22:46:15+00:00", 
  "DetectorName": "HURD"}
