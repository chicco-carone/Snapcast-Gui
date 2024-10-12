import sys
import json
import logging

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QGroupBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt

class SnapserverConfigurationEditor(QDialog):
    def __init__(self, parent=None, log_level=logging.DEBUG):
        super().__init__()
        self.setWindowTitle("Snapserver Configuration Editor")
        
        self.setBaseSize(600, 300)
        self.setMinimumWidth(250)
        
        self.logger = logging.getLogger("SnapserverConfigurationEditor")
        self.logger.setLevel(log_level)
        self.logger.debug("Initialized.")

        self.config_file = "config_options.json"
        self.config = self.load_config()

        self.layout = QVBoxLayout()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        self.init_ui()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_config)
        self.layout.addWidget(self.scroll_area)
        self.layout.addWidget(self.save_button)
        self.scroll_area.setWidget(self.scroll_content)
        self.setLayout(self.layout)

    def load_config(self) -> dict:
        """
        Load the configuration from a JSON file.

        Returns:
            dict: The configuration data loaded from the file.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        with open(self.config_file, 'r') as file:
            config = json.load(file)
            logging.info("Configuration loaded from %s", self.config_file)
            return config

    def init_ui(self) -> None:
        """
        Initializes the user interface by creating and arranging widgets based on the configuration.

        This method iterates through the configuration sections and their respective options,
        creating a group box for each section and adding corresponding widgets for each option.
        The widgets are created using the `create_widget` method and are assigned tooltips
        based on the option descriptions. Each widget is also dynamically assigned as an
        attribute of the class instance for easy access.

        The created section group boxes are added to the scroll layout of the dialog.

        Returns:
            None
        """
        for section, options in self.config.items():
            section_group = QGroupBox(section.capitalize())
            section_layout = QFormLayout()

            for option, details in options.items():
                widget = self.create_widget(details)
                if widget:
                    widget.setToolTip(details['description'])
                    section_layout.addRow(option.capitalize(), widget)
                    setattr(self, f"{section}_{option}", widget)
                    logging.debug(
                        "Created widget for %s in section %s", option, section)

            section_group.setLayout(section_layout)
            self.scroll_layout.addWidget(section_group)
            logging.info("Added section: %s", section)

    def create_widget(self, details: dict) -> QLineEdit | QComboBox | QCheckBox | None:
        """
        Creates a widget based on the provided details.

        Args:
            details (dict): A dictionary containing the details for the widget creation.
                The dictionary should have the following keys:
                    - 'type' (str): The type of widget to create. Can be 'text', 'dropdown', or 'checkbox'.
                    - 'default' (str or bool): The default value for the widget. For 'text' and 'dropdown', this should be a string. For 'checkbox', this should be a boolean.
                    - 'options' (list, optional): A list of options for the dropdown widget. Required if 'type' is 'dropdown'.

        Returns:
            QLineEdit | QComboBox | QCheckBox | None: The created widget, or None if the type is not recognized.
        """
        widget = None
        if details['type'] == 'text':
            widget = QLineEdit()
            widget.setPlaceholderText(details['default'])
        elif details['type'] == 'dropdown':
            widget = QComboBox()
            widget.addItems(details['options'])
            widget.setCurrentText(details['default'])
        elif details['type'] == 'checkbox':
            widget = QCheckBox()
            widget.setChecked(details['default'])

        logging.debug("Widget created: %s", details)
        return widget

    def save_config(self) -> None:
        """
        Saves the current configuration to a JSON file.

        This method iterates over the sections and options in the `self.config` dictionary,
        retrieves the corresponding widget values, and constructs a new configuration dictionary.
        The configuration is then written to the file specified by `self.config_file`.

        The widget values are retrieved based on the type specified in the `details` dictionary:
        - 'text': Retrieves the text from the widget or its placeholder text if empty.
        - 'dropdown': Retrieves the currently selected text from the dropdown widget.
        - 'checkbox': Retrieves the checked state of the checkbox widget.

        The resulting configuration is saved in JSON format with an indentation of 4 spaces.

        Raises:
            AttributeError: If a widget corresponding to a section and option is not found.

        Logs:
            Info: Logs the file path where the configuration is saved.
        """
        config: dict[str, dict[str, str | bool]] = {}
        for section, options in self.config.items():
            config[section] = {}
            for option, details in options.items():
                widget = getattr(self, f"{section}_{option}")
                if details['type'] == 'text':
                    value = widget.text() or widget.placeholderText()
                    config[section][option] = value
                elif details['type'] == 'dropdown':
                    config[section][option] = widget.currentText()
                elif details['type'] == 'checkbox':
                    config[section][option] = widget.isChecked()

        with open(self.config_file, 'w') as file:
            json.dump(config, file, indent=4)
            logging.info("Configuration saved to %s", self.config_file)