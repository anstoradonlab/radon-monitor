import logging
import sys

import pyqtgraph
from ansto_radon_monitor.main import setup_logging
from .mainwindow import MainWindow
# from PyQt5.QtWidgets import QMainWindow
from PyQt5 import QtCore, QtWidgets, uic



def main():
    print("Starting GUI")
    setup_logging(loglevel=logging.DEBUG)

    # Ref for this idea: https://stackoverflow.com/questions/8786136/pyqt-how-to-detect-and-close-ui-if-its-already-running
    lockfile_path = QtCore.QDir.tempPath() + "/ansto_radon_monitor_gui.lock"
    lockfile = QtCore.QLockFile(lockfile_path)

    if lockfile.tryLock(100):
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        exit_code = app.exec_()
        sys.exit(exit_code)
    else:
        print(f"lockfile unavailable: {lockfile_path}")
        sys.exit("app is already running")


if __name__ == "__main__":
    main()