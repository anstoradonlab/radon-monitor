rem This script re-generates the Python code for the user interface.
rem Run it after making changes in QT Designer.
pyuic5 ui/main_window.ui >              src/ansto_radon_monitor/gui/ui_mainwindow.py
pyuic5 ui/data_view.ui >                src/ansto_radon_monitor/gui/ui_data_view.py
pyuic5 ui/c_and_b.ui >                  src/ansto_radon_monitor/gui/ui_c_and_b.py
pyuic5 ui/system_information.ui >       src/ansto_radon_monitor/gui/ui_system_information.py
pyuic5 ui/sensitivity_sweep.ui >        src/ansto_radon_monitor/gui/ui_sensitivity_sweep.py
pyuic5 ui/cal_bg_start_time_widget.ui > src/ansto_radon_monitor/gui/ui_cal_bg_start_time_widget.py

