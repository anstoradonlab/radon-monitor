import ctypes
import logging
import math
import os
import struct
import threading
import time
from typing import List

import u12

from .calbox_device import CalboxDevice

_logger = logging.getLogger(__name__)

# reference for Labjack interface:
#

def get_u12_error_string(errorcode: int) -> str:
    """Like u12.getErrorString, return a string description of an error

    This is included because the u12 function has a bug where a unicode string is 
    used instead of byte string, meaning that it doesn't work on Python 3.

    Args:
        errorcode (int): Error code from labjack library

    Returns:
        str: Description of the error
    """
    staticLib = u12.staticLib
    # this line has the change, b" "*50 instead of " "*50
    errorString = ctypes.c_char_p(b" "*50)
    staticLib.GetErrorString(errorcode, errorString)
    # also different - conversion from bytes to str
    return str(errorString.value, 'ascii')


def bool_list_to_int(a):
    """
    convert a list of boolean flags into an integer-based bitfield

    The boolean flags toggle the bits from the LSB,
    i.e. a[0] corresponds to the least significant bit,
    so the list written out is in the reverse order to the binary
    representation printed using bin(bitfield)
    """
    bitfield = 0
    for ii in range(len(a)):
        bitfield = bitfield | int(a[ii]) << ii
    return bitfield


def int_to_bool_list(bitfield, numbits, dtype=bool):
    """
    Convert an integer-based bitfield into a list of boolean flags
    """
    bitfield = int(bitfield)
    a = [False for ii in range(numbits)]
    for ii in range(numbits):
        a[ii] = dtype(bitfield >> ii & 1)
    return a

def flow_sensor_v_to_lpm(V: float, coeffs: List[float]) -> float:
    """Convert from voltage (V) into flow rate (lpm) for the flow sensor in the Labjack-based calibration units

    Args:
        V (float): Voltage measured on sensor
        coeffs (List[float]): three polynomial coefficients to do the conversion, 
                    [V*2 coefficient, V coefficient, constant]

    Returns:
        float: flow rate in lpm
    """    
    if V is None:
        return None
    flow_lpm = (coeffs[0]*V**2 + coeffs[1]*V + coeffs[2]) / 100.0
    return flow_lpm

