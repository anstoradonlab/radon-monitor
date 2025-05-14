import datetime
import logging
import sys
import time
import traceback
import typing

import numpy as np
import pyqtgraph as pg
from .plotutils import data_to_columns, get_pen, groupby_series
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
        self._plot_objects = []
        self._pen_idx_lookup = []
        # TODO: this will need to change if we decide to support more than just the Results table
        plot_yvar = [
            "ApproxRadon",
            "LLD_Tot",
            "ULD_Tot",
            "ExFlow_Tot",
            "ExFlow_Avg",
            "InFlow_Avg",
            "HV_Avg",
            "AirT_Avg",
        ]
        plot_row = [
            0,1,2,3,3,4,5,6
        ]
        self._units_dict = {
            "ApproxRadon": "Bq/m³",
            "LLD_Tot": "/30-min",
            "ULD_Tot": "/30-min",
            "ExFlow_Tot": "l/min",
            "ExFlow_Avg": "l/min",
            "InFlow_Avg": "m/s",
            "HV_Avg": "V",
            "AirT_Avg": "°C",
        }
        self._name_dict = {
            "ApproxRadon": "Rn",
            "LLD_Tot": "Counts",
            "ULD_Tot": "Noise",
            "ExFlow_Tot": "Ext. flow",
            "ExFlow_Avg": "Ext. flow",
            "InFlow_Avg": "Int. flow",
            "HV_Avg": "PMT",
            "AirT_Avg": "Air temp.",
        }

        N = max(plot_row) + 1
        win.resize(400, 100 * N)

        datac = data_to_columns(data)
        datac["Datetime"] = np.array(
            [itm.timestamp() + time.timezone for itm in datac["Datetime"]]
        )

        for idx, k in zip(plot_row, plot_yvar):
            if k in datac:
                self.plot(
                    win,
                    data=datac,
                    xvar="Datetime",
                    yvar=k,
                    huevar="DetectorName",
                    idx=idx,
                    Nplts=N,
                )
            else:
                # this is expected to be hit often, some detectors will use ExtFLow_Tot others _Avg, 
                # so usually we won't have both
                _logger.debug(f"Column {k} was not found in data.  Data has columns: {list(datac.keys())}")
        
        # set the width of the y-labels so that the axes align
        try:
            plots = [itm['plot'] for itm in self._plot_objects if 'plot' in itm]
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
        _logger.debug(f"Plotting {xvar} vs {yvar} styled by {huevar}")
        po = {}
        po["xvar"] = xvar
        po["yvar"] = yvar
        po["huevar"] = huevar
        po["fig_idx"] = idx
        try:
            x = data[xvar]
            # conversion into dtype=float converts None values into nan
            y = np.array(data[yvar], dtype=float)
            legend_data = data[huevar]
        except Exception as e:
            _logger.error(f"Encounted error while generating plot: {e}")
            return
        
        # does this axis already exist?  If so, we can just add the plots.
        p = None
        for itm in self._plot_objects:
            try:
                if itm["fig_idx"] == idx:
                    p = itm["plot"]
                    break
            except IndexError:
                # no "fig_idx" present in itm
                pass
        if p is None:
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
                legend_dict = {"fig_idx":"legend", "legend":legend}
                self._plot_objects.append(po)
        else:
            po["plot"] = p
            po["series"] = {}
        
        for (x, y, label) in groupby_series(x, y, legend_data):
            series_idx = label+"__"+yvar
            s = p.plot(x, y, pen=self.get_pen(series_idx), name=label)
            po["series"][series_idx] = s

        self._plot_objects.append(po)

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
        for po in self._plot_objects:
            idx = po["fig_idx"]
            if idx == "legend":
                continue
            x = po["xvar"]
            y = po["yvar"]
            hue = po["huevar"]
            x = datac[x]
            # conversion into dtype=float converts None values into nan
            y = np.array(datac[y], dtype=float)
            legend_data = datac[hue]

            for (x, y, label) in groupby_series(x, y, legend_data):
                series_idx = label+"__"+po["yvar"]
                try:
                    s = po["series"][series_idx]
                    # subtract time.timezone to get display in UTC
                    xfloat = [itm.timestamp() + time.timezone for itm in x]
                    s.setData(x=xfloat, y=y)
                except KeyError:
                    # update failed, plot needs to be regenerated
                    # this is normal behaviour if a new variable has been added to the database
                    # (likely to hit this on the first execution of a fresh installation)
                    _logger.debug(f"Error while updating plots: {traceback.format_exc()}")
                    flag_need_regenerate = True

        if flag_need_regenerate:
            # regenerate the entire plot
            self.win.clear()
            self.setup(self.win, data)

    def get_pen(self, series_idx):
        """
        Return a pen definition based on a series index.  Series index is expected
        to be in the form
        
            label__variablename

        for example

            BHURD__ExFlow_Tot
        """
        k = series_idx.split("__")[0]
        if not k in self._pen_idx_lookup:
            self._pen_idx_lookup.append(k)
        ii = self._pen_idx_lookup.index(k)
        return get_pen(ii)
