import logging
from functools import partial
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import QUrl

class ServerSourceStrGeneratorDialog(QDialog):
    """
    A dialog window that allows the user to configure a Snapserver source.
    """

    def __init__(self, parent=None, log_level=logging.DEBUG):
        super().__init__(parent)
        logging.getLogger().setLevel(log_level)
        logging.debug("Snapserver Source Dialog: Initialized.")

        self.setWindowTitle("Snapserver Source Configuration")
        self.setMinimumSize(380, 600)
        self.layout = QVBoxLayout()

        self.input_layout = QHBoxLayout()

        self.type_label = QLabel("Input Type:")
        self.type_dropdown = QComboBox()
        self.type_dropdown.addItems(["pipe", "librespot", "airplay", "file", "process", "tcp server", "tcp client", "alsa", "jack", "meta"])
        self.type_dropdown.currentIndexChanged.connect(self.update_input_fields)
        self.layout.addWidget(self.type_label)
        self.input_layout.addWidget(self.type_dropdown)

        self.info_button = QPushButton()
        self.info_button.setIcon(QIcon.fromTheme("dialog-information"))
        self.info_button.setToolTip("Show info for the desired source on Github.")
        self.info_button.clicked.connect(lambda: self.link_to_info_page_on_github())
        self.info_button.setFixedSize(30, 30)
        self.input_layout.addWidget(self.info_button)

        self.layout.addLayout(self.input_layout)

        self.input_fields_layout = QVBoxLayout()
        self.layout.addLayout(self.input_fields_layout)

        self.generate_button = QPushButton("Generate Input String")
        self.generate_button.clicked.connect(self.generate_input_string)
        self.layout.addWidget(self.generate_button)

        self.setLayout(self.layout)

        self.layout.setAlignment(Qt.AlignTop)

        self.update_input_fields()

    def update_input_fields(self) -> None:
        """
        Update the input fields based on the selected input type.
        """
        for i in reversed(range(self.input_fields_layout.count())):
            self.input_fields_layout.itemAt(i).widget().deleteLater()

        input_type = self.type_dropdown.currentText()
        logging.debug(f"Snapserver Source Dialog: Selected input type {input_type}.")

        if input_type == "pipe":
            self.add_input_field("Path to Pipe", "path/to/pipe", "Required")
            self.add_input_field("Name", "Pipe Name", "Required")
            self.add_input_field("Mode", "create or read", "Optional")
        elif input_type == "librespot":
            self.add_input_field("Path to Librespot", "path/to/librespot", "Required")
            self.add_input_field("Name", "Librespot Name", "Required")
            self.add_input_field("Username", "Username", "Optional")
            self.add_input_field("Password", "Password", "Optional")
            self.add_input_field("Device Name", "Snapcast", "Optional")
            self.add_input_field("Bitrate", "320", "Optional")
        elif input_type == "airplay":
            self.add_input_field("Path to Shairport-sync", "path/to/shairport-sync", "Required")
            self.add_input_field("Name", "Airplay Name", "Required")
            self.add_input_field("Device Name", "Snapcast", "Optional")
            self.add_input_field("Port", "5000", "Optional")
            self.add_input_field("Password", "Password", "Optional")
        elif input_type == "file":
            self.add_input_field("Path to PCM File", "path/to/pcm/file", "Required")
            self.add_input_field("Name", "File Name", "Required")
        elif input_type == "process":
            self.add_input_field("Path to Process", "path/to/process", "Required")
            self.add_input_field("Name", "Process Name", "Required")
            self.add_input_field("Params", "Process Params", "Optional")
        elif input_type == "tcp server":
            self.add_input_field("Listen IP", "127.0.0.1", "Required")
            self.add_input_field("Port", "4953", "Optional")
            self.add_input_field("Name", "TCP Server Name", "Required")
            self.add_input_field("Mode", "server", "Optional")
        elif input_type == "tcp client":
            self.add_input_field("Server IP", "127.0.0.1", "Required")
            self.add_input_field("Port", "4953", "Optional")
            self.add_input_field("Name", "TCP Client Name", "Required")
            self.add_input_field("Mode", "client", "Optional")
        elif input_type == "alsa":
            self.add_input_field("Name", "ALSA Name", "Required")
            self.add_input_field("Device", "default or hw:0,0", "Optional")
            self.add_input_field("Send Silence", "false", "Optional")
            self.add_input_field("Idle Threshold", "100", "Optional")
            self.add_input_field("Silence Threshold Percent", "0.0", "Optional")
        elif input_type == "jack":
            self.add_input_field("Name", "Jack Name", "Required")
            self.add_input_field("Sample Format", "48000:16:2", "Optional")
            self.add_input_field("Auto Connect", "", "Optional")
            self.add_input_field("Auto Connect Skip", "0", "Optional")
            self.add_input_field("Send Silence", "false", "Optional")
            self.add_input_field("Idle Threshold", "100", "Optional")
        elif input_type == "meta":
            self.add_input_field("Name", "Meta Name", "Required")
            self.add_input_field("Sources", "source1/source2/...", "Required")
            self.add_input_field("Codec", "null", "Optional")

    def add_input_field(self, label_text: str, placeholder_text: str ="", requirement: str ="Optional") -> None:
        """
        Add a labeled input field to the layout with tooltip and default text.

        Args:
            label_text (str): The text for the label.
            placeholder_text (str): The placeholder text for the input field.
            requirement (str): Indicates if the field is optional or required.
        """
        label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(f"{placeholder_text} ({requirement})")
        line_edit.setToolTip(f"{label_text} - {requirement}")
        self.input_fields_layout.addWidget(label)
        self.input_fields_layout.addWidget(line_edit)
        logging.debug(f"Snapserver Source Dialog: Added input field {label_text} ({requirement}).")


    def generate_input_string(self) -> None:
        """
        Generate the input string from the user inputs.
        """
        input_type = self.type_dropdown.currentText()
        inputs = [self.input_fields_layout.itemAt(i).widget().text() for i in range(self.input_fields_layout.count()) if i % 2 != 0]
        labels = [self.input_fields_layout.itemAt(i).widget().text() for i in range(self.input_fields_layout.count()) if i % 2 == 0]

        required_fields = {
            "pipe": ["Path to Pipe", "Name"],
            "librespot": ["Path to Librespot", "Name"],
            "airplay": ["Path to Shairport-sync", "Name"],
            "file": ["Path to PCM File", "Name"],
            "process": ["Path to Process", "Name"],
            "tcp server": ["Listen IP", "Name"],
            "tcp client": ["Server IP", "Name"],
            "alsa": ["Name"],
            "jack": ["Name"],
            "meta": ["Name", "Sources"]
        }

        for label, input_text in zip(labels, inputs):
            if label in required_fields[input_type] and not input_text:
                QMessageBox.warning(self, "Input Error", f"{label} is required.")
                logging.debug(f"Snapserver Source Dialog: Missing required field {label}.")
                return

        input_string = f"{input_type}://"
        if input_type == "pipe":
            input_string += f"/{inputs[0]}?name={inputs[1]}"
            if inputs[2]:
                input_string += f"&mode={inputs[2]}"
        elif input_type == "librespot":
            input_string += f"/{inputs[0]}?name={inputs[1]}"
            if inputs[2]:
                input_string += f"&username={inputs[2]}"
            if inputs[3]:
                input_string += f"&password={inputs[3]}"
            if inputs[4]:
                input_string += f"&devicename={inputs[4]}"
            if inputs[5]:
                input_string += f"&bitrate={inputs[5]}"
        elif input_type == "airplay":
            input_string += f"/{inputs[0]}?name={inputs[1]}"
            if inputs[2]:
                input_string += f"&devicename={inputs[2]}"
            if inputs[3]:
                input_string += f"&port={inputs[3]}"
            if inputs[4]:
                input_string += f"&password={inputs[4]}"
        elif input_type == "file":
            input_string += f"/{inputs[0]}?name={inputs[1]}"
        elif input_type == "process":
            input_string += f"/{inputs[0]}?name={inputs[1]}"
            if inputs[2]:
                input_string += f"&params={inputs[2]}"
        elif input_type == "tcp server":
            input_string += f"{inputs[0]}:{inputs[1]}?name={inputs[2]}"
            if inputs[3]:
                input_string += f"&mode={inputs[3]}"
        elif input_type == "tcp client":
            input_string += f"{inputs[0]}:{inputs[1]}?name={inputs[2]}"
            if inputs[3]:
                input_string += f"&mode={inputs[3]}"
        elif input_type == "alsa":
            input_string += f"/?name={inputs[0]}"
            if inputs[1]:
                input_string += f"&device={inputs[1]}"
            if inputs[2]:
                input_string += f"&send_silence={inputs[2]}"
            if inputs[3]:
                input_string += f"&idle_threshold={inputs[3]}"
            if inputs[4]:
                input_string += f"&silence_threshold_percent={inputs[4]}"
        elif input_type == "jack":
            input_string += f"/?name={inputs[0]}"
            if inputs[1]:
                input_string += f"&sampleformat={inputs[1]}"
            if inputs[2]:
                input_string += f"&autoconnect={inputs[2]}"
            if inputs[3]:
                input_string += f"&autoconnect_skip={inputs[3]}"
            if inputs[4]:
                input_string += f"&send_silence={inputs[4]}"
            if inputs[5]:
                input_string += f"&idle_threshold={inputs[5]}"
        elif input_type == "meta":
            input_string += f"/{inputs[1]}?name={inputs[0]}"
            if inputs[2]:
                input_string += f"&codec={inputs[2]}"

        logging.debug(f"Snapserver Source Dialog: Generated input string: {input_string}")
        QMessageBox.information(self, "Input String", f"Generated Input String:\n{input_string}")
        
    def link_to_info_page_on_github(self) -> None:
        
        dropdown_text = self.type_dropdown.currentText()
        match dropdown_text:
            case "pipe":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#pipe")
            case "librespot":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#librespot")
            case "airplay":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#airplay")
            case "file":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#file")
            case "process":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#process")
            case "tcp server":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#tcp-server")
            case "tcp client":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#tcp-client")
            case "alsa":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#alsa")
            case "jack":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#jack")
            case "meta":
                self.open_url("https://github.com/badaix/snapcast/blob/develop/doc/configuration.md#meta")
                
    def open_url(self, url: str) -> None:
        """
        Open a URL in the default web browser.

        Args:
            url (str): The URL to open.
        """
        logging.debug(f"Snapserver Source Dialog: Opening URL {url}.")
        QDesktopServices.openUrl(QUrl(url))