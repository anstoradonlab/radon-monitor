import datetime
import logging
import math
import time
from typing import Dict

import numpy as np
import pyqtgraph as pg
from plotutils import groupby_series
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QSettings, Qt, QTimer
from pyqtgraph import PlotWidget
from ui_data_view import Ui_DataViewForm

_logger = logging.getLogger(__name__)


class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        if len(data) > 0:
            self._column_names = list(data[0])
        else:
            self._column_names = []

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # Get the raw value
            value = list(self._data[index.row()].values())[index.column()]

            # Perform per-type checks and render accordingly.
            if isinstance(value, datetime.datetime):
                # Render date and time
                return value.strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(value, float):
                # Render float to 2 dp
                return "%.2f" % value

            if isinstance(value, str):
                # Render strings just as-is
                return value

            # Default (anything not captured above: e.g. int)
            return str(value)

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first dict, and returns
        # the length (only works if all rows are an equal length)
        if len(self._data) > 0:
            ncols = len(self._data[0])
        else:
            ncols = 0
        return ncols

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._column_names[section])

            if orientation == Qt.Vertical:
                # use row number here
                return str(section)

    def update_data(self, new_data):
        if len(new_data) == 0 and len(self._data) == 0:
            # no-op
            return
        self.beginResetModel()
        self._data = new_data
        self._column_names = list(new_data[0])
        self.endResetModel()

    # def append_data(self, new_data):
    #    self.beginResetModel()
    #    self._data.extend(new_data)
    #    self.endResetModel()

    def append_data(self, new_data):

        N = len(self._data)
        Nnew = len(new_data)
        if Nnew == 0:
            return

        if N == 0:
            # can't trust existing column names - reset
            self.update_data(new_data)
            return

        if not (self._column_names) == list(new_data[0]):
            # new data looks different to old data - reset
            import traceback

            tb = "\n".join(traceback.format_stack())
            _logger.warning(
                f"Old vs new column names do not match.  Old: {self._column_names}, New: {list(new_data[0])}, backtrace:\n{tb}"
            )
            self.update_data(new_data)
            return

        if (
            "Datetime" in self._column_names
            and not self._data[-1]["Datetime"] <= new_data[0]["Datetime"]
        ):
            # print("new data breaks sorting, resetting model")
            # appending new data would make the model no longer sorted by date
            # (new data are sorted, and old data are sorted)
            data = []
            data.extend(self._data)
            data.extend(new_data)
            data.sort(key=lambda x: x["Datetime"])
            self.update_data(data)
            return

        # print(f"new data:{new_data}, length {N}, {N+len(new_data)-1}")
        self.beginInsertRows(QtCore.QModelIndex(), N, N + len(new_data) - 1)
        self._data.extend(new_data)
        self.endInsertRows()

        assert len(self._data) == N + Nnew

        # remove rows if maximum has been exceeded
        N_max = 8640  # TODO: config?  Now, use enough for 24h of 10 sec values
        if len(self._data) > N_max:
            N_to_remove = len(self._data) - N_max
            self.beginRemoveRows(QtCore.QModelIndex(), 0, N_to_remove - 1)
            self._data = self._data[N_to_remove:]
            assert len(self._data) == N_max
            self.endRemoveRows()

    def get_plot_data(self, column_idx):
        if len(self._data) == 0:
            return "", []
        values = [list(row.values())[column_idx] for row in self._data]
        colname = list(self._data[0].keys())[column_idx]
        return colname, values

    def get_detector_name_data(self):
        if "DetectorName" in self._data[0]:
            values = [row["DetectorName"] for row in self._data]
        else:
            values = None
        return values


