import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QMessageBox, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QFont

import mock_server
from workers import LoginWorker
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
            QPushButton#mockBtn {
                background-color: #1a1a24;
                color: #00d2d3;
                border: 1px solid #00d2d3;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#mockBtn:hover {
                background-color: rgba(0, 210, 211, 0.1);
            }
            QPushButton#mockBtn:pressed {
                background-color: rgba(0, 210, 211, 0.2);
            }
            QPushButton#togglePassBtn {
                background: none;
                border: none;
                color: #8f8f9e;
                font-weight: bold;
                padding: 0px 5px;
            }
            QPushButton#togglePassBtn:hover {
                color: #ffffff;
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
        card = QFrame(self)
        card.setObjectName("card")
        card.setFixedWidth(400)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
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
        
        pass_input_layout = QHBoxLayout()
        self.pass_input = QLineEdit(self)
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter your password")
        
        self.toggle_pass_btn = QPushButton("👁", self)
        self.toggle_pass_btn.setObjectName("togglePassBtn")
        self.toggle_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pass_btn.clicked.connect(self.toggle_password_visibility)
        
        # Position absolute feel inside lineedit or side-aligned
        pass_input_layout.addWidget(self.pass_input)
        pass_input_layout.addWidget(self.toggle_pass_btn)
        
        card_layout.addWidget(pass_label)
        card_layout.addLayout(pass_input_layout)

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

        # Divider
        divider_layout = QHBoxLayout()
        line1 = QFrame(self)
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("background-color: #282830;")
        line2 = QFrame(self)
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("background-color: #282830;")
        or_label = QLabel("OR", self)
        or_label.setStyleSheet("color: #6f6f7e; font-size: 11px;")
        
        divider_layout.addWidget(line1)
        divider_layout.addWidget(or_label)
        divider_layout.addWidget(line2)
        card_layout.addLayout(divider_layout)

        # Mock Server Button
        self.mock_btn = QPushButton("⚡ USE LOCAL MOCK SERVER", self)
        self.mock_btn.setObjectName("mockBtn")
        self.mock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mock_btn.clicked.connect(self.login_with_mock)
        card_layout.addWidget(self.mock_btn)

        outer_layout.addWidget(card)

    def toggle_password_visibility(self):
        if self.pass_input.echoMode() == QLineEdit.EchoMode.Password:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pass_btn.setText("🙈")
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_btn.setText("👁")

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
        self.mock_btn.setEnabled(enabled)
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

    def login_with_mock(self):
        # Start local mock server
        mock_server.start_server()
        
        # Fill in mock server details
        self.host_input.setText("http://127.0.0.1:8081")
        self.user_input.setText("mock_user")
        self.pass_input.setText("mock_password")
        
        # Log in
        self.start_login()
