import datetime
import logging
import math
import time

from cal_bg_start_time_widget import CalBgStartWidget
from PyQt5 import QtCore, QtWidgets
from ui_c_and_b import Ui_CAndBForm

_logger = logging.getLogger(__name__)


def t_into_utc(t):
    """converts a datetime (t) without any timezone info into
    the same t but identified as utc"""
    t = datetime.datetime(*t.timetuple()[:6], tzinfo=datetime.timezone.utc)
    return t


# note: special handling for the case where this dialog appears
# before the controller is set up (or when it is turned off)
## - using the 'schedule_pending' flag
class CAndBForm(QtWidgets.QWidget, Ui_CAndBForm):
    def __init__(self, mainwindow, *args, **kwargs):
        super(CAndBForm, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.mainwindow = mainwindow
        self.schedule_pending = False
        self._controls_to_disable_in_scheduled_mode = [
            self.operationTypeComboBox,
            self.startLaterCheckBox,
            self.startStopPushButton,
            self.cal_bg_start_times_layout,
            self.calibrationIntervalSpinBox,
            self.backgroundIntervalSpinBox,
            self.flushSpinBox,
            self.injectSpinBox,
            self.backgroundSpinBox,
        ]
        self._controls_to_disable_during_onceoff = [
            self.operationTypeComboBox,
            self.startLaterCheckBox,
            self.calbgDateTimeEdit,
        ]
        self._finalise_ui()
        self.connect_signals()
        try:
            self.restore_state_from_qsettings()
        except Exception as e:
            import traceback

            bt = traceback.format_exc()
            _logger.error(
                f"Unable to restore calibration/background state from QSettings.  Check cal/background configuration and restart. {bt}"
            )
        self.update_local_times()

    def _finalise_ui(self):
        """Finish setting up the UI

        * for each detector, create a cal/bg start time widget
        """
        self._generate_cal_bg_start_time_widgets()
        self._setup_calibration_options()

    def _generate_cal_bg_start_time_widgets(self):
        """
        For each detector in the configuration, create a cal/bg
        start time widget
        """
        config = self.mainwindow.config
        if config is None:
            return
        container = self.cal_bg_start_times_layout
        while len(container) > 0:
            container.removeWidget(container.children[0])
        self._start_time_widgets = []
        for ii, detector_config in enumerate(config.detectors):
            widget = CalBgStartWidget(
                sequence_number=ii + 1, detector_name=detector_config.name
            )
            container.addWidget(widget)
            self._start_time_widgets.append(widget)

    def _setup_calibration_options(self):
        """Populate the options in the combobox"""
        combobox = self.operationTypeComboBox
        combobox.clear()
        config = self.mainwindow.config
        if config is None:
            return
        num_detectors = len(self.mainwindow.config.detectors)
        operations = []
        for ii in range(num_detectors):
            for calbg in ("Calibrate", "Background"):
                s = f"{calbg} detector {ii+1}"
                operations.append(s)

        combobox.addItems(operations)

    def _read_gui_state(self):
        """
        Read data from GUI into a dict
        """
        # TODO: write this and use it instead of reading from each widget
        #       individually!
        background_interval_days = int(self.backgroundIntervalSpinBox.value())
        bg_interval = datetime.timedelta(days=background_interval_days)
        cal_interval_days = int(self.calibrationIntervalSpinBox.value())
        cal_interval = datetime.timedelta(days=cal_interval_days)

    def connect_signals(self):
        self.enableScheduleButton.clicked.connect(self.on_enable_schedule_clicked)
        # once-off calibration/bg time
        self.calbgDateTimeEdit.dateTimeChanged.connect(self.update_local_times)
        # disable calendar edit if the checkbox is disabled
        self.startLaterCheckBox.toggled.connect(self.calbgDateTimeEdit.setEnabled)
        self.startStopPushButton.clicked.connect(self.onStartStop)
        self.calibrationIntervalSpinBox.valueChanged.connect(
            self.on_cal_interval_changed
        )

        # TODO: consider using a single timer in mainwindow
        self.redraw_timer = QtCore.QTimer()
        self.redraw_timer.setInterval(1000)
        self.redraw_timer.timeout.connect(self.update_displays)
        self.redraw_timer.start()

    def on_cal_interval_changed(self, s):
        """Keep the background interval set to a constant multiple of the cal interval"""
        background_interval_days = int(self.backgroundIntervalSpinBox.value())
        cal_interval_days = int(self.calibrationIntervalSpinBox.value())

        if cal_interval_days == 0:
            cal_interval_days = 1
        # round-off to multiple of cal_interval_days
        v = int(round(background_interval_days / cal_interval_days)) * cal_interval_days
        self.backgroundIntervalSpinBox.setSingleStep(1)
        self.backgroundIntervalSpinBox.setValue(v)
        self.backgroundIntervalSpinBox.setSingleStep(cal_interval_days)

    def onStartStop(self):
        # read some state from the gui
        if self.startLaterCheckBox.isChecked():
            start_time = (
                self.calbgDateTimeEdit.dateTime()
                .toPyDateTime()
                .replace(tzinfo=datetime.timezone.utc)
            )
        else:
            start_time = None
        flush_duration_sec = self.flushSpinBox.value() * 3600
        inject_duration_sec = self.injectSpinBox.value() * 3600
        background_duration_sec = self.backgroundSpinBox.value() * 3600.0
        flag_start = self.startStopPushButton.isChecked()
        operation_str = self.operationTypeComboBox.currentText()
        if len(operation_str) == 0:
            # nothing selected yet
            _logger.info("No operation selected")
            return
        # operation_str is a string like "Calibrate detector 1" or
        # "Background detector 2"
        detector_idx = int(operation_str.split()[-1]) - 1
        op = operation_str.split()[0].lower()

        if flag_start:
            for itm in self._controls_to_disable_during_onceoff:
                itm.setEnabled(False)
            self.startStopPushButton.setText("Stop")
            if op == "calibrate":
                self.mainwindow.instrument_controller.run_calibration(
                    start_time=start_time,
                    flush_duration=flush_duration_sec,
                    inject_duration=inject_duration_sec,
                    detector_idx=detector_idx,
                )
            elif op == "background":
                self.mainwindow.instrument_controller.run_background(
                    start_time=start_time,
                    duration=background_duration_sec,
                    detector_idx=detector_idx,
                )
            else:
                _logger.error(f"Programming error - unexpected value for op: {op}")

        else:
            if op == "background":
                self.mainwindow.instrument_controller.stop_background()
            elif op == "calibrate":
                self.mainwindow.instrument_controller.stop_calibration()
            else:
                _logger.error(f"Programming error - unexpected value for op: {op}")
                self.mainwindow.instrument_controller.stop_background()
                self.mainwindow.instrument_controller.stop_calibration()
            for itm in self._controls_to_disable_during_onceoff:
                itm.setEnabled(True)
            # special case - enabled only if option box is checked
            self.calbgDateTimeEdit.setEnabled(self.startLaterCheckBox.isChecked())
            self.startStopPushButton.setText("Start")

        self.update_main_display()

    def update_local_times(self):
        t0_single = self.calbgDateTimeEdit.dateTime().toPyDateTime()
        tstr = str(t_into_utc(t0_single).astimezone())
        self.calbgLocalTimeLabel.setText(tstr)

    def on_enable_schedule_clicked(self, s):

        ic = self.mainwindow.instrument_controller

        if s:
            msg = "Scheduled calibration and backgrounds are active"
            # durations are in seconds
            background_duration = self.backgroundSpinBox.value() * 3600.0
            inject_duration = self.injectSpinBox.value() * 3600.0
            flush_duration = self.flushSpinBox.value() * 3600.0

            bg_times = [itm.bg_start_time for itm in self._start_time_widgets]
            cal_times = [itm.cal_start_time for itm in self._start_time_widgets]
            background_interval_days = int(self.backgroundIntervalSpinBox.value())
            background_interval = datetime.timedelta(days=background_interval_days)
            cal_interval_days = int(self.calibrationIntervalSpinBox.value())
            cal_interval = datetime.timedelta(days=cal_interval_days)

            if ic is not None:
                for ii, (t0_background, t0_cal) in enumerate(zip(bg_times, cal_times)):
                    if cal_interval_days > 0:
                        ic.schedule_recurring_calibration(
                            flush_duration,
                            inject_duration,
                            t0_cal,
                            cal_interval,
                            detector_idx=ii,
                        )
                    if background_interval_days > 0:
                        ic.schedule_recurring_background(
                            background_duration,
                            t0_background,
                            background_interval,
                            detector_idx=ii,
                        )
                self.schedule_pending = False
            else:
                self.schedule_pending = True
            button_msg = "Disable Schedule"
        else:
            msg = ""
            button_msg = "Enable Schedule"
            self.schedule_pending = False
            if ic is not None:
                ic.stop_calibration()
                ic.stop_background()
        for itm in self._controls_to_disable_in_scheduled_mode:
            itm.setEnabled(not s)
        # disabling the parent layout doesn't seem to disable the
        # start time widgets
        for itm in self._start_time_widgets:
            itm.setEnabled(not s)
        self.scheduleEngagedLabel.setText(msg)
        self.enableScheduleButton.setText(button_msg)
        self.save_state_to_qsettings()

    def schedule_engaged(self):
        return self.enableScheduleButton.isChecked()

    def update_main_display(self):
        """tells the main Gui to update"""
        # TODO: there might be a simpler way to do this,
        #  'schedule next event loop' or similar
        t = QtCore.QTimer(self)
        t.setInterval(100)
        t.setSingleShot(True)
        t.timeout.connect(self.mainwindow.update_displays)
        t.start()

    def update_displays(self):
        # update the calibration time widgets
        # next 30 min interval
        next30min = datetime.datetime.fromtimestamp(
            math.ceil(time.time() / 60 / 30) * 60 * 30
        )
        self.calbgDateTimeEdit.setMinimumDateTime(next30min)

        # A period check that a cal or bg is running, if the start button is checked
        if self.startStopPushButton.isChecked():
            ic = self.mainwindow.instrument_controller
            reset_onceoff_controls = (ic is None) or (
                not ic.cal_running and not ic.bg_running
            )
            if reset_onceoff_controls:
                self.startStopPushButton.setChecked(False)
                for itm in self._controls_to_disable_during_onceoff:
                    itm.setEnabled(True)
                # special case - enabled only if option box is checked
                self.calbgDateTimeEdit.setEnabled(self.startLaterCheckBox.isChecked())
                self.startStopPushButton.setText("Start")

        # A periodic check that the
        # schedule is correctly engaged, if the button has been
        # engaged.
        # --- this is the situation where the schedule is engaged,
        # --- but the instrument controller was not ready
        if self.schedule_pending:
            self.on_enable_schedule_clicked(True)
        # --- this is the situation where the instrument controller
        # --- was stopped and restarted, and the schedule needs to be
        # --- retransmitted after the restart
        ic = self.mainwindow.instrument_controller
        if (
            self.schedule_engaged()
            and ic is not None
            and not ic.cal_and_bg_is_scheduled()
        ):
            self.on_enable_schedule_clicked(True)

    def onCalibrate(self, s=None):
        if self.startLaterCheckBox.isChecked():
            start_time = (
                self.calbgDateTimeEdit.dateTime()
                .toPyDateTime()
                .replace(tzinfo=datetime.timezone.utc)
            )
        else:
            start_time = None
        flush_duration_sec = self.flushSpinBox.value() * 3600
        inject_duration_sec = self.injectSpinBox.value() * 3600
        self.mainwindow.instrument_controller.run_calibration(
            start_time=start_time,
            flush_duration=flush_duration_sec,
            inject_duration=inject_duration_sec,
        )
        self.update_main_display()

    def onStopCal(self, s=None):
        self.mainwindow.instrument_controller.stop_calibration()
        # TODO: re-schedule calibrations if enabled
        self.update_main_display()

    def onBackground(self, s=None):
        if self.startLaterCheckBox.isChecked():
            start_time = (
                self.calbgDateTimeEdit.dateTime()
                .toPyDateTime()
                .replace(tzinfo=datetime.timezone.utc)
            )
        else:
            start_time = None
        duration_sec = self.backgroundSpinBox.value() * 3600
        self.mainwindow.instrument_controller.run_background(
            start_time=start_time, duration=duration_sec
        )
        self.update_main_display()

    def onStopBg(self, s):
        self.mainwindow.instrument_controller.stop_background()
        self.update_main_display()

    def save_state_to_qsettings(self):
        qs = self.mainwindow.qsettings
        background_duration = self.backgroundSpinBox.value()
        qs.setValue("background_duration", background_duration)
        inject_duration = self.injectSpinBox.value()
        qs.setValue("inject_duration", inject_duration)
        flush_duration = self.flushSpinBox.value()
        qs.setValue("flush_duration", flush_duration)

        bg_times = [itm.bg_start_time for itm in self._start_time_widgets]
        qs.setValue("t0_background", bg_times)
        cal_times = [itm.cal_start_time for itm in self._start_time_widgets]
        qs.setValue("t0_cal", cal_times)

        background_interval_days = int(self.backgroundIntervalSpinBox.value())
        qs.setValue("background_interval", background_interval_days*3600*24)
        cal_interval_days = int(self.calibrationIntervalSpinBox.value())
        qs.setValue("cal_interval", cal_interval_days*3600*24)

        # schedule enabled/disabled
        qs.setValue("schedule_enabled", self.enableScheduleButton.isChecked())

    def restore_state_from_qsettings(self):
        qs = self.mainwindow.qsettings
        for k, w in zip(
            ("background_duration", "inject_duration", "flush_duration"),
            (self.backgroundSpinBox, self.injectSpinBox, self.flushSpinBox),
        ):
            v = qs.value(k)
            if v is not None:
                w.setValue(int(v))
        
        try:
            background_interval = float(qs.value("background_interval"))
            if background_interval is not None:
                days = int(round(background_interval / 3600.0 / 24.0))
                self.backgroundIntervalSpinBox.setValue(days)
            cal_interval = float(qs.value("cal_interval"))
            if cal_interval is not None:
                days = int(round(cal_interval / 3600.0 / 24.0))
                self.calibrationIntervalSpinBox.setValue(days)
        except Exception as ex:
            _logger.error(
                f"Unable to restore background or calibration interval from QSettings."
            )

        bg_times = qs.value("t0_background")
        # should be an array of datetimes, but the array length might be
        # wrong or it might be a single value left over from a previous
        # version of our software
        if type(bg_times) == type([]):
            for ii, t in enumerate(bg_times):
                try:
                    self._start_time_widgets[ii].bg_start_time = t
                except Exception as e:
                    _logger.error(
                        f"Unable to read background start time from QSettings.  Detector {ii+1}, bg_times: {bg_times}"
                    )
        # repeat for cal times
        cal_times = qs.value("t0_cal")
        if type(cal_times) == type([]):
            for ii, t in enumerate(cal_times):
                try:
                    self._start_time_widgets[ii].cal_start_time = t
                except Exception as e:
                    _logger.error(
                        f"Unable to read background start time from QSettings.  Detector {ii+1}, bg_times: {bg_times}"
                    )
        schedule_state = qs.value("schedule_enabled")
        if schedule_state is not None:
            # instead of using self.enableScheduleButton.setChecked(schedule_state)
            # we 'click' the button so that it emits events
            schedule_state = schedule_state.lower() == "true"
            btn_state = self.enableScheduleButton.isChecked()
            if not btn_state == schedule_state:
                self.enableScheduleButton.click()

    def hideEvent(self, event):
        self.save_state_to_qsettings()
        super(CAndBForm, self).hideEvent(event)

    def __del__(self):
        self.redraw_timer.disconnect()
        self.redraw_timer.deleteLater()