class LabjackWrapper:
    """Wrapper for the labjack interface.

    Purpose is to provide a specialized version of the interface, which only includes
    the functions needed for our calibration system.

    There are multiple APIs to access the LabJack, so the use of this wrapper means
    that we'll be able to switch later if needed.

    Only DIO ports 0-5 are used in our setup.

    Note: this code is not thread safe (not re-entrant)

    """

    def __init__(self, labjack_id=-1, serialNumber=None):
        self._thread_id = threading.get_ident()
        # this is what we expect the output state to be in
        self._current_state = [None] * 16
        try:
            if serialNumber is not None:
                self.device = u12.U12(debug=False, serialNumber=serialNumber)
            else:
                self.device = u12.U12(id=labjack_id, debug=False)
            self.max_channel = 5
            try:
                self.reset_dio()
            except Exception as ex:
                _logger.error(f"Error calling reset_dio(): {ex}")
                raise
        except u12.U12Exception as ex:
            error_txt = ""
            if len(ex.args) == 1:
                error_txt = '(' + get_u12_error_string(int(ex.args[0])) + ')'
            _logger.error(f"Unable to connect to labjack because of error: {ex} {error_txt}")
            raise
        except Exception as ex:
            _logger.error(f"Unable to connect to labjack because of error: {ex}")
            raise

    def set_digital_outputs(self, state: List[bool]):
        """
        Set all digital outputs

        All digitial IO lines are set to output mode

        Channels are set to high or low depending on the values of state.
        Channel 0 is set from state[0], channel 1 from state[1], etc.

        state must have length of 16
        """
        bool_repr = {True: 'T', False: 'F'}
        state_txt = "".join([bool_repr[itm] for itm in state])
        _logger.debug(f"Setting digital outputs to: {state_txt}")
        d = self.device
        assert len(state) == 16
        assert (self._thread_id == threading.get_ident())
        self._current_state = list(state)
        if os.name == "nt":
            # the IO lines are unused - but we need to set something
            trisIO = 0
            stateIO = 0
            stateD = bool_list_to_int(state)
            # trisD 1-valued bits to signal digital output
            all_high = 2**16 - 1
            d.digitalIO(
                trisD=all_high,
                stateD=stateD,
                updateDigital=1,
                trisIO=trisIO,
                stateIO=stateIO,
            )
        else:
            D15toD8States = bool_list_to_int(state[8:16])
            D7toD0States = bool_list_to_int(state[:8])

            status = d.rawDIO(
                D15toD8Directions=0,
                D7toD0Directions=0,
                D15toD8States=D15toD8States,
                D7toD0States=D7toD0States,
                IO3toIO0DirectionsAndStates=0,
                UpdateDigital=True,
            )

    def reset_dio(self):
        """Sets output to zero on all channels while also configuring all DIO channels as output"""
        _logger.debug(f"Setting all digital outputs to zero")
        assert (self._thread_id == threading.get_ident())
        self._current_state = [0 for ii in range(16)]
        d = self.device
        # eDigitalOut doesn't work on Windows, so use the low-level commands
        if os.name == "nt":
            # there are 16 DIO channels, here is a bit flag of 16 1s
            all_high = 2**16 - 1
            d.digitalIO(trisD=all_high, stateD=0, updateDigital=1, trisIO=0, stateIO=0)
        else:
            all_high_byte = 2**8 - 1
            # Args:
            # D15toD8Directions, A byte where 0 = Output, 1 = Input for D15-8
            # D7toD0Directions, A byte where 0 = Output, 1 = Input for D7-0
            # D15toD8States, A byte where 0 = Low, 1 = High for D15-8
            # D7toD0States, A byte where 0 = Low, 1 = High for D7-0
            # IO3toIO0DirectionsAndStates, Bits 7-4: Direction, 3-0: State
            # UpdateDigital, True if you want to update the IO/D line. False to
            #             False to just read their values.
            status = d.rawDIO(
                D15toD8Directions=0,
                D7toD0Directions=0,
                D15toD8States=0,
                D7toD0States=0,
                IO3toIO0DirectionsAndStates=0,
                UpdateDigital=True,
            )

    def set_dio(self, channel, state):
        """Set one DIO channel to 1 or 0"""
        assert state == 0 or state == 1
        assert (self._thread_id == threading.get_ident())
        _logger.debug(f"Setting one digital output, channel: {channel}, state: {state}")
        d = self.device
        ret = d.eDigitalOut(channel, state)
        # TODO: raise an exception instead (may have lost connection to labjack)
        assert ret["idnum"] == d.id
        self._current_state[channel] = state

    @property
    def dio_states(self):
        """
        Read the DIO states
        """
        assert (self._thread_id == threading.get_ident())
        _logger.debug(f"Reading DIO states")
        d = self.device
        if os.name == "nt":
            status = d.digitalIO(
                updateDigital=0,
            )
            direction = int_to_bool_list(status["trisD"], 16)
            level = int_to_bool_list(status["stateD"], 16)
        else:
            status = d.rawDIO(UpdateDigital=False)
            direction = int_to_bool_list(
                status["D7toD0Directions"], 8
            ) + int_to_bool_list(status["D15toD8Directions"], 8)
            level = int_to_bool_list(status["D7toD0States"], 8) + int_to_bool_list(
                status["D15toD8States"], 8
            )

        for expected, actual in zip(self._current_state, level):
            if not bool(expected) == bool(actual):
                _logger.error(f"Expected DIO state did not match the value read from Labjack.  Expected: {self._current_state}, Actual: {level}")
                # TODO: Raise error???

        return level, direction

        # this would have the side-effect of setting all channels to input
        # if this function is needed, it will need to use rawDIO on linux, digitialIO on
        # windows
        # refer to https://labjack.com/forums/u12/liblabjackusbso-undefined-symbol-digitalio

        # TODO: this should be implemented because sometimes (Weybourne) we've noticed
        # the DIO state changing without being told to.

        # TODO: Here's some notes for the rawDIO on linux:
        # import u12
        # d = u12.U12()
        # state = d.rawDIO()
        # # remove the latch states (so we can send 'state' back to the function as **state)
        # state.pop('D15toD8OutputLatchStates')
        # state.pop('D7toD0OutputLatchStates')
        # # remove the IO data
        # state.pop('IO3toIO0States')
        # # set one of the channels
        # k = 'D0'
        # direction = 0 # 0 is output
        # signal = 1 # 0 is low voltage, 1 is high voltage
        # setattr(state['D7toD0Directions'], k, direction)
        # setattr(state['D7toD0States'], k, signal)
        # d.rawDIO(**state, UpdateDigital=True)

    @property
    def analogue_states(self):
        return self._analogue_states_func()
    
    def _analogue_states_func(self, retries=3):
        """Read analog channels 0 and 1"""
        assert (self._thread_id == threading.get_ident())
        _logger.debug(f"Reading analog channels")
        d = self.device
        success = True
        try:
            if os.name == "nt":
                # eAnalogIn does not work on windows OS
                a_in = d.aiSample(channels=[0, 1], numChannels=2)
                # a_in is now something like: {'idnum': -1,
                #    'stateIO': 0,
                #    'overVoltage': 999,  # 0 - not over voltage, >0 - over voltage
                #    'voltages': [2.5, 1.9677734375]}
                if a_in["overVoltage"] > 0:
                    _logger.error(f"One of the Labjack analog channels is over voltage")
                voltages = a_in["voltages"]

            else:
                # aiSample is only available on windows OS
                # (rawAISample is an option too, but eAnalogIn seems
                # to do what we need for now)
                voltages = []
                for ii in range(2):
                    try:
                        a_in = d.eAnalogIn(ii)
                    except Exception as ex:
                        _logger.error(f"Error reading from labjack analogue channel {ii}: {ex}")
                        voltages.append(None)
                        continue

                    if a_in["overVoltage"]:
                        _logger.error(f"Labjack analogue channel {ii} is over voltage")
                    voltages.append(a_in["voltage"])

            # remember - special value of -1 means 'talk to any labjack'
            if d.id != -1 and a_in["idnum"] != d.id:
                _logger.error(
                    f"Labjack reports IDNUM={a_in['idnum']} but we expected {d.id}"
                )
            
        except Exception as ex:
            _logger.error(f"Error reading from labjack analogue channels: {ex}")
            voltages = [None, None]
            success = False
        
        if not success and retries > 0:
            time.sleep(0.5)
            voltages = self._analogue_states_func(retries=retries - 1)
        
        return voltages

    @property
    def serial_number(self):
        assert (self._thread_id == threading.get_ident())
        _logger.debug(f"Reading labjack serial number")
        d = self.device
        # serial no is four bytes at address 0
        if os.name == "nt":
            serial_no_bytes = d.readMem(0)
            serial_no = struct.unpack(">I", struct.pack("BBBB", *serial_no_bytes))[0]
        else:
            r = d.rawReadRAM()
            # >>> print(r)
            # {'DataByte3': 5, 'DataByte2': 246, 'DataByte1': 139, 'DataByte0': 170}
            serial_no_bytes = [
                r["DataByte3"],
                r["DataByte2"],
                r["DataByte1"],
                r["DataByte0"],
            ]
            serial_no = struct.unpack(">I", struct.pack("BBBB", *serial_no_bytes))[0]
        return serial_no


