# Changelog

## Version 10.17.2

 - Increase the amount of log messages during datalogger connection
 - Add an option to report pakbus activity

## Version 10.17.1

8 November 2024

 - Fix a problem with the sensitivity sweep dialog

## Version 10.17

16 October 2024

 - Adds the option to connect to radon detector's internal datalogger over ethernet 
   instead of the serial port.
   This is only supported for dataloggers without pakbus encryption and without
   a security code, so only use it over trusted networks.  To configure this,
   remove the `serial_port` key from the `detector` configuration and instead
   add `network_address=[ip address or hostname]`.  If the datalogger is re-configured
   to use a non-standard port, also add `network_port=[port]`.  For example, instead of: 

        [detector1]
        serial_port=COM1

    use something like this instead (using your own IP address): 

        [detector1]
        network_address=192.168.1.100

    By default, `network_port` is set to PakBus default of `6785` and does not need
    to be specified.

 - Fix GUI and command-line conflicts on Linux.  As an interim solution, now, on Linux:
    - The command line can be used to start a background process which performs
      logging without requiring a GUI, for example on a headless machine, but
    - Starting the GUI stops the background process and instead starts logging
      from inside the GUI
    - Stopping the GUI stops logging, and the user needs to restart logging 
      from the command line.

## Version 10.16

7 August 2024

 - Transparently handle data from kinds of external flow sensors and rapidly update the 
   flow rate display for the sensors which allow this
 - Remove duplicate rows when archiving data (duplicates are rare but possible)
 - Improve clock synchronisation accuracy between computer and datalogger
 - Optionally check PC clock against an independent NTP server.  Note that many
   corporate filewalls are set to block NTP traffic, so you might need to use
   your organisation's NTP server.  If enabled, datalogger clocks will only be
   updated if this check succeeds but RDM will never change the computer clock 
   To enable this option, set the NTP server  name in the configuration file, 
   for example: 

        [data]
        ntp_server=pool.ntp.org
        


## Version 10.15.1

31 July 2024

 - Change the NSIS installer so that it runs an uninstaller when installing 
   a new version into the same directory (on Windows)
 - Open serial port in exclusive mode on Linux
 - Fix a problem with command-line "query" when running on Linux

## Version 10.15

23 July 2024 

*found issues with installer so the installer was not posted to github*

 - Packaging on Windows now uses Python v3.11 and PyQt v5.15
 - Added a "scheduled tasks" view which displays RDM's internal state.  This is useful for debugging or for displaying the time until the next calibration.
 - Prevent the 'inconsistent state' message from appearing more than once per hour
 - Improve missing data handling in sensitivity sweep

## Version 10.14

