import logging
import subprocess
import sys

from PySide6.QtCore import QProcess, Qt, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from snapcast_gui.misc.notifications import Notifications
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables
from snapcast_gui.misc.log_highlighter import LogHighlighter

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings


class ServerWindow(QMainWindow):
    """
    Represents the Server window of the program.
    """

    def __init__(self, snapcast_settings: "SnapcastSettings", log_level: int):
        super(ServerWindow, self).__init__()
        self.logger = logging.getLogger("ServerWindow")
        self.logger.setLevel(log_level)

        self.snapcast_settings = snapcast_settings

        self.snapserver_process = None
        self.cleanup_connected = True
        self.snapserver_finished_signal = None

        self.setGeometry(100, 0, 400, 500)
        self.setWindowTitle("Snapserver {}".format(SnapcastGuiVariables.snapcast_gui_version))
        self.setWindowIcon(QIcon(SnapcastGuiVariables.snapcast_icon_path))

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setAlignment(Qt.AlignTop)

        self.connect_button = QPushButton("Run Snapserver", self)
        self.connect_button.clicked.connect(self.run_snapserver)
        layout.addWidget(self.connect_button)

        self.before_command = QTextEdit(self)
        self.before_command.setPlaceholderText(
            "Command to run before starting the snapserver"
        )
        
        self.before_command.setText(
            snapcast_settings.read_setting("snapserver/config_before_start") or ""
        )
        self.before_command.setFixedHeight(30)
        if (
            len(snapcast_settings.read_setting("snapserver/config_before_start") or "")
            < 30
        ):
            self.before_command.setFixedHeight(30)
        else:
            self.before_command.setFixedHeight(60)
        self.before_command.textChanged.connect(
            lambda: self.snapcast_settings.update_setting(
                "snapserver/config_before_start", self.before_command.toPlainText()
            )
        )
        layout.addWidget(self.before_command)

        self.after_command = QTextEdit(self)
        self.after_command.setPlaceholderText(
            "Command to run after stopping the snapserver"
        )
        self.after_command.setText(
            snapcast_settings.read_setting("snapserver/config_after_start") or ""
        )
        self.after_command.setFixedHeight(30)
        if (len(self.snapcast_settings.read_setting("snapserver/config_after_start") or "") < 30):
            self.after_command.setFixedHeight(30)
        else:
            self.after_command.setFixedHeight(60)
        self.after_command.textChanged.connect(
            lambda: self.snapcast_settings.update_setting(
                "snapserver/config_after_start", self.after_command.toPlainText()
            )
        )
        layout.addWidget(self.after_command)

        if sys.platform == "linux" or sys.platform == "darwin":
            self.before_command.setToolTip(
                "Set the command to run before starting the snapserver. Hint: You can concatenate multiple commands with &&."
            )
            self.after_command.setToolTip("Set the command to run after stopping the snapserver. Hint: You can concatenate multiple commands with &&.")
        else:
            self.before_command.setToolTip(
                "Set the command to run before starting the snapserver. Hint: You can concatenate multiple commands with &."
            )
            self.after_command.setToolTip(
                "Set the command to run after stopping the snapserver. Hint: You can concatenate multiple commands with &."
            )

        self.log_label = QLabel("Log")
        layout.addWidget(self.log_label)

        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setAcceptRichText(True)  # Enable HTML formatting
        layout.addWidget(self.log_area)

        self.snapserver_thread = QThread()

        if self.snapcast_settings.read_setting("snapserver/autostart"):
            self.run_snapserver()
            self.show()

    def run_snapserver(self) -> None:
        """
        Runs the Snapserver process.

        This method checks if the Snapserver process is already running. If it is, an error message is displayed and the method returns.
        If the Snapserver process is not running, it starts the process, sets up the necessary connections, and updates the UI accordingly.
        """
        if (
            self.snapserver_process is not None
            and self.snapserver_process.state() == QProcess.Running
        ):
            QMessageBox.critical(self, "Error", "Snapserver process already running.")
            self.logger.warning(
                "Snapserver process already running.")
            return

        def start_snapserver():
            self.snapserver_process = QProcess()
            self.snapserver_process.setProgram(
                self.snapcast_settings.read_setting("snapserver/custom_path")
            )
            self.log_area.clear()
            self.snapserver_process.setProcessChannelMode(QProcess.MergedChannels)
            self.snapserver_process.readyReadStandardOutput.connect(self.read_output)
            self.run_command(self.before_command.toPlainText())
            self.before_command.setReadOnly(True)
            self.after_command.setReadOnly(True)
            self.logger.debug("Snapserver executable {}".format(
                self.snapcast_settings.read_setting("snapserver/custom_path")
            ))
            self.logger.debug(
                "Snapserver command: {}".format(
                    self.snapserver_process.program()
                )
            )
            self.snapserver_process.started.connect(
                lambda: self.logger.info("Snapserver process started.")
            )
            self.snapserver_process.start()

        self.snapserver_thread.started.connect(start_snapserver)
        self.snapserver_thread.start()

        self.connect_button.setText("Stop Snapserver")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.stop_snapserver)
        Notifications.send_notify("Snapserver started", "Snapserver", self.snapcast_settings)

    def stop_snapserver(self) -> None:
        """
        Stops the snapserver process if it is running and disconnects the signals.
        If the process is running, it terminates it, waits for it to finish, and performs cleanup tasks.
        If the process is not running, it displays a warning message and logs a warning.
        """
        if (
            self.snapserver_process is not None
            and self.snapserver_process.state() == QProcess.Running
        ):
            if self.snapserver_finished_signal is not None:
                self.snapserver_finished_signal.disconnect()
            self.snapserver_process.finished.connect(self.cleanup_snapserver_thread)
            self.snapserver_process.terminate()
            self.snapserver_process.waitForFinished()
            self.after_command.setReadOnly(False)
            self.before_command.setReadOnly(False)
            self.run_command(self.after_command.toPlainText())
            self.connect_button.setText("Run Snapserver")
        else:
            QMessageBox.warning(self, "Warning", "Snapserver process is not running.")
            self.logger.warning(
                "Snapserver process is not running.")
            self.process_finished("")

    def cleanup_snapserver_thread(self) -> None:
        """
        Cleans up the snapserver thread and signals.

        This method disconnects the snapserver process and signals, quits the snapserver thread,
        waits for it to finish, and sends a notification that the snapserver has stopped.
        """
        if self.cleanup_connected:
            if self.snapserver_process is not None:
                self.snapserver_process.finished.disconnect(
                    self.cleanup_snapserver_thread
                )
            if self.snapserver_finished_signal is not None:
                self.snapserver_finished_signal.disconnect()
        self.snapserver_thread.quit()
        self.snapserver_thread.wait()
        self.process_finished("Snapserver process finished.")
        Notifications.send_notify("Snapserver stopped", "Snapserver", self.snapcast_settings)

    def process_finished(self, log: str) -> None:
        """
        Appends the highlighted log to the log area and resets the snapserver process and button.
        """
        highlighted_log = LogHighlighter.highlight_text(log + "\n")
        self.log_area.insertHtml(highlighted_log)
        self.snapserver_process = None
        self.connect_button.setText("Run Snapserver")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.run_snapserver)
        Notifications.send_notify(log, "Snapserver", self.snapcast_settings)
        self.logger.info(f"serverwindow: {log}")

    def read_output(self):
        """
        Reads the output of the snapserver process, highlights it, and appends to the log area.

        This method reads the standard output of the snapserver process, applies HTML highlighting
        for keywords and timestamps, then appends the formatted HTML to the log area.
        """
        self.logger.debug("Reading snapserver output.")
        output = self.snapserver_process.readAllStandardOutput().data().decode()
        highlighted_output = LogHighlighter.highlight_text(output)
        self.log_area.insertHtml(highlighted_output)

    def closeEvent(self, event) -> None:
        """
        Override for the default close event to show a message box if the snapserver process is running to choose between closing the window or hiding it.
        """
        if (
            self.snapserver_process is not None
            and self.snapserver_process.state() == QProcess.Running
        ):
            close_event_msg_box = QMessageBox()
            close_event_msg_box.setIcon(QMessageBox.Question)
            close_event_msg_box.setWindowTitle("Close Snapserver")
            close_event_msg_box.setText(
                "Snapserver is running. Do you want to close it or just hide the window?"
            )
            close_event_msg_box.setStandardButtons(
                QMessageBox.Cancel | QMessageBox.Close | QMessageBox.Yes
            )
            close_event_msg_box.setDefaultButton(QMessageBox.Cancel)
            close_event_msg_box.setButtonText(QMessageBox.Close, "Close Snapserver")
            close_event_msg_box.setButtonText(QMessageBox.Yes, "Hide Window")

            cancel_button = close_event_msg_box.button(QMessageBox.Cancel)
            cancel_button.clicked.connect(lambda: event.ignore())

            close_button = close_event_msg_box.button(QMessageBox.Close)
            close_button.clicked.connect(lambda: self.stop_snapserver())
            close_button.clicked.connect(lambda: event.accept())

            hide_button = close_event_msg_box.button(QMessageBox.Yes)
            hide_button.clicked.connect(lambda: event.ignore())
            hide_button.clicked.connect(lambda: self.hide())

            close_event_msg_box.exec()

    def run_command(self, command: str) -> None:
        """
        Runs the specified command using subprocess. Is used to run the before and after commands.
        """
        if command != "":
            process = subprocess.run(command)
            self.logger.debug(f"Ran command: {command} with output: {process.stdout.decode()}")