class CalBoxLabjack(CalboxDevice):
    """Hardware interface for the labjack inside our Cal Box.

    Note: this is intended to be thread-safe
    TODO: maybe lock more, perhaps even the whole thing
    """

    def __init__(self, labjack_id=-1, serialNumber=None, flow_sensor_polynomial=None):
        """Interface for the labjack, as it is installed in our pumped Cal Box

        Parameters
        ----------
        labjack_id : int, optional
            ID number of the labjack to connect to, by default -1
            Special values:
                * `-1`: connect to whichever labjack we can find
                * `None`: don't connect to a labjack, but run anyway (this is
                  for testing without access to a labjack)

        flow_sensor_polynomial (List[float]): 
            three polynomial coefficients to do the conversion from V to lpm, 
                [V*2 coefficient, V coefficient, constant]

        serialNumber : int, optional
            If provided, this is the serial number of the labjack to connect to
        """
        if flow_sensor_polynomial is None:
            flow_sensor_polynomial = [0.1025, -0.17965, 0.0669979]
        self._flow_sensor_polynomial = flow_sensor_polynomial
        self._init_serial_number = serialNumber
        self._init_labjack_id = labjack_id
        self.no_hardware_mode = labjack_id is None
        self.serial_number = None

        self._thread_id = threading.get_ident()
        # initialise some flags on the computer-side (no comms)
        self._init_flags()
        # placeholder for labjack interface
        self.lj = None

        self._ljlock = threading.RLock()

        with self._ljlock:
            try:
                if labjack_id is not None:
                    self.lj = LabjackWrapper(labjack_id, serialNumber=serialNumber)
                    self.serial_number = self.lj.serial_number
                    _logger.info(
                        f"Connected to labjack with serial number: {self.serial_number}"
                    )
                else:
                    _logger.warning(
                        f"Running in test mode without trying to connect to labjack because labjack_id has been set to 'None'"
                    )

                self._send_state_to_device()
                # assume connection is Ok if we made it to here
                self._connected = True
            except Exception as ex:
                raise ex

    def _init_flags(self):
        # current state of DIO channel (boolean - True/False)
        self.digital_output_state = {}
        # mapping from text label to DIO channel number
        self.digital_output_channel = {}
        # this defines how the digital outputs are wired up.
        # The list starts from DIO channel 0 ("ActivatePump")
        for ii, k in enumerate(
            [
                "ActivatePump",
                "ActivateInject",
                "ActivateCutoffValve",
                "DisableStackBlower",
                "DisableExternalBlower",
                "DisableInternalBlower",
            ]
        ):
            self.digital_output_state[k] = False
            self.digital_output_channel[k] = ii

        # flow measured on analogue channel 0, Pump voltage on analogue channel 1
        self.analogue_input_channel = {"Flow": 0, "Pump": 1}

    def flush(self):
        """Start source-flush pump"""
        self.digital_output_state["ActivatePump"] = True
        self.digital_output_state["ActivateInject"] = False
        _logger.info(f"Cal Box flush")
        self._send_state_to_device()

    def inject(self, detector_idx=0):
        """Inject radon from source"""
        if self.digital_output_state["DisableInternalBlower"] == True:
            _logger.warning(
                "Switching directly from background to inject: background may have been terminated early."
            )
        assert detector_idx == 0
        self.digital_output_state["ActivatePump"] = True
        self.digital_output_state["ActivateInject"] = True
        self.digital_output_state["ActivateCutoffValve"] = False
        self.digital_output_state["DisableStackBlower"] = False
        self.digital_output_state["DisableExternalBlower"] = False
        self.digital_output_state["DisableInternalBlower"] = False
        _logger.info(f"Cal Box inject")
        self._send_state_to_device()

    def reset_flush(self):
        """Stop source-flush pump"""
        self.digital_output_state["ActivatePump"] = False
        self.digital_output_state["ActivateInject"] = False
        _logger.info(f"Cal Box flush and injection state reset")
        self._send_state_to_device()

    def start_background(self, detector_idx=0):
        """Put detector in background mode"""
        assert detector_idx == 0
        if self.digital_output_state["ActivateInject"] == True:
            _logger.warning(
                "Switching directly from inject to background: a surprisingly high background is likely."
            )
        self.digital_output_state["ActivateInject"] = False
        self.digital_output_state["ActivateCutoffValve"] = True
        self.digital_output_state["DisableStackBlower"] = True
        self.digital_output_state["DisableExternalBlower"] = True
        self.digital_output_state["DisableInternalBlower"] = True
        _logger.info(f"Cal Box entered background mode")
        self._send_state_to_device()

    def reset_background(self):
        """Cancel a running background (but leave source flushing if it already is running)"""
        self.digital_output_state["ActivateCutoffValve"] = False
        self.digital_output_state["DisableStackBlower"] = False
        self.digital_output_state["DisableExternalBlower"] = False
        self.digital_output_state["DisableInternalBlower"] = False
        _logger.info(f"Cal Box background state reset")
        self._send_state_to_device()

    def reset_calibration(self):
        """Cancel a running calibration (but leave background-related
        flags unchanged)"""
        self.reset_flush()

    def reset_all(self):
        """return to idle state"""
        for k, v in self.digital_output_state.items():
            self.digital_output_state[k] = False
        _logger.info(f"Cal Box reset")
        self._send_state_to_device()

    @property
    def analogue_states(self):
        channels_dict = {}
        if self.no_hardware_mode:
            for k in self.analogue_input_channel:
                channels_dict[k] = math.nan
        else:
            with self._ljlock:
                voltages = self.lj.analogue_states
            for k in self.analogue_input_channel:
                channels_dict[k] = voltages[self.analogue_input_channel[k]]
        if "Flow" in channels_dict:
            # calibrated flow rate, "Flow" is measured in V
            V = channels_dict["Flow"]
            channels_dict["Flow_lpm"] = flow_sensor_v_to_lpm(V, self._flow_sensor_polynomial)
        return channels_dict

    def _send_state_to_device(self):
        if not self.no_hardware_mode:
            all_states = [False for ii in range(16)]
            for k, state in self.digital_output_state.items():
                channel = self.digital_output_channel[k]
                all_states[channel] = state
            with self._ljlock:
                self.lj.set_digital_outputs(all_states)
            _logger.debug(
                f"Labjack digital output ports set: {self.digital_output_state.items()}"
            )
        else:
            _logger.debug("Labjack interface running in no-hardware mode.")

    @property
    def status(self):
        """generate a human-readable status message based on DIO flags"""
        if self.lj is not None:
            # force a read from the device
            _device_states = self.lj.dio_states
        flags = [
            self.digital_output_state["ActivatePump"],
            self.digital_output_state["ActivateInject"],
            self.digital_output_state["ActivateCutoffValve"],
            self.digital_output_state["DisableStackBlower"],
            self.digital_output_state["DisableExternalBlower"],
            self.digital_output_state["DisableInternalBlower"],
        ]
        if flags == [False, False, False, False, False, False]:
            s = "Normal operation"
        elif flags == [True, False, False, False, False, False]:
            s = "Flushing source"
        elif flags == [True, True, False, False, False, False]:
            s = "Injecting from source"
        elif flags == [False, False, True, True, True, True]:
            s = "Performing background"
        elif flags == [True, False, True, True, True, True]:
            s = "Flushing source and performing background"
        else:
            s = "Unexpected DIO state: {flags}"
        status = {}
        status["message"] = s
        status["digital out"] = {}
        status["analogue in"] = {}
        status["analogue in"].update(self.analogue_states)
        status["digital out"].update(self.digital_output_state)
        status["serial"] = self.serial_number
        return status


