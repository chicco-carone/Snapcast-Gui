import logging
import os
import shutil
import subprocess
import sys

from PySide6.QtCore import QStandardPaths, Qt, QUrl, QTimer
from PySide6.QtGui import QIcon, QTextCursor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStyleFactory,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings
    from snapcast_gui.windows.main_window import MainWindow


class SettingsWindow(QMainWindow):
    """
    Represents the settings window of the Snapcast-Gui application.
    """

    def __init__(self, snapcast_settings: "SnapcastSettings", main_window: "MainWindow", log_level: int):
        super().__init__()
        logging.getLogger().setLevel(log_level)

        self.snapcast_settings = snapcast_settings
        self.main_window = main_window
        self.log_file_path = SnapcastGuiVariables.log_file_path
        self.log_level_file_path = SnapcastGuiVariables.log_level_file_path

        self.setWindowTitle("Snapcast Gui Settings")
        self.setMinimumSize(700, 400)

        self.setWindowIcon(QIcon(SnapcastGuiVariables.snapcast_icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar_layout = QVBoxLayout()
        main_layout.addLayout(self.sidebar_layout, 1)

        self.settings_layout = QVBoxLayout()
        main_layout.addLayout(self.settings_layout, 2)
        self.settings_layout.setAlignment(Qt.AlignTop)

        self.setup_sidebar()

    def setup_sidebar(self):
        """
        Sets up the sidebar for the settings window.

        This method creates the sidebar for the settings window and adds the items to the sidebar list.
        It also connects the currentRowChanged signal of the sidebar_options QListWidget to the show_settings method.
        """
        self.sidebar_label = QLabel("Settings")
        self.sidebar_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.sidebar_label)
        self.sidebar_label.setObjectName("sidebar_label")
        self.sidebar_layout.setObjectName("sidebar_layout")

        self.sidebar_options = QListWidget()
        self.sidebar_options.addItems(
            ["Themes", "Snapclient", "Snapserver", "Shortcuts", "Logs", "About"]
        )
        self.sidebar_options.currentRowChanged.connect(self.show_settings)
        self.sidebar_options.setObjectName("sidebar_options")
        self.sidebar_layout.addWidget(self.sidebar_options)
        self.sidebar_options.setFixedWidth(150)

    def show_settings(self, index: int):
        """
        Clears the settings layout and shows the settings based on the index of the sidebar.

        Parameters:
            index: The index of the sidebar.
        """
        self.clear_settings_layout()
        match index:
            case 0:
                self.setup_theme_settings()
            case 1:
                self.setup_snapclient_settings()
            case 2:
                self.setup_snapserver_settings()
            case 3:
                self.setup_shortcut_settings()
            case 4:
                self.setup_log_settings()
            case 5:
                self.setup_about_settings()

    def clear_settings_layout(self):
        """
        Clears the settings layout to prepare for the new one.

        This method removes all widgets from the settings layout and any additional layouts (such as shortcut layout
        and horizontal log layout) that may exist.

        Note:
            - The `settings_layout` is assumed to be a layout object that contains the settings widgets.
            - The `shortcut_layout` and `horizontal_log_layout` are optional layouts that may exist within the`settings_layout`.
        """
        logging.debug("Clearing settings layout")
        for i in reversed(range(self.settings_layout.count())):
            widget = self.settings_layout.itemAt(i).widget()
            if widget:
                logging.debug(f"Removing widget: {widget}")
                self.settings_layout.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()

        if hasattr(self, "shortcut_layout") and self.shortcut_layout:
            logging.debug("Shortcut layout exists, removing...")
            while self.shortcut_layout.count():
                item = self.shortcut_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    logging.debug(f"Removing shortcut widget: {widget}")
                    widget.setParent(None)
                    widget.deleteLater()
            logging.debug("Removing shortcut layout from main layout")
            self.settings_layout.removeItem(self.shortcut_layout)
            self.shortcut_layout = None

        if hasattr(self, "horizontal_log_layout") and self.horizontal_log_layout:
            logging.debug("Horizontal log layout exists, removing...")
            while self.horizontal_log_layout.count():
                item = self.horizontal_log_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    logging.debug(f"Removing horizontal log widget: {widget}")
                    widget.setParent(None)
                    widget.deleteLater()
            logging.debug("Removing horizontal log layout from main layout")
            self.settings_layout.removeItem(self.horizontal_log_layout)
            self.horizontal_log_layout = None

        self.settings_layout.update()

    def setup_theme_settings(self):
        """
        Sets up the theme settings.

        This method creates and configures the UI elements related to theme settings,
        such as labels and a combo box for selecting the theme. It also connects the
        appropriate signals to their respective slots.
        """
        logging.info("SettingWindow: Setting up theme settings")
        theme_label = QLabel("Theme Settings")
        theme_label.setAlignment(Qt.AlignCenter)
        theme_label.setObjectName("theme_label")
        self.settings_layout.addWidget(theme_label)

        theme_combo_label = QLabel("Theme")
        theme_combo_label.setObjectName("theme_combo_label")
        self.settings_layout.addWidget(theme_combo_label)

        self.theme_combo = QComboBox()
        self.populate_theme_dropdown()
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        current_theme = self.snapcast_settings.read_setting("Themes/Current_Theme")
        index = self.theme_combo.findText(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(
            lambda: self.snapcast_settings.update_setting(
                "Themes/Current_Theme", self.theme_combo.currentText()
            )
        )
        self.theme_combo.setObjectName("theme_combo")
        self.settings_layout.addWidget(self.theme_combo)

    def change_theme(self):
        """
        Changes the theme based on the selected theme in the dropdown.

        This method retrieves the selected theme from the dropdown and sets it as the application's style.
        """
        style_name = self.theme_combo.currentText()
        logging.debug("settingswindow: Changing theme to " + style_name)
        QApplication.setStyle(style_name)

    def populate_theme_dropdown(self):
        """
        Populates the theme dropdown with the available styles (only works while using system libraries).
        """
        available_styles = QStyleFactory.keys()
        logging.debug("settingswindow: Available styles: " + str(available_styles))
        self.theme_combo.addItems(available_styles)

    def setup_snapclient_settings(self):
        """
        Sets up the snapclient settings.

        This method initializes and configures the UI elements related to snapclient settings.
        It creates labels, checkboxes, and text fields for various snapclient settings.
        It also connects the appropriate signals to update the settings when the user interacts with the UI.
        """
        logging.info("SettingWindow: Setting up snapclient settings")
        autostart_snapclient = self.snapcast_settings.read_setting(
            "Snapclient/autostart"
        )
        show_advanced_settings = self.snapcast_settings.read_setting(
            "Snapclient/show_advanced_settings_on_startup"
        )
        snapclient_label = QLabel("Snapclient Settings")
        snapclient_label.setAlignment(Qt.AlignCenter)
        snapclient_label.setObjectName("snapclient_label")
        self.settings_layout.addWidget(snapclient_label)

        self.autostart_snapclient_checkbox = QCheckBox("Automatic Start Snapclient")
        self.autostart_snapclient_checkbox.setChecked(autostart_snapclient)
        self.autostart_snapclient_checkbox.setObjectName(
            "autostart_snapclient_checkbox"
        )
        self.settings_layout.addWidget(self.autostart_snapclient_checkbox)
        self.autostart_snapclient_checkbox.stateChanged.connect(
            lambda: self.snapcast_settings.update_setting(
                "Snapclient/autostart", self.autostart_snapclient_checkbox.isChecked()
            )
        )
        # self.autostart_snapclient_checkbox.stateChanged.connect(lambda: self.setup_snapclient_autostart_settings(self.autostart_snapclient_checkbox.isChecked()))

        if autostart_snapclient:
            self.setup_snapclient_autostart_settings(autostart_snapclient)

        self.show_advanced_settings_checkbox = QCheckBox("Show Advanced Settings")
        self.show_advanced_settings_checkbox.setChecked(show_advanced_settings)
        self.show_advanced_settings_checkbox.setObjectName(
            "show_advanced_settings_checkbox"
        )
        self.settings_layout.addWidget(self.show_advanced_settings_checkbox)
        self.show_advanced_settings_checkbox.stateChanged.connect(
            lambda: self.snapcast_settings.update_setting(
                "Snapclient/Show_Advanced_Settings_on_startup",
                self.show_advanced_settings_checkbox.isChecked(),
            )
        )

        self.advanced_snapclient_settings_label = QLabel(
            "Advanced Settings (Proceed With Caution)"
        )
        self.advanced_snapclient_settings_label.setObjectName("advanced_snapclient_settings_label")
        self.settings_layout.addWidget(self.advanced_snapclient_settings_label)

        self.custom_snapclient_path_checkbox = QCheckBox("Enable Custom Path")
        self.custom_snapclient_path_checkbox.stateChanged.connect(
            lambda: self.snapcast_settings.update_setting(
                "Snapclient/Enable_Custom_Path", self.custom_snapclient_path_checkbox.isChecked()
            )
        )
        self.custom_snapclient_path_checkbox.stateChanged.connect(
            lambda: self.custom_snapclient_path_text.setEnabled(
                self.custom_snapclient_path_checkbox.isChecked()
            )
        )
        self.custom_snapclient_path_checkbox.setObjectName("custom_snapclient_path_checkbox")
        self.settings_layout.addWidget(self.custom_snapclient_path_checkbox)

        self.custom_snapclient_path_text = QTextEdit()
        self.custom_snapclient_path_text.setPlaceholderText("Custom Path")
        self.custom_snapclient_path_text.setText(
            self.snapcast_settings.read_setting("Snapclient/Custom_Path")
        )
        self.custom_snapclient_path_text.setFixedHeight(35)
        self.custom_snapclient_path_text.setToolTip(
            "Set the custom path for snapclient (eg: /usr/bin/snapclient has to be absolute path)"
        )
        self.custom_snapclient_path_text.setPlaceholderText(
            "Custom Path (eg: /usr/bin/snapclient)"
        )
        self.custom_snapclient_path_text.setObjectName("custom_snapclient_path_text")
        self.settings_layout.addWidget(self.custom_snapclient_path_text, alignment=Qt.AlignTop)
        if self.snapcast_settings.read_setting("Snapclient/Enable_Custom_Path"):
            self.custom_snapclient_path_text.setEnabled(True)
        else:
            self.custom_snapclient_path_text.setEnabled(False)

    def setup_snapclient_autostart_settings(self, autostart_snapclient: bool):
        """
        Sets up the snapclient autostart settings based on the value of autostart_snapclient.

        If autostart_snapclient is False, the method removes any existing autostart settings widgets from the layout.
        If autostart_snapclient is True, the method creates and adds the autostart settings widgets to the layout.
        """

        if not autostart_snapclient:
            if hasattr(self, "autoconnect_settings") and self.autoconnect_settings is not None:
                self.settings_layout.removeWidget(self.autoconnect_settings)
                self.autoconnect_settings.deleteLater()
                self.autoconnect_settings: Optional[QLabel] = None

            if hasattr(self, "default_ip_dropdown") and self.default_ip_dropdown is not None:
                self.settings_layout.removeWidget(self.default_ip_dropdown)
                self.default_ip_dropdown.deleteLater()
                self.default_ip_dropdown: Optional[QComboBox] = None

            if hasattr(self, "default_audio_engine_dropdown") and self.default_audio_engine_dropdown is not None:
                self.settings_layout.removeWidget(self.default_audio_engine_dropdown)
                self.default_audio_engine_dropdown.deleteLater()
                self.default_audio_engine_dropdown: Optional[QComboBox] = None

            if hasattr(self, "command_after_launch") and self.command_after_launch is not None:
                self.settings_layout.removeWidget(self.command_after_launch)
                self.command_after_launch.deleteLater()
                self.command_after_launch: Optional[QTextEdit] = None
        else:
            if not hasattr(self, "autoconnect_settings"):
                self.autoconnect_settings = QLabel("Autoconnect Settings")
                self.default_ip_dropdown = QComboBox()
                self.default_ip_dropdown.addItems(
                    self.snapcast_settings.read_config_file()
                )
                self.default_audio_engine_dropdown = QComboBox()
                self.default_audio_engine_dropdown.addItems(["Alsa", "Pulseaudio"])
                self.command_after_launch = QTextEdit()
                self.command_after_launch.setPlaceholderText(
                    "Command to run after snapclient is launched"
                )

                self.settings_layout.addWidget(self.autoconnect_settings)
                self.settings_layout.addWidget(self.default_ip_dropdown)
                self.settings_layout.addWidget(self.default_audio_engine_dropdown)
                self.settings_layout.addWidget(self.command_after_launch)

    def setup_snapserver_settings(self):
        """
        Sets up the snapserver settings.

        This method creates and configures the UI elements related to snapserver settings,
        such as the snapserver label and the automatic start checkbox.

        """
        logging.info("SettingWindow: Setting up snapserver settings")
        snapserver_label = QLabel("Snapserver Settings")
        snapserver_label.setAlignment(Qt.AlignCenter)
        snapserver_label.setObjectName("snapserver_label")
        self.settings_layout.addWidget(snapserver_label)

        autostart_snapserver = QCheckBox("Automatic Start Snapserver")
        autostart_snapserver.setChecked(
            self.snapcast_settings.read_setting("Snapserver/autostart")
        )
        autostart_snapserver.setObjectName("autostart_snapserver")
        self.settings_layout.addWidget(autostart_snapserver)

        advanced_snapserver_settings_label = QLabel("Advanced Settings (Proceed With Caution)")
        advanced_snapserver_settings_label.setObjectName("advanced_snapserver_settings_label")
        self.settings_layout.addWidget(advanced_snapserver_settings_label)

        custom_snapserver_path_checkbox = QCheckBox("Enable Custom Path")
        custom_snapserver_path_checkbox.setObjectName("custom_snapserver_path_checkbox")
        self.settings_layout.addWidget(custom_snapserver_path_checkbox)

        custom_snapserver_path_text = QTextEdit()
        custom_snapserver_path_text.setPlaceholderText("Custom Path")
        custom_snapserver_path_text.setText(
            self.snapcast_settings.read_setting("Snapclient/Custom_Path")
        )
        custom_snapserver_path_text.setFixedHeight(35)
        custom_snapserver_path_text.setToolTip(
            "Set the custom path for snapclient (eg: /usr/bin/snapclient has to be absolute path)"
        )
        custom_snapserver_path_text.setPlaceholderText(
            "Custom Path (eg: /usr/bin/snapclient)"
        )
        custom_snapserver_path_text.setObjectName("custom_path_text")
        self.settings_layout.addWidget(custom_snapserver_path_text, alignment=Qt.AlignTop)
        if self.snapcast_settings.read_setting("Snapserver/Enable_Custom_Path"):
            custom_snapserver_path_text.setEnabled(True)
        else:
            custom_snapserver_path_text.setEnabled(False)

    def setup_shortcut_settings(self):
        """
        Sets up the shortcut settings in the settingswindow.

        This method creates and configures the shortcut settings layout, including
        the shortcut labels, shortcut layout, and save shortcuts button.
        """
        logging.info("SettingWindow: Setting up shortcut settings")
        shortcut_label = QLabel("Shortcut Settings")
        shortcut_label.setAlignment(Qt.AlignCenter)
        shortcut_label.setObjectName("shortcut_label")
        self.settings_layout.addWidget(shortcut_label)

        self.shortcut_layout = QVBoxLayout()
        self.shortcut_layout.setAlignment(Qt.AlignTop)
        self.settings_layout.addLayout(self.shortcut_layout)
        self.shortcut_layout.setObjectName("shortcut_layout")
        self.shortcuts = {}

        self.create_shortcut("Open Settings", "Open_Settings")
        self.create_shortcut("Connect Disconnect", "Connect_Disconnect")
        self.create_shortcut("Toggle Snapclient", "Toggle_Snapclient")
        self.create_shortcut("Toggle Snapserver", "Toggle_Snapserver")
        self.create_shortcut("Quit", "Quit")
        self.create_shortcut("Hide", "Hide")

        shortcut_alert_label = QLabel(
            "Note: Shortcuts will only work when the main window is in focus."
        )
        shortcut_alert_label.setObjectName("shortcut_alert_label")
        self.settings_layout.addWidget(shortcut_alert_label)

        save_shortcuts_button = QPushButton("Save Shortcuts")
        save_shortcuts_button.clicked.connect(self.save_shortcuts)
        save_shortcuts_button.setObjectName("save_shortcuts_button")
        self.settings_layout.addWidget(save_shortcuts_button)

        apply_shortcuts_button = QPushButton("Apply Shortcuts")
        apply_shortcuts_button.clicked.connect(self.main_window.tray_icon.load_shortcuts)

    def create_shortcut(self, action_name, shortcut_config_name):
        """
        Creates a shortcut with the given action name and shortcut config name.

        Args:
            action_name (str): The name of the action associated with the shortcut.
            shortcut_config_name (str): The name of the shortcut configuration.
        """
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setObjectName("{}_shortcut_layout".format(action_name))

        label = QLabel(action_name)
        label.setObjectName("{}_label".format(action_name))
        shortcut_edit = QKeySequenceEdit()
        shortcut_edit.setKeySequence(
            self.snapcast_settings.read_setting("Shortcuts/" + shortcut_config_name)
        )
        shortcut_edit.setObjectName("{}_shortcut_edit".format(action_name))
        clear_shortcut_button = QPushButton()
        clear_shortcut_button.setText("Clear")
        clear_shortcut_button.setObjectName(
            "{}_clear_shortcut_button".format(action_name)
        )

        clear_shortcut_button.clicked.connect(shortcut_edit.clear)

        layout.addWidget(label)
        layout.addWidget(shortcut_edit)
        layout.addWidget(clear_shortcut_button)

        self.shortcut_layout.addLayout(layout)

    def save_shortcuts(self):
        """
        Saves the shortcuts to the settings file.

        This method iterates over the shortcut layout and retrieves the key-value pairs
        for each shortcut. It then updates the corresponding setting in the snapcast
        settings file. Finally, it logs a debug message indicating that the shortcuts
        have been saved successfully.
        """
        for i in range(self.shortcut_layout.count()):
            layout = self.shortcut_layout.itemAt(i)
            key = layout.itemAt(0).widget().text().replace(" ", "_")
            value = layout.itemAt(1).widget().keySequence().toString()
            self.snapcast_settings.update_setting("Shortcuts/{}".format(key), value)
        logging.debug("settingswindow: Shortcuts saved successfully.")

    def setup_log_settings(self):
        """
        Sets up the log settings and displays the logs from the log file.

        This method adds a log label and a log area to the settings layout. It reads the logs from the log file
        and displays them in the log area. It also adds buttons to open the log file in the default text editor
        and refresh the log file.
        """
        logging.info("settingswindow: Setting up log settings")

        log_label = QLabel("Log")
        log_label.setAlignment(Qt.AlignCenter)
        log_label.setObjectName("log_label")
        self.settings_layout.addWidget(log_label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setObjectName("log_area")
        self.update_log()
        logging.debug("settingswindow: Log file read successfully.")
        self.settings_layout.addWidget(self.log_area)
        self.settings_layout.setAlignment(Qt.AlignTop)

        self.horizontal_log_layout = QHBoxLayout()
        self.horizontal_log_layout.setAlignment(Qt.AlignTop)
        self.horizontal_log_layout.setObjectName("horizontal_log_layout")

        open_file_button = QPushButton("Open Log File")
        open_file_button.clicked.connect(lambda: self.open_file(SnapcastGuiVariables.log_file_path))
        open_file_button.clicked.connect(
            lambda: logging.debug("settingswindow: Log file opened.")
        )
        open_file_button.setToolTip(
            "Opens the log file in the default text editor. {}".format(SnapcastGuiVariables.log_file_path)
        )
        open_file_button.setObjectName("open_file_button")
        self.horizontal_log_layout.addWidget(open_file_button)

        export_log_button = QPushButton("Export Log")
        export_log_button.clicked.connect(self.export_log)
        export_log_button.setToolTip("Exports the log file.")
        export_log_button.setObjectName("export_log_button")
        self.horizontal_log_layout.addWidget(export_log_button)
        self.settings_layout.addLayout(self.horizontal_log_layout)

        self.change_log_level_dropdown = QComboBox()
        self.change_log_level_dropdown.addItems(
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        try:
            with open(SnapcastGuiVariables.log_level_file_path, "r") as log_level_file:
                self.change_log_level_dropdown.setCurrentText(log_level_file.read().strip())
        except IsADirectoryError:
            os.removedirs(os.path.dirname(SnapcastGuiVariables.log_level_file_path))
            logging.error(
                f"settingswindow: Log level file path is a directory: {SnapcastGuiVariables.log_level_file_path}. Removing directory"
            )
        self.change_log_level_dropdown.currentIndexChanged.connect(
            self.update_log_level
        )
        self.change_log_level_dropdown.setObjectName("change_log_level_dropdown")
        self.change_log_level_dropdown.setToolTip(
            "Change the log level. (Only works after restarting the application)"
        )
        self.horizontal_log_layout.addWidget(self.change_log_level_dropdown)

        self.autoscroll_button = QPushButton()
        self.autoscroll_button.setText("Refresh Log")
        self.autoscroll_button.setObjectName("refresh_log_button")
        self.autoscroll_button.setToolTip("Refresh the log reading it from the file again")
        self.autoscroll_button.clicked.connect(self.update_log)
        self.horizontal_log_layout.addWidget(self.autoscroll_button)

    def update_log(self):
        try:
            logging.debug("settingswindow: Updating log")
            with open(SnapcastGuiVariables.log_file_path, "r") as log_file:
                self.log_area.setPlainText(log_file.read())
            self.log_area.moveCursor(QTextCursor.End)
            self.log_area.ensureCursorVisible()
        except Exception as e:
            logging.debug("settingswindow: Error while updating log: {}".format(e))

    def update_log_level(self):
        """
        Updates the log level in the log level file based on the selected log level in the dropdown
        """
        logging.info("settingswindow: Updating log level")
        try:
            with open(SnapcastGuiVariables.log_level_file_path, "w") as log_level_file:
                log_level_file.truncate(0)
                log_level_file.write(self.change_log_level_dropdown.currentText())
                logging.debug(
                    f"settingswindow: Log level updated to {self.change_log_level_dropdown.currentText()}"
                )
        except IsADirectoryError:
            os.removedirs(os.path.dirname(SnapcastGuiVariables.log_level_file_path))
            logging.error(
                f"settingswindow: Log level file path is a directory: {SnapcastGuiVariables.log_level_file_path}. Removing directory"
            )
        except Exception as e:
            logging.error(f"settingswindow: Error updating log level: {e}")
            QMessageBox.critical(self, "Error", "Error updating log level")

    def export_log(self):
        """
        Opens a dialog to select the path to export the log file.
        If no path is selected, the log file will be exported to the Downloads folder.
        """
        logging.info("settingswindow: Exporting log file")
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "", "Text Files (*.txt)", options=options
        )
        if file_path:
            shutil.copy(SnapcastGuiVariables.log_file_path, file_path)
            logging.debug(f"settingswindow: Log file exported to {file_path}")
        else:
            downloads_folder = QStandardPaths.writableLocation(
                QStandardPaths.DownloadLocation
            )
            file_name = "snapcast-gui.log"
            file_path = os.path.join(downloads_folder, file_name)
            shutil.copy(SnapcastGuiVariables.log_file_path, file_path)
            logging.debug(f"settingswindow: Log file exported to {file_path}")

    def setup_about_settings(self):
        """
        Sets up the about settings and gets the versions of snapclient and snapserver.

        This method adds labels to the settings layout to display information about the Snapcast-Gui version,
        Snapclient version, and Snapserver version.
        """
        logging.info("settingswindow: Setting up about settings")
        about_label = QLabel("About")
        about_label.setAlignment(Qt.AlignCenter)
        about_label.setObjectName("about_label")
        self.settings_layout.addWidget(about_label)

        snapcast_gui_version_label = QLabel(
            f"Snapcast-Gui Version: {SnapcastGuiVariables.snapcast_gui_version}"
        )
        snapcast_gui_version_label.setObjectName("snapcast_gui_version_label")
        self.settings_layout.addWidget(snapcast_gui_version_label)
        snapclient_version, snapserver_version = self.get_versions()
        snapclient_version_label = QLabel(f"Snapclient Version: {snapclient_version}")
        snapclient_version_label.setObjectName("snapclient_version_label")
        self.settings_layout.addWidget(snapclient_version_label)

        if sys.platform == "windows":
            snapserver_version_label = QLabel(f"Snapserver Version: Unsupported on windws")
            snapserver_version_label.setObjectName("snapserver_version_label")
            snapserver_version_label.setToolTip("Snapserver version is only available on Linux")
        else:
            snapserver_version_label = QLabel(f"Snapserver Version: {snapserver_version}")
            snapserver_version_label.setObjectName("snapserver_version_label")

        self.settings_layout.addWidget(snapserver_version_label)

        self.check_latest_version_button = QPushButton("Check Latest Version")
        self.check_latest_version_button.setToolTip("Check the latest version of Snapcast-Gui on Github")
        self.check_latest_version_button.setIcon(QIcon.fromTheme("system-search"))
        self.check_latest_version_button.clicked.connect(self.check_latest_version)
        self.check_latest_version_button.setObjectName("check_latest_version_button")
        self.settings_layout.addWidget(self.check_latest_version_button)


        github_button = QPushButton()
        github_button.setIcon(QIcon(SnapcastGuiVariables.github_icon_path))
        github_button.setFixedSize(40, 40)
        github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/chicco-carone/Snapcast-Gui")))
        github_button.setToolTip("Open Snapcast-Gui Github page")
        github_button.setObjectName("github_button")
        # self.settings_layout.addWidget(github_button)

    def check_latest_version(self):
        """
        Checks the latest version of Snapcast-Gui on Github.
        """
        latest_version = SnapcastGuiVariables.get_latest_version(SnapcastGuiVariables.snapcast_gui_github_url)
        if latest_version:
            if latest_version != SnapcastGuiVariables.snapcast_gui_version:
                QMessageBox.information(
                    self,
                    "New Version Available",
                    f"A new version of Snapcast-Gui is available: {latest_version}",
                )
            else:
                QMessageBox.information(
                    self,
                    "No New Version Available",
                    f"Snapcast-Gui is up to date: {SnapcastGuiVariables.snapcast_gui_version}",
                )

    def get_versions(self) -> tuple[str, str]:
        """
        Retrieves the versions of snapclient and snapserver using subprocess.

        Returns:
            A tuple containing the snapclient version and snapserver version.
        """
        snapclient_version = subprocess.run(
            [self.snapcast_settings.read_setting("Snapclient/Custom_Path"), "--version"], capture_output=True, text=True
        ).stdout.split()[1]
        snapserver_version = subprocess.run(
            [self.snapcast_settings.read_setting("Snapserver/Custom_Path"), "--version"], capture_output=True, text=True
        ).stdout.split()[1]
        logging.debug(f"settingswindow: Snapclient version: {snapclient_version}")
        logging.debug(f"settingswindow: Snapserver version: {snapserver_version}")
        return snapclient_version, snapserver_version

    def open_file(self, file_path: str):
        """
        Opens the file at the specified path.

        Parameters:
            file_path: The path to the file to be opened.
        """
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        logging.debug(f"settingswindow: Opening file at {file_path}")
