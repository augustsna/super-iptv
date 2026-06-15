import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QMessageBox, QGraphicsDropShadowEffect, QSizePolicy,
    QDialog, QFormLayout, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QColor, QFont

import mock_server
from workers import LoginWorker, SyncWorker, AdminAuthWorker, AdminSaveWorker
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LoginWidget(QWidget):
    # Signal emitted on successful login, sending the authenticated XtreamClient object
    login_success = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("XtreamPlayer", "LoginDetails")
        self.login_worker = None
        
        self.setup_ui()
        self.load_saved_credentials()
        self.start_sync()

    def setup_ui(self):
        self.setObjectName("LoginWidget")
        # Global widget background
        self.setStyleSheet("""
            #LoginWidget {
                background-color: #0c0c0e;
            }
            QFrame#card {
                background-color: #16161a;
                border: 1px solid #282830;
                border-radius: 16px;
            }
            QLabel#title {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            QLabel#subtitle {
                color: #8f8f9e;
                font-size: 13px;
                margin-bottom: 20px;
            }
            QLabel#fieldLabel {
                color: #c5c5d2;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 4px;
            }
            QLineEdit {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid #2d2d38;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                selection-background-color: #6c5ce7;
            }
            QLineEdit:focus {
                border-color: #6c5ce7;
                background-color: #22222b;
            }
            QPushButton#loginBtn {
                background-color: #6c5ce7;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#loginBtn:hover {
                background-color: #5b4cc4;
            }
            QPushButton#loginBtn:pressed {
                background-color: #4a3cb0;
            }
            QPushButton#adminBtn {
                background: none;
                border: none;
                color: #8f8f9e;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                padding: 5px;
                margin-top: 5px;
            }
            QPushButton#adminBtn:hover {
                color: #6c5ce7;
            }
            QLabel#statusLabel {
                color: #ff7675;
                font-size: 13px;
                font-weight: bold;
            }
        """)

        # Main Layout (Centering container)
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Login Card
        self.card = QFrame(self)
        self.card.setObjectName("card")
        self.card.setFixedWidth(400)
        self.card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(35, 40, 35, 40)
        card_layout.setSpacing(15)

        # Header
        title = QLabel("XTREME STREAMER", self)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Login with your Xtream Codes API server", self)
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        # Input Fields
        # 1. Server Host URL
        host_label = QLabel("SERVER HOST URL", self)
        host_label.setObjectName("fieldLabel")
        self.host_input = QLineEdit(self)
        self.host_input.setPlaceholderText("http://your-iptv-server.com:8080")
        
        card_layout.addWidget(host_label)
        card_layout.addWidget(self.host_input)

        # 2. Username
        user_label = QLabel("USERNAME", self)
        user_label.setObjectName("fieldLabel")
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("Enter your username")
        
        card_layout.addWidget(user_label)
        card_layout.addWidget(self.user_input)

        # 3. Password
        pass_label = QLabel("PASSWORD", self)
        pass_label.setObjectName("fieldLabel")
        self.pass_input = QLineEdit(self)
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal) # Do not censor!
        self.pass_input.setPlaceholderText("Enter your password")
        
        card_layout.addWidget(pass_label)
        card_layout.addWidget(self.pass_input)
 
        # Status Message area
        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)
 
        # Buttons
        self.login_btn = QPushButton("LOG IN", self)
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.start_login)
        card_layout.addWidget(self.login_btn)
 
        # Divider line above Admin button
        admin_divider = QFrame(self)
        admin_divider.setFrameShape(QFrame.Shape.HLine)
        admin_divider.setStyleSheet("background-color: #282830; margin-top: 15px; margin-bottom: 5px;")
        card_layout.addWidget(admin_divider)

        # Admin Panel Link Button
        self.admin_btn = QPushButton("🔐 SERVER ADMIN PANEL", self)
        self.admin_btn.setObjectName("adminBtn")
        self.admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.admin_btn.clicked.connect(self.open_admin_panel)
        card_layout.addWidget(self.admin_btn)

        outer_layout.addWidget(self.card)

    def load_saved_credentials(self):
        self.host_input.setText(self.settings.value("host", ""))
        self.user_input.setText(self.settings.value("username", ""))
        self.pass_input.setText(self.settings.value("password", ""))

    def save_credentials(self, host, username, password):
        self.settings.setValue("host", host)
        self.settings.setValue("username", username)
        self.settings.setValue("password", password)

    def set_ui_enabled(self, enabled):
        self.host_input.setEnabled(enabled)
        self.user_input.setEnabled(enabled)
        self.pass_input.setEnabled(enabled)
        self.login_btn.setEnabled(enabled)
        if not enabled:
            self.login_btn.setText("CONNECTING...")
        else:
            self.login_btn.setText("LOG IN")

    def start_login(self):
        host = self.host_input.text().strip()
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not host or not username or not password:
            self.status_label.setText("⚠ Please fill in all fields.")
            return

        self.status_label.setText("")
        self.set_ui_enabled(False)

        # Start LoginWorker Thread
        self.login_worker = LoginWorker(host, username, password)
        self.login_worker.finished.connect(self.on_login_finished)
        self.login_worker.start()

    def on_login_finished(self, success, message):
        self.set_ui_enabled(True)
        if success:
            logging.info("LoginWidget: Login successful.")
            # Save credentials for convenience
            self.save_credentials(self.host_input.text(), self.user_input.text(), self.pass_input.text())
            # Emit success signal with client instance
            self.login_success.emit(self.login_worker.client)
        else:
            logging.warning(f"LoginWidget: Login failed - {message}")
            self.status_label.setText(f"⚠ {message}")

    def start_sync(self):
        self.status_label.setStyleSheet("color: #8f8f9e;")
        self.status_label.setText("Syncing with Ubuntu server...")
        self.set_ui_enabled(False)
        
        # Start SyncWorker Thread
        self.sync_worker = SyncWorker()
        self.sync_worker.finished.connect(self.on_sync_finished)
        self.sync_worker.start()

    def on_sync_finished(self, success, data, message):
        self.set_ui_enabled(True)
        if success:
            xtream_url = data.get("xtreamUrl", "")
            username = data.get("username", "")
            password = data.get("password", "")
            
            self.host_input.setText(xtream_url)
            self.user_input.setText(username)
            self.pass_input.setText(password)
            
            logging.info("LoginWidget: Synced with Ubuntu Server successfully.")
            self.status_label.setStyleSheet("color: #00d2d3; font-weight: bold;")
            self.status_label.setText("✔ Synced with Ubuntu Server successfully!")
        else:
            logging.warning(f"LoginWidget: Sync failed - {message}")
            self.status_label.setStyleSheet("color: #ff7675; font-weight: bold;")
            self.status_label.setText(f"⚠ Sync failed: {message}")

    def open_admin_panel(self):
        dialog = AdminPanelDialog(self)
        dialog.resize(self.card.size())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.start_sync()


