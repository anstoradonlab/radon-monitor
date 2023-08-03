from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.exceptions import ConnectionException
import time
import logging
import traceback
from typing import Dict, Any, List, Optional


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
    MFC_DEFAULT_FLOW = 0.5 # L/min
    BYTEORDER = {"byteorder":Endian.Big, "wordorder":Endian.Big}
    NUM_RETRIES = 10
    RETRY_WAIT_INTERVAL = 0.1

    def __init__(self, ip_address: str, flush_flow_rate: float, inject_flow_rate: float, option_2b=False):
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
        4 - Disable internal blower
        5 - Disable external blower
        6 - Enable cutoff valve
        7 - Disable stack blower

        NOTE: we don't have enough coils to use this approach (one coil per function) for
        two detectors.  For option_2b (the two background option) the coils are re-defined
        like this:

        Coils
        0 - Valve 1
        1 - Valve 2
        2 - Valve 3
        3 - Valve 4
        4 - Enable background mode on detector 1
        5 - Enable background mode on detector 2
        6 - unused
        7 - unused

        and each of the "background" digital outputs are connected to three relays.

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
        self._option_2b = option_2b
        if option_2b:
            self.FLAG_NAMES = (
                "SourceFlush",
                "SourceFlushExhaust",
                "Inject1",
                "Inject2",
                "Background1",
                "Background2",
            )
        else:
            self.FLAG_NAMES = (
                "SourceFlush",
                "SourceFlushExhaust",
                "Inject1",
                "Inject2",
                "DisableInternalBlower",
                "DisableExternalBlower",
                "ActivateCutoffValve",
                "DisableStackBlower",
            )

        _logger.info(f"Trying to connect to Burkert Calbox at IP address {ip_address}")
        self._ip_address = ip_address
        if flush_flow_rate is not None:
            self._mfc_setpoint_flush = flush_flow_rate
        else:
            self._mfc_setpoint_flush = self.MFC_DEFAULT_FLOW
        if inject_flow_rate is not None:
            self._mfc_setpoint_inject = inject_flow_rate
        else:
            self._mfc_setpoint_inject = self.MFC_DEFAULT_FLOW

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
            # read, but ignore, this
            self._read_values()
            # set the MFC and valves to idle state
            self.reset_all(pressurise=False)
            time.sleep(1.0)
        except ConnectionException as ex:
            _logger.error(f"Unable to connect to calibration box due to error: {ex}")
            # TODO: how to communicate that the device didn't connect/isn't connected?
            raise

    def _set_mfc_flowrate_worker(self, setpoint_lpm):
        builder = BinaryPayloadBuilder(**self.BYTEORDER)
        builder.add_32bit_float(setpoint_lpm)
        payload = builder.to_registers()
        self._client.write_registers(self.MFC_SETPOINT_ADDRESS, payload)


    def _set_mfc_flowrate(self, setpoint_lpm):
        """
        Turn on flow through the MFC by setting the target flow rate to the defined setpoint
        """
        for ii in range(self.NUM_RETRIES+1):
            try:
                resp_list = self._set_mfc_flowrate_worker(setpoint_lpm)
                break
            except:
                if ii == self.NUM_RETRIES:
                    raise
                time.sleep(self.RETRY_WAIT_INTERVAL)


    def _read_flags_worker(self) -> List[bool]:
        resp = self._client.read_coils(self.DIGITAL_IO_ADDRESS, 8)
        # sometimes, perhaps also depending on the version of modbus lib,
        # the response can be an exception
        if issubclass(type(resp), Exception):
            _logger.error(f"Modbus error {resp}")
        resp_list = list(resp.bits)[: self.NUM_DIO]
        return resp_list
    
    def _read_flags(self) -> List[bool]:
        """
        return flags (True means on) for
        [V1, V2, V3, V4, 
        DisableInternalBlower, DisableExternalBlower,
        ActivateCutoffValve, DisableStackBlower]
        """
        for ii in range(self.NUM_RETRIES+1):
            try:
                resp_list = self._read_flags_worker()
                break
            except:
                if ii == self.NUM_RETRIES:
                    raise
                time.sleep(self.RETRY_WAIT_INTERVAL)
        
        return resp_list

    def _read_values_worker(self):
        address_count_name = [
            (0, 2, "SourcePressure"),
            (2, 2, "MfcFlowRate"),
            (4, 2, "MfcDutyCycle"),
            (6, 1, "MfcTemperature"),
            (7, 2, "MfcTotalVolume"),
            (9, 2, "MfcUsedSetPointValue"),
        ]
        data = {}

        for addr, count, name in address_count_name:
            result = self._client.read_input_registers(addr, count=count)
            if count == 2:
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, **self.BYTEORDER)
                decoded_val = decoder.decode_32bit_float()
            elif count == 1:
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, **self.BYTEORDER)
                decoded_val = decoder.decode_16bit_uint()

            data[name] = decoded_val

        # MFC set point is read/write and accessed with a different function
        result = self._client.read_holding_registers(2, 2)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers, **self.BYTEORDER)
        decoded_val = decoder.decode_32bit_float()
        data["MfcSetPoint"] = decoded_val

        return data

    def _read_values(self):
        """
        read values from device
        """
        for ii in range(self.NUM_RETRIES+1):
            try:
                resp_list = self.read_values_worker()
                break
            except:
                if ii == self.NUM_RETRIES:
                    raise
                time.sleep(self.RETRY_WAIT_INTERVAL)
        
        return resp_list


    def _read_constant_values_worker(self):
        add_count_name_decoderfunc = [
            (849, 2, "Serial Number", lambda x: x.decode_32bit_uint()),
            (821, 10, "Device Name", lambda x: x.decode_string(10)),
        ]
        data = {}
        for addr, count, name, decoderfunc in add_count_name_decoderfunc:
            result = self._client.read_holding_registers(addr, count=count)
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers, **self.BYTEORDER)
            decoded_val = decoderfunc(decoder)
            data[name] = decoded_val
        return data

    def _read_constant_values(self):
        """
        Read 'acyclic' values (which I take to mean non-updating constants, e.g. serial number)
        """
        for ii in range(self.NUM_RETRIES+1):
            try:
                resp_list = self._read_constant_values_worker()
                break
            except:
                if ii == self.NUM_RETRIES:
                    raise
                time.sleep(self.RETRY_WAIT_INTERVAL)
        
        return resp_list


    def _set_flags_worker(self, flags: List[bool]):
        """ """
        assert len(flags) == self.NUM_DIO
        flags_to_send = list(flags) + [False] * (8 - self.NUM_DIO)
        resp = self._client.write_coils(self.DIGITAL_IO_ADDRESS, flags_to_send)
        # basic check for error - resp should have .address and .count fields
        # and this will raise an exception we have some other object instead
        _ = resp.address
        _ = resp.count

    def _set_flags(self, flags: List[bool]):
        """Set DIO flags

        Parameters
        ----------
        flags : List[bool]
            List of boolean values, True is high (1)
        """
        for ii in range(self.NUM_RETRIES+1):
            try:
                self._set_flags_worker(flags)
                break
            except:
                if ii == self.NUM_RETRIES:
                    raise
                time.sleep(self.RETRY_WAIT_INTERVAL)
        

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
        self._set_mfc_flowrate(self._mfc_setpoint_flush)

    def inject(self, detector_idx: int = 0) -> None:
        """Inject radon from source
        (if we're in BG mode then switch out of it)"""
        assert detector_idx == 0 or detector_idx == 1
        # choose the valve and bg flag matching this detector
        valve_idx = 2 + detector_idx
        bg_idx = 4 + detector_idx
        flags = self._read_flags()
        flags[0] = True
        flags[1] = False
        flags[2] = False
        flags[3] = False
        flags[valve_idx] = True # this is valve 2 or valve 3
        # make sure this detector is switched out of background
        flags[bg_idx] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(self._mfc_setpoint_inject)

    def reset_flush(self, pressurise: bool = True) -> None:
        """Exit from source-flush mode"""
        if pressurise:
            self.pressurise_source_capsule()
        flags = self._read_flags()
        flags[0] = False
        flags[1] = False
        flags[2] = False
        flags[3] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(0.0)
    
    def pressurise_source_capsule(self) -> None:
        """Set pressure in source capsule to approx 10 kPa.
        
        This is roughly the same pressure as a person can deliver from their lungs)
        e.g. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4001942/"""

        # as a secondary fail-safe, and regardless of what else happens, 
        # never put in more than this much air to limit the overpressure
        # to a relatively small value
        target_source_pressure_pa = 10_000.0

        # if the source capsule is already pressurised, there's nothing to do
        data = self._read_values()
        p_meas = data["SourcePressure"]
        if p_meas >= target_source_pressure_pa:
            return

        # source volume is about 230 ml, 10kPa overpressure is about a tenth
        # of atmosphere, so we want to add about 23 ml to reach 10kPa.  Allow
        # for roughly double that (50 ml) as our maximum overpressure.
        max_volume_l = 0.05
        max_time_sec = (max_volume_l / self.MFC_DEFAULT_FLOW) * 60
        t0 = time.time()
        # start pressurising
        flags = self._read_flags()
        flags[0] = True
        flags[1] = False
        flags[2] = False
        flags[3] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(self.MFC_DEFAULT_FLOW)

        pressure_set_success = False
        p_meas = None
        _logger.info(f"Pressurising source capsule to {target_source_pressure_pa} kPa.")
        while (time.time() - t0) < max_time_sec:
            data = self._read_values()
            p_meas = data["SourcePressure"]
            if p_meas >= target_source_pressure_pa:
                _logger.info("Pressure in source capsule reached target.")
                pressure_set_success = True
                break
        if not pressure_set_success:
            _logger.warning(f"Pressure in source capsule did not reach target.  Target: {target_source_pressure_pa/1000.0}, actual: {p_meas/1000.0:.04} kPa")
        flags[0] = False
        self._set_flags(flags)
        self._set_mfc_flowrate(0.0)


    def start_background(self, detector_idx: int = 0) -> None:
        """Put detector in background mode"""
        if self._option_2b:
            assert detector_idx == 0 or detector_idx == 1
        else:
            assert detector_idx == 0
        # choose the valve and bg flag matching this detector
        inject_valve_idx = 2 + detector_idx
        if self._option_2b:
            # all of these are switched from a single DIO
            bg_idx = 4 + detector_idx
            internal_blower_idx = bg_idx
            external_blower_idx = bg_idx
            cutoff_valve_idx = bg_idx
            stack_blower_idx = bg_idx
        else:
            internal_blower_idx = 4
            external_blower_idx = 5
            cutoff_valve_idx = 6
            stack_blower_idx = 7
        flags = self._read_flags()
        if flags[inject_valve_idx] == True:
            # current detector is injecting, so cancel this before switching to BG
            self.reset_calibration()
        flags[internal_blower_idx] = True
        flags[external_blower_idx] = True
        flags[cutoff_valve_idx] = True
        flags[stack_blower_idx] = True

        self._set_flags(flags)

    def reset_background(self, detector_idx: Optional[int] = None) -> None:
        """Cancel a running background (but leave source flushing if it already is running)"""
        if self._option_2b:
            assert detector_idx == 0 or detector_idx == 1 or detector_idx is None
        else:
            assert detector_idx == 0 or detector_idx is None
        if detector_idx is not None and self._option_2b:
            # all of these are switched from a single DIO
            bg_idx = 4 + detector_idx
            internal_blower_idx = bg_idx
            external_blower_idx = bg_idx
            cutoff_valve_idx = bg_idx
            stack_blower_idx = bg_idx
        elif detector_idx is None and self._option_2b:
            # set both detectors out of background
            internal_blower_idx = 4
            external_blower_idx = 5
            cutoff_valve_idx = 4
            stack_blower_idx = 5

        else:
            internal_blower_idx = 4
            external_blower_idx = 5
            cutoff_valve_idx = 6
            stack_blower_idx = 7

        flags = self._read_flags()
        flags[internal_blower_idx] = False
        flags[external_blower_idx] = False
        flags[cutoff_valve_idx] = False
        flags[stack_blower_idx] = False

        self._set_flags(flags)

    def reset_calibration(self) -> None:
        """Cancel a running calibration (but leave background-related
        flags unchanged)"""
        self.reset_flush()

    def reset_all(self, pressurise: bool = True) -> None:
        """return to idle state"""
        self.reset_flush(pressurise=pressurise)
        self.reset_background()

    @property
    def analogue_states(self) -> Dict[str, float]:
        data = self._read_values()
        return data
    
    @property
    def digital_output_state(self) -> Dict[str, bool]:
        flags = self._read_flags()
        # flags as a dict
        fd = {k: v for k, v in zip(self.FLAG_NAMES, flags)}
        return fd


    @property
    def status(self) -> Dict[str, Any]:
        """generate a human-readable status message based on DIO flags"""
        try:
            flags = self._read_flags()
            fd = {k: v for k, v in zip(self.FLAG_NAMES, flags)}
            if not True in flags:
                s = "Normal operation"
            else:
                sl: List[str] = []
                if fd["Inject1"]:
                    sl.append("Injecting from source into detector 1")
                elif fd["Inject2"]:
                    sl.append("Injecting from source into detector 2")
                elif fd["SourceFlush"]:
                    sl.append("Flushing source")
                if (not self._option_2b) and fd["DisableInternalBlower"]:
                    sl.append("Performing background on detector 1")
                elif self._option_2b and fd["Background1"]:
                    sl.append("Performing background on detector 1")
                elif self._option_2b and fd["Background2"]:
                    sl.append("Performing background on detector 2")

                s = ", ".join(sl)

            status: Dict[str, Any] = {}
            status["message"] = s
            status["digital out"] = fd
            status["analogue in"] = self.analogue_states
            status["serial"] = self.serial_number
        except Exception as ex:
            _logger.error(f"Unable to read status from Burkert Gateway because of error {ex}.  {traceback.format_exc()}")
            raise
        return status
