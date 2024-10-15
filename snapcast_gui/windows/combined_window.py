import logging
import os
import sys
import time

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QSplitter,
    QToolBar,
    QWidget,
    QApplication,
    QMessageBox,
    QStyleFactory,
)

from snapcast_gui.dialogs.path_input_dialog import PathInputDialog
from snapcast_gui.dialogs.server_source_str_generator_dialog import ServerSourceStrGeneratorDialog
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables
from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables
from snapcast_gui.dialogs.snapserver_configuration_editor import SnapserverConfigurationEditor


class CombinedWindow(QMainWindow):
    """A class that handles the union of the main window and client window into a single window.
    """
    def __init__(
        self,
        main_window: QWidget,
        client_window: QWidget,
        server_window: QWidget,
        settings_window: QWidget,
        snapcast_settings: SnapcastSettings,
        log_level: int,
    ):
        """
        Initializes the combinedwindow class.
        """
        super().__init__()
        self.log_level = log_level
        self.logger = logging.getLogger("CombinedWindow")
        self.logger.setLevel(self.log_level)

        self.settings_window = settings_window
        self.server_window = server_window
        self.snapcast_settings = snapcast_settings
        self.main_window = main_window

        self.setWindowTitle("Snapcast Gui {}".format(SnapcastGuiVariables.snapcast_gui_version))
        self.setWindowIcon(QIcon(SnapcastGuiVariables.snapcast_icon_path))
        self.setMinimumSize(250, 150)

        self.splitter = QSplitter()
        self.splitter.addWidget(main_window)
        self.splitter.addWidget(client_window)

        self.setCentralWidget(self.splitter)

        self.resize(1000, 650)
        main_window.resize(650, 650)
        client_window.resize(350, 650)

        self.toolbar = QToolBar("Toolbar")
        self.addToolBar(self.toolbar)

        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(
            lambda: self.toggle_settings_window())

        if sys.platform == "linux" or sys.platform == "darwin":
            self.server_action = QAction("Snapserver", self)
            self.server_action.triggered.connect(
                lambda: self.toggle_server_window())
        elif sys.platform == "win32":
            self.server_action = QAction("Snapserver (Unsupported)", self)
            self.server_action.setEnabled(False)
            self.server_action.setToolTip(
                "Snapserver is not supported on Windows")

        self.source_generator_action = QAction("Source Generator", self)
        self.source_generator_action.triggered.connect(
            lambda: ServerSourceStrGeneratorDialog().exec())
        self.source_generator_action.setToolTip(
            "Generate a Snapserver source configuration")
        
        self.snapserver_configuration_action = QAction("Snapserver Configuration", self)
        self.snapserver_configuration_action.triggered.connect(
            lambda: SnapserverConfigurationEditor().exec())
        self.snapserver_configuration_action.setToolTip(
            "Edit the Snapserver configuration")

        self.toolbar.addAction(self.settings_action)
        self.toolbar.addAction(self.server_action)
        self.toolbar.addAction(self.source_generator_action)
        self.toolbar.addAction(self.snapserver_configuration_action)

        self.update_paths()
        self.load_selected_theme()

    def toggle_settings_window(self) -> None:
        """
        Toggles the settings window.
        """
        self.logger.debug("Toggling settings window")
        if self.settings_window.isVisible():
            self.settings_window.hide()
            self.logger.debug("Hiding settings window")
        else:
            self.settings_window.show()
            self.logger.debug("Showing settings window")

    def toggle_server_window(self) -> None:
        """
        Toggles the server window.
        """
        if self.server_window.isVisible():
            self.server_window.hide()
        else:
            self.server_window.show()

    def find_program(self, program_name: str) -> str:
        if sys.platform in ["linux", "darwin"]:
            path_dirs = os.environ.get("PATH")
            if path_dirs:
                for directory in path_dirs.split(os.pathsep):
                    program_path = os.path.join(directory, program_name)
                    if os.path.exists(program_path) and os.access(program_path, os.X_OK):
                        return program_path

            dialog = PathInputDialog(program_name, self.log_level)
            if dialog.exec() == QDialog.Accepted:
                program_path = dialog.get_path()
                if os.path.exists(program_path) and os.access(program_path, os.X_OK):
                    return program_path

        elif sys.platform == "win32": 
            dialog = PathInputDialog(program_name, self.log_level)
            if dialog.exec() == QDialog.Accepted:
                program_path = dialog.get_path()
                if os.path.exists(program_path):
                    return program_path


        raise Exception(
            f"Unable to find path for program: {program_name} and no valid path provided by user"
        )

    def update_paths(self) -> None:
        """
        Updates the paths for the Snapclient and Snapserver executables.
        """
        try:
            if sys.platform == "linux":
                snapclient_path = self.find_program("snapclient")
                snapserver_path = self.find_program("snapserver")

                if not self.snapcast_settings.read_setting(
                    "Snapclient/enable_custom_path"
                ):
                    self.snapcast_settings.update_setting(
                        "Snapclient/Custom_Path", snapclient_path
                    )
                if not self.snapcast_settings.read_setting(
                    "Snapserver/enable_custom_path"
                ):
                    self.snapcast_settings.update_setting(
                        "Snapserver/Custom_Path", snapserver_path
                    )
                else:
                    custom_snapserver_path = self.snapcast_settings.read_setting(
                        "Snapserver/Custom_Path"
                    )
                    if not os.path.exists(custom_snapserver_path):
                        snapserver_path = self.find_program("snapserver")
                        self.snapcast_settings.update_setting(
                            "Snapserver/Custom_Path", snapserver_path
                        )

            elif sys.platform == "win32":
                snapclient_path = self.find_program("snapclient.exe")

                if not self.snapcast_settings.read_setting(
                    "Snapclient/enable_custom_path"
                ):
                    self.snapcast_settings.update_setting(
                        "Snapclient/Custom_Path", snapclient_path
                    )

            elif sys.platform == "darwin":
                snapclient_path = self.find_program("snapclient")

                if not self.snapcast_settings.read_setting(
                    "Snapclient/enable_custom_path"
                ):
                    self.snapcast_settings.update_setting(
                        "Snapclient/Custom_Path", snapclient_path
                    )

        except Exception as e:
            self.logger.error(f"Error updating paths: {e}")

    def load_selected_theme(self):
        """
        Loads the theme selected by the user in the settings window if available.
        """
        self.logger.debug("Loading selected theme")
        try:
            theme = self.snapcast_settings.read_setting("Themes/Current_Theme")
            self.logger.debug(f"Theme: {theme}")
            if theme:
                available_styles = QStyleFactory.keys()
                self.logger.debug(f"Available themes: {available_styles}")
                if theme in available_styles:
                    QApplication.setStyle(theme)
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"The selected theme '{theme}' is not available on your system. Do you want to use the default theme?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if QMessageBox.Yes:
                        self.logger.debug("Using default theme")
                        theme = self.find_default_theme()
                        self.snapcast_settings.update_setting("Themes/Current_Theme", theme)
                        self.logger.debug(f"Selected theme: {theme}")
                    else:
                        self.logger.debug("No matching theme found")
                        theme = QApplication.style().objectName()
                        self.snapcast_settings.update_setting("Themes/Current_Theme", theme)
                        self.logger.debug(f"Default theme: {theme}")
            else:
                self.logger.debug("No theme selected")
                theme = self.find_default_theme()
                self.snapcast_settings.update_setting("Themes/Current_Theme", theme)
                self.logger.debug(f"Default theme: {theme}")
        except Exception as e:
            self.logger.error(f"Error loading theme {theme}: {e}")

    def find_default_theme(self) -> str:
        """
        Finds the default theme for the application.

        Returns:
        - The default theme for the application.
        """
        self.logger.debug("Finding default theme")
        theme = QApplication.style().objectName()
        available_themes = QStyleFactory.keys()
        for available_theme in available_themes:
            if available_theme.lower() == theme.lower():
                self.logger.debug(f"Default theme found: {available_theme}")
                return available_theme
        self.logger.debug(f"Default theme not found, using the default application object style: {theme}")
        return theme
    
    def download_snapclient(self) -> None:
        """Downloads the snapclient executable for supported plaforms (Windows)
        """
        if sys.platform == "win32":
            logging.debug()
    
    def update_snapclient(self) -> None:
        """Updates the snapclient executable for supported platforms (Windows)
        """
        raise NotImplementedError("Still need to implement the update functionanlity")
