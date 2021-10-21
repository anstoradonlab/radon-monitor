import ctypes
import logging
import math
import struct

import u12


_logger = logging.getLogger(__name__)

# reference for Labjack interface:
#


class LabjackWrapper:
    """Wrapper for the labjack interface.

    Purpose is to provide a specialized version of the interface, which only includes
    the functions needed for our calibration system.

    There are multiple APIs to access the LabJack, so the use of this wrapper means
    that we'll be able to sitch later if needed.

    Only DIO ports 0-5 are used in our setup.

    """

    def __init__(self, labjack_id=-1, serialNumber=None):
        if serialNumber is not None:
            self.device = u12.U12(debug=False, serialNumber=serialNumber)
        else:
            self.device = u12.U12(id=labjack_id, debug=False)
        self.max_channel = 5
        self.reset_dio()

    def reset_dio(self):
        """Sets output to zero on all channels while also configuring all DIO channels as output"""
        d = self.device
        for ii in range(self.max_channel + 1):
            ret = d.eDigitalOut(ii, 0)

    def set_dio(self, channel, state):
        """Set one DIO channel to 1 or 0"""

        d = self.device
        ret = d.eDigitalOut(channel, state)
        # TODO: raise an exception instead (may have lost connection to labjack)
        assert ret["idnum"] == d.id

    @property
    def dio_states(self):
        raise NotImplementedError

        # this would have the side-effect of setting all channels to input
        # if this function is needed, it will need to use rawDIO on linux, digitialIO on
        # windows
        # refer to https://labjack.com/forums/u12/liblabjackusbso-undefined-symbol-digitalio

    @property
    def analogue_states(self):
        d = self.device
        values = []
        for ii in range(2):
            a_in = d.eAnalogIn(0)
            # what to do if overVoltage??
            # this is indicated by a_in["overVoltage"]
            # TODO: log as error
            values.append(a_in["voltage"])
            assert a_in["idnum"] == d.id

        return values

    @property
    def serial_number(self):
        d = self.device
        # by default, this reads the bytes which make up the serial number
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


class CalBoxLabjack:
    """Hardware interface for the labjack inside our Cal Box.
    """

    def __init__(self, labjack_id=-1, serialNumber=None):
        """Interface for the labjack, as it is installed in our pumped Cal Box

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
        self.no_hardware_mode = True
        self.serial_number = None

        if labjack_id is not None:
            self.lj = LabjackWrapper(labjack_id, serialNumber=serialNumber)
            self.no_hardware_mode = False
            self.serial_number = self.lj.serial_number
            _logger.info(
                f"Connected to labjack with serial number: {self.serial_number}"
            )
        else:
            _logger.warning(
                f"Running without trying to connect to labjack because labjack_id is None"
            )

        self._init_flags()

    def _init_flags(self):
        # current state of DIO channel (boolean - True/False)
        self.digital_output_state = {}
        # mapping from text label to DIO channel number
        self.digital_output_channel = {}
        # this defines how the digital outputs are wired up.
        # The list starts from DIO channel 0 ("activate_pump")
        for ii, k in enumerate(
            [
                "activate_pump",
                "activate_inject",
                "activate_cutoff_valve",
                "disable_stack_blower",
                "disable_external_blower",
                "disable_internal_blower",
            ]
        ):
            self.digital_output_state[k] = False
            self.digital_output_channel[k] = ii

        # flow measured on analogue channel 0, Pump voltage on analogue channel 1
        self.analogue_input_channel = {"flow": 0, "pump": 1}

    def flush(self):
        """Start source-flush pump"""
        self.digital_output_state["activate_pump"] = True
        self.digital_output_state["activate_inject"] = False
        _logger.info(f"Cal Box flush")
        self._send_state_to_device()

    def inject(self):
        """Inject radon from source"""
        if self.digital_output_state["disable_internal_blower"] == True:
            _logger.warning(
                "Switching directly from background to inject: background may have been terminated early."
            )
        self.digital_output_state["activate_pump"] = True
        self.digital_output_state["activate_inject"] = True
        self.digital_output_state["activate_cutoff_valve"] = False
        self.digital_output_state["disable_stack_blower"] = False
        self.digital_output_state["disable_external_blower"] = False
        self.digital_output_state["disable_internal_blower"] = False
        _logger.info(f"Cal Box inject")
        self._send_state_to_device()

    def reset_flush(self):
        """Stop source-flush pump"""
        self.digital_output_state["activate_pump"] = False
        self.digital_output_state["activate_inject"] = False
        _logger.info(f"Cal Box flush stopped")
        self._send_state_to_device()

    def start_background(self):
        """Put detector in background mode"""
        if self.digital_output_state["activate_inject"] == True:
            _logger.warning(
                "Switching directly from inject to background: a surprisingly high background is likely."
            )
        self.digital_output_state["activate_inject"] = False
        self.digital_output_state["activate_cutoff_valve"] = True
        self.digital_output_state["disable_stack_blower"] = True
        self.digital_output_state["disable_external_blower"] = True
        self.digital_output_state["disable_internal_blower"] = True
        _logger.info(f"Cal Box entered background mode")
        self._send_state_to_device()

    def reset_background(self):
        """Cancel a running background (but leave source flushing if it already is running)
        """
        self.digital_output_state["activate_cutoff_valve"] = False
        self.digital_output_state["disable_stack_blower"] = False
        self.digital_output_state["disable_external_blower"] = False
        self.digital_output_state["disable_internal_blower"] = False
        _logger.info(f"Cal Box entered background mode")
        self._send_state_to_device()

    def reset_calibration(self):
        """Cancel a running background (but leave background-related 
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
            voltages = self.lj.analogue_states
            for k in self.analogue_input_channel:
                channels_dict[k] = voltages[self.analogue_input_channel[k]]
        return channels_dict

    def _send_state_to_device(self):
        if not self.no_hardware_mode:
            settings = []
            for k, state in self.digital_output_state.items():
                channel = self.digital_output_channel[k]
                self.lj.set_dio(channel, state)
                settings.append((channel, state))
            _logger.debug(
                f"Labjack digital output ports set: {self.digital_output_state.items()}"
            )
        else:
            _logger.debug("Labjack interface running in no-hardware mode.")

    @property
    def status(self):
        """generate a human-readable status message based on DIO flags"""
        flags = [
            self.digital_output_state["activate_pump"],
            self.digital_output_state["activate_inject"],
            self.digital_output_state["activate_cutoff_valve"],
            self.digital_output_state["disable_stack_blower"],
            self.digital_output_state["disable_external_blower"],
            self.digital_output_state["disable_internal_blower"],
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
        status["digital out"].update(self.digital_output_state)
        status["analogue in"].update(self.analogue_states)
        status["serial"] = self.serial_number
        return status


#
# .... utility functions
#


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

    TODO: return types differ between windows and linux versions FIXME
    """
    dev = u12.U12()
    try:
        # this is implemented by labjack on windows but not linux/mac
        # returns {"serialnumList": serialnumList, "localIDList":localIDList, "numberFound":numberFound.value}
        info = dev.listAll()
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

    def setup_logging(loglevel, logfile=None):
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

    setup_logging(logging.DEBUG)

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