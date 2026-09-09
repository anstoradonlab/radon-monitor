rem This script re-generates the Python code for the user interface.
rem Run it after making changes in QT Designer.
pyside6-uic ui/main_window.ui >              src/ansto_radon_monitor/gui/ui_mainwindow.py
pyside6-uic ui/data_view.ui >                src/ansto_radon_monitor/gui/ui_data_view.py
pyside6-uic ui/c_and_b.ui >                  src/ansto_radon_monitor/gui/ui_c_and_b.py
pyside6-uic ui/system_information.ui >       src/ansto_radon_monitor/gui/ui_system_information.py
pyside6-uic ui/sensitivity_sweep.ui >        src/ansto_radon_monitor/gui/ui_sensitivity_sweep.py
pyside6-uic ui/cal_bg_start_time_widget.ui > src/ansto_radon_monitor/gui/ui_cal_bg_start_time_widget.py

