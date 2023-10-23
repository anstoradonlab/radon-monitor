import collections
import copy
import datetime
import logging
import math
import os
import pprint
import sys
import threading
import time
from typing import Dict, List, Optional, Union

import numpy as np
import pyqtgraph as pg
import sip
from ansto_radon_monitor.configuration import (Configuration,
                                               config_from_inifile)
from ansto_radon_monitor.main import setup_logging
from ansto_radon_monitor.main_controller import MainController, initialize
from c_and_b import CAndBForm
from data_plotter import DataPlotter
from data_view import DataViewForm
from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5 import QtCore, QtGui, QtWidgets, uic
# from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QSettings, Qt, QTimer
from sensitivity_sweep import SensitivitySweepForm
from system_information import SystemInformationForm
from timeout_dialog import TimeoutDialog
from ui_mainwindow import Ui_MainWindow

# import pandas as pd
# import tabulate


# data model for linking table view with instrument data
# here's an intro to this approach:
# https://www.learnpyqt.com/tutorials/qtableview-modelviews-numpy-pandas/
# more docs:
# https://doc.qt.io/archives/qtforpython-5.12/overviews/model-view-programming.html#model-view-programming
# https://doc.qt.io/qtforpython/PySide6/QtCore/QAbstractTableModel.html

# useful sample code:
# https://stackoverflow.com/questions/22791760/pyqt-adding-rows-to-qtableview-using-qabstracttablemodel


_logger = logging.getLogger(__name__)

# small class for our 'log message' signal to live in
class QTextEditLogger(logging.Handler, QtCore.QObject):
    appendPlainText = QtCore.pyqtSignal(str)

    def __init__(self, widget):
        super().__init__()
        QtCore.QObject.__init__(self)
        self.widget = widget
        self.widget.setReadOnly(True)
        self.appendPlainText.connect(self.widget.appendPlainText)

    def emit(self, record):
        msg = self.format(record)
        self.appendPlainText.emit(msg)


class QTextEditLogger_non_threadsafe(logging.Handler):
    def __init__(self, widget):
        """widget - a QPlainTextEdit to send log messages to"""
        super().__init__()
        self.widget = widget
        self.widget.setReadOnly(True)

    def emit(self, record):
        assert threading.current_thread() is threading.main_thread()
        msg = self.format(record)
        self.widget.appendPlainText(msg)


# Utility class for preventing windows' sleep


