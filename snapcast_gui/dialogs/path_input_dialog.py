import logging

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
)
from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings


class PathInputDialog(QDialog):
    """
    A dialog window for inputting a path.

    This dialog allows the user to input a path for a specific program.
    It provides a text field for entering the path, a browse button for
    selecting the path using a file dialog, and OK/Cancel buttons for
    accepting or rejecting the input.
    """

    def __init__(self, program_name: str, log_level: int):
        super().__init__()
        self.logger = logging.getLogger("PathInputDialog")
        self.logger.setLevel(log_level)
        self.logger.debug(f"Initializing for {program_name}")

        self.setWindowTitle(f"Provide path for {program_name}")

        self.layout = QVBoxLayout(self)

        self.label = QLabel(f"Unable to find path for {program_name}. Please provide the path:")
        self.layout.addWidget(self.label)

        self.path_edit = QLineEdit(self)
        self.layout.addWidget(self.path_edit)

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_path)
        self.layout.addWidget(self.browse_button)

        self.ignore_popup_checkbox = QCheckBox("Don't ask again", self)
        self.layout.addWidget(self.ignore_popup_checkbox)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def browse_path(self) -> None:
        """
        Opens a file dialog for browsing the file system and selecting a path.

        This method is triggered when the browse button is clicked. It opens
        a file dialog for the user to browse the file system and select a path.
        If a path is selected, it sets the text of the path_edit field to the
        selected path.
        """
        self.logger.debug("Browsing for path")
        path, _ = QFileDialog.getOpenFileName(self, "Select Program Path")
        if path:
            self.path_edit.setText(path)

    def get_path(self) -> str:
        """
        Returns the path entered by the user.

        Returns:
            str: The path entered by the user in the path_edit field.
        """
        self.logger.debug(f"Returning path: {self.path_edit.text()}")
        return self.path_edit.text()

    def accept(self) -> None:
        """
        Accepts the dialog and stores the user's preference for ignoring the popup.

        This method is triggered when the OK button is clicked. It stores the user's
        preference for ignoring the popup in the settings file using the SnapcastSettings
        class and then accepts the dialog.
        """
        ignore_popup = self.ignore_popup_checkbox.isChecked()
        SnapcastSettings().set_ignore_popup(ignore_popup)
        self.logger.debug(f"Ignore popup preference set to: {ignore_popup}")
        super().accept()
