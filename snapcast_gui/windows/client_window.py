import logging
import re
import sys

from PySide6.QtCore import QProcess, QSize, Qt, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings

from snapcast_gui.misc.notifications import Notifications
from typing import List, Union


class ClientWindow(QMainWindow):
    def __init__(self, snapcast_settings: SnapcastSettings, log_level: int) -> None:
        """
        Initializes the clientwindow object.
        """
        super(ClientWindow, self).__init__()
        self.logger = logging.getLogger("ClientWindow")
        self.logger.setLevel(log_level)

        self.snapcast_settings = snapcast_settings

        self.audio_engine = "alsa"
        self.buffer_size = "20"
        self.snapclient_process = None
        self.cleanup_connected = False
        self.snapclient_finished_signal = None

        self.setGeometry(400, 0, 400, 600)

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setAlignment(Qt.AlignTop)

        self.ip_dropdown = QComboBox(self)
        self.ip_dropdown.setEditable(True)
        self.ip_input = self.ip_dropdown.lineEdit()
        self.ip_input.setPlaceholderText("Enter IP Address")
        self.ip_input.setToolTip("Ip address of the Snapserver to connect")
        layout.addWidget(self.ip_dropdown)

        self.connect_button = QPushButton("Run Snapclient", self)
        self.connect_button.clicked.connect(self.run_snapclient)
        layout.addWidget(self.connect_button)

        if sys.platform == "linux":
            self.audio_engine_label = QLabel("Audio Engine", self)
            self.audio_engine_dropdown = QComboBox(self)
            self.audio_engine_dropdown.addItems(["Alsa", "PulseAudio"])
            self.audio_engine_dropdown.currentIndexChanged.connect(self.update_audio_engine)
            self.audio_engine_dropdown.setToolTip("Select the audio engine to use")
            layout.addWidget(self.audio_engine_label)
            layout.addWidget(self.audio_engine_dropdown)

        self.buffer_size_label = QLabel("Buffer Size", self)
        self.buffer_size_dropdown = QComboBox(self)
        self.buffer_size_dropdown.addItems(
            ["20", "40", "60", "80", "100", "120", "140", "160", "180", "200"]
        )
        self.buffer_size_dropdown.currentIndexChanged.connect(self.update_buffer_size)
        self.buffer_size_dropdown.setToolTip("Select the buffer size to use")
        layout.addWidget(self.buffer_size_label)
        layout.addWidget(self.buffer_size_dropdown)

        self.show_advanced_checkbox = QCheckBox("Show Advanced", self)
        self.show_advanced_checkbox.stateChanged.connect(self.toggle_advanced_options)
        layout.addWidget(self.show_advanced_checkbox)

        self.pcms_label = QLabel("PCMs", self)
        self.pcms_dropdown = QComboBox(self)
        self.pcms_dropdown.addItem("Switch to PulseAudio to see PCMs")
        self.pcms_dropdown.setToolTip(
            "Select the output PCM to use (only for PulseAudio)"
        )
        self.pcms_dropdown.setEnabled(False)

        self.pcms_refresh_button = QPushButton()
        self.pcms_refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.pcms_refresh_button.setIconSize(QSize(24, 24))
        self.pcms_refresh_button.setToolTip("Refresh PCMs List")
        self.pcms_refresh_button.setEnabled(False)
        self.pcms_refresh_button.clicked.connect(self.update_audio_engine)

        dropdown_height = self.pcms_dropdown.sizeHint().height()

        self.pcms_refresh_button.setFixedHeight(dropdown_height)

        pcms_layout = QHBoxLayout()
        pcms_layout.addWidget(self.pcms_dropdown)
        pcms_layout.addWidget(self.pcms_refresh_button)

        layout.addWidget(self.pcms_label)
        layout.addLayout(pcms_layout)

        self.resample_label = QLabel("Resample Output", self)

        self.frequency_dropdown = QComboBox(self)
        self.frequency_dropdown.addItems(
            ["Default", "Custom", "42000", "48000", "96000", "192000"]
        )
        self.frequency_dropdown.currentIndexChanged.connect(self.update_frequency)
        self.frequency_dropdown.setToolTip(
            "Select the frequency to resample to output to"
        )
        self.frequency_dropdown.setMinimumWidth(100)

        self.bitrate_dropdown = QComboBox(self)
        self.bitrate_dropdown.addItems(["Default", "Custom", "16", "24", "32"])
        self.bitrate_dropdown.currentIndexChanged.connect(self.update_bitrate)
        self.bitrate_dropdown.setToolTip("Select the bitrate to resample to output to")
        self.bitrate_dropdown.setMinimumWidth(100)

        self.channels_dropdown = QComboBox(self)
        self.channels_dropdown.addItems(["Default", "Custom", "2", "4", "6", "8", "16"])
        self.channels_dropdown.currentIndexChanged.connect(self.update_channels)
        self.channels_dropdown.setToolTip(
            "Select the number of channels for the output"
        )
        self.channels_dropdown.setMinimumWidth(100)

        resample_layout = QHBoxLayout()
        resample_layout.addWidget(self.frequency_dropdown)
        resample_layout.addWidget(self.bitrate_dropdown)
        resample_layout.addWidget(self.channels_dropdown)

        layout.addWidget(self.resample_label)
        layout.addLayout(resample_layout)

        self.log_label = QLabel("Log:", self)
        layout.addWidget(self.log_label)

        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setToolTip("Log of the Snapclient process")
        layout.addWidget(self.log_area)

        self.snapclient_thread = QThread()

        if self.snapcast_settings.read_setting("snapclient/autostart"):
            self.run_snapclient()

        if self.snapcast_settings.read_setting(
            "snapclient/show_advanced_settings_on_startup"
        ):
            self.show_advanced_options()
            self.show_advanced_checkbox.setChecked(True)
        else:
            self.hide_advanced_options()

        self.populate_ip_dropdown()

    def populate_ip_dropdown(self) -> None:
        """
        Populates the IP dropdown with the IP addresses from the config file.
        """
        self.logger.debug("Populating IP dropdown")
        self.ip_addresses = self.snapcast_settings.read_config_file()
        self.ip_dropdown.clear()
        self.ip_dropdown.addItems(self.ip_addresses)

    def update_audio_engine(self):
        """
        Updates the audio engine based on the selected value from the dropdown.
        If PulseAudio is selected, it populates the PCMs dropdown.
        """
        self.audio_engine = self.audio_engine_dropdown.currentText().lower()
        if self.audio_engine == "pulseaudio":
            self.audio_engine = "pulse"
            self.logger.info("Audio engine set to PulseAudio")
            self.pcms_dropdown.clear()
            self.pcms_dropdown.setEnabled(True)
            self.pcms_refresh_button.setEnabled(True)

            self.snapclient_process = QProcess()
            self.snapclient_process.setProgram("snapclient")
            self.snapclient_process.setArguments(["--list"])
            self.snapclient_process.setProcessChannelMode(QProcess.MergedChannels)
            self.snapclient_process.readyReadStandardOutput.connect(
                self.read_snapclient_output
            )
            self.snapclient_process.start()
            self.logger.info("Snapclient process started to get PCMs")
            self.snapclient_process.waitForFinished()
        else:
            self.pcms_dropdown.clear()
            self.pcms_dropdown.addItem("Switch to PulseAudio to see PCMs")
            self.pcms_dropdown.setEnabled(False)

    def read_snapclient_output(self) -> List[str]:
        """
        Reads the output of the snapclient process to get the PCMs to populate the PCMs dropdown.
        """
        self.logger.debug("Reading snapclient output")
        if self.snapclient_process is not None:
            output = self.snapclient_process.readAllStandardOutput().data().decode()
            self.logger.error(f"Snapclient output: {output}")
            device_pattern = r":\s*(.+)$"
            device_names: List[str] = re.findall(device_pattern, output, re.MULTILINE)

        if device_names:
            self.pcms_dropdown.clear()
            self.pcms_dropdown.addItem("Default")
            self.pcms_dropdown.addItems(device_names)
            self.logger.error(f"PCMs found: {device_names}")
            return device_names
        else:
            QMessageBox.warning(
                self, "Warning", "No audio devices found. Can't populate PCMs dropdown."
            )
            self.pcms_dropdown.addItem("No audio devices found")
            self.pcms_dropdown.setEnabled(False)
            return []

    def update_frequency(self) -> None:
        """
        Updates the frequency dropdown based on the selected value.
        Makes the frequency dropdown editable if "Custom" is selected.
        """
        if self.frequency_dropdown.currentText() == "Custom":
            self.frequency_dropdown.setEditable(True)
            self.logger.debug("Frequency set to custom")
        else:
            self.frequency_dropdown.setEditable(False)
            self.logger.debug("Frequency set to system")

    def update_bitrate(self) -> None:
        """
        Updates the bitrate dropdown based on the selected value.
        Makes the bitrate dropdown editable if "Custom" is selected.
        """
        if self.bitrate_dropdown.currentText() == "Custom":
            self.bitrate_dropdown.setEditable(True)
            self.logger.debug("Bitrate set to custom")
        else:
            self.bitrate_dropdown.setEditable(False)
            self.logger.debug("Bitrate set to system")
            self.logger.debug("Bitrate set to system")

    def update_channels(self) -> None:
        """
        Update the channels dropdown based on the current selection.

        If the current selection is "Custom", make the channels dropdown editable.
        Otherwise, make it non-editable.

        This method is called when the channels dropdown selection changes.
        """
        if self.channels_dropdown.currentText() == "Custom":
            self.channels_dropdown.setEditable(True)
            self.logger.debug("Channels set to custom")
        else:
            self.channels_dropdown.setEditable(False)
            self.logger.debug("Channels set to system")

    def check_dropdown_selection(self) -> bool:
        """
        Check if the resampling dropdowns are set to custom.
        """
        if (
            self.frequency_dropdown.currentText() != "Default"
            and self.bitrate_dropdown.currentText() != "Default"
            and self.channels_dropdown.currentText() != "Default"
        ):
            return True
        else:
            return False

    def update_buffer_size(self) -> None:
        """
        Update the buffer size based on the selected value from the dropdown.

        This method sets the buffer size attribute of the clientwindow object to the selected value from the dropdown.
        It also logs a debug message indicating the new buffer size.
        """
        self.buffer_size = self.buffer_size_dropdown.currentText()
        self.logger.error(f"Buffer size set to {self.buffer_size}")

    def generate_snapclient_arguments(self) -> Union[List[str], None]:
        """
        Generate the arguments for the snapclient process using the selected values from the dropdowns.

        Returns:
            list: A list of arguments for the snapclient process.
                    Returns None if any required values are not selected.
        """
        arguments = []
        if self.ip_input.text() != "":
            arguments.append("-h")
            arguments.append(self.ip_input.text())
        if sys.platform == "linux":
            arguments.append("--player")
            arguments.append(f"{self.audio_engine}:buffer_time:{self.buffer_size}")
        if self.audio_engine == "pulse":
            arguments.extend(["--pcm", self.pcms_dropdown.currentText()])
        if (
            self.frequency_dropdown.currentText() != "Default"
            or self.bitrate_dropdown.currentText() != "Default"
            or self.channels_dropdown.currentText() != "Default"
        ):
            if self.frequency_dropdown.currentText() == "Default":
                QMessageBox.warning(self, "Warning", "Please select a frequency.")
                return None
            if self.bitrate_dropdown.currentText() == "Default":
                QMessageBox.warning(self, "Warning", "Please select a bitrate.")
                return None
            if self.channels_dropdown.currentText() == "Default":
                QMessageBox.warning(
                    self, "Warning", "Please select the number of channels."
                )
                return None
            resampling_arguments = [
                "--sampleformat",
                "{}:{}:{}".format(
                    self.frequency_dropdown.currentText(),
                    self.bitrate_dropdown.currentText(),
                    self.channels_dropdown.currentText(),
                ),
            ]
            arguments.extend(resampling_arguments)
        return arguments

    def run_snapclient(self) -> None:
        """
        Runs the snapclient process with the generated arguments, handling the case where the process is already running.
        If the process is already running, it shows a warning message and does not start the process again.
        """
        if (
            self.snapclient_process is not None
            and self.snapclient_process.state() == QProcess.Running
        ):
            QMessageBox.critical(self, "Error", "Snapclient process already running.")
            self.logger.warning("Snapclient process already running.")
            return

        def start_snapclient():
            """
            Starts the snapclient process and connects the finished signal to the cleanup function.
            It also disables the controls while the process is running.
            """
            arguments = self.generate_snapclient_arguments()
            if arguments is None:
                return
            self.snapclient_process = QProcess()
            self.snapclient_process.setProgram(
                self.snapcast_settings.read_setting("snapclient/custom_path")
            )
            self.snapclient_process.setArguments(arguments)
            self.log_area.clear()
            self.snapclient_process.setProcessChannelMode(QProcess.MergedChannels)
            self.snapclient_process.readyReadStandardOutput.connect(self.read_output)
            self.logger.debug(
                "Snapclient executable {}".format(
                    self.snapcast_settings.read_setting("snapclient/custom_path")
                )
            )
            self.logger.debug(
                "Snapclient command: {}".format(" ".join(arguments))
            )
            self.snapclient_process.started.connect(
                lambda: self.logger.info("Snapclient process started.")
            )
            self.snapclient_process.start()

        if self.generate_snapclient_arguments() is None:
            return
        self.snapclient_thread.started.connect(start_snapclient)
        self.snapclient_thread.start()
        self.connect_button.setText("Stop Snapclient")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.stop_snapclient)
        self.disable_controls()
        Notifications.send_notify("Snapclient started", "Snapclient")

    def stop_snapclient(self) -> None:
        """
        Stop the snapclient process and perform necessary cleanup.

        If the snapclient process is running, it will be terminated and the finished signal will be connected
        to the cleanup_snapclient_thread function. The controls will be disabled and the connect_button text
        will be set to "Run Snapclient". If the snapclient process is not running, a warning message will be
        displayed and a warning log will be recorded.
        """
        if (
            self.snapclient_process is not None
            and self.snapclient_process.state() == QProcess.Running
        ):
            self.cleanup_connected = True
            if self.snapclient_finished_signal is not None:
                self.snapclient_finished_signal.disconnect()
            self.snapclient_process.finished.connect(self.cleanup_snapclient_thread)
            self.snapclient_process.terminate()
            self.disable_controls()
            self.connect_button.setText("Run Snapclient")
        else:
            QMessageBox.warning(self, "Warning", "Snapclient process is not running.")
            self.logger.warning("Snapclient process is not running.")
            self.process_finished("")

    def cleanup_snapclient_thread(self) -> None:
        """
        Cleanup the snapclient thread and enable the controls.

        This method is responsible for cleaning up the snapclient thread and enabling the controls.
        It disconnects the finished signal from the snapclient process and waits for the thread to finish.
        Finally, it sends a notification indicating that the snapclient has stopped.
        """
        if self.cleanup_connected:
            if self.snapclient_process is not None:
                self.snapclient_process.finished.disconnect(
                    self.cleanup_snapclient_thread
                )
            if self.snapclient_finished_signal is not None:
                self.snapclient_finished_signal.disconnect()
        self.snapclient_thread.quit()
        self.snapclient_thread.wait()
        self.process_finished("Snapclient process finished.")
        Notifications.send_notify("Snapclient stopped", "Snapclient")

    def process_finished(self, log: str) -> None:
        """
        Handles the case where the snapclient process finishes and reenables the controls.

        Args:
            log: The log message from the snapclient process.
        """
        self.log_area.append(log)
        self.snapclient_process = None
        self.connect_button.setText("Run Snapclient")
        self.enable_controls()
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.run_snapclient)
        self.connect_button.setToolTip(
            "Start the Snapclient process using executable {}".format(
                self.snapcast_settings.read_setting("snapclient/custom_path")
            )
        )
        Notifications.send_notify(log, "Snapclient")
        self.logger.info(f" Logs from snapclient process{log}")

    def disable_controls(self) -> None:
        """
        Disable the controls in the window when needed.

        This method disables various controls in the window, such as dropdown menus and input fields,
        to prevent user interaction when certain conditions are met.
        """
        self.logger.debug("Disabling controls")
        self.buffer_size_dropdown.setEnabled(False)
        self.bitrate_dropdown.setEnabled(False)
        self.channels_dropdown.setEnabled(False)
        self.frequency_dropdown.setEnabled(False)
        self.pcms_dropdown.setEnabled(False)
        self.pcms_refresh_button.setEnabled(False)
        self.ip_input.setEnabled(False)
        self.ip_input.setReadOnly(True)
        if sys.platform == "linux":
            self.audio_engine_dropdown.setEnabled(False)

    def enable_controls(self) -> None:
        """
        Enable the controls in the window when needed.

        This method enables various controls in the window, allowing the user to interact with them.
        Additionally, it sets the readOnly property of ip_input to False, allowing the user to edit its value.
        """
        self.logger.debug("Enabling controls")
        self.buffer_size_dropdown.setEnabled(True)
        self.bitrate_dropdown.setEnabled(True)
        self.channels_dropdown.setEnabled(True)
        self.frequency_dropdown.setEnabled(True)
        self.pcms_dropdown.setEnabled(True)
        self.pcms_refresh_button.setEnabled(True)
        self.ip_input.setEnabled(True)
        self.ip_input.setReadOnly(False)
        if sys.platform == "linux":
            self.audio_engine_dropdown.setEnabled(True)

    def toggle_advanced_options(self, state: int) -> None:
        """
        Toggle the advanced options in the window (PCMs, resampling options).

        Args:
            state: The state of the toggle. 2 represents 'show', 0 represents 'hide'.
        """
        self.logger.debug("Toggling advanced options")
        self.logger.debug("State: {}".format(state))
        if state == 2:
            self.show_advanced_options()
        elif state == 0:
            self.hide_advanced_options()

    def toggle_snapclient(self) -> None:
        """
        Toggle the snapclient process.

        This method toggles the snapclient process based on its current state.
        If the snapclient process is running, it will be stopped. If it is not running, it will be started.
        """
        if (
            self.snapclient_process is not None
            and self.snapclient_process.state() == QProcess.Running
        ):
            self.stop_snapclient()
            self.logger.debug("Stopping snapclient from toggle")
        else:
            self.run_snapclient()
            self.logger.debug("Starting snapclient from toggle")

    def hide_advanced_options(self) -> None:
        """
        Hide the advanced options in the window.

        This method hides the advanced options in the client window, including the PCMs dropdown,
        the PCMs refresh button, the resample label, the frequency dropdown, the bitrate dropdown,
        and the channels dropdown.
        """
        self.logger.debug("Hiding advanced options")
        self.pcms_label.hide()
        self.pcms_dropdown.hide()
        self.pcms_refresh_button.hide()
        self.resample_label.hide()
        self.frequency_dropdown.hide()
        self.bitrate_dropdown.hide()
        self.channels_dropdown.hide()

    def show_advanced_options(self) -> None:
        """
        Show the advanced options in the window.

        This method displays the advanced options in the client window, including the PCMs dropdown,
        the resample options, and the channel configuration dropdowns.

        Args:
            None
        """
        self.logger.debug("Showing advanced options")
        self.pcms_label.show()
        self.pcms_dropdown.show()
        self.pcms_refresh_button.show()
        self.resample_label.show()
        self.frequency_dropdown.show()
        self.bitrate_dropdown.show()
        self.channels_dropdown.show()

    def read_output(self):
        """
        Read the output of the snapclient process and append it to the log area.

        This method reads the standard output of the snapclient process and decodes it as a string.
        The decoded output is then appended to the log area.
        """
        self.logger.debug("Reading output")
        output = self.snapclient_process.readAllStandardOutput().data().decode()
        self.log_area.append(output)
