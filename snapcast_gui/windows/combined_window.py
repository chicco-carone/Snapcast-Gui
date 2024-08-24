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
        logging.getLogger().setLevel(self.log_level)

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
            lambda: self.show_source_generator_dialog())
        self.source_generator_action.setToolTip(
            "Generate a Snapserver source configuration")

        self.toolbar.addAction(self.settings_action)
        self.toolbar.addAction(self.server_action)
        self.toolbar.addAction(self.source_generator_action)

        self.update_paths()
        self.load_selected_theme()

    def toggle_settings_window(self) -> None:
        """
        Toggles the settings window.
        """
        logging.debug("combinedwindow: Toggling settings window")
        if self.settings_window.isVisible():
            self.settings_window.hide()
            logging.debug("combinedwindow: Hiding settings window")
        else:
            self.settings_window.show()
            logging.debug("combinedwindow: Showing settings window")

    def toggle_server_window(self) -> None:
        """
        Toggles the server window.
        """
        if self.server_window.isVisible():
            self.server_window.hide()
        else:
            self.server_window.show()

    def show_source_generator_dialog(self) -> None:
        """
        Shows the source generator dialog.
        """
        source_generator_dialog = ServerSourceStrGeneratorDialog(self, self.log_level)
        source_generator_dialog.exec()

    def find_program(self, program_name: str) -> str:
        if sys.platform != "win32":
            path_dirs = os.environ.get("PATH")
            if path_dirs:
                for directory in path_dirs.split(os.pathsep):
                    program_path = os.path.join(directory, program_name)
                    if os.path.exists(program_path):
                        return program_path

            dialog = PathInputDialog(program_name, self.log_level)
            if dialog.exec() == QDialog.Accepted:
                program_path = dialog.get_path()
                if os.path.exists(program_path):
                    return program_path
        else:
            dialog = PathInputDialog(program_name, self.log_level)
            if dialog.exec() == QDialog.Accepted:
                program_path = dialog.get_path()
                if os.path.exists(program_path):
                    return program_path

        raise Exception(
            f"Unable to find path for program: {
                program_name} and no valid path provided by user"
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
            logging.error(f"combinedwindow: Error updating paths: {e}")

    def load_selected_theme(self):
        """
        Loads the theme selected by the user in the settings window if available.
        """
        logging.debug("combinedwindow: Loading selected theme")
        try:
            theme = self.snapcast_settings.read_setting("Themes/Current_Theme")
            logging.debug(f"combinedwindow: Theme: {theme}")
            if theme:
                available_styles = QStyleFactory.keys()
                logging.debug(f"combinedwindow: Available themes: {available_styles}")
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
                        logging.debug("combinedwindow: Using default theme")
                        theme = self.find_default_theme()
                        self.snapcast_settings.update_setting("Themes/Current_Theme", theme)
                        logging.debug(f"combinedwindow: Selected theme: {theme}")
                    else:
                        logging.debug("combinedwindow: No matching theme found")
                        theme = QApplication.style().objectName()
                        self.snapcast_settings.update_setting("Themes/Current_Theme", theme)
                        logging.debug(f"combinedwindow: Default theme: {theme}")
            else:
                logging.debug("combinedwindow: No theme selected")
                theme = self.find_default_theme()
                self.snapcast_settings.update_setting("Themes/Current_Theme", theme)
                logging.debug(f"combinedwindow: Default theme: {theme}")
        except Exception as e:
            logging.error(f"combinedwindow: Error loading theme {theme}: {e}")

    def find_default_theme(self) -> str:
        """
        Finds the default theme for the application.

        Returns:
        - The default theme for the application.
        """
        logging.debug("combinedwindow: Finding default theme")
        theme = QApplication.style().objectName()
        available_themes = QStyleFactory.keys()
        for available_theme in available_themes:
            if available_theme.lower() == theme.lower():
                logging.debug(f"combinedwindow: Default theme found: {available_theme}")
                return available_theme
        logging.debug(f"combinedwindow: Default theme not found, using the default application object style: {theme}")
        return theme
