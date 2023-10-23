import datetime
import logging
import sys
import time
import typing

import numpy as np
import pyqtgraph as pg
from plotutils import data_to_columns, get_pen, groupby_series
from PyQt5 import QtCore, QtWidgets

_logger = logging.getLogger(__name__)


# PgPlot examples:
# python ...\env\lib\site-packages\pyqtgraph\examples\ExampleApp.py


class DataPlotter(object):
    def __init__(self, win: pg.GraphicsLayoutWidget, data: typing.List):
        self.setup(win, data)
        self.flag_setup_neeeded = False

    def setup(self, win: pg.GraphicsLayoutWidget, data):
        self.win: pg.GraphicsLayoutWidget = win
        # persistant storage of plot info needed for updates
        self._plot_objects = {}
        # TODO: this will need to change if we decide to support more than just the Results table
        plot_yvars = [
            "ApproxRadon",
            "LLD_Tot",
            "ULD_Tot",
            "ExFlow_Tot",
            "InFlow_Avg",
            "HV_Avg",
            "AirT_Avg",
        ]
        self._units_dict = {
            "ApproxRadon": "Bq/m³",
            "LLD_Tot": "/30-min",
            "ULD_Tot": "/30-min",
            "ExFlow_Tot": "l/min",
            "InFlow_Avg": "m/s",
            "HV_Avg": "V",
            "AirT_Avg": "°C",
        }
        self._name_dict = {
            "ApproxRadon": "Rn",
            "LLD_Tot": "Counts",
            "ULD_Tot": "Noise",
            "ExFlow_Tot": "Ext. flow",
            "InFlow_Avg": "Int. flow",
            "HV_Avg": "PMT",
            "AirT_Avg": "Air temp.",
        }

        N = len(plot_yvars)
        win.resize(400, 100 * N)

        datac = data_to_columns(data)
        datac["Datetime"] = np.array(
            [itm.timestamp() + time.timezone for itm in datac["Datetime"]]
        )

        for idx, k in enumerate(plot_yvars):
            self.plot(
                win,
                data=datac,
                xvar="Datetime",
                yvar=k,
                huevar="DetectorName",
                idx=idx,
                Nplts=N,
            )
        
        # set the width of the y-labels so that the axes align
        try:
            plots = [self._plot_objects[ii]['plot'] for ii in range(N)]
            widths = [p.getAxis('left').width() for p in plots]
            # the extra padding helps if the initial plot range is quite small
            maxwidth = max(widths) + 10
            for p in plots:
                p.getAxis('left').setWidth(int(maxwidth))
        except Exception as ex:
            import traceback
            traceback.print_exc()

        self.flag_setup_neeeded = False

    def plot(self, win: pg.GraphicsLayoutWidget, data, xvar, yvar, huevar, idx, Nplts):
        po = {}
        po["xvar"] = xvar
        po["yvar"] = yvar
        po["huevar"] = huevar
        po["idx"] = idx
        try:
            x = data[xvar]
            # conversion into dtype=float converts None values into nan
            y = np.array(data[yvar], dtype=float)
            legend_data = data[huevar]
        except Exception as e:
            _logger.error(f"Encounted error while generating plot: {e}")
            print(str(data.keys()))
            return
        p = win.addPlot(
            row=idx,
            col=0,
            axisItems={
                "bottom": pg.DateAxisItem(),
            },
        )
        if idx > 0:
            p_ref = self._plot_objects[0]['plot']
            p.setXLink(p_ref)
        labelStyle = {"font-size": "10pt"}
        p.setLabel(
            "left",
            self._name_dict.get(yvar, yvar),
            units=self._units_dict.get(yvar, "Unknown units"),
            **labelStyle,
        )
        # do not convert units from e.g. V to kV
        p.getAxis("left").enableAutoSIPrefix(False)
        po["plot"] = p
        po["series"] = {}
        if idx == Nplts - 1 and len(set(legend_data)) > 1:
            # add legend to the bottom plot, if there are more than one
            # detectors
            legend = p.addLegend(frame=False, rowCount=1, colCount=2)
            self._plot_objects["legend"] = legend

        for series_idx, (x, y, label) in enumerate(groupby_series(x, y, legend_data)):
            s = p.plot(x, y, pen=get_pen(series_idx), name=label)
            po["series"][series_idx] = s

        self._plot_objects[idx] = po

    def clear(self):
        self.win.clear()
        self.flag_setup_neeeded = True

    def update(self, data):
        if self.flag_setup_neeeded:
            # regenerate the entire plot
            self.win.clear()
            self.setup(self.win, data)
            return

        flag_need_regenerate = False
        datac = data_to_columns(data)
        for idx, po in self._plot_objects.items():
            if idx == "legend":
                continue
            x = po["xvar"]
            y = po["yvar"]
            hue = po["huevar"]
            idx = po["idx"]
            x = datac[x]
            # conversion into dtype=float converts None values into nan
            y = np.array(datac[y], dtype=float)
            legend_data = datac[hue]

            for series_idx, (x, y, label) in enumerate(
                groupby_series(x, y, legend_data)
            ):
                try:
                    s = po["series"][series_idx]
                    # subtract time.timezone to get display in UTC
                    xfloat = [itm.timestamp() + time.timezone for itm in x]
                    s.setData(x=xfloat, y=y)
                except KeyError:
                    # update failed, plot needs to be regenerated
                    flag_need_regenerate = True

        if flag_need_regenerate:
            # regenerate the entire plot
            self.win.clear()
            self.setup(self.win, data)
