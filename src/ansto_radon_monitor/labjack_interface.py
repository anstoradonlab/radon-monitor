import logging
import math

import u12

_logger = logging.getLogger(__name__)

# reference for Labjack interface:
# 


class LabjackWrapper():
    """Wrapper for the labjack interface.

    Purpose is to provide a specialized version of the interface, which only includes
    the functions needed for our calibration system.

    Only DIO ports 0-5 are used in our setup.

    """
    def __init__(self, labjack_id=-1):
        self.device = u12.U12(id=labjack_id, debug=False)
        self.max_channel = 5
        self.reset_dio()
    
    def reset_dio(self):
        """Sets output to zero on all channels while also configuring all DIO channels as output"""
        d = self.device
        for ii in range(self.max_channel+1):
            ret = d.eDigitalOut(ii, 0)

    def set_dio(self, channel, state):
        """Set one DIO channel to 1 or 0"""
        
        d = self.device
        ret =  d.eDigitalOut(channel, state)
        # TODO: raise an exception instead (may have lost connection to labjack)
        assert(ret['idnum'] == d.id)
        
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
            values.append(a_in['voltage'])
            assert(a_in['idnum'] == d.id)
        
        return values


class CalBoxLabjack():
    """Hardware interface for the labjack inside our Cal Box.
    """
    def __init__(self, labjack_id=-1):
        """Interface for the labjack, as it is installed in our pumped Cal Box

        Parameters
        ----------
        labjack_id : int, optional
            ID number of the labjack to connect to, by default -1
            Special values:
                * `-1`: connect to whichever labjack we can find
                * `None`: don't connect to a labjack, but run anyway (this is 
                  for testing without access to a labjack)
        """
        self.no_hardware_mode = True
        if labjack_id is not None:
            self.lj = LabjackWrapper(labjack_id)
            self.no_hardware_mode = False

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
        self.digital_output_state["activate_pump"] = False
        self.digital_output_state["activate_inject"] = False
        self.digital_output_state["activate_cutoff_valve"] = True
        self.digital_output_state["disable_stack_blower"] = True
        self.digital_output_state["disable_external_blower"] = True
        self.digital_output_state["disable_internal_blower"] = True
        _logger.info(f"Cal Box entered background mode")
        self._send_state_to_device()

    def reset_all(self):
        """return to idle state"""
        for k, v in self.digital_output_state.items():
            self.digital_output_state[k] = False
        _logger.info(f"Cal Box reset")
        self._send_state_to_device()

    @property
    def analogue_states(self):
        if self.no_hardware_mode:
            return [math.nan, math.nan]
        else:
            return self.lj.analogue_states


    def _send_state_to_device(self):
        if not self.no_hardware_mode:
            settings = []
            for k,state in self.digital_output_state.items():
                channel = self.digital_output_channel[k]
                self.lj.set_dio(channel, state)
                settings.append((channel,state))
            _logger.debug(f"Labjack digital output ports set: {self.digital_output_state.items()}")
        else:
            _logger.debug("Labjack interface running in no-hardware mode.")


if __name__ == "__main__":
    def setup_logging(loglevel, logfile=None):
        """Setup basic logging

        Args:
            loglevel (int): minimum loglevel for emitting messages
        """
        # logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
        logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
        logging.basicConfig(
            level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
        )

    import sys
    setup_logging(logging.DEBUG)

    for ljid in [-1, None]:
        print(f'Running with labjack ID {ljid}')
        lj = CalBoxLabjack(ljid)
        lj.reset_all()

        lj.flush()
        lj.reset_flush()
        lj.inject()
        lj.reset_all()

        lj.start_background()
        lj.reset_all()

        print(f'Analogue channel voltages: {lj.analogue_states}')
