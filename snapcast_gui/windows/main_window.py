import asyncio
import logging
import socket
import json

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLayout,
)
from PySide6.QtGui import QIcon

from snapcast.control import create_server
from snapcast.control.client import Snapclient

from snapcast_gui.misc.notifications import Notifications
from snapcast_gui.misc.tray_icon import TrayIcon
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables
from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings
from snapcast_gui.windows.client_window import ClientWindow
from snapcast_gui.dialogs.client_info_dialog import ClientInfoDialog
from snapcast_gui.dialogs.group_info_dialog import GroupInfoDialog
from snapcast_gui.dialogs.server_info_dialog import ServerInfoDialog

from typing import Dict, Optional, Any, List


class MainWindow(QMainWindow):
    """
    The main window of the Snapcast GUI application which contains the controls for the server and is part of the combinedwindow
    """

    def __init__(self, snapcast_settings: SnapcastSettings, client_window: ClientWindow, log_level: int):
        super(MainWindow, self).__init__()
        logging.getLogger().setLevel(log_level)

        self.snapcast_settings: SnapcastSettings = snapcast_settings
        self.client_window: ClientWindow = client_window
        self.log_level: int = log_level

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        self.layout = QVBoxLayout(main_widget)

        ip_label = QLabel("IP Address", self)
        self.layout.addWidget(ip_label)

        self.ip_addresses = []
        self.ip_addresses = snapcast_settings.read_config_file()
        self.path = SnapcastGuiVariables.config_file_path

        self.ip_dropdown = QComboBox(self)
        self.ip_dropdown.setEditable(True)
        if self.ip_addresses != []:
            self.ip_dropdown.addItems(self.ip_addresses)
        self.ip_input = self.ip_dropdown.lineEdit()
        self.ip_input.setPlaceholderText("Enter IP Address")
        self.ip_input.setToolTip(
            "List of all the IP addresses in the config file.")
        self.layout.addWidget(self.ip_dropdown)

        ip_button_layout = QHBoxLayout()

        add_ip_button = QPushButton("Add IP", self)
        ip_button_layout.addWidget(add_ip_button)
        add_ip_button.setToolTip("Add the IP address to the config file.")
        add_ip_button.clicked.connect(self.add_ip)
        add_ip_button.setMinimumWidth(50)

        remove_ip_button = QPushButton("Remove IP", self)
        ip_button_layout.addWidget(remove_ip_button)
        remove_ip_button.setToolTip(
            "Remove the IP address from the config file.")
        remove_ip_button.clicked.connect(self.remove_ip)
        remove_ip_button.setMinimumWidth(50)

        self.layout.addLayout(ip_button_layout)

        server_button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect", self)
        self.connect_button.setToolTip("Connect to the selected server.")
        self.connect_button.clicked.connect(self.create_server)
        server_button_layout.addWidget(self.connect_button)

        self.server_info_button = QPushButton()
        self.server_info_button.setIcon(QIcon.fromTheme("dialog-information"))
        self.server_info_button.setFixedSize(30, 30)
        self.server_info_button.setToolTip("Show server information")
        self.server_info_button.clicked.connect(self.show_server_info)

        server_button_layout.addWidget(self.server_info_button)

        self.layout.addLayout(server_button_layout)

        self.show_offline_clients_button = QCheckBox(
            "Show Offline Clients", self)
        self.show_offline_clients_button.setToolTip(
            "Show the offline clients when connecting."
        )
        self.show_offline_clients_button.stateChanged.connect(
            self.create_volume_sliders
        )

        self.layout.addWidget(self.show_offline_clients_button)

        self.slider_layout = QVBoxLayout()
        self.layout.addLayout(self.slider_layout)

        self.layout.setAlignment(Qt.AlignTop)

        self.server = None

        if snapcast_settings.read_setting("General/AutoConnect"):
            self.create_server()

    def add_ip(self) -> None:
        """
        Adds an IP address to the config file and dropdown, while updating the client window dropdown.

        If the IP address already exists in the config file, a warning message is displayed and the IP address is not added.

        Raises:
            Exception: If there is an error adding the IP address to the config file.
        """
        if self.ip_input.text() in self.ip_addresses:
            QMessageBox.warning(
                self, "Warning", "IP Address already exists in the config file."
            )
            logging.warning(
                "mainwindow: IP Address already exists in the config file.")
            return

        self.ip_addresses.append(str(self.ip_input.text()))
        self.ip_dropdown.addItem(str(self.ip_input.text()))
        self.ip_dropdown.setCurrentIndex(
            self.ip_dropdown.findText(str(self.ip_input.text()))
        )

        try:
            self.snapcast_settings.add_ip(str(self.ip_dropdown.currentText()))
            logging.info("mainwindow: IP Address added to config file.")
            QMessageBox.information(
                self, "Success", "IP Address added to config file.")
            self.client_window.populate_ip_dropdown()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not add IP Address to config file: {
                    str(e)}"
            )
            logging.error(
                f"mainwindow: Could not add IP Address to config file: {
                    str(e)}"
            )
            return

    def remove_ip(self) -> None:
        """
        Removes the IP Address from the config file and dropdown menu, and updates the client window dropdown.

        If the IP Address does not exist in the config file, a warning message is displayed.
        If an error occurs while removing the IP Address from the config file, an error message is displayed.

        Raises:
            Exception: If there is an error removing the IP Address from the config file.
        """
        if self.ip_input.text() not in self.ip_addresses:
            QMessageBox.warning(
                self, "Warning", "IP Address does not exist in the config file."
            )
            logging.warning(
                "mainwindow: IP Address does not exist in the config file.")
            return
        selected_index = self.ip_dropdown.currentIndex()
        selected_text = self.ip_dropdown.itemText(selected_index)
        self.ip_addresses.remove(selected_text)
        self.ip_dropdown.removeItem(selected_index)
        try:
            self.snapcast_settings.remove_ip(selected_text)
            logging.info("mainwindow: IP Address removed from config file.")
            QMessageBox.information(
                self, "Success", "IP Address removed from config file."
            )
            self.client_window.populate_ip_dropdown()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not remove IP Address from config file: {
                    str(e)}"
            )
            logging.error(
                f"mainwindow: Could not remove IP Address from config file: {
                    str(e)}"
            )
            return

    def create_server(self) -> None:
        """
        Checks if the server is listening on the default port and if it is then connects to the server and creates the necessary UI elements.

        Raises:
            Exception: If there is an error connecting to the server.
        """
        ip_value = str(self.ip_input.text())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip_value, 1705))
        sock.close()
        if result != 0:
            QMessageBox.critical(
                self, "Error", "Server is not online or unreachable.")
            logging.error("mainwindow: Server is not online or unreachable.")
            return

        try:
            logging.info("mainwindow: Connecting to server.")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.connect_button.setText("Connecting...")
            self.connect_button.setEnabled(False)

            self.server = self.loop.run_until_complete(
                create_server(self.loop, ip_value)
            )
            self.connected_ip = ip_value
            logging.info(f"mainwindow: Connected to server {ip_value}.")
            Notifications.send_notify("Connected to server {}.".format(
                ip_value), "Snapcast Gui")

            self.create_volume_sliders()
            self.connect_button.setText("Disconnect")
            self.connect_button.clicked.disconnect()
            self.connect_button.clicked.connect(self.disconnect)
            self.connect_button.setToolTip("Disconnect from the server.")
            self.connect_button.setEnabled(True)
            return self.server
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not connect to server: {str(e)}"
            )
            logging.error(f"mainwindow: Could not connect to server: {str(e)}")
            self.connect_button.setText("Connect")
            self.connect_button.setEnabled(True)
            return

    def create_sources_list(self) -> Dict[str, str]:
        """
        Creates the sources list for the server.

        Returns:
            sources_dict (dict): A dictionary containing the sources friendly name and unique identifier.
        """
        logging.debug("mainwindow: Creating sources list.")
        sources_dict: Dict[str, str] = {}
        if self.server is not None:
            for source in self.server.streams:
                logging.debug(f"mainwindow: Source {source.identifier} found.")
                sources_dict[source.friendly_name] = source.identifier
        return sources_dict

    def create_volume_sliders(self) -> None:
        """
        Creates the volume sliders, info button, mute button, and the client name text box for each client connected to the server.
        """
        logging.debug("mainwindow: Creating volume sliders.")
        if self.server is None:
            return
        self.slider_widgets: List[QLayout] = []

        for i in reversed(range(self.slider_layout.count())):
            widget = self.slider_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for client in self.server.clients:
            if self.show_offline_clients_button.isChecked() or client.connected:
                logging.debug(
                    f"mainwindow: Creating volume slider for {client.identifier}. {client.friendly_name}."
                )
                client_layout = QHBoxLayout()

                client_label = QTextEdit(self)
                client_label.setText(client.friendly_name)
                client_label.setFixedSize(100, 30)
                client_label.textChanged.connect(
                    partial(self.change_client_name, client.identifier, client_label)
                )

                speaker_icon = QIcon()
                if client.muted:
                    speaker_icon = QIcon.fromTheme("audio-volume-muted")
                else:
                    speaker_icon = QIcon.fromTheme("audio-volume-high")

                if not client.connected:
                    speaker_icon = QIcon.fromTheme("network-offline")

                speaker_button = QPushButton(self)
                speaker_button.setIcon(speaker_icon)
                speaker_button.setToolTip("Mute/Unmute client.")
                speaker_button.clicked.connect(
                    partial(self.change_button_icon, client.identifier, speaker_button)
                )

                if not client.connected:
                    speaker_button.setEnabled(False)
                    speaker_button.setToolTip("Client is offline.")

                client_layout.addWidget(speaker_button)

                slider = QSlider(Qt.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(100)
                slider.setValue(client.volume)

                slider.valueChanged.connect(
                    partial(self.change_volume, client.identifier)
                )

                client_layout.addWidget(client_label)
                client_layout.addWidget(slider)

                if client.connected:
                    info_button = QPushButton()
                    info_button.setIcon(QIcon.fromTheme("dialog-information"))
                    info_button.setToolTip("Show client info.")
                    info_button.clicked.connect(
                        partial(
                            self.show_client_info,
                            client.identifier,
                            slider,
                            speaker_button,
                            client_label,
                        )
                    )
                else:
                    info_button = QPushButton()
                    info_button.setIcon(QIcon.fromTheme("user-trash-full"))
                    info_button.setToolTip("Delete the client.")
                    info_button.clicked.connect(lambda client=client.identifier: self.remove_client(client))

                client_layout.addWidget(info_button)


                if not client.connected:
                    slider.setEnabled(False)

                self.slider_layout.addLayout(client_layout)
                self.slider_widgets.append(client_layout)
                self.slider_layout.setAlignment(Qt.AlignTop)

    def set_slider_value(self, client_id: str, value: int):
        """
        Set slider value knowing the snapcast client id.
        Used to update the sliders with the server.
    
        Args:
            client_id (str): The UID of the client.
            value (int): The new value of the slider.
        """
        try:
            for client_layout in self.slider_widgets:
                if client_layout.itemAt(0).widget().objectName() == client_id:
                    for i in range(client_layout.count()):
                        widget = client_layout.itemAt(i).widget()
                        if isinstance(widget, QSlider):
                            widget.setValue(value)
                    logging.debug("mainwindow: Slider value updated for {} to {}.".format(client_id, value))
                    break
        except Exception as e:
            logging.error("mainwindow: Error updating slider value for {}: {}".format(client_id, str(e)))

    """Methods to interact with clients."""

    def change_volume(self, client_id: str, volume: int) -> None:
        """Changes the volume of the client with the provided ID.

        Args:
            client_id (str): The UID of the client.
            volume (int): The new volume level.

        Raises:
            Exception: If there is an error changing the volume.
        """
        try:
            if self.server:
                client: Optional[Snapclient] = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_id and client.connected
                    ),
                    None,
                )
                logging.debug(
                    f"mainwindow: Changing volume for client {client_id} to {volume}."
                )
            else:
                logging.warning("mainwindow: Server is not available.")
            if client:
                self.loop.run_until_complete(client.set_volume(volume))
                logging.debug(
                    f"mainwindow: Volume changed for client {client_id} to {volume}."
                )
            else:
                logging.warning("mainwindow: Client not found with the provided ID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided ID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not change volume for client: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(f"mainwindow: Could not change volume for client: {str(e)}")


    def change_muted_state(self, client_id: str) -> None:
        """
        Changes the muted state of the client with the provided ID.

        Args:
            client_id (str): The unique identifier of the client.

        Raises:
            QMessageBox.critical: If the client is not found with the provided ID or an error occurs while changing the muted state.
        """
        try:
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_id and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                self.loop.run_until_complete(
                    client.set_muted(not client.muted))
                logging.debug(
                    f"mainwindow: Muted state changed for client {client_id}."
                )
            else:
                logging.warning(
                    "mainwindow: Client not found with the provided ID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided ID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not change muted state for client: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(
                f"mainwindow: Could not change muted state for client: {
                    str(e)}"
            )

    def change_button_icon(self, client_uid: str, button: QPushButton) -> None:
        """
        Changes the icon of the button to the muted icon if the client is muted and vice versa.

        Raises:
            QMessageBox.critical: If the client is not found with the provided UID.
            QMessageBox.critical: If there is an error while changing the button icon.
        """
        try:
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_uid and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                if isinstance(button, QPushButton):
                    if client.muted:
                        button.setIcon(QIcon.fromTheme("audio-volume-high"))
                    else:
                        button.setIcon(QIcon.fromTheme("audio-volume-muted"))
                    self.change_muted_state(client_uid)
            else:
                logging.warning(
                    "mainwindow: Client not found with the provided UID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided UID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not change button icon for client: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(
                f"mainwindow: Could not change button icon for client: {
                    str(e)}"
            )

    def change_client_name(self, client_uid: str, qtextedit: QTextEdit) -> None:
        """
        Changes the name of the client using the provided UID and the text from the qtextedit.

        Raises:
            Exception: If there is an error while changing the name for the client.
        """
        try:
            qtextedit_text = qtextedit.toPlainText()
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_uid and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                self.loop.run_until_complete(client.set_name(qtextedit_text))
                logging.debug(
                    f"mainwindow: Name changed for client {client_uid} to {qtextedit_text}."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not change name for client: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(
                f"mainwindow: Could not change name for client: {str(e)}")

    def change_latency(self, client_uid: str, new_latency: int) -> None:
        """
        Changes the latency of the client with the provided UID.

        Raises:
            Exception: If an error occurs while changing the latency.
        """
        try:
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_uid and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                self.loop.run_until_complete(client.set_latency(new_latency))
                logging.debug(
                    f"mainwindow: Latency changed for client {
                        client_uid} to {new_latency}."
                )
            else:
                logging.warning(
                    "mainwindow: Client not found with the provided UID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided UID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not change latency for client: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(
                f"mainwindow: Could not change latency for client: {str(e)}"
            )

    def change_group_volume(self, client_uid: str, volume: int) -> None:
        """
        Changes the group volume of the client with the provided UID.

        Raises:
            Exception: If an error occurs while changing the group volume.
        """
        try:
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_uid and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                self.loop.run_until_complete(client.group.set_volume(volume))
                logging.debug(
                    f"mainwindow: Group volume changed for client {
                        client_uid} to {volume}."
                )
            else:
                logging.warning(
                    "mainwindow: Client not found with the provided UID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided UID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while changing group volume: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(
                f"mainwindow: An error occurred while changing group volume: {
                    str(e)}"
            )

        """Methods to interact with groups."""

    def change_group_name(self, client_uid: str, group_name: str) -> None:
        """
        Changes the group name of the client with the provided UID.

        Raises:
            QMessageBox.critical: If the client is not found with the provided UID.
            QMessageBox.critical: If an error occurs while changing the group name.
        """
        try:
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_uid and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                self.loop.run_until_complete(
                    client.group.set_name(str(group_name)))
                logging.debug(
                    f"mainwindow: Group name changed for client {
                        client_uid} to {group_name}."
                )
            else:
                logging.warning(
                    "mainwindow: Client not found with the provided UID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided UID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while changing group name: {str(e)}",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            logging.warning(
                f"mainwindow: An error occurred while changing group name: {
                    str(e)}"
            )

    def change_singular_client_source(self, client_uid: str, stream_id: str) -> None:
        """
        Changes the source of the client with the provided UID.

        Raises:
            QMessageBox.critical: If the client is not found with the provided UID.
            QMessageBox.critical: If an error occurs while changing the source.
        """
        try:
            logging.debug(f"Attempting to find client with UID: {client_uid}")
            if self.server:
                client = self.server.client(client_uid)
            else:
                logging.warning("mainwindow: Server is not available.")
                return
            if not client:
                error_message = f"Client with UID {client_uid} not found."
                logging.error(error_message)
                QMessageBox.critical(None, "Client Not Found", error_message)
                return

            logging.debug(f"Changing stream for client {client_uid} to stream {stream_id}.")
            group = client.group
            group.set_stream(stream_id)
            logging.debug(f"Stream changed successfully for client {client_uid}.")

        except Exception as e:
            error_message = f"An error occurred while changing the source: {e}"
            logging.error(error_message)
            QMessageBox.critical(None, "Error", error_message)

    def change_group_source(self, group_id: str, stream_id: str) -> None:
        """Changes the source for the group with the provided ID.

        Args:
            group_id: The unique identifier of the group.
            stream_id: The unique identifier of the stream stream to change to.
        """
        try:
            logging.debug(f"Attempting to find group with UID: {group_id}")
            if self.server:
                group = self.server.group(group_id)
            else:
                logging.warning("mainwindow: Server is not available.")
                return
            if not group:
                error_message = f"Group with UID {group_id} not found."
                logging.error(error_message)
                QMessageBox.critical(None, "Group Not Found", error_message)
                return

            logging.debug(f"Changing stream for group {group_id} to stream {stream_id}.")
            group.set_stream(stream_id)
            logging.debug(f"Stream changed successfully for group {group_id}.")

        except Exception as e:
            error_message = f"An error occurred while changing the source: {e}"
            logging.error(error_message)
            QMessageBox.critical(None, "Error", error_message)

    def remove_client(self, client_uid: str) -> None:
        """
        Removes the client with the provided UID.

        Raises:
            QMessageBox.critical: If the client is not found with the provided UID.
            QMessageBox.critical: If an error occurs while removing the client.
        """
        try:
            if self.server:
                client = next(
                    (
                        client
                        for client in self.server.clients
                        if client.identifier == client_uid and client.connected
                    ),
                    None,
                )
            else:
                client = None
            if client:
                self.loop.run_until_complete(client.remove())
                logging.debug(f"mainwindow: Client {client_uid} removed.")
            else:
                logging.warning(
                    "mainwindow: Client not found with the provided UID.")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Client not found with the provided UID.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while removing client: {str(e)}",
                QMessageBox.Ok,
            )
            logging.warning(
                f"mainwindow: An error occurred while removing client: {
                    str(e)}"
            )

    def show_client_info(self, client_id: str, slider: QSlider, mute_button: QPushButton, client_label: QTextEdit) -> None:
        """
        Shows the client info dialog for the client with the provided UID while passing the slider to update the volume and the mute button to update the mute state and icon.
        """
        client_info: Dict[str, Any] = {}
        if self.server:
            for client in self.server.clients:
                if client.identifier == client_id:
                    client_info = {
                        "friendly_name": client.friendly_name,
                        "identifier": client.identifier,
                        "volume": client.volume,
                        "latency": client.latency,
                        "muted": client.muted,
                        "group": client.group.friendly_name,
                        "group_id": client.group.identifier,
                        "groups_available": "non funza ancora",
                        "group_volume": client.group.volume,
                        "version": client.version,
                    }
                    logging.debug(f"mainwindow: Client Info for {client_id} found.")
                    break
            else:
                logging.warning(f"mainwindow: Client {client_id} not found in client dictionary.")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Client {client_id} not found in client dictionary.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
                return
        else:
            logging.warning("mainwindow: Server is not available.")
            QMessageBox.critical(
                self,
                "Error",
                "Server is not available.",
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            return

        dialog = ClientInfoDialog(
            client_info,
            self,
            slider,
            mute_button,
            client_label,
            self.create_sources_list(),
            self.log_level,
        )
        dialog.exec()
        logging.debug("mainwindow: Client Info Dialog shown.")

    def show_server_info(self) -> None:
        """
        Shows the server info dialog for the server.
        """
        logging.debug("mainwindow: Showing server info dialog.")
        if self.server:
            server_info_json = json.dumps(self.loop.run_until_complete(self.server.status()))

            dialog = ServerInfoDialog(server_info_json, self.log_level)
            dialog.exec()

    """Methods to interact with groups."""

    def disconnect(self):
        """
        Disconnects from the server and removes all the UI elements.

        This method iterates over the `slider_widgets` list and removes all the widgets from each slider layout.
        It also removes all the widgets from the main slider layout.

        After disconnecting from the server, it updates the connect button text and connects it to the `create_server` method.
        """
        for slider_layout in self.slider_widgets:
            while slider_layout.count():
                item = slider_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        while self.slider_layout.count():
            item = self.slider_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.loop.close()
        logging.info("mainwindow: Disconnected from server.")
        Notifications.send_notify("Disconnected from server.", "Snapcast Gui")

        self.connect_button.setText("Connect")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.create_server)
        self.server = None

    def disable_controls(self) -> None:
        """
        Disables the controls when needed to connect to the server.
        """
        logging.debug("mainwindow: Disabling controls.")
        self.ip_input.setEnabled(False)
        self.ip_dropdown.setEnabled(False)
        self.add_ip_button.setEnabled(False)
        self.remove_ip_button.setEnabled(False)
        self.server_info_button.setEnabled(True)

    def enable_controls(self) -> None:
        """
        Enables the controls when needed to disconnect from the server.
        """
        logging.debug("mainwindow: Enabling controls.")
        self.ip_input.setEnabled(True)
        self.ip_dropdown.setEnabled(True)
        self.add_ip_button.setEnabled(True)
        self.remove_ip_button.setEnabled(True)
        self.server_info_button.setEnabled(False)

    def create_tray_icon(
        self,
        main_window,
        client_window,
        server_window,
        settings_window,
        combined_window,
        snapcast_settings,
        log_level,
    ):
        """
        Creates the tray icon for the application while passing all the windows instances to the tray icon class. Gets called by the main

        Args:
            main_window: The instance of the main window.
            client_window: The instance of the client window.
            server_window: The instance of the server window.
            settings_window: The instance of the settings window.
            combined_window: The instance of the combined window.
            log_level: The log level for debugging.
        """
        self.tray_icon = TrayIcon(
            main_window,
            client_window,
            server_window,
            settings_window,
            combined_window,
            snapcast_settings,
            log_level,
        )
        self.tray_icon.show()
        logging.debug("mainwindow: Tray Icon created.")
