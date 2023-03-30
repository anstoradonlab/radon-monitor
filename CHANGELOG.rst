=========
Changelog
=========


Version 10.6
============
not yet released

  - Potential fix for issue #4 (calbox once failed to reset, and kept injecting)
  - Add the option to run without a calibration unit
      This adds a configuration option and handles
      the absence of a calibration unit::
      
      [calbox]
      kind=none
      
  - Added calibrated flow to CalibrationUnit table

    The CalibrationUnit table now includes the calibrated flow rate
    in a field called `Flow_lpm` in addition to the existing `Flow`
    column which records the voltage of the flow rate transmiter, a
    Honeywell AWM3100.

    There is a new configuration option to control the conversion
    from voltage to flow rate. It can be left unset, as it has a reasonable
    default value as follows::
    
    [calbox]
    flow_sensor_polynomial=0.1025, -0.17965, 0.0669979

  - log the clock offset, even when it badly out of sync (more than 1 minute)
  - Add countdown dialog to GUI during startup
  - set default baud rate to 9600 to make communications as robust as possible.
    Users can still change the baudrate if their setup supports higher baudrates.
  
  - add option to report PakBus statistics (currently on disconnect and hourly, 
    default is False)::

    [detector1]
    report_pakbus_statistics=True


Version 10.5
============
13 February 2023

 - Bugfix relese: keep running when csv sync fails (just log the error)

Version 10.4
============
14 December 2022

 - Support for Burkert calibration unit
 - Calculate radon concentration when reading Results table and report in an `ApproxRadon`` column

Version 10.3
============
1 December 2022

- Add source activity to calibration metadata
- Add ApproxRadon column to csv output (no GUI yet - relies on manually setting cal/bg in 'persistent_state' table in database)
- Improve behaviour during shutdown, avoiding a hang
- Sync csv output every 30 minutes
- Fix issue where CSV files stopped updating at end of month
- Improve plotting and slightly adjust labels to fit better on small screens

Version 10.2
============
24 October 2022

- Repeated attempts to re-connect to a datalogger or calibration box happen at increasing 
  intervals (starting at 30 seconds delay increasing to 5 minutes)
- Reconnection to data logger is more error-tolerant
- Certain tasks (e.g. syncing time and downloading files from datalogger) are allowed to take
  much longer before they are identifed as having hung
- Provide more detail in log message diagnostics
- Fix external flow rate display (now showing mean flow rate over the last 30 minutes)
- Users can trigger a backup/csv sync from the File menu
- A banner display is shown at the top of the app during calibration or background
- Write a summary message to LogMessages at the end of a complete calibration or background, e.g.::

  {"EventType": "Calibration", 
  "FlushStart": "2022-10-20 22:46:15+00:00", 
  "Start": "2022-10-20 22:46:15+00:00", 
  "Stop": "2022-10-20 22:46:15+00:00", 
  "DetectorName": "HURD"}

- Display 24h of data in the RTV (10-sec) display
- Keep tables scrolled to the bottom in GUI, unless the user scrolls up

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
- Add configuration option for backup time of day::

    [data]
    backup_time_of_day=10:15

Version 10.0
============
18 August 2022

- First release, alpha quality
