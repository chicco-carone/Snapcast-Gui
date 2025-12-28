import json
from PySide6.QtCore import QUrl, QObject, Signal, Slot, QProcess
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtCore import QStandardPaths
from pathlib import Path
import sys
import os
import logging


class SnapcastGuiVariables(QObject):
    """
    This class contains variables and methods used in the Snapcast-Gui application.

    Attributes:
    - snapcast_github_url: A QUrl object representing the GitHub API URL for Snapcast.
    - snapcast_gui_github_url: A QUrl object representing the GitHub API URL for Snapcast-Gui.
    - snapcast_gui_version: A string representing the version of the Snapcast-Gui application.
    - snapclient_version: A string representing the version of snapclient.
    - snapserver_version: A string representing the version of snapserver.
    - config_dir: A string representing the path to the config directory.
    - log_file_path: A string representing the path to the log file.
    - settings_file_path: A string representing the path to the settings file.
    - config_file_path: A string representing the path to the config file.
    - log_level_file_path: A string representing the path to the log level file.
    - snapcast_icon_path: A string representing the path to the Snapcast icon.
    - github_icon_path: A string representing the path to the GitHub icon.
    """

    snapcast_github_url = QUrl(
        "https://api.github.com/repos/badaix/snapcast/releases/latest"
    )
    snapcast_gui_github_url = QUrl(
        "https://api.github.com/repos/chicco-carone/Snapcast-Gui/releases/latest"
    )
    snapcast_gui_version = "0.1.1"

    snapclient_version = ""
    snapserver_version = ""

    config_dir: str = str(
        Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
        / "snapcast-gui"
    )
    log_file_path: str = str(Path(config_dir) / "snapcast-gui.log")
    settings_file_path: str = str(Path(config_dir) / "settings.ini")
    config_file_path: str = str(Path(config_dir) / "config.ini")
    log_level_file_path: str = str(Path(config_dir) / "log_level.txt")

    snapcast_icon_path: str = ""
    github_icon_path: str = ""

    latest_version_fetched = Signal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("SnapcastGuiVariables")
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_version_fetched)

        SnapcastGuiVariables.initialize_icons()

    @staticmethod
    def get_program_version(program_path: str) -> str:
        """
        Get the version of a program using QProcess instead of subprocess.

        Parameters:
        - program_path: Path to the executable

        Returns:
        - Version string or empty string if detection fails
        """
        try:
            logger = logging.getLogger("SnapcastGuiVariables")
            process = QProcess()
            process.setProgram(program_path)
            process.setArguments(["--version"])
            process.start()

            if process.waitForFinished(5000):
                output = process.readAllStandardOutput().data().decode()
                error_output = process.readAllStandardError().data().decode()

                full_output = output + error_output

                lines = full_output.strip().split("\n")
                if lines:
                    first_line = lines[0].strip()
                    parts = first_line.split()
                    if len(parts) >= 2:
                        version = parts[1]
                        logger.debug(f"Detected {program_path} version: {version}")
                        return version

            logger.warning(
                f"Failed to get version for {program_path}. Process exit code: {process.exitCode()}"
            )
            return ""

        except Exception as e:
            logger = logging.getLogger("SnapcastGuiVariables")
            logger.error(f"Error getting version for {program_path}: {e}")
            return ""

    @staticmethod
    def initialize_program_versions():
        """
        Initialize snapclient and snapserver versions using QProcess.
        This should be called during application startup.
        """
        logger = logging.getLogger("SnapcastGuiVariables")
        logger.info("Initializing program versions...")

        default_snapclient_path = "snapclient"
        default_snapserver_path = "snapserver"

        SnapcastGuiVariables.snapclient_version = (
            SnapcastGuiVariables.get_program_version(default_snapclient_path)
        )
        SnapcastGuiVariables.snapserver_version = (
            SnapcastGuiVariables.get_program_version(default_snapserver_path)
        )

        logger.info(f"Snapclient version: {SnapcastGuiVariables.snapclient_version}")
        logger.info(f"Snapserver version: {SnapcastGuiVariables.snapserver_version}")

    @staticmethod
    def initialize_icons():
        """Initialize the paths for icon files, considering different environments."""

        snapcast_icon_system = "/usr/share/icons/hicolor/256x256/apps/snapcast-gui.png"
        github_icon_system = "/usr/share/icons/hicolor/256x256/apps/github.png"

        if os.path.exists(snapcast_icon_system):
            SnapcastGuiVariables.snapcast_icon_path = snapcast_icon_system
        else:
            SnapcastGuiVariables.snapcast_icon_path = (
                SnapcastGuiVariables.resource_path("icons/Snapcast.png")
            )

        if os.path.exists(github_icon_system):
            SnapcastGuiVariables.github_icon_path = github_icon_system
        else:
            SnapcastGuiVariables.github_icon_path = SnapcastGuiVariables.resource_path(
                "icons/Github.png"
            )

    @staticmethod
    def get_latest_version(git_url: QUrl):
        """
        Get the latest version from the provided GitHub URL.

        Parameters:
        - git_url: A QUrl object representing the GitHub API URL to fetch the latest release.
        """
        network_manager = QNetworkAccessManager()
        request = QNetworkRequest(git_url)
        network_manager.get(request)

    @Slot("QNetworkReply*")
    def on_version_fetched(self, reply):
        """
        Slot to handle the finished signal of the network request.

        Parameters:
        - reply: QNetworkReply object with the result of the HTTP request.
        """
        if reply.error() == reply.NoError:
            try:
                data = reply.readAll().data().decode()
                json_data = json.loads(data)
                latest_version = json_data.get("tag_name", "")
                self.latest_version_fetched.emit(latest_version)
            except Exception as e:
                self.latest_version_fetched.emit("")
        else:
            self.latest_version_fetched.emit("")

        reply.deleteLater()

    @staticmethod
    def resource_path(relative_path: str) -> str:
        """Gets the path to the resource, considering the PyInstaller bundle."""
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)


SnapcastGuiVariables.initialize_icons()
