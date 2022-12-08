from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.exceptions import ConnectionException
import time
import logging
from typing import Dict, Any, List


from .calbox_device import CalboxDevice

_logger = logging.getLogger(__name__)


class BurkertGateway(CalboxDevice):
    """
    Control a Burket calibration unit built around a ME43 gateway and communicating
    over modbus-tcp
    """

    MFC_SETPOINT_ADDRESS = 2
    DIGITAL_IO_ADDRESS = 0
    NUM_DIO = 8  # number of DIO lines (coils, in modbus terms)
    FLAG_NAMES = (
        "SourceFlush",
        "SourceFlushExhaust",
        "Inject1",
        "Inject2",
        "DisableStackBlower1",
        "DisableStackBlower2",
        "ActivateCutoffValve1",
        "ActivateCutoffValve2",
    )

    def __init__(self, ip_address: str):
        """
        Control a Burket calibration unit.

        The calbox is arranged like this:

        [Compressed gas bottle and regulator]
          |
        [Mass flow controller (MFC)]
          |
        [Valve 1]
          |
        [Source capsule]--[Pressure transmitter]
          |
        [   Valve 2   ]-[     Valve 3     ]-[     Valve 4     ]
          |               |                   |
        [Flush exhaust] [Inject detector 1] [Inject detector 2]

        Connection definitions
        ----------------------

        Coils
        0 - Valve 1
        1 - Valve 2
        2 - Valve 3
        3 - Valve 4
        4 - no connection, planned as "Disable stack blower detector 0"
        5 - no connection, planned as "Disable stack blower detector 1"
        6 - no connection, planned as "Activate cutoff valve detector 0"
        7 - no connection, planned as "Activate cutoff valve detector 1"

        Read-only registers (modbus FC04, pymodbus client.read_input_registers)
        Address     Length      Datatype       Name
        0           2           Float          Pressure transducer (maybe, TBC)
        2           2           Float          MFC actual flow rate (l/min at STP, aka Nl/min)
        4           2           Float          MFC duty cycle (%)
        6           1           Unsigned16     MFC medium temperature (K)
        7           2           Float          MFC mass volume (l at STP)
        9           2           Float          MFC used set-point value (l/min at STP)

        Read-write registers (modbus FC03 to read, FC016 to write, pymodbus
          client.read_holding_registers, client.write_registers )
        Address     Length      Datatype       Name
        2           2           Float          MFC flow rate set point (l/min at STP, aka Nl/min)

        """
        self._ip_address = ip_address
        self._mfc_setpoint = 1.0
        self.serial_number = None
        # this is able to connect even if ip_address is wrong
        # (but will fail later)
        self._client = ModbusTcpClient(ip_address)
        try:
            # to establish the connection:
            #  1. read some data
            #  2. pause for a bit
            # because otherwise the device returns bogus data for the first
            # few samples (for about 1 sec, or about 30 samples)
            # It's ok to read the serial number right away, though
            consts = self._read_constant_values()
            self.serial_number = consts["Serial Number"]
            self._client.read_input_registers(0, count=2)
            time.sleep(1.0)
        except ConnectionException as ex:
            _logger.error(f"Unable to connect to calibration box due to error: {ex}")
            # TODO: how to communicate that the device didn't connect/isn't connected?
            raise

    def _set_mfc_flowrate(self, setpoint_lpm):
        """
        Turn on flow through the MFC by setting the target flow rate to the defined setpoint
        """
        builder = BinaryPayloadBuilder()
        builder.add_32bit_float(setpoint_lpm)
        payload = builder.to_registers()
        self._client.write_registers(self.MFC_SETPOINT_ADDRESS, payload)

    def _read_flags(self) -> List[bool]:
        """
        return flags (True means on) for
        [V1, V2, V3, V4, BACKGROUND_RUNNING]"""
        resp = self._client.read_coils(self.DIGITAL_IO_ADDRESS, 8)
        return list(resp.bits)[: self.NUM_DIO]

    def _read_values(self):
        """
        read values from device
        """
        address_count_name = [
            (0, 2, "source_pressure"),
            (2, 2, "MFC flow rate"),
            (4, 2, "MFC duty cycle"),
            (6, 1, "MFC temperature"),
            (7, 2, "MFC total volume"),
            (9, 2, "MFC used set point value"),
        ]
        data = {}

        for addr, count, name in address_count_name:
            result = self._client.read_input_registers(addr, count=count)
            if count == 2:
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers)
                decoded_val = decoder.decode_32bit_float()
            elif count == 1:
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers)
                decoded_val = decoder.decode_16bit_uint()

            data[name] = decoded_val

        # MFC set point is read/write and accessed with a different function
        result = self._client.read_holding_registers(2, 2)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers)
        decoded_val = decoder.decode_32bit_float()
        data["MFC set point"] = decoded_val

        return data

    def _read_constant_values(self):
        """
        Read 'acyclic' values (which I take to mean non-updating constants, e.g. serial number)
        """
        add_count_name_decoderfunc = [
            (849, 2, "Serial Number", lambda x: x.decode_32bit_uint()),
            (821, 10, "Device Name", lambda x: x.decode_string(10)),
        ]
        data = {}
        for addr, count, name, decoderfunc in add_count_name_decoderfunc:
            result = self._client.read_holding_registers(addr, count=count)
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers)
            decoded_val = decoderfunc(decoder)
            data[name] = decoded_val
        return data

    def _set_flags(self, flags: List[bool]):
        """ """
        assert len(flags) == self.NUM_DIO
        flags_to_send = list(flags) + [False] * (8 - self.NUM_DIO)
        resp = self._client.write_coils(self.DIGITAL_IO_ADDRESS, flags_to_send)
        # TODO check for error

    def flush(self) -> None:
        """Start source-flush by
        - open valve for inlet and flush exhaust outlet
        - enable MFC and allow flow
        """
        flags = self._read_flags()
        flags[0] = True
        flags[1] = True
        flags[2] = False
        flags[3] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(self._mfc_setpoint)

    def inject(self, detector_idx: int = 0) -> None:
        """Inject radon from source
        (if we're in BG mode then switch out of it)"""
        assert detector_idx == 0 or detector_idx == 1
        # choose the valve and bg flag matching this detector
        valve_idx = 2 + detector_idx
        bg_idx = 4 + detector_idx
        flags = self._read_flags()
        flags[0] = True
        flags[valve_idx] = True
        # make sure this detector is switched out of background
        flags[bg_idx] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(self._mfc_setpoint)

    def reset_flush(self) -> None:
        """Exit from source-flush mode"""
        flags = self._read_flags()
        flags[0] = False
        flags[1] = False
        flags[2] = False
        flags[3] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(0.0)
        # todo: leave the source capsule with an overpressure of about 10 kPa
        # (roughly the same pressure as a person can deliver from their lungs)

    def start_background(self, detector_idx: int = 0) -> None:
        """Put detector in background mode"""
        assert detector_idx == 0 or detector_idx == 1
        # choose the valve and bg flag matching this detector
        valve_idx = 2 + detector_idx
        bg_idx = 4 + detector_idx
        iso_valve_idx = 6 + detector_idx
        flags = self._read_flags()
        if flags[valve_idx] == True:
            # current detector is injecting, so cancel this before switching to BG
            self.reset_calibration()
        flags[bg_idx] = True
        flags[iso_valve_idx] = True
        self._set_flags(flags)

    def reset_background(self, detector_idx: int = 0) -> None:
        """Cancel a running background (but leave source flushing if it already is running)"""
        assert detector_idx == 0 or detector_idx == 1
        bg_idx = 4 + detector_idx
        iso_valve_idx = 6 + detector_idx
        flags = self._read_flags()
        flags[bg_idx] = False
        flags[iso_valve_idx] = False
        self._set_flags(flags)

    def reset_calibration(self) -> None:
        """Cancel a running calibration (but leave background-related
        flags unchanged)"""
        self.reset_flush()

    def reset_all(self) -> None:
        """return to idle state"""
        self.reset_flush()
        self.reset_background(0)
        self.reset_background(1)

    @property
    def analogue_states(self) -> Dict[Any]:
        data = self._read_values()
        return data

    @property
    def status(self) -> Dict[Any]:
        """generate a human-readable status message based on DIO flags"""
        flags = self._read_flags()
        # flags as a dict
        fd = {k: v for k, v in zip(self.FLAG_NAMES, flags)}
        if not True in flags:
            s = "Normal operations"
        else:
            s = []
            if fd["Inject1"]:
                s.append("Injecting from source into detector 1")
            elif fd["Inject2"]:
                s.append("Injecting from source into detector 2")
            elif fd["SourceFlush"]:
                s.append("Flushing source")
            if fd["DisableInternalBlower1"]:
                s.append("Performing background on detector 1")
            if fd["DisableInternalBlower2"]:
                s.append("Performing background on detector 2")

            s = ", ".join(s)

        status = {}
        status["message"] = s
        status["digital out"] = fd
        status["analogue in"] = self.analogue_states
        status["serial"] = self.serial_number
        return status
