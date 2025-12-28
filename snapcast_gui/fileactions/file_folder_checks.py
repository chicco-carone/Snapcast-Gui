import logging
import os

from snapcast_gui.misc.notifications import Notifications
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables


class FileFolderChecks:
    @staticmethod
    def ensure_folder_creation() -> None:
        """
        Ensures that the required folders and files exist.
        """
        try:
            os.makedirs(SnapcastGuiVariables.config_dir, exist_ok=True)
            print(
                "Folders and files created successfully in {}".format(
                    SnapcastGuiVariables.config_dir
                )
            )
        except FileExistsError:
            print(
                "Folders and files already exist in {}".format(
                    SnapcastGuiVariables.config_dir
                )
            )
            pass
        except PermissionError:
            Notifications.send_notify(
                "Error", "Permission denied to create config folder."
            )
            logging.error("Permission denied to create folders and files.")
        except Exception as e:
            Notifications.send_notify("Error", f"Error creating folders and files: {e}")
            logging.error(f"Error creating folders and files: {e}")

    @staticmethod
    def create_missing_files() -> None:
        """
        Creates any missing files required by the application.

        Raises:
            IsADirectoryError: If a file path is a directory and removes the directory.
        """
        required_files = [
            SnapcastGuiVariables.log_file_path,
            SnapcastGuiVariables.settings_file_path,
            SnapcastGuiVariables.config_file_path,
            SnapcastGuiVariables.log_level_file_path,
        ]
        missing_files = [file for file in required_files if not os.path.exists(file)]
        if missing_files:
            for file in missing_files:
                os.makedirs(os.path.dirname(file), exist_ok=True)
                try:
                    with open(file, "w") as f:
                        f.write("")
                        print("snapcastsettings: Created missing file: {}".format(file))
                except IsADirectoryError:
                    os.removedirs(os.path.dirname(file))
                    logging.error(
                        "snapcastsettings: File path is a directory: {}. Removing directory".format(
                            file
                        )
                    )
                print("snapcastsettings: Created missing file: {}".format(file))

    @staticmethod
    def set_file_permission() -> None:
        """
        Sets the permissions for application files.
        """
        try:
            os.chmod(SnapcastGuiVariables.log_file_path, 0o644)
            os.chmod(SnapcastGuiVariables.log_level_file_path, 0o644)
            os.chmod(SnapcastGuiVariables.settings_file_path, 0o644)
        except PermissionError:
            Notifications.send_notify(
                "Error", "Permission denied to set file permissions."
            )
            logging.error("Permission denied to set file permissions.")
        except Exception as e:
            Notifications.send_notify("Error", f"Error setting file permissions: {e}")
            logging.error(f"Error setting file permissions: {e}")
