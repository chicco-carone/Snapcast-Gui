import logging
import json
from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from snapcast_gui.windows.main_window import MainWindow


class ServerInfoDialog(QDialog):
    """A class to create a dialog window to display server information.
    """
    def __init__(self, server_data_json, log_level: int = logging.DEBUG) -> None:
        super().__init__()
        logging.getLogger().setLevel(log_level)

        logging.debug("Server Info Dialog: Created Dialog Successfully")

        self.setWindowTitle("Server Information")

        self.server_data = server_data_json

        server_host = self.server_data["server"]["host"]
        snapserver_info = self.server_data["server"]["snapserver"]
        streams = self.server_data["streams"]
        
        self.layout = QVBoxLayout()

        self.add_info_label("Server Host Name", server_host["name"])
        self.add_info_label("Server Host IP", server_host["ip"])
        self.add_info_label("Server Host MAC", server_host["mac"])
        self.add_info_label("Server Host Architecture", server_host["arch"])
        self.add_info_label("Server Host OS", server_host["os"])

        self.add_info_label("Snapserver Name", snapserver_info["name"])
        self.add_info_label("Snapserver Version", snapserver_info["version"])
        self.add_info_label("Snapserver Protocol Version",
                            snapserver_info["protocolVersion"])
        self.add_info_label("Control Protocol Version",
                            snapserver_info["controlProtocolVersion"])

        for stream in streams:
            stream_id = stream["id"]
            stream_status = stream["properties"]["status"]
            stream_uri = stream["uri"]["raw"]

            self.add_info_label(f"Stream ID", stream_id)
            self.add_info_label(f"Stream Status", stream_status)
            self.add_info_label(f"Stream URI", stream_uri)

        self.setLayout(self.layout)

    def add_info_label(self, label_text: str, value: str) -> None:
        """
        Add a label to the layout with the provided text and value.

        Args:
            label_text (str): The text for the label.
            value (str): The value to display next to the label.
        """
        label = QLabel(f"{label_text}: {value}")
        label.setToolTip(f"{label_text}")
        self.layout.addWidget(label)
        logging.debug(f"Server Info Dialog: Added label for {label_text} with value {value}")
