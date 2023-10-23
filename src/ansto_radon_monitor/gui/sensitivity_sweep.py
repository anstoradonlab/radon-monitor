import copy
import datetime
import math
import time

import numpy as np
import pyqtgraph as pg
from plotutils import data_to_columns, get_pen, groupby_series
from PyQt5 import QtCore, QtWidgets
from ui_sensitivity_sweep import Ui_SensitivitySweepForm


class SensitivitySweepForm(QtWidgets.QWidget, Ui_SensitivitySweepForm):
    def __init__(self, mainwindow, *args, **kwargs):
        super(SensitivitySweepForm, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self._win = pg.GraphicsLayoutWidget(show=True, title="Sensitivity Sweep")
        self._p1 = self._win.addPlot(
            row=0, col=0, axisItems={"bottom": pg.DateAxisItem()}
        )
        self._p1.setLabel("left", "PMT Voltage", units="V")
        self._p2 = self._win.addPlot(row=1, col=0)
        self._p2.setLabel("left", "LLD", units="cps")
        self._p2.setLabel("bottom", "PMT Voltage", units="V")
        self._s1 = []
        self._s2 = []
        self.mainVerticalLayout.addWidget(self._win)

        self._sweep_is_running = False
        self._all_detectors = [itm.name for itm in mainwindow.config.detectors]
        self.comboBox.addItems(self._all_detectors)
        self._detector_name = self._all_detectors[0]

        self.connect_signals(mainwindow)

        # p = win.addPlot(row=idx, col=0, axisItems={"bottom": pg.DateAxisItem()})
        # p.setLabel("left", yvar, units="TODO")
        # s = p.plot(x, y, pen=self.get_pen(series_idx), name=label)

    def connect_signals(self, mainwindow):
        self.startButton.clicked.connect(self.onStart)
        self.stopButton.clicked.connect(self.onStop)
        self.comboBox.currentIndexChanged.connect(self.onDetectorChanged)
        mainwindow.data_update.connect(self.onData)

    def onStart(self):
        self.hvSweepGroupBox.setEnabled(False)
        self.statusGroupBox.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.startButton.setEnabled(False)

        self._sweep_is_running = True

        self.v0 = self.hvLowSpinBox.value()
        self.v1 = self.hvHighSpinBox.value()
        self.vstep = self.hvStepSpinBox.value()
        self.sec = self.hvSecSpinBox.value()
        self.npoints = int(self.sec / 10)
        self.v = self.v0

        self._samples_at_voltage = {self.v: 0}
        self.timeseries_data = []
        self.sweep_data = []

        self.hvTargetLabel.setText(f"{self.v0} V")
        self.hvMeasuredLabel.setText("--- V")

    def onStop(self):
        self.hvSweepGroupBox.setEnabled(True)
        self.statusGroupBox.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.startButton.setEnabled(True)
        self._sweep_is_running = False

    def onDetectorChanged(self):
        self._detector_name = self.comboBox.currentText()

    def onData(self, table_name, row):
        if not self._sweep_is_running:
            return
        if not table_name == "RTV":
            return
        if not row["DetectorName"] == self._detector_name:
            return
        row = copy.deepcopy(row)
        row["HV_nominal"] = np.NaN
        noiseOk = True
        if self.noiseCheckBox.isEnabled():
            # Check that there isn't any noise on this measurement
            try:
                # on the RTV table, ULD is just called "ULD" (not ULD_Tot)
                if row["ULD"] > 0:
                    noiseOk=False
            except:
                # TODO: log this error somehow?
                noiseOk=True

        if noiseOk:
            self.timeseries_data.append(row)

        target = self.v
        self.hvTargetLabel.setText(f"{target} V")

        # handle multipe HV columnms (looking at you, Cape Grim detector)
        hv_cols = sorted(
            [
                itm
                for itm in row.keys()
                if itm.startswith("HV") and not itm.endswith("nominal")
            ]
        )
        hv_label = " ".join([str(row[k]) for k in hv_cols])
        self.hvMeasuredLabel.setText(f"{hv_label} V")

        tolerance = 5

        hv_ok = True
        for k in hv_cols:
            if abs(row[k] - target) > tolerance:
                hv_ok = False

        if not hv_ok:
            self.instructionLabel.setText(
                "Set PMT voltage (HV supply) to target value..."
            )
        elif noiseOk:
            row["HV_nominal"] = target
            n = self._samples_at_voltage[target]
            n += 1
            self._samples_at_voltage[target] = n
            self.progressBar.setValue(float(100.0 * n / self.npoints))
            self.sweep_data.append(row)
            self.instructionLabel.setText("")
            self.update_plot()

            if n >= self.npoints:
                # check - is this the final point
                if (self.v + self.vstep) > self.v1:
                    self.finish_sweep()
                    return
                # go to the next voltage
                self.v += self.vstep
                self._samples_at_voltage[self.v] = 0
        else:
            # We're at the right HV setting, but noise was detected on the measurement
            pass

    def update_plot(self):

        # Timeseries plot (taking the simple route - remove all lines and re-add them)
        while len(self._s1) > 0:
            s = self._s1.pop()
            self._p1.removeItem(s)
        datac = data_to_columns(self.timeseries_data)
        x = np.array([itm.timestamp() + time.timezone for itm in datac["Datetime"]])
        idx = 0
        for k in datac.keys():
            if k.startswith("HV") and not k.endswith("nominal"):
                y = datac[k]
                self._s1.append(self._p1.plot(x=x, y=y, pen=get_pen(idx), name=k))
                idx += 1

        # HV vs counts
        while len(self._s2) > 0:
            s = self._s2.pop()
            self._p2.removeItem(s)

        hv_groups = list(set([itm["HV_nominal"] for itm in self.sweep_data]))
        hv_names = [
            itm
            for itm in self.sweep_data[0].keys()
            if itm.startswith("HV") and not itm.endswith("nominal")
        ]
        datac = data_to_columns(self.sweep_data)
        for ii, hv_name in enumerate(hv_names):
            lld_name = hv_name.replace("HV", "LLD")
            pen = get_pen(ii)
            x = datac[hv_name]
            y = datac[lld_name] / 10.0
            self._s2.append(self._p2.plot(x=x, y=y, pen=None, symbol="x", name=k))
            # sum up counts and average HV
            grouped_data = groupby_series(
                datac[hv_name], datac[lld_name], datac["HV_nominal"]
            )
            xplt = []
            yplt = []
            sigmaplt = []
            for xii, yii, labelii in grouped_data:
                x = xii.mean()
                n = len(xii)
                y = yii.mean() / 10.0  # counts per second
                sigma = np.sqrt(yii.sum()) / yii.sum() * y
                xplt.append(x)
                yplt.append(y)
                sigmaplt.append(sigma)
            xplt = np.array(xplt)
            yplt = np.array(yplt)
            sigmaplt = np.array(sigmaplt)
            errorbar = pg.ErrorBarItem(
                x=xplt,
                y=yplt,
                top=sigmaplt,
                bottom=sigmaplt,
                pen=pen,
                beam=1.0,
                name=lld_name + "_averaged",
            )
            self._s2.append(errorbar)
            self._p2.addItem(errorbar)
            s = self._p2.plot(x=xplt, y=yplt, pen=None, symbol="o", name=lld_name)
            self._s2.append(s)

    def finish_sweep(self):
        self.progressBar.setValue(0.0)
        self.onStop()

    def hideEvent(self, event):
        if self._sweep_is_running:
            self.onStop()
