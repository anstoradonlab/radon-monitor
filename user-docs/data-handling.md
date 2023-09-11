## Data handling in RDM

### Files on disk

This is a how the data directory might look with two radon detectors connected.

```
radon_data
├── archive
│   ├── 2022-05-radon.db   <- monthly backup
│   ├── 2022-06-radon.db   <- monthly backup
│   ├── 2022-07-radon.db   <- monthly backup
│   └── radon-backup.db    <- a snapshot of "current/radon.db"
├── current
│   ├── radon.db-wal       <- active database (ancillary file)
│   ├── radon.db-shm       <- active database (ancillary file)
│   └── radon.db           <- active database (main file)
├── height02
│   ├── TEST_002Jul22.CSV  <- monthly data in "legacy" format
│   ├── TEST_002Jun22.CSV  <- monthly data in "legacy" format
│   └── TEST_002May22.CSV  <- monthly data in "legacy" format
├── height50
│   ├── TEST_050Jul22.CSV  <- monthly data in "legacy" format
│   ├── TEST_050Jun22.CSV  <- monthly data in "legacy" format
│   └── TEST_050May22.CSV  <- monthly data in "legacy" format
├── configuration.ini      <- configuration file
├── radon_monitor_messages.log <- informative log messages
├── radon_monitor_messages.log.1 <- old log messages
└── radon_monitor_messages.log.2 <- even older log messages
```

Our intention is that **all** data required to fully document the radon detector, and to calculate final radon concentrations, is contained inside the `archive` directory, although there might be a lag of up to one day.  As well as sensor data, the database files contain information about the start/stop time of calibrations, diagnostic information, and copies of the site configuration.

To make it easier to switch from the old version of our logging software, we also write out `CSV` files in the same format as the old software.  These don't quite contain enough information to calculate radon concentrations, and may not be great for troubleshooting, but are still good for a quick look at the data using a spreadsheet.  In this example, legacy files have been written to the `height02` and `height050` subdirectories, for radon detectors with air intakes at 2 m and 50 m above ground level.

The `*.log` files contain information which describes what the software is doing.  They should be necessary only for near-real-time monitoring or for troubleshooting problems.

### Database file structure

Within RDM, data comes from:
 - radon detectors, at 30-minute and 10-second temporal resolution
 - a calibration unit, 10-second temporal resolution
 - the RDM software itself, as needed

Inside the database files, this data is fed into these tables:

 - *Results*: 30 minute data from radon detectors (also recorded in the `CSV` files)
 - *RTV*: similar to the `Results` table, but data is recorded at 10-s temporal resolution
 - *CalibrationUnit*: data from sensors in the calibration unit
 - *LogMessages*: messages recorded by `RDM`, including the status of clock checks, configuration, start/stop times of calibration events.


### Backup schedule

RDM includes the ability to transfer files to an FTP server as a backup mechanism.  All files are sent to the FTP server except for: 
 - the active database
 - files which are unchanged since the last backup

The ability to perform backups via FTP has been included because it was a feature of the old version of the logging software.  In new installations, it's advisable to use a dedicated backup tool such as rsync (Linux), rclone (command line tool, supports cloud services), or winSCP (Windows, GUI, but [scriptable](https://winscp.net/eng/docs/scripting).

By default, RDM makes a backup copy of the local database at 00:10 each day and updates the CSV files 15 seconds after the half hour.  Scripts which perform offsite backups should be scheduled to run a short time after.