18 June 2024

 - Add an experimental option to send incoming data out across the network.
   This is a feature which is intended for use with [OpenRVDAS](https://openrvdas.org/), although it could be 
   used in other situations too.  30-minute summaries from the "Results" table are sent
   as UDP packets, formatted as JSON.  An example configuration, which sends data
   to multicast group 224.0.36.0, looks like: 

        [data]
        udp_destination=224.0.36.0
        udp_port=51520
        udp_multicast_interface=<host name or ip address of the computer running RDM>

    Internally, RDM uses a vendored copy of [UDPWriter](https://github.com/OceanDataTools/openrvdas/blob/master/logger/writers/udp_writer.py) from OpenRVDAS.  It is [documented here](https://htmlpreview.github.io/?https://raw.githubusercontent.com/oceandatatools/openrvdas/master/docs/html/logger/writers/udp_writer.html). 

    If `udp_destination` is not set in the configuration file, this feature is disabled.

- Avoid crashing the GUI when the output data directory can't be created during startup

## Version 10.13

18 March 2024

- Add "gui" command line option on Linux.  (GUI is the default on Windows)
- Display pressure on main display only to one decimal place
- Add a configuration option for 700l detector: 

        [detector1]
        kind=L700

## Version 10.12

19 December 2023

-   Use thicker lines on some plots for better visibility
-   Filter FTP settings from configuration before dumping config to database
-   Bugfix: improve flag calculation so that flag no longer stays stuck in state 2

## Version 10.11

25 October 2023

-   Similar functionality to version 10.10 but the GUI code has been
    merged into the same repository as the command-line/library code.

## Version 10.10

25 October 2023

-   Sensitivty sweep: change limits on GUI inputs so that this is
    suitable for background sweep, add noise handling.
-   Bugfix: disable fitting column width for Datetime column, as this
    sometimes causes crashes.

## Version 10.9

21 September 2023

-   Fix an issue where duplicate values were retrieved from the
    datalogger and saved to the database
-   When backing up files to FTP, (1) record the time of backup
    per-file instead of using a single reference time for the entire
    data set and (2) attempt to resume interrupted uploads part way
    through. This will help with FTP over unreliable links.
-   After backing up the active database, generate a "SHA256SUMS" file
    which includes checksums of the data files. Data integrity can be
    checked later, from a unix-like command prompt, by running:
        sha256sum --check SHA256SUMS

## Version 10.8.1

7 August 2023

-   Improve initial connection to Burkert calibration box
-   Improve error handling with Burkert calibration box
-   Improve FTP upload by checking file size on server after file upload

## Version 10.8.0

3 August 2023 Not released because of poorly handled communication
errors when used with Burkert calibration box

-   Add a new type of calibration box, "BurkertModel1-2b", a version of
    the Burkert compressed-gas calibration unit which has
    background-mode outputs for two radon detectors
-   When driving a Burkert calibration box, slightly overpressure the
    source capsule at the end of a flush or inject sequence to let the
    user detect leaks from the source capsule
-   GUI: display an estimate of the current radon concentration in the
    list of plots as well as making the plots look a little nicer

-   Bugfix: during the flag calculation, reset to 0 after a startup event
    (to prevent labelling a long time period as a calibration/bg event
    following a software crash and restart)

## Version 10.7.2

27 June 2023

Bugfix release: fix an error in the task scheduler which causes RDM to
use 100% of the available cpu time after running for about a week. With
this fix, RDM will typically use less than 1% CPU during normal
operation.

## Version 10.7.1

13 June 2023

Bugfix release: fix an error introduced in v10.7 where the flag
calculation can fail.

## Version 10.7

8 June 2023

**This release includes a change to the 'legacy' csv file format. This
format was intended to be a drop-in replacement for the output from the
previous version of RDM, but some of the details did not match. After
installing this upgrade, if the legacy output is enabled, users should
delete the current .csv files. The csv files will be regenerated after
RDM starts up**

-   Interpret LabJack errors in the logfile, e.g. "2" becomes "No
    LabJacks found."

-   Re-sync all of the legacy-format csv files on startup or when a sync
    is requested from the File menu. This also means that users can
    re-generate legacy csv output by deleting the csv files and then
    selecting File-\>Sync output files.

-   Fix the legacy-format csv files so that they have the same column
    names as the previous version of RDM. There is a new configuration
    option making it possible to disable the ApproxRadon column, since
    this column was not present in the old format:

        [data]
        legacy_file_write_approx_radon=True

-   Fix an issue where data could be missing from the csv files at the
    end of the month if csv file output is set to a time zone other than
    UTC

-   Fix an issue with the Calibration dialog box where the time between
    calibration and background events was not being saved to disk

## Version 10.6

27 April 2023

-   Fix an issue where a disconnected calibration unit will eventually
    crash the logging software

-   Add an option to set the injection flow rate on a Burkert
    calibration box:

        [calbox]
        inject_flow_rate=0.5
        flush_flow_rate=0.5

-   Potential fix for issue \#4 (calbox once failed to reset, and kept
    injecting)

-   Add the option to run without a calibration unit This adds a
    configuration option and handles the absence of a calibration unit:

        [calbox]
        kind=none

-   Added calibrated flow to CalibrationUnit table

    The CalibrationUnit table now includes the calibrated flow rate in a
    field called `Flow_lpm` in addition to
    the existing `Flow` column which
    records the voltage of the flow rate transmiter, a Honeywell
    AWM3100.

    There is a new configuration option to control the conversion from
    voltage to flow rate. The polynomial is written as the V^2 term,
    then the V term, then the constant. It can be left unset, as it has
    a reasonable default value as follows:

        [calbox]
        flow_sensor_polynomial=0.1025, -0.17965, 0.0669979

    Some calibration boxes use compressed gas with a mass flow
    controller (MFC, instead of a flow meter). The MFC is configured
    with flow rate as an analog output. 0..5V represents 0..500 cc/min,
    so for these calibration boxes set:

        [calbox]
        flow_sensor_polynomial=0.0, 0.1, 0.0

    In between calibration cycles, the MFC is powered off and the
    reported values have no useful meaning.

-   log the clock offset, even when it badly out of sync (more than 1
    minute)

-   Add countdown dialog to GUI during startup

-   set default baud rate to 9600 to make communications as robust as
    possible. Users can still change the baudrate if their setup
    supports higher baudrates.

-   add option to report PakBus statistics (currently on disconnect and
    hourly, default is False):

        [detector1]
        report_pakbus_statistics=True

## Version 10.5

13 February 2023

-   Bugfix relese: keep running when csv sync fails (just log the error)

## Version 10.4

14 December 2022

-   Support for Burkert calibration unit
-   Calculate radon concentration when reading Results table and report
    in an `ApproxRadon` column

## Version 10.3

1 December 2022

-   Add source activity to calibration metadata
-   Add ApproxRadon column to csv output (no GUI yet - relies on
    manually setting cal/bg in 'persistent_state' table in database)
-   Improve behaviour during shutdown, avoiding a hang
-   Sync csv output every 30 minutes
-   Fix issue where CSV files stopped updating at end of month
-   Improve plotting and slightly adjust labels to fit better on small
    screens

## Version 10.2

24 October 2022

-   Repeated attempts to re-connect to a datalogger or calibration box
    happen at increasing intervals (starting at 30 seconds delay
    increasing to 5 minutes)

-   Reconnection to data logger is more error-tolerant

-   Certain tasks (e.g. syncing time and downloading files from
    datalogger) are allowed to take much longer before they are
    identifed as having hung

-   Provide more detail in log message diagnostics

-   Fix external flow rate display (now showing mean flow rate over the
    last 30 minutes)

-   Users can trigger a backup/csv sync from the File menu

-   A banner display is shown at the top of the app during calibration
    or background

-   Write a summary message to LogMessages at the end of a complete
    calibration or background, e.g.:

        {"EventType": "Calibration", 
        "FlushStart": "2022-10-20 22:46:15+00:00", 
        "Start": "2022-10-20 22:46:15+00:00", 
        "Stop": "2022-10-20 22:46:15+00:00", 
        "DetectorName": "HURD"}

-   Display 24h of data in the RTV (10-sec) display

-   Keep tables scrolled to the bottom in GUI, unless the user scrolls
    up

## Version 10.1

10 October 2022

-   Allow Campbell loggers to be set to non-UTC

-   Store some persistent state to database

-   Only communicate through a single thread with LabJack (that is, stop
    assuming that there's no thread-local state in the labjack driver)

-   Switch to using forked cr1000 communication library

-   Handle multi-head detector and test at Cape Grim

-   No longer create Views in database

-   Add configuration option for backup time of day:

        [data]
        backup_time_of_day=10:15

## Version 10.0

18 August 2022

-   First release, alpha quality
