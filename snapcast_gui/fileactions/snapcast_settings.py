import logging
import os

from PySide6.QtCore import QSettings

from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables


class SnapcastSettings:
    """
    A class that handles the settings for the Snapcast GUI application.
    """

    def __init__(self, log_level: int = logging.DEBUG) -> None:
        """
        Initializes the snapcastsettings object.

        Args:
            log_level: The log level to set for the application.
        """
        self.logger = logging.getLogger("SnapcastSettings")
        self.logger.setLevel(log_level)

        self.ensure_settings()

    def ensure_settings(self) -> None:
        """
        Ensures that all settings are present in the settings file and have default values.
        """
        default_settings = {
            "General/AutoConnect": False,
            "Themes/Current_Theme": "",
            "Snapclient/autostart": False,
            "Snapclient/show_advanced_settings_on_startup": False,
            "Snapclient/enable_custom_path": False,
            "Snapclient/Custom_Path": "",
            "Snapclient/Ignore_Popup": False,
            "Snapserver/autostart": False,
            "Snapserver/Config_Before_Start": "",
            "Snapserver/Config_After_Start": "",
            "Shortcuts/Open_Settings": "Ctrl+O",
            "Shortcuts/Connect_Disconnect": "Ctrl+C",
            "Shortcuts/Toggle_Snapclient": "Ctrl+E",
            "Shortcuts/Toggle_Snapserver": "Ctrl+R",
            "Shortcuts/Quit": "Ctrl+Q",
            "Shortcuts/Hide": "Ctrl+H",
        }

        settings = QSettings(
            SnapcastGuiVariables.settings_file_path, QSettings.IniFormat)
        for key, value in default_settings.items():
            if not settings.contains(key):
                settings.setValue(key, value)
        settings.sync()

    def update_setting(self, key: str, value: str) -> None:
        """
        Updates a setting in the settings file with the given key and value.

        Args:
            key: The key of the setting to update.
            value: The new value for the setting.
        """
        settings = QSettings(
            SnapcastGuiVariables.settings_file_path, QSettings.IniFormat)
        settings.setValue(key, value)
        settings.sync()
        self.logger.debug("Updated setting: {} = {}".format(key, value))

    def read_setting(self, setting_name: str) -> str:
        """
        Reads a setting from the settings file with the given setting_name and returns its value.

        Returns:
            The value of the setting.
        """
        settings = QSettings(
            SnapcastGuiVariables.settings_file_path, QSettings.IniFormat)
        value = settings.value(setting_name)
        if value is None:
            value = ""
        if isinstance(value, str):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
        self.logger.debug(
            "Read setting: {} = {}, type {}".format(
                setting_name, value, type(value)
            )
        )
        return value

    def read_config_file(self) -> list[str]:
        """
        Reads the config file and returns the list of IP addresses.

        Returns:
            A list of IP addresses.

        Raises:
            Exception: If an error occurs while reading the config file.
            IsADirectoryError: If the config file path is a directory and removes the directory.
        """
        ip_addresses = []
        try:
            with open(SnapcastGuiVariables.config_file_path, "r") as f:
                f.close()
            settings = QSettings(
                SnapcastGuiVariables.config_file_path, QSettings.IniFormat)
            ip_addresses = settings.value("SERVER/ip_addresses").split(",")
            for ip_address in ip_addresses:
                if ip_address == "":
                    ip_addresses.remove(ip_address)
            self.logger.debug("Read config file: {}".format(ip_addresses))
            return ip_addresses
        except IsADirectoryError:
            os.removedirs(os.path.dirname(
                SnapcastGuiVariables.config_file_path))
            self.logger.error(
                "File path is a directory: {}. Removing directory".format(
                    SnapcastGuiVariables.config_file_path
                )
            )
            return []
        except Exception as e:
            self.logger.error("Error reading config file: {}".format(e))
            return []

    def add_ip(self, ip: str) -> None:
        """
        Adds an IP address to the config file.
        
        Args:
            ip: The IP address to add.
        """
        try:
            settings = QSettings(
                SnapcastGuiVariables.config_file_path, QSettings.IniFormat)
            ip_addresses = settings.value(
                "SERVER/ip_addresses", "localhost").split(",")
            ip_addresses.append(ip)
            settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
            settings.sync()
        except Exception as e:
            self.logger.error(
                f"Could not add IP Address to config file: {str(e)}"
            )
            return
        self.logger.debug(
            "IP Address {} added to config file.".format(ip)
        )

    def remove_ip(self, ip: str) -> None:
        """
        Removes an IP address from the config file.
        
        Args:
            ip: The IP address to remove.
        """
        try:
            settings = QSettings(
                SnapcastGuiVariables.config_file_path, QSettings.IniFormat)
            ip_addresses = settings.value(
                "SERVER/ip_addresses", "localhost").split(",")
            ip_addresses.remove(ip)
            settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
            settings.sync()
        except Exception as e:
            self.logger.error(
                f"Could not remove IP Address from config file: {str(e)}"
            )
            return
        self.logger.debug(
            "IP Address {} removed from config file.".format(ip)
        )

    def should_ignore_popup(self) -> bool:
        """
        Reads the setting for ignoring the popup and returns its value.

        Returns:
            bool: True if the popup should be ignored, False otherwise.
        """
        return self.read_setting("Snapclient/Ignore_Popup")

    def set_ignore_popup(self, value: bool) -> None:
        """
        Updates the setting for ignoring the popup.

        Args:
            value (bool): The new value for the setting.
        """
        self.update_setting("Snapclient/Ignore_Popup", str(value))