class WindowsInhibitor:
    """Prevent OS sleep/hibernate in windows; code from:
    https://github.com/h3llrais3r/Deluge-PreventSuspendPlus/blob/master/preventsuspendplus/core.py
    API documentation:
    https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx"""

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

    def __init__(self):
        pass

    def inhibit():
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(
            WindowsInhibitor.ES_CONTINUOUS | WindowsInhibitor.ES_SYSTEM_REQUIRED
        )

    def uninhibit():
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(WindowsInhibitor.ES_CONTINUOUS)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    # a signal which gets emitted when new data arrives
    # arguments are table_name, data
    data_update = QtCore.pyqtSignal(str, object)

    def __init__(self, appctxt: ApplicationContext, *args, **kwargs):
        # fbs application context
        self.appctxt = appctxt
        super(MainWindow, self).__init__(*args, **kwargs)

        if os.name == "nt":
            WindowsInhibitor.inhibit()

        self.qsettings = QSettings("au.gov.ansto", appctxt.app.applicationName())
        _logger.debug(f"QSettings initialised at {self.qsettings.fileName()}")

        self.setupUi(self)
        # plot default settings
        pg.setConfigOption("antialias", True)

        # dark/light mode handling
        app = QtWidgets.QApplication.instance()
        self._default_app_style = app.style().objectName()
        self._default_palette = app.palette()

        ## QSettings value might be True, False or None
        self._use_dark_theme = self.qsettings.value("use_dark_theme") == "true"
        self.set_dark_theme(self._use_dark_theme)
        self.actionDarkMode.setChecked(self._use_dark_theme)

        self.instrument_controller: Optional[MainController] = None
        self.config: Optional[Configuration] = None
        self.configured_tables: List[str] = []

        # multi-panel plot window
        self.pgwin: Union[pg.GraphicsLayoutWidget, None] = None
        # data plotter object
        self.data_plotter = None
        # cache of data for multi-panel plot
        self.plot_data = None

        # Load the UI Page
        # uic.loadUi(appctxt.get_resource("main_window.ui"), baseinstance=self)

        self.maintenanceModeFrame.setVisible(False)
        self.alertFrame.setVisible(False)

        self.setup_statusbar()

        logTextBox = self.logArea
        guilogger = QTextEditLogger(logTextBox)
        logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
        guilogger.setFormatter(logging.Formatter(logformat))
        logging.getLogger().addHandler(guilogger)
        # Get log level from config file
        if self.config is not None:
            loglevel = self.config.loglevel
        else:
            loglevel = logging.INFO
        logging.getLogger().setLevel(loglevel)

        self.connect_signals()

        # muck around with splitter positions
        self.splitter.setSizes([500, 10])

        self.redraw_timer = QTimer()
        self.redraw_timer.setInterval(5000)
        self.redraw_timer.timeout.connect(self.update_displays)
        self.redraw_timer.start()

        self.cal_dialog = None
        self.sysinfo_dialog = None
        self.sensitivity_sweep_dialog = None

        geom = self.qsettings.value("geometry")
        winstate = self.qsettings.value("windowState")
        # if the qsettings value does not exist it is set to None
        if geom is None or winstate is None:
            pass
        else:
            try:
                self.restoreGeometry(geom)
                self.restoreState(winstate)
            except Exception as ex:
                _logger.error(f"Error restoring window state: {ex}")

        # Begin logging if we can find a configuration file
        if self.qsettings.contains("config_fname"):
            config_fname = self.qsettings.value("config_fname")
            # allow the user to interrupt startup
            td = TimeoutDialog(timeout=10, config_fname=config_fname, parent=self)
            if td.exec():
                self.begin_controlling(config_fname)

        # create dialog (but don't show it)
        self.create_calibration_dialog()

    def setup_statusbar(self):
        sb = self.statusbar
        lab = QtWidgets.QLabel("")
        self.statusbarlabel_right = lab
        sb.addPermanentWidget(lab)

        lab2 = QtWidgets.QLabel("Startup")
        sb.addWidget(lab2)
        self.statusbarlabel_left = lab2

    def set_dark_theme(self, dark_theme_on):
        app = QtWidgets.QApplication.instance()
        self.qsettings.setValue("use_dark_theme", dark_theme_on)
        if dark_theme_on:
            app.setPalette(dark_palette())
            pg.setConfigOption("background", (42, 42, 42))
            pg.setConfigOption("foreground", "w")
            # also, works best in 'fusion' style
            app.setStyle("Fusion")
        else:
            pg.setConfigOption("background", "w")
            pg.setConfigOption("foreground", "k")
            # app.setStyle(self._default_app_style)
            app.setStyle("Native")
            app.setPalette(self._default_palette)

    def set_maintenance_mode(self, mm_on=False):
        app = QtWidgets.QApplication.instance()
        self.qsettings.setValue("maintenance_mode_on", mm_on)
        self._maintenance_mode = mm_on
        self.maintenanceModeFrame.setVisible(mm_on)
        # in case this was called from elsewhere, sync the checkmark
        # in the menu item
        self.actionMaintence_Mode.setChecked(mm_on)
        if self.instrument_controller is not None:
            self.instrument_controller.maintenance_mode = mm_on

    def show_or_hide_calibration_alert(self):
        cal_active = False
        ic = self.instrument_controller
        if ic is not None:
            try:
                ic_status = ic.get_status()
                if "CalibrationUnitThread" in ic_status:
                    cal_unit_message = ic_status["CalibrationUnitThread"]["status"][
                        "message"
                    ].lower()
                    cal_active = not (
                        cal_unit_message == "normal operation"
                        or cal_unit_message == "no connection"
                    )
                else:
                    # if there is no calibration unit active, then there will be no message about it in the status
                    # but also 'cal_active' should always be false
                    cal_active = False
            except Exception as ex:
                import traceback

                msg = traceback.format_exc()
                _logger.error(msg)

        self.alertFrame.setVisible(cal_active)

    def set_status(self, message, happy=None):
        if happy is None:
            icon = ""
        elif happy:
            icon = "🙂"
        else:
            icon = "😬"
        self.statusbarlabel_left.setText(message)
        self.statusbarlabel_right.setText(icon)

    def show_data(self):
        if self.config is not None:
            data_dir = os.path.realpath(self.config.data_dir)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(data_dir))

    def sync_output(self):
        if self.instrument_controller is not None:
            self.instrument_controller.backup_now()

    def connect_signals(self):
        self.actionLoad_Configuration.triggered.connect(self.onLoadConfiguration)
        self.actionQuit.triggered.connect(self.close)
        self.actionShow_Data.triggered.connect(self.show_data)
        self.actionSync_Output.triggered.connect(self.sync_output)
        self.actionViewCalibration.triggered.connect(self.view_calibration_dialog)
        self.actionDarkMode.triggered.connect(self.set_dark_theme)
        self.actionMaintence_Mode.triggered.connect(self.set_maintenance_mode)
        self.exitMaintenancePushButton.clicked.connect(self.set_maintenance_mode)
        self.actionViewSystemInformation.triggered.connect(
            self.view_system_information_dialog
        )
        self.actionViewSensitivitySweep.triggered.connect(
            self.view_sensitivity_sweep_dialog
        )

    def onLoadConfiguration(self, s):
        # print(f"Load the configuration... {s}")
        config_fname, config_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open configuration",
            ".",
            "Configuration files (*.ini);;All files (*.*)",
        )
        if config_fname == "":
            # user pressed cancel, do nothing
            return

        # print(f"Loading from {config_fname}")
        self.qsettings.setValue("config_fname", config_fname)
        self.begin_controlling(config_fname)

    def create_calibration_dialog(self):
        # side note: this is quite a nice example of how to generate UI with code
        # using current idioms
        # https://doc.qt.io/qtforpython/tutorials/basictutorial/dialog.html
        w = CAndBForm(mainwindow=self)
        cal_dialog = QtWidgets.QDialog(parent=self)
        cal_dialog.setWindowTitle("Calibration and Background Control")
        layout = QtWidgets.QVBoxLayout(cal_dialog)
        layout.addWidget(w)
        self.cal_dialog = cal_dialog

    def view_calibration_dialog(self):
        if self.cal_dialog is None:
            self.create_calibration_dialog()
        self.cal_dialog.show()

    def close_calibration_dialog(self):
        """close calibration dialog and (if a cal is running) reset the calbox state"""
        if self.cal_dialog is not None:
            self.cal_dialog.close()
        self.cal_dialog = None

    def view_system_information_dialog(self):
        if self.sysinfo_dialog is not None:
            self.sysinfo_dialog.show()
        else:
            w = SystemInformationForm(mainwindow=self)
            sysinfo_dialog = QtWidgets.QDialog(parent=self)
            sysinfo_dialog.setWindowTitle("System Information")
            layout = QtWidgets.QVBoxLayout(sysinfo_dialog)
            layout.addWidget(w)
            sysinfo_dialog.show()
            self.sysinfo_dialog = sysinfo_dialog

    def view_sensitivity_sweep_dialog(self):
        if self.sensitivity_sweep_dialog is not None:
            self.sensitivity_sweep_dialog.show()
        else:
            w = SensitivitySweepForm(mainwindow=self)
            sensitivity_sweep_dialog = QtWidgets.QDialog(parent=self)
            sensitivity_sweep_dialog.setWindowTitle("Sensitivity Sweep")
            layout = QtWidgets.QVBoxLayout(sensitivity_sweep_dialog)
            layout.addWidget(w)
            sensitivity_sweep_dialog.show()
            self.sensitivity_sweep_dialog = sensitivity_sweep_dialog

    def update_plot_data(self, table_name):
        """Update the local cache of plot data

        Returns:
         - a flag,  True if the data has changed
         - the data (in a collections.deque)
        """
        k = table_name
        default_npoints = {"RTV": 600 * 24, "Results": 24 * 2 * 10}
        npoints = default_npoints.get(k, 1000)
        default_max_age = {
            "RTV": datetime.timedelta(days=1),
            "Results": datetime.timedelta(days=10),
        }
        max_age = default_max_age.get(k, datetime.timedelta(days=1))
        if self.plot_data is None:
            self.plot_data = {"buffer": {}, "t": {}}

        buffer = self.plot_data["buffer"].get(k, collections.deque(maxlen=npoints))
        told = self.plot_data["t"].get(k, None)
        if told is None:
            told = datetime.datetime.now(tz=datetime.timezone.utc) - max_age
        tnew, newdata = self.instrument_controller.get_rows(table_name, told)
        # don't consider the time of the update, just the database rowid (see LastRowToken)
        # which lets us handle multiple detectors & interruptions in data transfer from
        # one of them
        if tnew is not None:
            tnew.t = None
        data_has_changed = False
        if not tnew == told:
            self.plot_data["t"][k] = tnew
            for row in newdata:
                buffer.append(row)
                data_has_changed = True
                # emit data as a qtSignal
                # self.data_update.emit(table_name, row)
            # emit the most recent data from each detector
            most_recent = {}
            for row in newdata:
                most_recent[row["DetectorName"]] = row
            for row in most_recent.values():
                self.data_update.emit(table_name, row)

        self.plot_data["buffer"][k] = buffer
        return data_has_changed, buffer

    def draw_plots(self, data):
        if self.pgwin is not None:
            self.close_plots()
        self.pgwin = pg.GraphicsLayoutWidget()
        self.plotSplitter.addWidget(self.pgwin)
        self.plotSplitter.setSizes([200, 20])
        # the constructor also draws the initial plot
        self.data_plotter = DataPlotter(self.pgwin, data)

    def update_plots(self, table_name):
        # check that window is visible
        # TODO: this always seems to return True, even when the window
        # is hidden
        if self.pgwin is not None:
            pass
            # print("*** visible?:", self.pgwin.isVisible())
        if self.pgwin is not None and not self.pgwin.isVisible():
            # the widget isn't visible, so skip this update
            return

        update_needed, data = self.update_plot_data(table_name)
        if update_needed:
            if self.pgwin is None:
                self.draw_plots(data)
            else:
                self.data_plotter.update(data)

    def close_plots(self):
        if self.pgwin is not None:
            self.pgwin.close()
            # self.pgwin.destroyLater()
            self.pgwin = None

    def clear_plots(self):
        if self.pgwin is not None:
            self.data_plotter.clear()
        self.plot_data = None

    def begin_controlling(self, config_fname):

        # TODO: more of the gui needs to be shutdown/re-configured
        #  * calibration dialog
        #  * large plots

        # The calibration dialog needs to be closed to cancel an in-progress cal
        # but also because it needs to be re-generated with options which suit
        # the newly-loaded configuration file
        self.close_calibration_dialog()

        if self.instrument_controller is not None:
            self.instrument_controller.shutdown()
        # update times need to be reset
        self.update_times = {}
        # data display should be cleared
        self.reset_views()
        self.set_status("Connecting to instrument...", False)
        _logger.debug(f"Reading configuration from {config_fname}")
        try:
            config = config_from_inifile(config_fname)
        except Exception as ex:
            import traceback

            _logger.warning(
                f"Exception occured while trying to load configuration: {ex}, {traceback.format_exc()}"
            )
            self.set_status(f"Unable to load configuration: {config_fname}", False)
            return

        self.config = config

        setup_logging(config.loglevel, config.logfile)

        self.instrument_controller = initialize(config, mode="thread")

        # sync the gui's Maintenance mode state with the backend
        mm = self.instrument_controller.maintenance_mode
        self.actionMaintence_Mode.setChecked(mm)
        self.maintenanceModeFrame.setVisible(mm)

        # enable/disable the view->calibration menu item as appropriate
        self.actionViewCalibration.setEnabled(
            self.instrument_controller.has_calibration_unit
        )

    def closeEvent(self, event):
        # catch the close event
        if os.name == "nt":
            WindowsInhibitor.uninhibit()

        # TODO: don't shut down IC on Linux
        # print("shutting down instrument controller")
        if self.instrument_controller is not None:
            self.instrument_controller.shutdown()

        self.qsettings.setValue("geometry", self.saveGeometry())
        self.qsettings.setValue("windowState", self.saveState())

        event.accept()
        # abort exiting with "event.ignore()"

    def update_displays(self):
        # print('update display')
        ic = self.instrument_controller
        if not self.is_logging:
            self.set_status("Disconnected", False)
            self.hudTextBrowser.setHtml("")
            self.clear_plots()
            return
        self.update_plots("Results")
        self.update_plot_data("RTV")
        ic_status = ic.get_status()
        self.set_status(ic_status["summary"], None)
        # if the Calibration Unit is active then turn on a banner display
        self.show_or_hide_calibration_alert()
        tables = ic.list_data_tables()
        html = ic.html_current_measurement()
        self.hudTextBrowser.setHtml(html)
        num_detectors = len(self.config.detectors)
        hud_height = num_detectors * 160
        self.hudTextBrowser.setMinimumHeight(hud_height)

        if not set(self.configured_tables) == set(tables):
            # build data view UI
            tabwidget = self.tabWidget
            self.configured_tables = []
            # remove tabs which are not in the current set
            idx = 0
            while not tabwidget.tabText(idx) == "":
                txt = tabwidget.tabText(idx)
                if not txt in tables:
                    data_view = tabwidget.widget(idx)
                    tabwidget.removeTab(idx)
                    sip.delete(data_view)
                else:
                    self.configured_tables.append(txt)
                    idx += 1
            missing_tables = [
                itm for itm in tables if not itm in self.configured_tables
            ]

            for table_name in missing_tables:
                data_view = DataViewForm(self, table_name)
                tabwidget.addTab(data_view, table_name)
                self.configured_tables.append(table_name)

    def reset_views(self):
        """reset all widgets in the main window to (about) their initial state"""
        tabwidget = self.tabWidget
        # remove all tabs
        while len(tabwidget) > 0:
            widget = tabwidget.widget(0)
            tabwidget.removeTab(0)
            sip.delete(widget)
        self.configured_tables = []
        # for visual purposes
        lab = QtWidgets.QLabel("")
        tabwidget.addTab(lab, "Waiting for data")
        ## the plots on the right-hand side of main window
        self.clear_plots()

    @property
    def is_logging(self):
        return self.instrument_controller is not None

    def stop_logging(self):
        if self.is_logging:
            self.instrument_controller.shutdown()
            self.instrument_controller = None

    def start_logging(self):
        if not self.is_logging:
            if self.qsettings.contains("config_fname"):
                config_fname = self.qsettings.value("config_fname")
                self.begin_controlling(config_fname)
            else:
                # TODO: this method might not exist!
                self.actionLoad_Configuration.emit()


def dark_palette():
    """A dark color palette

    From https://github.com/Jorgen-VikingGod/Qt-Frameless-Window-DarkStyle/blob/master/DarkStyle.cpp


    Use like this:
    app = QtWidgets.QApplication.instance()
    app.setPalette(dark_palette())
    # also, works best in 'fusion' style
    app.setStyle("Fusion")
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QPalette

    darkPalette = QPalette()
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.WindowText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
    darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    darkPalette.setColor(QPalette.ToolTipBase, Qt.white)
    darkPalette.setColor(QPalette.ToolTipText, Qt.white)
    darkPalette.setColor(QPalette.Text, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ButtonText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.BrightText, Qt.red)
    darkPalette.setColor(QPalette.Link, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    darkPalette.setColor(QPalette.HighlightedText, Qt.white)
    darkPalette.setColor(
        QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127)
    )
    return darkPalette
