import logging
from functools import partial
from typing import TYPE_CHECKING
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QSlider,
    QComboBox,
    QWidget
)

if TYPE_CHECKING:
    from snapcast_gui.windows.main_window import MainWindow


class GroupInfoDialog(QDialog):
    """A class to create a dialog window to display group information."""

    def __init__(
        self,
        client_info: dict,
        mainwindow: "MainWindow",
        slider: QSlider,
        mute_button: QPushButton,
        client_label: QLabel,
        sources_dictionary: dict,
        log_level: int = logging.DEBUG,
    ) -> None:
        super().__init__()
        self.logger = logging.getLogger("GroupInfoDialog")
        self.logger.setLevel(log_level)

        self.logger.debug("Created for client {}.".format(
            client_info.get("identifier", "Unknown")))

        self.setWindowTitle(
            "Group Info for {}".format(
                client_info.get("friendly_name", "Unknown"))
        )

        self.layout = QVBoxLayout()

        name_label = QLabel("Name")
        self.layout.addWidget(name_label)

        name = QTextEdit(client_info.get("friendly_name", "Unknown"))
        name.setToolTip("Group's name")
        name.setFixedHeight(30)
        name.textChanged.connect(
            partial(
                mainwindow.change_group_name,
                client_info.get("identifier", "Unknown"),
                name.toPlainText(),
            ))
        self.layout.addWidget(name)

        identifier_label = QLabel("Identifier")
        self.layout.addWidget(identifier_label)

        identifier = QLabel(client_info.get("identifier", "Unknown"))
        identifier.setToolTip("Group's identifier")
        self.layout.addWidget(identifier)

        volume_label = QLabel("Volume")
        self.layout.addWidget(volume_label)

        volume = QSpinBox(self)
        volume.setToolTip("Change the volume of the client")
        volume.setValue(client_info.get("volume", 0))
        volume.setMinimum(0)
        volume.setMaximum(100)
        self.layout.addWidget(volume)

        sources_label = QLabel("Sources")
        self.layout.addWidget(sources_label)

        sources_dropdown = QComboBox(self)
        sources_dropdown.setToolTip("Change the source of the group")
        sources_dropdown.addItems(sources_dictionary.keys())
        sources_dropdown.currentIndexChanged.connect(
            partial(
                mainwindow.change_group_source,
                client_info.get("identifier", "Unknown"),
                sources_dictionary.get(
                    sources_dropdown.currentText(), "Unknown"),
            ))
        sources_dropdown.setCurrentText(
            client_info.get("source_name", "Unknown"))
        self.layout.addWidget(sources_dropdown)

        self.muted = QPushButton("Muted", self)
        self.muted.setCheckable(True)
        if client_info.get("muted", False):
            self.muted.setText("Unmute")
            self.muted.setChecked(True)
        else:
            self.muted.setText("Mute")
            self.muted.setChecked(False)
        self.muted.setToolTip("Change the mute state of the client")

    def closeEvent(self, event) -> None:
        self.logger.debug("Closed.")
        event.accept()