class DataViewForm(QtWidgets.QWidget, Ui_DataViewForm):
    def __init__(self, main_window, table_name: str, *args, **kwargs):
        super(DataViewForm, self).__init__(*args, **kwargs)
        self.setupUi(self)

        # set the first column in the table (the Datetime column) to fit its data
        # note: this is done by setting an absolute value, because setting the column
        # with to automatically resize to fit its data seems to crash the program
        # (maybe due to no data being present at startup?)
        if False:
            header = self.pastDataTableView.horizontalHeader()
            header.resizeSection(0, 10)
        if False:
            # set the first column in the table (the Datetime column) to resize to fit its data
            header = self.pastDataTableView.horizontalHeader()
            try:
                header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            except Exception as ex:
                print(ex)
                import traceback
                traceback.print_exc()


        self.plot_series = []

        tables_without_plots = ["LogMessages"]
        if not table_name in tables_without_plots:
            self.graph_widget = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
            self.graph_widget.showGrid(x=True, y=True)
            self.splitter.addWidget(self.graph_widget)
            self.splitter.setSizes([1, 1])
        else:
            self.graph_widget = None

        self.main_window = main_window
        self.table_name = table_name
        self.selected_column = None

        self.model = TableModel([])
        self.pastDataTableView.setModel(self.model)
        # the last time this table was updated
        self.last_update_time = None
        self.last_redraw_time = 0
        # this is set to True when there is new data which hasn't yet
        # been drawn on the plot
        self.flag_new_plot_data = False
        # for detecting a change in column
        self.previous_selected_column = -1

        self.connect_signals()

        self.update_times: Dict[str, datetime.datetime] = {}

        # import matplotlib.cm; tuple([tuple(itm) for itm in (np.array(matplotlib.cm.tab20c.colors[2::4]) * 255).astype(int)])
        self._colormap = (
            (158, 202, 225),
            (253, 174, 107),
            (161, 217, 155),
            (188, 189, 220),
            (189, 189, 189),
        )
        self.legend = None

    def get_color(self, idx):
        N = len(self._colormap)
        return self._colormap[idx % N]

    def connect_signals(self):
        self.redraw_timer = QTimer()
        self.redraw_timer.setInterval(1000)
        self.redraw_timer.timeout.connect(self.update_displays)
        self.redraw_timer.start()

        self.pastDataTableView.selectionModel().currentChanged.connect(
            self.table_selected
        )

        # TODO: chase up how to extract the column names from a selection range
        # rather than just the position.

        # self.pastDataTableView.selectionModel().selectionChanged.connect(
        #    self.test
        # )

    # def test(self, arg1, arg2):
    #    print("===", arg1, arg2)
    #    for itm in arg1:
    #        print(itm)

    def table_selected(self, idx):
        # print('column selected')
        c0, r0 = idx.column(), idx.row()
        # print(f'{c0,r0}')
        self.selected_column = idx.column()

    def plot(self, x, y, legend_data=None, title=None):
        if self.legend is not None:
            self.graph_widget.removeItem(self.legend)
        self.legend = self.graph_widget.addLegend(frame=False, rowCount=1, colCount=2)
        for itm in self.plot_series:
            self.graph_widget.removeItem(itm)
            self.plot_series = []
        for idx, (x, y, label) in enumerate(groupby_series(x, y, legend_data)):
            p = self.graph_widget.plot(x, y, pen=self.get_color(idx))
            self.plot_series.append(p)
        self.graph_widget.setTitle(title)

    def step_plot(self, x, y, legend_data=None, title=None):
        x_all = x
        y_all = y
        smooth_these = ["LLD", "ULD", "ExFlow"]
        do_smoothing = title in smooth_these
        if self.legend is not None:
            self.graph_widget.removeItem(self.legend)
        # if do_smoothing:
        #    rc = 2
        # else:
        #    rc = 1
        self.legend = self.graph_widget.addLegend(frame=False, colCount=1)

        for itm in self.plot_series:
            self.graph_widget.removeItem(itm)
            self.plot_series = []

        dark_mode = self.main_window._use_dark_theme

        # WARNING - MAGIC NUMBERS (assumes 10-sec)
        # sampling interval, TODO: fix
        conv_width = 6 * 30 // 2

        data_is_not_numeric = False
        for idx, (x, y, label) in enumerate(groupby_series(x_all, y_all, legend_data)):
            dx = np.median(np.diff(x))
            xplt = np.empty(len(x) * 2)
            # end each bar at 'x', start at 'x-dx'
            xplt[::2] = x - dx
            xplt[1::2] = x
            yplt = np.empty(len(y) * 2)
            try:
                yplt[::2] = y
                yplt[1::2] = y
            except ValueError:
                data_is_not_numeric = True
                break
            color = self.get_color(idx)
            if do_smoothing:
                # blend the color into the background
                if dark_mode:
                    color = color[0] // 2, color[1] // 2, color[2] // 2
                else:
                    color = (
                        (color[0] + 255) // 2,
                        (color[1] + 255) // 2,
                        (color[2] + 255) // 2,
                    )
            pen = pg.mkPen(color)
            p = self.graph_widget.plot(xplt, yplt, name=label, pen=pen)
            self.plot_series.append(p)

        if do_smoothing:
            # loop again, so that smooth lines are plotted on top
            # of the earlier series
            for idx, (x, y, label) in enumerate(
                groupby_series(x_all, y_all, legend_data)
            ):
                # also add smoothed value for some inputs
                dx = np.r_[np.median(np.diff(x)), np.diff(x)]
                xplt = np.empty(len(x) * 2)
                xplt[::2] = x - dx
                xplt[1::2] = x
                # 30 minutes smoothing
                # only plot the smoothed version if there is enough data
                if len(y) > conv_width * 3:
                    conv = np.ones(conv_width + 1, dtype=float)
                    conv /= conv.sum()
                    y_s = np.convolve(conv, np.array(y).astype(float), mode="same")
                    y_s[: conv_width // 2] = np.NaN
                    y_s[-conv_width // 2 :] = np.NaN
                    yplt = np.empty(len(y) * 2)
                    yplt[::2] = y_s
                    yplt[1::2] = y_s
                    pen = pg.mkPen(self.get_color(idx))
                    pen.setWidth(3)
                    p = self.graph_widget.plot(
                        xplt, yplt, name=label + " smoothed", pen=pen
                    )
                    self.plot_series.append(p)

        self.graph_widget.setTitle(title)

    def autoScroll(self):
        """
        Scroll the table view to the bottom.  Uses a timer so that the table can
        update itself before the scroll happens
        """
        QtCore.QTimer.singleShot(0, self.pastDataTableView.scrollToBottom)

    def update_displays(self):
        dt_threshold = 0.95
        ic = self.main_window.instrument_controller
        # return if not connected or if the last redraw *completed* less than
        # dt_threshold seconds ago
        if ic is None or (time.time() - self.last_redraw_time) < dt_threshold:
            return

        first_run = self.last_update_time is None

        if self.last_update_time is None:
            if self.table_name == "Results":
                # only retrieve data from the last week
                start_time = datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(days=7)
            else:
                start_time = datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(days=1)
        else:
            start_time = self.last_update_time
        t, newdata = ic.get_rows(self.table_name, start_time=start_time)
        if len(newdata) > 0:
            self.flag_new_plot_data = True

        if t is not None:
            self.last_update_time = t
            # use the database rowid as the reference, rather than taking the
            # time into account (this handles multipe detectors where one might
            # stop updating for a while)
            self.last_update_time.t = None
            sb = self.pastDataTableView.verticalScrollBar()
            scroll_bar_at_bottom = sb.value() >= sb.maximum()
            self.model.append_data(newdata)
            if scroll_bar_at_bottom or first_run:
                self.autoScroll()
            
            # this is disabled because sometimes RDM produces a table without any data
            # in it, which crashes the program.  We shall re-enable when we get this working
            # (needs a check for empty data tables)
            if first_run and False:
                # set the first column in the table (the Datetime column) to resize to fit its data
                header = self.pastDataTableView.horizontalHeader()
                try:
                    header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
                except Exception as ex:
                    import traceback
                    traceback.print_exc()


        # TODO: link to plot data, or somehow avoid copying the entire
        # x/y series each time
        redraw_plot = False
        redraw_plot = (
            (self.graph_widget is not None)
            and (first_run or self.graph_widget.isVisible())
            and (self.selected_column is not None)
            and (self.selected_column != 0)
            and (
                self.flag_new_plot_data
                or (self.selected_column != self.previous_selected_column)
            )
        )
        ## for debugging
        # if self.graph_widget is not None:
        #    print("***", self.graph_widget, redraw_plot, self.graph_widget.isVisible())

        if redraw_plot:
            # find DetectorName column
            yname, y = self.model.get_plot_data(column_idx=self.selected_column)
            xname, x = self.model.get_plot_data(column_idx=0)
            detector_name = self.model.get_detector_name_data()
            # pyqtgraph timestamps are assumed to be in non-daylight saving time
            # Here, I'm subtracting the timezone offset (in seconds) so that
            # the plotted value is in UTC
            x = [itm.timestamp() + time.timezone for itm in x]
            self.step_plot(x, y, legend_data=detector_name, title=yname)
            self.flag_new_plot_data = False
            self.previous_selected_column = self.selected_column

        self.last_redraw_time = time.time()


#    def __del__(self):
#        """ Handy for ensuring the widget is really getting deleted"""
#        print("INSIDE DEL METHOD *************************")
