import logging
import os

from PySide6.QtCore import QSettings

from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables


class SnapcastSettings:
    """
    A class that handles the settings for the Snapcast GUI application.
    """

    def __init__(self, log_level: int) -> None:
        """
        Initializes the snapcastsettings object.

        Args:
            log_level: The log level to set for the application.
        """
        logging.getLogger().setLevel(log_level)

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

        settings = QSettings(SnapcastGuiVariables.settings_file_path, QSettings.IniFormat)
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
        settings = QSettings(SnapcastGuiVariables.settings_file_path, QSettings.IniFormat)
        settings.setValue(key, value)
        settings.sync()
        logging.debug("snapcastsettings: Updated setting: {} = {}".format(key, value))

    def read_setting(self, setting_name: str)-> str:
        """
        Reads a setting from the settings file with the given setting_name and returns its value.

        Returns:
            The value of the setting.
        """
        settings = QSettings(SnapcastGuiVariables.settings_file_path, QSettings.IniFormat)
        value = settings.value(setting_name)
        if value is None:
            value = ""
        if isinstance(value, str):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
        logging.debug(
            "snapcastsettings: Read setting: {} = {}, type {}".format(
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
            settings = QSettings(SnapcastGuiVariables.config_file_path, QSettings.IniFormat)
            ip_addresses = settings.value("SERVER/ip_addresses").split(",")
            for ip_address in ip_addresses:
                if ip_address == "":
                    ip_addresses.remove(ip_address)
            logging.debug("snapcastsettings: Read config file: {}".format(ip_addresses))
            return ip_addresses
        except IsADirectoryError:
            os.removedirs(os.path.dirname(SnapcastGuiVariables.config_file_path))
            logging.error(
                "snapcastsettings: File path is a directory: {}. Removing directory".format(
                    SnapcastGuiVariables.config_file_path
                )
            )
            return []
        except Exception as e:
            logging.error("snapcastsettings: Error reading config file: {}".format(e))
            return []

    def add_ip(self, ip: str) -> None:
        """
        Adds an IP address to the config file.
        
        Args:
            ip: The IP address to add.
        """
        try:
            settings = QSettings(SnapcastGuiVariables.config_file_path, QSettings.IniFormat)
            ip_addresses = settings.value("SERVER/ip_addresses", "localhost").split(",")
            ip_addresses.append(ip)
            settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
            settings.sync()
        except Exception as e:
            logging.error(
                f"snapcastsettings: Could not add IP Address to config file: {str(e)}"
            )
            return
        logging.debug(
            "snapcastsettings: IP Address {} added to config file.".format(ip)
        )

    def remove_ip(self, ip: str) -> None:
        """
        Removes an IP address from the config file.
        
        Args:
            ip: The IP address to remove.
        """
        try:
            settings = QSettings(SnapcastGuiVariables.config_file_path, QSettings.IniFormat)
            ip_addresses = settings.value("SERVER/ip_addresses", "localhost").split(",")
            ip_addresses.remove(ip)
            settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
            settings.sync()
        except Exception as e:
            logging.error(
                f"snapcastsettings: Could not remove IP Address from config file: {str(e)}"
            )
            return
        logging.debug(
            "snapcastsettings: IP Address {} removed from config file.".format(ip)
        )