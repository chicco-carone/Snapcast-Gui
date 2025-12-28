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
    QScrollArea,
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
from snapcast_gui.misc.async_bridge import AsyncBridge
from snapcast_gui.fileactions.snapcast_settings import SnapcastSettings
from snapcast_gui.windows.client_window import ClientWindow
from snapcast_gui.dialogs.client_info_dialog import ClientInfoDialog
from snapcast_gui.dialogs.server_info_dialog import ServerInfoDialog

from typing import Dict, Optional, Any, List


class MainWindow(QMainWindow):
    """
    The main window of the Snapcast GUI application which contains the controls for the server and is part of the combinedwindow
    """

    def __init__(
        self,
        snapcast_settings: SnapcastSettings,
        client_window: ClientWindow,
        async_bridge: AsyncBridge,
        log_level: int,
    ):
        super(MainWindow, self).__init__()
        self.logger = logging.getLogger("MainWindow")
        self.logger.setLevel(log_level)

        self.snapcast_settings: SnapcastSettings = snapcast_settings
        self.client_window: ClientWindow = client_window
        self.async_bridge: AsyncBridge = async_bridge
        self.log_level: int = log_level

        # Connect AsyncBridge signals for real-time updates
        self._connect_async_bridge_signals()

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
        self.ip_input.setToolTip("List of all the IP addresses in the config file.")
        # Connect signal to dynamically enable/disable Remove IP button
        self.ip_input.textChanged.connect(self.update_remove_ip_button_state)
        self.layout.addWidget(self.ip_dropdown)

        ip_button_layout = QHBoxLayout()

        self.add_ip_button = QPushButton("Add IP", self)
        ip_button_layout.addWidget(self.add_ip_button)
        self.add_ip_button.setToolTip("Add the IP address to the config file.")
        self.add_ip_button.clicked.connect(self.add_ip)
        self.add_ip_button.setMinimumWidth(50)

        self.remove_ip_button = QPushButton("Remove IP", self)
        ip_button_layout.addWidget(self.remove_ip_button)
        self.remove_ip_button.setToolTip("Remove the IP address from the config file.")
        self.remove_ip_button.clicked.connect(self.remove_ip)
        self.remove_ip_button.setMinimumWidth(50)
        # Initially disable if no valid text
        self.update_remove_ip_button_state()

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

        self.show_offline_clients_button = QCheckBox("Show Offline Clients", self)
        self.show_offline_clients_button.setToolTip(
            "Show the offline clients when connecting."
        )
        self.show_offline_clients_button.stateChanged.connect(
            self.create_volume_sliders
        )

        self.layout.addWidget(self.show_offline_clients_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.slider_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)

        self.layout.setAlignment(Qt.AlignTop)

        self.server = None

        if snapcast_settings.read_setting("general/autoconnect"):
            self.create_server()

    def _connect_async_bridge_signals(self) -> None:
        """Connect AsyncBridge signals for real-time server updates."""
        self.async_bridge.server_updated.connect(self._on_server_updated)
        self.async_bridge.server_disconnected.connect(self._on_server_disconnected)
        self.async_bridge.client_updated.connect(self._on_client_updated)
        self.async_bridge.client_connected.connect(self._on_client_connected)
        self.async_bridge.client_disconnected.connect(self._on_client_disconnected)
        self.async_bridge.async_error.connect(self._on_async_error)
        self.logger.debug("AsyncBridge signals connected")

    def _on_server_updated(self, server) -> None:
        """Handle server update from AsyncBridge - refresh UI."""
        self.logger.debug("Server update received, refreshing UI")
        self.create_volume_sliders()

    def _on_server_disconnected(self) -> None:
        """Handle unexpected server disconnection."""
        self.logger.warning("Server disconnected unexpectedly")
        Notifications.send_notify(
            "Server disconnected unexpectedly.", "Snapcast Gui", self.snapcast_settings
        )
        self._cleanup_after_disconnect()

    def _on_client_updated(self, client_id: str, client) -> None:
        """Handle individual client update - update specific widget or refresh if connection state changed."""
        self.logger.debug(f"Client {client_id} updated, connected: {client.connected}")

        # Check if this client's widget exists in the current view
        client_widget_exists = False
        for client_layout in self.slider_widgets:
            mute_button = client_layout.itemAt(0).widget()
            if (
                hasattr(mute_button, "property")
                and mute_button.property("client_id") == client_id
            ):
                client_widget_exists = True
                break

        # If client went offline and we're not showing offline clients, or
        # if client came online and wasn't shown before, refresh the entire list
        show_offline = self.show_offline_clients_button.isChecked()

        if client_widget_exists and not client.connected and not show_offline:
            # Client was shown but went offline - need to remove it
            self.logger.debug(
                f"Client {client_id} went offline, refreshing slider list"
            )
            self.create_volume_sliders()
        elif not client_widget_exists and client.connected:
            # Client wasn't shown but came online - already handled by _on_client_connected
            pass
        elif client_widget_exists:
            # Client still visible, just update the widget values
            self._update_client_widget(client_id, client)

    def _on_client_connected(self, client_id: str) -> None:
        """Handle new client connection - refresh sliders."""
        self.logger.info(f"New client connected: {client_id}")
        self.create_volume_sliders()

    def _on_client_disconnected(self, client_id: str) -> None:
        """Handle client disconnection - refresh sliders if not showing offline."""
        self.logger.info(f"Client disconnected: {client_id}")
        if not self.show_offline_clients_button.isChecked():
            self.create_volume_sliders()

    def _on_async_error(self, operation: str, error_msg: str) -> None:
        """Handle async operation errors."""
        self.logger.error(f"Async error in {operation}: {error_msg}")
        QMessageBox.critical(
            self,
            "Async Error",
            f"Error during {operation}: {error_msg}",
            QMessageBox.Ok,
        )

    def _update_client_widget(self, client_id: str, client) -> None:
        """Update a single client's widget without recreating all sliders."""
        try:
            for client_layout in self.slider_widgets:
                # Find the layout for this client by checking the mute button's object name
                mute_button = client_layout.itemAt(0).widget()
                if (
                    hasattr(mute_button, "property")
                    and mute_button.property("client_id") == client_id
                ):
                    # Update slider value
                    for i in range(client_layout.count()):
                        widget = client_layout.itemAt(i).widget()
                        if isinstance(widget, QSlider):
                            # Block signals to prevent feedback loop
                            widget.blockSignals(True)
                            widget.setValue(client.volume)
                            widget.blockSignals(False)
                        elif isinstance(widget, QPushButton) and i == 0:
                            # Update mute button icon
                            if client.muted:
                                widget.setIcon(QIcon.fromTheme("audio-volume-muted"))
                            else:
                                widget.setIcon(QIcon.fromTheme("audio-volume-high"))
                    self.logger.debug(f"Widget updated for client {client_id}")
                    return
        except Exception as e:
            self.logger.error(f"Error updating client widget: {e}")

    def _cleanup_after_disconnect(self) -> None:
        """Clean up UI after disconnect."""
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

        self.connect_button.setText("Connect")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.create_server)
        self.connect_button.setToolTip("Connect to the selected server.")
        self.connect_button.setEnabled(True)
        self.server = None
        self.async_bridge.clear_server()

    def add_ip(self) -> None:
        """
        Adds an IP address to the config file and dropdown, while updating the client window dropdown.

        If the IP address already exists in the config file, a warning message is displayed and the IP address is not added.
        If the input is empty or only whitespace, an error message is displayed.

        Raises:
            Exception: If there is an error adding the IP address to the config file.
        """
        ip_text = str(self.ip_input.text()).strip()

        # Validate input - reject empty or whitespace-only strings
        if not ip_text:
            QMessageBox.warning(
                self, "Invalid Input", "Please enter a valid IP address or hostname."
            )
            self.logger.warning("Attempted to add empty/whitespace IP address")
            return

        if ip_text in self.ip_addresses:
            QMessageBox.warning(
                self, "Warning", "IP Address already exists in the config file."
            )
            self.logger.warning("IP Address already exists in the config file.")
            return

        try:
            self.snapcast_settings.add_ip(ip_text)
            self.ip_addresses.append(ip_text)
            self.ip_dropdown.addItem(ip_text)
            self.ip_dropdown.setCurrentIndex(self.ip_dropdown.findText(ip_text))
            self.logger.info("IP Address added to config file.")
            QMessageBox.information(self, "Success", "IP Address added to config file.")
            self.client_window.populate_ip_dropdown()
        except ValueError as e:
            QMessageBox.warning(
                self, "Invalid Input", f"Invalid IP address: {str(e)}"
            )
            self.logger.error(f"Invalid IP address: {str(e)}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not add IP Address to config file: {str(e)}"
            )
            self.logger.error(
                f"mainwindow: Could not add IP Address to config file: {str(e)}"
            )

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
            self.logger.warning("IP Address does not exist in the config file.")
            return
        selected_index = self.ip_dropdown.currentIndex()
        selected_text = self.ip_dropdown.itemText(selected_index)
        self.ip_addresses.remove(selected_text)
        self.ip_dropdown.removeItem(selected_index)
        try:
            self.snapcast_settings.remove_ip(selected_text)
            self.logger.info("IP Address removed from config file.")
            QMessageBox.information(
                self, "Success", "IP Address removed from config file."
            )
            self.client_window.populate_ip_dropdown()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not remove IP Address from config file: {str(e)}"
            )
            self.logger.error(
                f"mainwindow: Could not remove IP Address from config file: {str(e)}"
            )
            return

    def update_remove_ip_button_state(self) -> None:
        """
        Updates the enabled state of the Remove IP button based on whether the current input text
        exists in the stored IP addresses list.
        """
        current_text = str(self.ip_input.text()).strip()
        # Enable button only if the text exists in the IP addresses list
        self.remove_ip_button.setEnabled(current_text in self.ip_addresses)

    def create_server(self) -> None:
        """
        Initiates async connection to the Snapcast server.

        This method validates the IP, updates UI to show connecting state,
        and schedules the async connection coroutine.
        """
        ip_value = str(self.ip_input.text()).strip()

        if not ip_value:
            QMessageBox.warning(
                self, "Invalid Input", "Please enter an IP address or hostname."
            )
            return

        self.connect_button.setText("Connecting...")
        self.connect_button.setEnabled(False)

        # Schedule the async connection
        self.async_bridge.schedule_coroutine(
            self._connect_to_server_async(ip_value),
            callback=self._on_connection_success,
            error_callback=self._on_connection_error,
        )

    async def _connect_to_server_async(self, ip_value: str):
        """
        Async coroutine to connect to the Snapcast server.

        Args:
            ip_value: The IP address or hostname to connect to.

        Returns:
            The connected server object.
        """
        loop = asyncio.get_event_loop()

        # First do a quick socket check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.setblocking(False)
            try:
                await loop.sock_connect(sock, (ip_value, 1705))
            except BlockingIOError:
                # Connection in progress - wait for it
                pass
            finally:
                sock.close()
        except socket.gaierror as e:
            raise ConnectionError(f"DNS resolution failed for '{ip_value}': {e}")
        except Exception as e:
            raise ConnectionError(f"Network error connecting to {ip_value}:1705: {e}")

        self.logger.info(f"Connecting to server {ip_value}")

        # Create the snapcast server connection
        server = await create_server(loop, ip_value)

        self.server = server
        self.connected_ip = ip_value

        # Register callbacks via AsyncBridge
        self.async_bridge.server = server

        return server

    def _on_connection_success(self, server) -> None:
        """Callback when async connection succeeds."""
        self.logger.info(f"Connected to server {self.connected_ip}")
        Notifications.send_notify(
            f"Connected to server {self.connected_ip}.",
            "Snapcast Gui",
            self.snapcast_settings,
        )

        self.create_volume_sliders()
        self.connect_button.setText("Disconnect")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.disconnect)
        self.connect_button.setToolTip("Disconnect from the server.")
        self.connect_button.setEnabled(True)

    def _on_connection_error(self, error: Exception) -> None:
        """Callback when async connection fails."""
        error_msg = str(error)
        error_type = type(error).__name__

        self.logger.error(f"Connection failed: {error_type} - {error_msg}")

        # Provide user-friendly error messages
        if "DNS" in error_msg or "gaierror" in error_msg:
            display_msg = (
                f"DNS resolution failed. Please check the IP address or hostname."
            )
        elif "timeout" in error_msg.lower():
            display_msg = (
                "Connection timed out. Server may be unreachable or firewalled."
            )
        elif "refused" in error_msg.lower():
            display_msg = "Connection refused. Server is not running or not accepting connections on port 1705."
        elif "unreachable" in error_msg.lower():
            display_msg = "Host unreachable. Check network connectivity."
        else:
            display_msg = f"Failed to connect: {error_msg}"

        QMessageBox.critical(self, "Connection Failed", display_msg)

        # Reset button state
        self.connect_button.setText("Connect")
        self.connect_button.setEnabled(True)

    def create_sources_list(self) -> Dict[str, str]:
        """
        Creates the sources list for the server.

        Returns:
            sources_dict (dict): A dictionary containing the sources friendly name and unique identifier.
        """
        self.logger.debug("Creating sources list.")
        sources_dict: Dict[str, str] = {}
        if self.server is not None:
            for source in self.server.streams:
                self.logger.debug(f"Source {source.identifier} found.")
                sources_dict[source.friendly_name] = source.identifier
        return sources_dict

    def create_volume_sliders(self) -> None:
        """
        Creates volume sliders for each client in the server.

        This method initializes and configures the volume sliders for each client
        connected to the server. It first clears any existing sliders from the layout,
        then iterates through the clients to create and add new sliders.

        The sliders allow users to adjust the volume for each client. Additionally,
        it creates buttons for muting/unmuting clients, displaying client information,
        and deleting offline clients.

        The method handles both connected and offline clients, displaying appropriate
        icons and enabling/disabling controls based on the client's connection status.
            None
        """
        self.logger.debug("Creating volume sliders.")
        if self.server is None:
            return
        self.slider_widgets: List[QLayout] = []

        def clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout:
                        clear_layout(sub_layout)

        clear_layout(self.slider_layout)

        for client in self.server.clients:
            if self.show_offline_clients_button.isChecked() or client.connected:
                self.logger.debug(
                    f"Creating volume slider for {client.identifier}. {
                        client.friendly_name
                    }."
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
                speaker_button.setProperty(
                    "client_id", client.identifier
                )  # For async updates
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
                    info_button.clicked.connect(
                        lambda client=client.identifier: self.remove_client(client)
                    )

                client_layout.addWidget(info_button)

                if not client.connected:
                    slider.setEnabled(False)

                self.slider_layout.addLayout(client_layout)
                self.slider_widgets.append(client_layout)
                self.slider_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setMinimumHeight(300)

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
                    self.logger.debug(
                        "Slider value updated for {} to {}.".format(client_id, value)
                    )
                    break
        except Exception as e:
            self.logger.error(
                "Error updating slider value for {}: {}".format(client_id, str(e))
            )

    """Methods to interact with clients."""

    def change_volume(self, client_id: str, volume: int) -> None:
        """Changes the volume of the client with the provided ID.

        Args:
            client_id (str): The UID of the client.
            volume (int): The new volume level.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        client: Optional[Snapclient] = next(
            (
                c
                for c in self.server.clients
                if c.identifier == client_id and c.connected
            ),
            None,
        )

        if not client:
            self.logger.warning("Client not found with the provided ID.")
            return

        self.logger.debug(f"Changing volume for client {client_id} to {volume}.")

        self.async_bridge.schedule_coroutine(
            client.set_volume(volume),
            callback=lambda _: self.logger.debug(
                f"Volume changed for client {client_id} to {volume}."
            ),
            error_callback=lambda e: self._handle_async_error("change volume", e),
        )

    def _handle_async_error(self, operation: str, error: Exception) -> None:
        """Handle errors from async operations."""
        error_msg = f"Could not {operation}: {str(error)}"
        self.logger.error(error_msg)
        QMessageBox.critical(self, "Error", error_msg, QMessageBox.Ok)

    def change_muted_state(self, client_id: str) -> None:
        """
        Changes the muted state of the client with the provided ID.

        Args:
            client_id (str): The unique identifier of the client.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        client = next(
            (
                c
                for c in self.server.clients
                if c.identifier == client_id and c.connected
            ),
            None,
        )

        if not client:
            self.logger.warning("Client not found with the provided ID.")
            QMessageBox.critical(
                self, "Error", "Client not found with the provided ID.", QMessageBox.Ok
            )
            return

        new_muted_state = not client.muted
        self.async_bridge.schedule_coroutine(
            client.set_muted(new_muted_state),
            callback=lambda _: self.logger.debug(
                f"Muted state changed for client {client_id}."
            ),
            error_callback=lambda e: self._handle_async_error("change muted state", e),
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
                self.logger.warning("Client not found with the provided UID.")
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
            self.logger.warning(f"Could not change button icon for client: {str(e)}")

    def change_client_name(self, client_uid: str, qtextedit: QTextEdit) -> None:
        """
        Changes the name of the client using the provided UID and the text from the qtextedit.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        qtextedit_text = qtextedit.toPlainText()
        client = next(
            (
                c
                for c in self.server.clients
                if c.identifier == client_uid and c.connected
            ),
            None,
        )

        if not client:
            return

        self.async_bridge.schedule_coroutine(
            client.set_name(qtextedit_text),
            callback=lambda _: self.logger.debug(
                f"Name changed for client {client_uid} to {qtextedit_text}."
            ),
            error_callback=lambda e: self._handle_async_error("change client name", e),
        )

    def change_latency(self, client_uid: str, new_latency: int) -> None:
        """
        Changes the latency of the client with the provided UID.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        client = next(
            (
                c
                for c in self.server.clients
                if c.identifier == client_uid and c.connected
            ),
            None,
        )

        if not client:
            self.logger.warning("Client not found with the provided UID.")
            QMessageBox.critical(
                self, "Error", "Client not found with the provided UID.", QMessageBox.Ok
            )
            return

        self.async_bridge.schedule_coroutine(
            client.set_latency(new_latency),
            callback=lambda _: self.logger.debug(
                f"Latency changed for client {client_uid} to {new_latency}."
            ),
            error_callback=lambda e: self._handle_async_error("change latency", e),
        )

    def change_group_volume(self, client_uid: str, volume: int) -> None:
        """
        Changes the group volume of the client with the provided UID.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        client = next(
            (
                c
                for c in self.server.clients
                if c.identifier == client_uid and c.connected
            ),
            None,
        )

        if not client:
            self.logger.warning("Client not found with the provided UID.")
            QMessageBox.critical(
                self, "Error", "Client not found with the provided UID.", QMessageBox.Ok
            )
            return

        self.async_bridge.schedule_coroutine(
            client.group.set_volume(volume),
            callback=lambda _: self.logger.debug(
                f"Group volume changed for client {client_uid} to {volume}."
            ),
            error_callback=lambda e: self._handle_async_error("change group volume", e),
        )

        """Methods to interact with groups."""

    def change_group_name(self, client_uid: str, group_name: str) -> None:
        """
        Changes the group name of the client with the provided UID.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        client = next(
            (
                c
                for c in self.server.clients
                if c.identifier == client_uid and c.connected
            ),
            None,
        )

        if not client:
            self.logger.warning("Client not found with the provided UID.")
            QMessageBox.critical(
                self, "Error", "Client not found with the provided UID.", QMessageBox.Ok
            )
            return

        self.async_bridge.schedule_coroutine(
            client.group.set_name(str(group_name)),
            callback=lambda _: self.logger.debug(
                f"Group name changed for client {client_uid} to {group_name}."
            ),
            error_callback=lambda e: self._handle_async_error("change group name", e),
        )

    def change_singular_client_source(self, client_uid: str, stream_id: str) -> None:
        """
        Changes the source of the client with the provided UID.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        self.logger.debug(f"Attempting to find client with UID: {client_uid}")
        client = self.server.client(client_uid)

        if not client:
            error_message = f"Client with UID {client_uid} not found."
            self.logger.error(error_message)
            QMessageBox.critical(None, "Client Not Found", error_message)
            return

        self.logger.debug(
            f"Changing stream for client {client_uid} to stream {stream_id}."
        )
        group = client.group

        self.async_bridge.schedule_coroutine(
            group.set_stream(stream_id),
            callback=lambda _: self.logger.debug(
                f"Stream changed successfully for client {client_uid}."
            ),
            error_callback=lambda e: self._handle_async_error("change source", e),
        )

    def change_group_source(self, group_id: str, stream_id: str) -> None:
        """Changes the source for the group with the provided ID.

        Args:
            group_id: The unique identifier of the group.
            stream_id: The unique identifier of the stream to change to.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        self.logger.debug(f"Attempting to find group with UID: {group_id}")
        group = self.server.group(group_id)

        if not group:
            error_message = f"Group with UID {group_id} not found."
            self.logger.error(error_message)
            QMessageBox.critical(None, "Group Not Found", error_message)
            return

        self.logger.debug(
            f"Changing stream for group {group_id} to stream {stream_id}."
        )

        self.async_bridge.schedule_coroutine(
            group.set_stream(stream_id),
            callback=lambda _: self.logger.debug(
                f"Stream changed successfully for group {group_id}."
            ),
            error_callback=lambda e: self._handle_async_error("change group source", e),
        )

    def remove_client(self, client_uid: str) -> None:
        """
        Removes the client with the provided UID.
        """
        if not self.server:
            self.logger.warning("Server is not available.")
            return

        client = next(
            (c for c in self.server.clients if c.identifier == client_uid),
            None,
        )

        if not client:
            self.logger.warning("Client not found with the provided UID.")
            QMessageBox.critical(
                self, "Error", "Client not found with the provided UID.", QMessageBox.Ok
            )
            return

        def on_remove_success(_):
            self.logger.debug(f"Client {client_uid} removed.")
            self.create_volume_sliders()  # Refresh UI

        self.async_bridge.schedule_coroutine(
            client.remove(),
            callback=on_remove_success,
            error_callback=lambda e: self._handle_async_error("remove client", e),
        )

    def show_client_info(
        self,
        client_id: str,
        slider: QSlider,
        mute_button: QPushButton,
        client_label: QTextEdit,
    ) -> None:
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
                    self.logger.debug(f"Client Info for {client_id} found.")
                    break
            else:
                self.logger.warning(
                    f"Client {client_id} not found in client dictionary."
                )
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Client {client_id} not found in client dictionary.",
                    QMessageBox.Ok,
                    QMessageBox.NoButton,
                )
                return
        else:
            self.logger.warning("Server is not available.")
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
        self.logger.debug("Client Info Dialog shown.")

    def show_server_info(self) -> None:
        """
        Shows the server info dialog for the server.
        """
        self.logger.debug("Showing server info dialog.")
        if not self.server:
            QMessageBox.warning(self, "Warning", "Not connected to a server.")
            return

        def on_status_received(status):
            server_info_json = json.dumps(status)
            dialog = ServerInfoDialog(server_info_json, self.log_level)
            dialog.exec()

        self.async_bridge.schedule_coroutine(
            self.server.status(),
            callback=on_status_received,
            error_callback=lambda e: self._handle_async_error("get server info", e),
        )

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

        # Clear server from AsyncBridge (do NOT close the shared event loop)
        self.async_bridge.clear_server()
        self.server = None

        self.logger.info("Disconnected from server.")
        Notifications.send_notify(
            "Disconnected from server.", "Snapcast Gui", self.snapcast_settings
        )

        self.connect_button.setText("Connect")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.create_server)
        self.connect_button.setToolTip("Connect to the selected server.")

    def disable_controls(self) -> None:
        """
        Disables the controls when needed to connect to the server.
        """
        self.logger.debug("Disabling controls.")
        self.ip_input.setEnabled(False)
        self.ip_dropdown.setEnabled(False)
        self.add_ip_button.setEnabled(False)
        self.remove_ip_button.setEnabled(False)
        self.server_info_button.setEnabled(True)

    def enable_controls(self) -> None:
        """
        Enables the controls when needed to disconnect from the server.
        """
        self.logger.debug("Enabling controls.")
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
        self.logger.debug("Tray Icon created.")
