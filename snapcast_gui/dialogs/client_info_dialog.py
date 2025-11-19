import logging
import json

from functools import partial
from typing import TYPE_CHECKING
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, Slot, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QSlider,
    QComboBox,
    QHBoxLayout,
    QMessageBox,
)
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables

if TYPE_CHECKING:
    from snapcast_gui.windows.main_window import MainWindow


class ClientInfoDialog(QDialog):
    latest_version_fetched = Signal(str)

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
        self.logger = logging.getLogger("ClientInfoDialog")
        self.logger.setLevel(log_level)

        self.logger.debug("Created for client {}.".format(
            client_info.get("identifier", "Unknown")))

        self.mainwindow = mainwindow
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.on_version_fetched)

        self.setWindowTitle(
            "Client Info for {}".format(
                client_info.get("friendly_name", "Unknown"))
        )

        self.main_layout = QVBoxLayout()

        name_label = QLabel("Name")
        name_label.setToolTip("Client's name")
        self.main_layout.addWidget(name_label)
        name = QTextEdit(self)
        name.setText(client_info.get("friendly_name", ""))
        name.setFixedHeight(30)
        name.setToolTip("Change the name of the client")
        name.textChanged.connect(
            partial(
                self.mainwindow.change_client_name,
                client_uid=client_info.get("identifier", "Unknown"),
                qtextedit=name,
            )
        )
        name.textChanged.connect(lambda: client_label.setText(name.toPlainText()))
        self.main_layout.addWidget(name)

        identifier_label = QLabel("Identifier")
        identifier_label.setToolTip("Unique identifier for the client")
        self.main_layout.addWidget(identifier_label)
        identifier_value = client_info.get("identifier", "Unknown")
        identifier = QLabel(identifier_value)
        identifier.setToolTip("Unique identifier for the client")
        self.main_layout.addWidget(identifier)

        version_layout = QHBoxLayout()

        version_label = QLabel("Version")
        version_label.setToolTip("Version of the client")
        self.main_layout.addWidget(version_label)
        version = QLabel()
        version.setToolTip("Version of the client")
        version_text: str = client_info.get("version", "Unknown")
        version.setText(version_text)
        version_layout.addWidget(version)

        self.check_version_button = QPushButton("Check Version")
        self.check_version_button.setToolTip("Check the version of the client")
        self.check_version_button.clicked.connect(self.check_version)
        version_layout.addWidget(self.check_version_button)

        self.main_layout.addLayout(version_layout)

        volume_label = QLabel("Volume")
        volume_label.setToolTip("Volume level of the client")
        self.main_layout.addWidget(volume_label)
        volume = QSpinBox(self)
        volume.setToolTip("Change the volume of the client")
        volume.setValue(client_info.get("volume", 0))
        volume.setMinimum(0)
        volume.setMaximum(100)
        volume.valueChanged.connect(
            partial(mainwindow.change_volume, client_info["identifier"])
        )
        volume.valueChanged.connect(lambda: slider.setValue(volume.value()))
        self.main_layout.addWidget(volume)

        self.muted = QPushButton("Muted", self)
        self.muted.setCheckable(True)
        if client_info.get("muted", False):
            self.muted.setText("Unmute")
            self.muted.setChecked(True)
        else:
            self.muted.setText("Mute")
            self.muted.setChecked(False)
        self.muted.setToolTip("Change the mute state of the client")
        self.muted.clicked.connect(
            lambda: self.change_muted_state(client_info, mute_button)
        )
        self.main_layout.addWidget(self.muted)

        latency_label = QLabel("Latency")
        latency_label.setToolTip("Latency of the client")
        self.main_layout.addWidget(latency_label)
        latency = QSpinBox(self)
        latency.setToolTip("Change the latency of the client")
        latency.setMinimum(-2000)
        latency.setMaximum(2000)
        latency.setValue(client_info.get("latency", 0))
        latency.valueChanged.connect(
            partial(self.mainwindow.change_latency, client_info["identifier"])
        )
        self.main_layout.addWidget(latency)

        group_information_label = QLabel("Group Information:")
        group_information_label.setToolTip(
            "Information about the group the client belongs to"
        )
        self.main_layout.addWidget(group_information_label)

        group_label = QLabel("Group Name")
        group_label.setToolTip("Name of the group the client belongs to")
        self.main_layout.addWidget(group_label)
        group_text = client_info.get("group", "Unknown")
        group = QTextEdit(self)
        group.setToolTip("Change the group name of the client")
        group.setText(group_text)
        if len(group_text) < 30:
            group.setFixedHeight(30)
        else:
            group.setFixedHeight(60)
        group.textChanged.connect(
            lambda: mainwindow.change_group_name(
                client_info["identifier"], group.toPlainText()
            )
        )
        self.main_layout.addWidget(group)

        group_volume_label = QLabel("Group Volume")
        group_volume_label.setToolTip(
            "Volume of the group the client belongs to")
        self.main_layout.addWidget(group_volume_label)

        group_volume = QSpinBox(self)
        group_volume.setToolTip(
            "Change the volume of the group the client belongs to")
        group_volume.setValue(client_info.get("group_volume", 0))
        group_volume.setMinimum(0)
        group_volume.setMaximum(100)
        group_volume.valueChanged.connect(
            partial(mainwindow.change_group_volume, client_info["identifier"])
        )
        self.main_layout.addWidget(group_volume)

        groups_available_label = QLabel("Groups Available")
        groups_available_label.setToolTip("Groups available to join")
        self.main_layout.addWidget(groups_available_label)

        sources_label = QLabel("Sources")
        sources_label.setToolTip("Sources available to join")
        self.main_layout.addWidget(sources_label)

        sources_dropdown = QComboBox()
        for source in sources_dictionary:
            sources_dropdown.addItem(source)
        sources_dropdown.setToolTip("Change the source of the client")
        self.main_layout.addWidget(sources_dropdown)

        self.setLayout(self.main_layout)

    def closeEvent(self, event) -> None:
        self.logger.debug("Closed.")
        event.accept()

    def change_muted_state(self, client_info: dict, mute_button: QPushButton) -> None:
        self.logger.debug("Muted state changed.")
        identifier = str(client_info.get("identifier", ""))
        self.mainwindow.change_muted_state(identifier)
        if self.muted.isChecked():
            self.logger.debug("Muted.")
            self.muted.setText("Unmute")
            mute_button.setIcon(QIcon.fromTheme("audio-volume-muted"))
        else:
            self.logger.debug("Unmuted.")
            self.muted.setText("Mute")
            mute_button.setIcon(QIcon.fromTheme("audio-volume-high"))

    def check_version(self):
        self.logger.debug("Checking version.")
        self.check_version_button.setText("Checking...")
        git_url = QUrl(SnapcastGuiVariables.snapcast_github_url)
        self.get_latest_version(git_url)

    def get_latest_version(self, git_url: QUrl):
        if self.network_manager is None:
            self.network_manager = QNetworkAccessManager(self)
            self.network_manager.finished.connect(self.on_version_fetched)
        request = QNetworkRequest(git_url)
        self.network_manager.get(request)

    @Slot(QNetworkReply)
    def on_version_fetched(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = reply.readAll().data().decode()
                json_data = json.loads(data)
                latest_version = json_data.get("tag_name", "")
                self.latest_version_fetched.emit(latest_version)
            except Exception as e:
                self.logger.error(f"Error parsing version data: {str(e)}")
                self.latest_version_fetched.emit("")
        else:
            self.logger.error(f"Network error occurred: {reply.errorString()}")
            self.latest_version_fetched.emit("")
        reply.deleteLater()

    @Slot(str)
    def on_version_fetched_response(self, version):
        self.check_version_button.setText("Check Version")
        if version:
            self.logger.debug("Latest version is {}.".format(version))
            QMessageBox.information(
                self,
                "Client is up to date",
                "Client is up to date. The latest version is {}.".format(
                    version),
            )
        else:
            self.logger.error("Error checking version.")
            QMessageBox.critical(
                self,
                "Error",
                "Error checking version. Check the logs for more information.",
            )
