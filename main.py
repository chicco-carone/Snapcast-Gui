import logging
import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from snapcast_gui.windows.combined_window import CombinedWindow
from snapcast_gui.fileactions.file_folder_checks import FileFolderChecks
from snapcast_gui.windows.main_window import MainWindow
from snapcast_gui.misc.notifications import Notifications
from snapcast_gui.windows.client_window import ClientWindow
from snapcast_gui.windows.server_window import ServerWindow
from snapcast_gui.windows.settings_window import SettingsWindow

from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables
from snapcast_gui.misc.logger_setup import LoggerSetup

def read_log_level(log_level_file_path: str) -> int:
    """
    Reads the log level from a file and returns the corresponding logging level.

    Args:
        log_level_file_path (str): The path to the log level file.

    Raises:
        FileNotFoundError: If the log level file is not found.
        Exception: If there is an error opening the log level file.
    """
    try:
        with open(log_level_file_path, "r+") as file:
            first_line = file.readline().strip().upper()
            if first_line == "":
                log_level = logging.INFO
                file.write("INFO\n")
            else:
                log_level = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL,
                }.get(first_line, logging.INFO)
    except FileNotFoundError:
        with open(log_level_file_path, "w") as file:
            log_level = logging.INFO
            file.write("INFO\n")
    except IsADirectoryError:
        os.removedirs(os.path.dirname(log_level_file_path))
        print("File path is a directory. Removing directory.")
        log_level = logging.INFO
    except Exception as e:
        Notifications.send_notify("Error", f"Error opening log level file: {e}")
        log_level = logging.DEBUG

    return log_level

def open_file(file_path: str) -> None:
    """
    Opens a file with the default application.

    Args:
        file_path (str): The path to the file.
    """
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication([])
    url = QUrl.fromLocalFile(file_path)
    QDesktopServices.openUrl(url)
    app.exit()
    
log_level = read_log_level(SnapcastGuiVariables.log_level_file_path)
log_file_path = SnapcastGuiVariables.log_file_path
LoggerSetup.setup_logging(log_file_path, log_level)

logger = LoggerSetup.get_logger("main")


def main():
    """
    The main function of the Snapcast-Gui application.

    It handles command line arguments, initializes the logging system,
    creates the application and window objects, and starts the event loop.
    """
    if len(sys.argv) > 1:
        option = sys.argv[1].lower()
        if option == "-h" or option == "--help":
            logger.debug("Showing help message")
            print("Usage: python main.py")
            print("Options:")
            print("  -h / --help             Show this help message and exit")
            print("  -v / --version          Show version and exit")
            print("  -c / --config           Open settings file")
            print("  -l / --log              Open log file")
            print("  -i / --ip               Open ip file")
            sys.exit(0)
        elif option == "-v" or option == "--version":
            logger.debug("Showing version")
            print("Snapcast-Gui version: {}".format(SnapcastGuiVariables.snapcast_gui_version))
        elif option == "-c" or option == "--config":
            open_file(SnapcastGuiVariables.settings_file_path)
            logger.debug("Opening settings file with open_file")
            sys.exit(0)
        elif option == "-l" or option == "--log":
            open_file(SnapcastGuiVariables.log_file_path)
            logger.debug("Opening log file with open_file")
            sys.exit(0)
        elif option == "-i" or option == "--ip":
            open_file(SnapcastGuiVariables.log_level_file_path)
            logger.debug("Opening log level file with open_file")
            sys.exit(0)
        else:
            logger.debug("Invalid argument")
            print("Invalid argument")
            print("")
            print("Usage: python main.py")
            print("Options:")
            print("  -h / --help             Show this help message and exit")
            print("  -v / --version          Show version and exit")
            print("  -c / --config           Open settings file")
            print("  -l / --log              Open log file")
            print("  -i / --ip               Open ip file")

            sys.exit(1)

    logger.info("Starting Snapcast-Gui")
    logger.debug("sys.platform: {}".format(sys.platform))

    snapcast_settings = SnapcastSettings(log_level)

    app = QApplication(sys.argv)
    client_window = ClientWindow(snapcast_settings, log_level)
    main_window = MainWindow(snapcast_settings, client_window, log_level)
    server_window = ServerWindow(snapcast_settings, log_level)
    settings_window = SettingsWindow(snapcast_settings, main_window, log_level)
    combined_window = CombinedWindow(
        main_window,
        client_window,
        server_window,
        settings_window,
        snapcast_settings,
        log_level,
    )
    main_window.create_tray_icon(
        main_window,
        client_window,
        server_window,
        settings_window,
        combined_window,
        snapcast_settings,
        log_level,
    )

    combined_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