class CapeGrimLabjack(CalBoxLabjack):
    def __init__(self, labjack_id=-1, serialNumber=None, flow_sensor_polynomial=None):
        """Interface for the labjack, as it is installed at Cape Grim

        Parameters
        ----------
        labjack_id : int, optional
            ID number of the labjack to connect to, by default -1
            Special values:
                * `-1`: connect to whichever labjack we can find
                * `None`: don't connect to a labjack, but run anyway (this is
                  for testing without access to a labjack)

        serialNumber : int, optional
            If provided, this is the serial number of the labjack to connect to
        """
        super().__init__(labjack_id, serialNumber, flow_sensor_polynomial)

    def _init_flags(self):

        # Based on a field trip (Oct 2022) we have the following:
        # Channel       | What happens if this channel is set to high (1)
        # 0             | Disable stack blower for BHURD
        # 1             | Disable stack blower for HURD
        # 2             | Isolate HURD (this happens during a background)
        # 3             | Isolate BHURD
        # 4             | Open valve A (connect source capsule to inject line)
        # 5             | Open valve B (connect inject line to HURD)
        # 6             | Open valve C (connect inject line to BHURD)
        # 7             | Switch on the pump pushing air through source capsule
        # 8             | Disable BHURD internal blowers
        # 9             | Disable HURD internal blowers


        # current state of DIO channel (boolean - True/False)
        self.digital_output_state = {}
        # mapping from text label to DIO channel number
        self.digital_output_channel = {}
        # this defines how the digital outputs are wired up.
        # I've indexed from 1 (instead of from 0, like detector_idx)
        # because these names are visible to the user (in the database)
        for ii, k in enumerate(
            [
                "DisableStackBlower2",  # 0
                "DisableStackBlower1",  # 1
                "ActivateCutoffValve1",  # 2
                "ActivateCutoffValve2",  # 3
                "ActivateInject",  # 4
                "Inject1",  # 5
                "Inject2",  # 6
                "ActivatePump",  # 7
                "DisableInternalBlower2",  # 8
                "DisableInternalBlower1",  # 9
            ]
        ):
            self.digital_output_state[k] = False
            self.digital_output_channel[k] = ii

        # flow measured on analogue channel 0,
        # No pump voltage??
        self.analogue_input_channel = {"Flow": 0}  # , "Pump": 1}

    def flush(self):
        """Start source-flush pump"""
        self.digital_output_state["ActivatePump"] = True
        self.digital_output_state["ActivateInject"] = False
        self.digital_output_state["Inject1"] = False
        self.digital_output_state["Inject2"] = False
        _logger.info(f"Cal Box flush")
        self._send_state_to_device()

    def inject(self, detector_idx=0):
        """Inject radon from source"""
        detector_idx = int(detector_idx)
        assert detector_idx == 0 or detector_idx == 1
        other_detector = 1 - detector_idx
        if self.digital_output_state[f"DisableInternalBlower{detector_idx+1}"] == True:
            _logger.warning(
                "Switching directly from background to inject: background may have been terminated early."
            )
        self.digital_output_state["ActivatePump"] = True
        self.digital_output_state["ActivateInject"] = True
        self.digital_output_state[f"Inject{detector_idx+1}"] = True
        self.digital_output_state[f"Inject{other_detector+1}"] = False
        self.digital_output_state[f"ActivateCutoffValve{detector_idx+1}"] = False
        self.digital_output_state[f"DisableStackBlower{detector_idx+1}"] = False
        self.digital_output_state[f"DisableInternalBlower{detector_idx+1}"] = False
        _logger.info(f"Cal Box inject, detector {detector_idx+1}")
        self._send_state_to_device()

    def reset_flush(self):
        """Stop source-flush pump"""
        self.digital_output_state["ActivatePump"] = False
        self.digital_output_state["ActivateInject"] = False
        self.digital_output_state[f"Inject1"] = False
        self.digital_output_state[f"Inject2"] = False
        _logger.info(f"Cal Box flush and injection state reset")
        self._send_state_to_device()

    def start_background(self, detector_idx=0):
        """Put detector in background mode"""
        detector_idx = int(detector_idx)
        assert detector_idx == 0 or detector_idx == 1

        if self.digital_output_state[f"Inject{detector_idx+1}"] == True:
            _logger.warning(
                "Switching directly from inject to background: a surprisingly high background is likely."
            )
            self.digital_output_state["ActivateInject"] = False
        # disable stack blower and allow some time for it to slow before closing the isolation valve
        self.digital_output_state[f"DisableStackBlower{detector_idx+1}"] = True
        self.digital_output_state[f"DisableInternalBlower{detector_idx+1}"] = True
        self._send_state_to_device()
        time.sleep(5)

        self.digital_output_state[f"ActivateCutoffValve{detector_idx+1}"] = True
        _logger.info(f"Cal Box entered background mode, detector {detector_idx+1}")
        self._send_state_to_device()

    def reset_background(self):
        """Cancel a running background (but leave source flushing if it already is running)"""
        self.digital_output_state["ActivateCutoffValve1"] = False
        self.digital_output_state["ActivateCutoffValve2"] = False
        self.digital_output_state["DisableStackBlower1"] = False
        self.digital_output_state["DisableStackBlower2"] = False
        self.digital_output_state[f"DisableInternalBlower1"] = False
        self.digital_output_state[f"DisableInternalBlower2"] = False
        _logger.info(f"Cal Box background state reset")
        self._send_state_to_device()

    @property
    def status(self):
        """generate a human-readable status message based on DIO flags"""
        state = self.digital_output_state
        flags = list(state.values())
        flags_txt = str([int(itm) for itm in flags])

        if not (True in flags):
            s = "Normal operation"
        elif flags == [
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            False,
            False,
        ]:
            s = "Flushing source"
        elif state["Inject1"]:
            s = "Injecting from source into detector 1"
        elif state["Inject2"]:
            s = "Injecting from source into detector 2"
        elif (
            state["ActivateCutoffValve1"]
            and state["DisableStackBlower1"]
            and state["DisableInternalBlower1"]
        ):
            s = "Performing background on detector 1"
        elif (
            state["ActivateCutoffValve2"]
            and state["DisableStackBlower2"]
            and state["DisableInternalBlower2"]
        ):
            s = "Performing background on detector 2"
        else:
            s = f"Unexpected DIO state: {flags_txt}"
        ## append all of the flags to the status message
        # if not s.endswith(']'):
        #    s = s+' '+flags_txt
        status = {}
        status["message"] = s
        status["digital out"] = {}
        status["analogue in"] = {}
        status["analogue in"].update(self.analogue_states)
        status["digital out"].update(self.digital_output_state)
        status["serial"] = self.serial_number
        return status


