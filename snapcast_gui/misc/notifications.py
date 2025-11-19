import logging
import sys

from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables

from notifypy import Notify

class Notifications:
    """
    Class for sending notifications.
    """
    logger = logging.getLogger("Notifications")
    logger.setLevel(logging.INFO)

    @staticmethod
    def send_notify(title: str, message: str, snapcast_settings=None) -> None:
        """
        Sends a notification with the specified title and message. Handles the icon based on the platform.

        Args:
            title: The title of the notification.
            message: The message of the notification.
            snapcast_settings: Optional SnapcastSettings instance to check if notifications are enabled.
        """
        if snapcast_settings and not snapcast_settings.read_setting("behavior/enable_notifications"):
            return
        try:
            notification = Notify()
            notification.application_name = "Snapcast-Gui"
            notification.title = title
            notification.message = message
        except Exception as e:
            Notifications.logger.error("Platform not supported: {} {}".format(sys.platform, e))

        Notifications.logger.info("Sending notification: {}".format(message))

        if sys.platform.startswith("linux") or sys.platform.startswith("win"):
            notification.icon = SnapcastGuiVariables.snapcast_icon_path
        elif sys.platform.startswith("darwin"):
            notification.icon = None
        notification.send()
