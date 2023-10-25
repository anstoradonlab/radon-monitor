import logging
import sys
import os

from ansto_radon_monitor.configuration import setup_logging
from PyQt5 import QtCore, QtWidgets, QtGui
from .mainwindow import MainWindow

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def main():
    print("Starting GUI")
    setup_logging(loglevel=logging.DEBUG)

    # this helps the taskbar icon to be grouped properly
    # ref: https://www.pythonguis.com/tutorials/packaging-pyqt5-pyside2-applications-windows-pyinstaller/
    try:
        from ctypes import windll  # Only exists on Windows.
        myappid = 'ansto.rdm.rdm.10'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass


    # Ref for this idea: https://stackoverflow.com/questions/8786136/pyqt-how-to-detect-and-close-ui-if-its-already-running
    lockfile_path = QtCore.QDir.tempPath() + "/ansto_radon_monitor_gui.lock"
    lockfile = QtCore.QLockFile(lockfile_path)

    if lockfile.tryLock(100):
        app = QtWidgets.QApplication(sys.argv)
        try:
            # set the icon, but don't panic if it's not possible
            app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'Icon.ico')))
        except:
            pass
        window = MainWindow()
        window.show()
        exit_code = app.exec_()
        sys.exit(exit_code)
    else:
        print(f"lockfile unavailable: {lockfile_path}")
        sys.exit("app is already running")


#if __name__ == "__main__":
#    main()