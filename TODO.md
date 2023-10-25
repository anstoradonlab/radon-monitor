# TODO list for both radon monitor and radon monitor gui

* Function to download logger firmware
* Regular clock synchronisation
* Log configuration to database on:
    - startup
    - rollover to new month
* Scheduler for calibrations
* Lots of error tolerance
    - run successfully without logger but with labjack
    - run successfully without labjack but with logger
    - tolerate disconnect/reconnect
        - even during data transfer or calibration/bg
    - details?
* Polish
    - remove leftovers from starting template
    - make the entire window glow red (or something) if it is not logging to file


* Document 
    - API
    - Data flow (aka "Instructions for backups")