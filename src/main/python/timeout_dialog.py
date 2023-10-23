# A dialog box with a time-out ("Closing in N seconds...")


from PyQt5 import QtCore, QtGui, QtWidgets


class TimeoutDialog(QtWidgets.QDialog):
    def __init__(self, timeout=10, config_fname="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resume logging")
        self.config_fname = config_fname
        self.n = timeout

        QBtn = QtWidgets.QDialogButtonBox.Yes | QtWidgets.QDialogButtonBox.No
        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        message = QtWidgets.QLabel(f"")
        self.message_widget = message
        self._set_message_text()
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        # Timeout handling
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._handle_tick)
        self.timer.start()

    def _handle_tick(self):
        self.n -= 1
        if self.n <= 0:
            self.buttonBox.accepted.emit()
        else:
            self._set_message_text()

    def _set_message_text(self):
        self.message_widget.setText(
            f"Resume logging using the configuration in\n\n"
            f"{self.config_fname}?\n\n\n"
            f"Logging will automatically resume in {self.n} sec"
        )
