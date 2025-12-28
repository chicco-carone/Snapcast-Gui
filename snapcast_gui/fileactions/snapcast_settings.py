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
            "general/autoconnect": False,
            "themes/current_theme": "",
            "behavior/enable_notifications": True,
            "snapclient/autostart": False,
            "snapclient/show_advanced_settings_on_startup": False,
            "snapclient/enable_custom_path": False,
            "snapclient/custom_path": "",
            "snapclient/ignore_popup": False,
            "snapclient/protocol": "tcp",
            "snapclient/port": "1705",
            "snapclient/show_connection_settings": False,
            "snapserver/autostart": False,
            "snapserver/config_before_start": "",
            "snapserver/config_after_start": "",
            "snapserver/ignore_popup": True,
            "shortcuts/open_settings": "Ctrl+O",
            "shortcuts/connect_disconnect": "Ctrl+C",
            "shortcuts/toggle_snapclient": "Ctrl+E",
            "shortcuts/toggle_snapserver": "Ctrl+R",
            "shortcuts/quit": "Ctrl+Q",
            "shortcuts/hide": "Ctrl+H",
        }

        settings = QSettings(
            SnapcastGuiVariables.settings_file_path, QSettings.IniFormat
        )
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
            SnapcastGuiVariables.settings_file_path, QSettings.IniFormat
        )
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
            SnapcastGuiVariables.settings_file_path, QSettings.IniFormat
        )
        value = settings.value(setting_name)
        if value is None:
            value = ""
        if isinstance(value, str):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
        self.logger.debug(
            "Read setting: {} = {}, type {}".format(setting_name, value, type(value))
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
                SnapcastGuiVariables.config_file_path, QSettings.IniFormat
            )
            existing_value = settings.value("SERVER/ip_addresses", "")
            if not existing_value:
                self.logger.debug("No IP addresses found in config file.")
                return []
            
            ip_addresses = existing_value.split(",")
            ip_addresses = [ip.strip() for ip in ip_addresses if ip.strip()]
            
            if len(ip_addresses) != len(existing_value.split(",")):
                settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
                settings.sync()
                self.logger.info("Removed empty IP addresses from config file.")
            
            self.logger.debug("Read config file: {}".format(ip_addresses))
            return ip_addresses
        except IsADirectoryError:
            os.removedirs(os.path.dirname(SnapcastGuiVariables.config_file_path))
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

        Raises:
            ValueError: If the IP address is empty or contains only whitespace.
        """
        ip_stripped = ip.strip()
        if not ip_stripped:
            raise ValueError("IP address cannot be empty or whitespace.")
        
        try:
            settings = QSettings(
                SnapcastGuiVariables.config_file_path, QSettings.IniFormat
            )
            # Check if setting exists; if not, initialize with empty string
            existing_value = settings.value("SERVER/ip_addresses", "")
            if existing_value:
                ip_addresses = existing_value.split(",")
                # Clean existing list of any empty entries
                ip_addresses = [addr.strip() for addr in ip_addresses if addr.strip()]
            else:
                ip_addresses = []
            
            ip_addresses.append(ip_stripped)
            settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
            settings.sync()
        except Exception as e:
            self.logger.error(f"Could not add IP Address to config file: {str(e)}")
            raise
        self.logger.debug("IP Address {} added to config file.".format(ip_stripped))

    def remove_ip(self, ip: str) -> None:
        """
        Removes an IP address from the config file.

        Args:
            ip: The IP address to remove.
        """
        try:
            settings = QSettings(
                SnapcastGuiVariables.config_file_path, QSettings.IniFormat
            )
            # Check if setting exists; if not, nothing to remove
            existing_value = settings.value("SERVER/ip_addresses", "")
            if not existing_value:
                self.logger.warning("No IP addresses to remove from config file.")
                return
            
            ip_addresses = existing_value.split(",")
            ip_addresses = [addr.strip() for addr in ip_addresses if addr.strip()]
            
            if ip in ip_addresses:
                ip_addresses.remove(ip)
            else:
                self.logger.warning(f"IP address {ip} not found in config file.")
                return
            
            settings.setValue("SERVER/ip_addresses", ",".join(ip_addresses))
            settings.sync()
        except Exception as e:
            self.logger.error(f"Could not remove IP Address from config file: {str(e)}")
            raise
        self.logger.debug("IP Address {} removed from config file.".format(ip))
