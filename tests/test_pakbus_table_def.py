# dig deeper into a crash in cr1000 code

from pycampbellcr1000 import CR1000
from pycampbellcr1000.pakbus import PakBus

# raw table def.  Can be obtained from the datalogger using:
# cr1000.getfile('.TDF')
raw = b"\x01Status\x00\x00\x00\x00\x01\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8bOSVersion\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x8bOSDate\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0c\x00\x00\x00\x0c\x00\x00\x00\x00\x86OSSignature\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bSerialNumber\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x8bRevBoard\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x0bStationName\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x8bProgName\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x8eStartTime\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86RunSignature\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ProgSignature\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06WatchdogErrors\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89PanelTemp\x00\x00\x00DegC\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89Battery\x00\x00\x00Volts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89LithiumBattery\x00\x00\x00Volts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06Low12VCount\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06Low5VCount\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bCompileResults\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x86StartUpCode\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ProgErrors\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VarOutOfBound\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06SkippedScan\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06SkippedSystemScan\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ErrorCalib\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MemorySize\x00\x00\x00bytes\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MemoryFree\x00\x00\x00bytes\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bCommsMemFree\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00T\x00\x00\x00T\x00\x00\x00\x00\x06FullMemReset\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MeasureOps\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MeasureTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ProcessTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06MaxProcTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86BuffDepth\x00\x00\x00scans\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00"

raw_ok = b"\x01Status\x00\x00\x00\x00\x01\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8bOSVersion\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00 \x00\x00\x00 \x00\x00\x00\x00\x8bOSDate\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x86OSSignature\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bSerialNumber\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x8bRevBoard\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x0bStationName\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x06PakBusAddress\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bProgName\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x8eStartTime\x00\x00\x00date\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86RunSignature\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ProgSignature\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89Battery\x00\x00\x00Volts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89PanelTemp\x00\x00\x00DegC\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06WatchdogErrors\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89LithiumBattery\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06Low12VCount\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06Low5VCount\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bCompileResults\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x86StartUpCode\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ProgErrors\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VarOutOfBound\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06SkippedScan\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06SkippedSystemScan\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ErrorCalib\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MemorySize\x00\x00\x00bytes\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MemoryFree\x00\x00\x00bytes\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CPUDriveFree\x00\x00\x00bytes\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86USRDriveFree\x00\x00\x00bytes\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommsMemFree\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x03\x00\x00\x00\x00\x06FullMemReset\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bDataTableName\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x18\x00\x00\x00\x01\x00\x00\x00\x18\x00\x00\x00\x00\x06SkippedRecord\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86DataRecordSize\x00\x00\x00records\x00\x00\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x00\x89SecsPerRecord\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x89DataFillDays\x00\x00\x00days\x00\x00\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x00\x8bCardStatus\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00P\x00\x00\x00P\x00\x00\x00\x00\x89CardBytesFree\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MeasureOps\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86MeasureTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86ProcessTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06MaxProcTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86BuffDepth\x00\x00\x00scans\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06MaxBuffDepth\x00\x00\x00scans\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8eLastSystemScan\x00\x00\x00date\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86SystemProcTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06MaxSystemProcTime\x00\x00\x00usec\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cPortStatus\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x8bPortConfig\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x1cSW12Volts\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06Security\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x03\x00\x00\x00\x00\x1cRS232Power\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06RS232Handshaking\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06RS232Timeout\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveRS232\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveME\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveCOM310\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveSDC7\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveSDC8\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveCOM320\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveSDC10\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveSDC11\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveCOM1\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveCOM2\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveCOM3\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cCommActiveCOM4\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigRS232\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigME\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigCOM310\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigSDC7\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigSDC8\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigCOM320\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigSDC10\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigSDC11\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigCOM1\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigCOM2\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigCOM3\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x86CommConfigCOM4\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateRS232\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateME\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateSDC\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateCOM1\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateCOM2\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateCOM3\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BaudrateCOM4\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x1cIsRouter\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06PakBusNodes\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06CentralRouters\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x06BeaconRS232\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconME\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconSDC7\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconSDC8\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconSDC10\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconSDC11\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconCOM1\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconCOM2\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconCOM3\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06BeaconCOM4\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifyRS232\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifyME\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifySDC7\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifySDC8\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifySDC10\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifySDC11\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifyCOM1\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifyCOM2\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifyCOM3\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06VerifyCOM4\x00\x00\x00Secs\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06MaxPacketSize\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06USRDriveSize\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x8bIPInfo\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01\x80\x00\x00\x01\x80\x00\x00\x00\x00\x06TCPPort\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x06pppInterface\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x0bpppIPAddr\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x10\x00\x00\x00\x10\x00\x00\x00\x00\x0bpppUsername\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x0bpppPassword\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00@\x00\x00\x00@\x00\x00\x00\x00\x0bpppDial\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00P\x00\x00\x00P\x00\x00\x00\x00\x0bpppDialResponse\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x10\x00\x00\x00\x10\x00\x00\x00\x00\x06IPTrace\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x0bMessages\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x89CalGain\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x12\x00\x00\x00\x12\x00\x00\x00\x00\x86CalSeOffset\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x12\x00\x00\x00\x12\x00\x00\x00\x00\x86CalDiffOffset\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x12\x00\x00\x00\x12\x00\x00\x00\x00\x00Table1\x00\x00\x02\xed\xf3\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00<\x00\x00\x00\x00\x87Batt_Volt_Avg\x00\x00Avg\x00Volts\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87Ref5V_mVolt_Avg\x00\x00Avg\x00Volts\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor1_mVolt_Avg\x00\x00Avg\x00mVolts\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor2_mVolt_Avg\x00\x00Avg\x00mVolts\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor3_mVolt_Avg\x00\x00Avg\x00mVolts\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor4_mVolt_Avg\x00\x00Avg\x00mVolts\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor1_mAmp_Avg\x00\x00Avg\x00mA\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor2_mAmp_Avg\x00\x00Avg\x00mA\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor3_mAmp_Avg\x00\x00Avg\x00mA\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x87CurSensor4_mAmp_Avg\x00\x00Avg\x00mA\x00Avg\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00Public\x00\x00\x00\x00\x01\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\tBatt_Volt\x00\x00\x00Volts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tRef5V_mVolt\x00\x00\x00Volts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor1_mVolt\x00\x00\x00mVolts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor1_mAmp\x00\x00\x00mA\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor2_mVolt\x00\x00\x00mVolts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor2_mAmp\x00\x00\x00mA\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor3_mVolt\x00\x00\x00mVolts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor3_mAmp\x00\x00\x00mA\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor4_mVolt\x00\x00\x00mVolts\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\tCurSensor4_mAmp\x00\x00\x00mA\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00"


class FakeLink(object):
    def open(self):
        pass

    def close(self):
        pass

    def write(self, data):
        pass

    def read(self, data):
        pass


pakbus = PakBus(FakeLink())
table_def = pakbus.parse_tabledef(raw_ok)
print(table_def)
table_def = pakbus.parse_tabledef(raw)
print(table_def)

# parse_tabledef(raw)