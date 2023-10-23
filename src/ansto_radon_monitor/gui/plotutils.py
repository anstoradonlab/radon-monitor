import numpy as np
import pyqtgraph as pg

_colormap = (
    (158, 202, 225),
    (253, 174, 107),
    (161, 217, 155),
    (188, 189, 220),
    (189, 189, 189),
)

_linewidth = 2


def data_to_columns(data):
    """convert data (list of dicts) into dict of arrays"""
    data_arrays = {}
    for k in data[0]:
        data_arrays[k] = np.array([itm[k] for itm in data])
    return data_arrays


def groupby_series(x, y, legend_data):
    x = np.array(x)
    y = np.array(y)
    if legend_data is None:
        ret = [(x, y, None)]
    else:
        legend_data = np.array(legend_data)
        ret = []
        for label in sorted(set(legend_data)):
            mask = legend_data == label
            xii = x[mask]
            yii = y[mask]
            ret.append((xii, yii, str(label)))
    return ret


def get_pen(idx):
    N = len(_colormap)
    pen = pg.mkPen(_colormap[idx % N])
    pen.setWidth(_linewidth)
    return pen
