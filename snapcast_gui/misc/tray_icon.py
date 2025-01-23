import logging
import sys

from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables

from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snapcast_gui.windows.main_window import MainWindow
    from snapcast_gui.windows.client_window import ClientWindow
    from snapcast_gui.windows.server_window import ServerWindow
    from snapcast_gui.windows.settings_window import SettingsWindow
    from snapcast_gui.windows.combined_window import CombinedWindow
    from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings


class TrayIcon(QSystemTrayIcon):
    """
    Represents a system tray icon for the Snapcast GUI application.
    """

    def __init__(
        self,
        main_window: 'MainWindow',
        client_window: 'ClientWindow',
        server_window: 'ServerWindow',
        settings_window: 'SettingsWindow',
        combined_window: 'CombinedWindow',
        snapcast_settings: 'SnapcastSettings',
        log_level: int,
    ):
        """
        Initializes a trayicon object.

        Args:
            main_window: The main window of the application.
            client_window: The window for managing Snapclient.
            server_window: The window for managing Snapserver.
            settings_window: The window for managing application settings.
            combined_window: The combined window that contains all the other windows.
            log_level: The log level for the application's logger.
        """
        super().__init__()

        self.setIcon(QIcon(SnapcastGuiVariables.snapcast_icon_path))
        self.setVisible(True)
        self.setToolTip("Snapcast Gui")

        self.logger = logging.getLogger("SnapcastGuiVariables")
        self.logger.setLevel(log_level)

        self.main_window = main_window
        self.client_window = client_window
        self.server_window = server_window
        self.settings_window = settings_window
        self.combined_window = combined_window
        self.snapcast_settings = snapcast_settings

        self.menu = QMenu()
        self.toggle_combined_window_action = self.menu.addAction("Hide")
        self.toggle_combined_window_action.triggered.connect(self.toggle_main_window)

        self.show_server_window_action = self.menu.addAction("Snapserver")
        self.show_server_window_action.triggered.connect(self.server_window.show)

        self.show_settings_window_action = self.menu.addAction("Settings")
        self.show_settings_window_action.triggered.connect(self.settings_window.show)

        self.menu.addSeparator()

        self.toggle_snapclient_action = self.menu.addAction("Start Snapclient")
        self.toggle_snapclient_action.triggered.connect(self.toggle_snapclient)

        if sys.platform == "linux" or sys.platform == "darwin":
            self.toggle_snapserver_action = self.menu.addAction("Start Snapserver")
            self.toggle_snapserver_action.triggered.connect(self.toggle_snapserver)
        elif sys.platform == "win32":
            self.toggle_snapserver_action = self.menu.addAction(
                "Start Snapserver (Unsupported)"
            )
            self.toggle_snapserver_action.setEnabled(False)
            self.toggle_snapserver_action.setToolTip(
                "Snapserver is not supported on Windows"
            )

        self.menu.addSeparator()

        self.exit_action = self.menu.addAction("Exit")
        self.exit_action.triggered.connect(QApplication.quit)

        self.setContextMenu(self.menu)

        self.load_shortcuts()

    def toggle_main_window(self) -> None:
        """
        Toggles the visibility of the combined window.

        If the combined window is visible, it will be hidden. If it is hidden, it will be shown.
        """
        if self.combined_window.isVisible():
            self.logger.debug("Hiding combined window")
            self.combined_window.hide()
            self.toggle_combined_window_action.setText("Show")
        else:
            self.logger.debug("Showing combined window")
            self.combined_window.show()
            self.toggle_combined_window_action.setText("Hide")

    def toggle_snapclient(self) -> None:
        """
        Toggles the Snapclient process.

        If the Snapclient process is not running, it will be started. If it is running, it will be stopped.
        """
        if self.client_window.snapclient_process is None:
            self.logger.debug("Starting Snapclient")
            self.client_window.run_snapclient()
            self.toggle_snapclient_action.setText("Stop Snapclient")
        else:
            self.logger.debug("Stopping Snapclient")
            self.client_window.stop_snapclient()
            self.toggle_snapclient_action.setText("Start Snapclient")

    def toggle_snapserver(self) -> None:
        """
        Toggles the Snapserver process.

        If the Snapserver process is not running, it will be started. If it is running, it will be stopped.
        """
        if self.server_window.snapserver_process is None:
            self.logger.debug("Starting Snapserver")
            self.server_window.run_snapserver()
            self.toggle_snapserver_action.setText("Stop Snapserver")
        else:
            self.logger.debug("Stopping Snapserver")
            self.server_window.stop_snapserver()
            self.toggle_snapserver_action.setText("Start Snapserver")

    def load_shortcuts(self) -> None:
        """
        Load shortcuts for various actions.

        This method loads shortcuts for opening settings, toggling Snapserver and Snapclient windows,
        quitting the application, and hiding the combined window.ù

        It reads the shortcuts from the settings file and creates QShortcut objects for each action.

        Shortcut actions are connected to their respective functions and logging statements are added
        to indicate when each shortcut is activated.
        """
        self.logger.debug("Loading shortcuts")
        self.settings_shortcut = QShortcut(
            QKeySequence(
                self.snapcast_settings.read_setting("shortcuts/open_settings")
            ),
            self.combined_window,
        )
        self.settings_shortcut.activated.connect(
            self.combined_window.toggle_settings_window
        )
        self.settings_shortcut.activated.connect(
            lambda: self.logger.debug("Open settings shortcut activated")
        )
        self.snapserver_shortcut = QShortcut(
            QKeySequence(
                self.snapcast_settings.read_setting("shortcuts/toggle_snapserver")
            ),
            self.combined_window,
        )
        self.snapserver_shortcut.activated.connect(
            self.combined_window.toggle_server_window
        )
        self.snapserver_shortcut.activated.connect(
            lambda: self.logger.debug("Toggle Snapserver shortcut activated")
        )
        self.snapclient_shortcut = QShortcut(
            QKeySequence(
                self.snapcast_settings.read_setting("shortcuts/toggle_snapclient")
            ),
            self.combined_window,
        )
        self.snapclient_shortcut.activated.connect(self.client_window.toggle_snapclient)
        self.snapclient_shortcut.activated.connect(
            lambda: self.logger.debug("Toggle Snapclient shortcut activated")
        )
        self.quit_shortcut = QShortcut(
            QKeySequence(self.snapcast_settings.read_setting("shortcuts/quit")),
            self.combined_window,
        )
        self.quit_shortcut.activated.connect(QApplication.quit)
        self.quit_shortcut.activated.connect(
            lambda: self.logger.debug("Quit shortcut activated")
        )
        self.hide_shortcut = QShortcut(
            QKeySequence(self.snapcast_settings.read_setting("shortcuts/hide")),
            self.combined_window,
        )
        self.hide_shortcut.activated.connect(self.combined_window.hide)
        self.hide_shortcut.activated.connect(
            lambda: self.logger.debug("Hide shortcut activated")
        )
