=========
Changelog
=========

Version 10.0
============
18 August 2022

- First release, alpha quality


Version 10.1
============
15 September 2022

- Allow Campbell loggers to be set to non-UTC
- Add persistent state to database (so far, used for maintenance mode)
- Only communicate through a single thread with LabJack (that is, stop assuming
  that there's no thread-local state in the labjack driver)
- Switch to using forked cr1000 communication library
- Handle multi-head detector
- No longer create Views in database