#
# .... utility functions
#

def get_labjack_error_string(errorcode: int) -> str:
    errorString = ctypes.c_char_p(b" "*50)
    errno = u12.staticLib.GetErrorString(errorcode, errorString)
    if errno == 0:
        ret = str(errorString.value, encoding='utf-8')
    else:
        ret = f"Error {errorcode}"
    return errorString.value

def list_all_u12():
    """
    A version of u12.listAll which works on both windows and linux/mac

    Original docs:

        Name: U12.listAll()
        Args: See section 4.22 of the User's Guide
        Desc: Searches the USB for all LabJacks, and returns the serial number and local ID for each

        >>> dev = U12()
        >>> dev.listAll()
        >>> {'serialnumList': <u12.c_long_Array_127 object at 0x00E2AD50>, 'numberFound': 1, 'localIDList': <u12.c_long_Array_127 object at 0x00E2ADA0>}

    TODO: return types differ between windows and linux versions (fixed but not verified)
    """
    dev = u12.U12()
    try:
        # this is implemented by labjack on windows but not linux/mac
        # returns {"serialnumList": serialnumList, "localIDList":localIDList, "numberFound":numberFound.value}
        info = dev.listAll()
        # manipulate info so that it has the some type as the linux version
        # (the driver returns arrays of fixed length 127 instead of lists, and the caller
        # isn't supposed to look past the numberFound index)
        N = info["numberFound"]
        info_ret = {
            "serialnumList": list(info["serialnumList"][:N]),
            "localIDList": list(info["localIDList"][:N]),
            "numberFound": N,
        }
        info = info_ret
        dev.close()

    except AttributeError:
        # this means that we're running on linux/mac
        dev.close()
        # follow the approach used in 'open' to open each device and get info.
        # This is brittle and relies on manipulating the 'handle' field inside
        # the U12 object, as well as direct access to the binary driver
        staticLib = u12._loadLibrary()
        devType = ctypes.c_ulong(1)
        openDev = staticLib.LJUSB_OpenDevice
        openDev.restype = ctypes.c_void_p
        info = {"serialnumList": [], "localIDList": [], "numberFound": 0}
        numDevices = staticLib.LJUSB_GetDevCount(devType)
        for ii in range(numDevices):
            handle = openDev(ii + 1, 0, devType)
            if handle != 0 and handle is not None:
                dev.handle = ctypes.c_void_p(handle)
                try:
                    info["serialnumList"].append(dev.rawReadSerial())
                    info["localIDList"].append(dev.rawReadLocalId())
                    info["numberFound"] += 1
                finally:
                    dev.close()

    return info


if __name__ == "__main__":

    def setup_test_logging(loglevel, logfile=None):
        """Setup basic logging

        Args:
            loglevel (int): minimum loglevel for emitting messages
        """
        # logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
        logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
        logging.basicConfig(
            level=loglevel,
            stream=sys.stdout,
            format=logformat,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    import sys

    setup_test_logging(logging.DEBUG)

    for ljid in [-1, None]:
        print(f"Running with labjack ID {ljid}")
        lj = CalBoxLabjack(ljid)
        lj.reset_all()

        lj.flush()
        lj.reset_flush()
        lj.inject()
        lj.reset_all()

        lj.start_background()
        lj.reset_all()

        print(f"Analogue channel voltages: {lj.analogue_states}")
