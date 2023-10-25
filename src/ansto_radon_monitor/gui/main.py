import logging
import sys

from ansto_radon_monitor.configuration import setup_logging
from PyQt5 import QtCore, QtWidgets
from .mainwindow import MainWindow


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


#if __name__ == "__main__":
#    main()