class AdminPanelDialog(QDialog):
    def __init__(self, parent=None, config_url="http://107.174.178.52/api/config"):
        super().__init__(parent)
        self.config_url = config_url
        self.admin_password = ""
        self.auth_worker = None
        self.save_worker = None
        
        self.setWindowTitle("Server Admin Panel")
        self.resize(450, 320)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121215;
                border: 1px solid #202026;
            }
            QLabel {
                color: #c5c5d2;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid #2d2d38;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6c5ce7;
                background-color: #22222b;
            }
            QPushButton {
                background-color: #6c5ce7;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5b4cc4;
            }
            QPushButton:pressed {
                background-color: #4a3cb0;
            }
            QPushButton:disabled {
                background-color: #2b2b35;
                color: #8f8f9e;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        self.stacked_widget = QStackedWidget(self)
        self.layout.addWidget(self.stacked_widget)

        # Page 1: Auth Screen
        self.auth_widget = QWidget()
        auth_layout = QVBoxLayout(self.auth_widget)
        auth_layout.setContentsMargins(0, 0, 0, 0)
        auth_layout.setSpacing(15)

        auth_layout.addStretch()

        title_label = QLabel("ADMIN AUTHENTICATION")
        title_label.setStyleSheet("font-size: 16px; color: #ffffff; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auth_layout.addWidget(title_label)

        # Password input
        self.admin_pass_input = QLineEdit()
        self.admin_pass_input.setPlaceholderText("Enter admin password")
        self.admin_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_pass_input.setFixedWidth(300)
        auth_layout.addWidget(self.admin_pass_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Auth Button
        self.auth_btn = QPushButton("LOGIN TO ADMIN PANEL")
        self.auth_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auth_btn.clicked.connect(self.start_auth)
        self.auth_btn.setFixedWidth(300)
        auth_layout.addWidget(self.auth_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Auth Status
        self.auth_status = QLabel("")
        self.auth_status.setStyleSheet("color: #ff7675; font-weight: bold;")
        self.auth_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auth_layout.addWidget(self.auth_status)
        
        auth_layout.addStretch()

        self.stacked_widget.addWidget(self.auth_widget)

        # Page 2: Config Screen
        self.config_widget = QWidget()
        config_layout = QVBoxLayout(self.config_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(8)

        config_layout.addStretch()

        config_title = QLabel("ADMIN CONFIGURATION")
        config_title.setStyleSheet("font-size: 16px; color: #ffffff; font-weight: bold; margin-bottom: 5px;")
        config_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(config_title)

        # Vertical labels and fields
        host_lbl = QLabel("DEFAULT SERVER HOST URL:")
        host_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.default_host_input = QLineEdit()
        self.default_host_input.setPlaceholderText("http://example.com:8080")
        self.default_host_input.setFixedWidth(300)
        
        user_lbl = QLabel("DEFAULT USERNAME:")
        user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.default_user_input = QLineEdit()
        self.default_user_input.setPlaceholderText("Username")
        self.default_user_input.setFixedWidth(300)
        
        pass_lbl = QLabel("DEFAULT PASSWORD:")
        pass_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.default_pass_input = QLineEdit()
        self.default_pass_input.setPlaceholderText("Password")
        self.default_pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self.default_pass_input.setFixedWidth(300)

        config_layout.addWidget(host_lbl)
        config_layout.addWidget(self.default_host_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(user_lbl)
        config_layout.addWidget(self.default_user_input, alignment=Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(pass_lbl)
        config_layout.addWidget(self.default_pass_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Save Button
        self.save_btn = QPushButton("SAVE CONFIGURATION")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.start_save)
        self.save_btn.setFixedWidth(300)
        config_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Config Status
        self.config_status = QLabel("")
        self.config_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        config_layout.addWidget(self.config_status)

        config_layout.addStretch()

        self.stacked_widget.addWidget(self.config_widget)

    def start_auth(self):
        password = self.admin_pass_input.text().strip()
        if not password:
            self.auth_status.setText("⚠ Please enter admin password.")
            return

        self.auth_status.setStyleSheet("color: #8f8f9e;")
        self.auth_status.setText("Authenticating...")
        self.auth_btn.setEnabled(False)
        self.admin_pass_input.setEnabled(False)

        self.auth_worker = AdminAuthWorker(self.config_url, password)
        self.auth_worker.finished.connect(self.on_auth_finished)
        self.auth_worker.start()

    def on_auth_finished(self, success, config, message):
        self.auth_btn.setEnabled(True)
        self.admin_pass_input.setEnabled(True)

        if success:
            self.admin_password = self.admin_pass_input.text().strip()
            self.auth_status.setText("")
            
            # Populate config fields
            self.default_host_input.setText(config.get("xtreamUrl", ""))
            self.default_user_input.setText(config.get("username", ""))
            self.default_pass_input.setText(config.get("password", ""))
            
            # Switch to config page
            self.stacked_widget.setCurrentIndex(1)
        else:
            self.auth_status.setStyleSheet("color: #ff7675; font-weight: bold;")
            self.auth_status.setText(f"⚠ {message}")

    def start_save(self):
        host = self.default_host_input.text().strip()
        user = self.default_user_input.text().strip()
        pwd = self.default_pass_input.text().strip()

        if not host or not user or not pwd:
            self.config_status.setStyleSheet("color: #ff7675; font-weight: bold;")
            self.config_status.setText("⚠ Please fill in all default config fields.")
            return

        self.config_status.setStyleSheet("color: #8f8f9e;")
        self.config_status.setText("Saving config to server...")
        self.save_btn.setEnabled(False)

        self.save_worker = AdminSaveWorker(self.config_url, self.admin_password, host, user, pwd)
        self.save_worker.finished.connect(self.on_save_finished)
        self.save_worker.start()

    def on_save_finished(self, success, message):
        self.save_btn.setEnabled(True)
        if success:
            self.config_status.setStyleSheet("color: #00d2d3; font-weight: bold;")
            self.config_status.setText(f"✔ {message}")
            QTimer.singleShot(1500, self.accept)
        else:
            self.config_status.setStyleSheet("color: #ff7675; font-weight: bold;")
            self.config_status.setText(f"⚠ {message}")
