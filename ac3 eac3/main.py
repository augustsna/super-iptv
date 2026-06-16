import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from login_widget import LoginWidget
from dashboard_widget import DashboardWidget
import mock_server
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Super Stream")
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "favicon.png")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(1100, 700)
        
        # Central Stacked Widget
        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)
        
        # Login Screen
        self.login_widget = LoginWidget(self)
        self.login_widget.login_success.connect(self.on_login_success)
        self.stacked_widget.addWidget(self.login_widget)
        
        self.dashboard_widget = None
        
        self.apply_theme()

    def apply_theme(self):
        # Apply clean dark styling globally
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0c0c0e;
            }
            QScrollBar:vertical {
                border: none;
                background: #121215;
                width: 10px;
                margin: 0px 0 0px 0;
            }
            QScrollBar::handle:vertical {
                background: #2c2c35;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c5ce7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #121215;
                height: 10px;
                margin: 0 0px 0 0px;
            }
            QScrollBar::handle:horizontal {
                background: #2c2c35;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #6c5ce7;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

    def on_login_success(self, client):
        logging.info("Main Window: Transitioning to Dashboard...")
        # Create the dashboard with authenticated API client
        self.dashboard_widget = DashboardWidget(client, self)
        self.dashboard_widget.logout_requested.connect(self.on_logout)
        
        # Add to stack and display
        self.stacked_widget.addWidget(self.dashboard_widget)
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)

    def on_logout(self):
        logging.info("Main Window: Returning to Login...")
        # Switch to login screen
        self.stacked_widget.setCurrentWidget(self.login_widget)
        
        # Clean up dashboard memory and close active worker threads/connections
        if self.dashboard_widget:
            self.stacked_widget.removeWidget(self.dashboard_widget)
            self.dashboard_widget.deleteLater()
            self.dashboard_widget = None

    def closeEvent(self, event):
        logging.info("Main Window: Shutting down. Terminating mock server and processes...")
        # Ensure player is stopped
        if self.dashboard_widget:
            try:
                self.dashboard_widget.player_widget.stop()
            except Exception:
                pass
                
        # Clean up mock server
        mock_server.stop_server()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set global modern Font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    # Safe execute
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
