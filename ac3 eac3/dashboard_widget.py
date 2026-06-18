import datetime
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QLineEdit, QStackedWidget, QSplitter,
    QFrame, QComboBox, QScrollArea, QSizePolicy, QStyle, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl, QTimer, QSettings
from PyQt6.QtGui import QColor, QFont, QPixmap, QIcon
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from player_widget import PlayerWidget
from workers import (
    FetchCategoriesWorker, FetchStreamsWorker, FetchSeriesInfoWorker
)
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DashboardWidget(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.settings = QSettings("XtreamPlayer", "AppSettings")
        self.batch_combo = None
        self.live_batch_combo = None
        self.movie_batch_combo = None
        self.series_batch_combo = None
        self.default_batch_limit = "50"
        self.client = client
        self.player_widget = PlayerWidget(self)
        self.player_widget.full_program_state_changed.connect(self.on_player_full_program_changed)
        self.network_manager = QNetworkAccessManager(self)
        self.logo_cache = {}
        self.downloading_urls = set()
        self.streams_data = {"live": [], "vod": [], "series": []}
        self.streams_loaded_count = {"live": 0, "vod": 0, "series": 0}
        
        # Cache for loaded categories and streams to avoid unnecessary network queries
        self.categories_cache = {"live": [], "vod": [], "series": []}
        self.streams_cache = {"live": {}, "vod": {}, "series": {}}
        self.current_streams = []
        
        # Track active workers to avoid race conditions
        self.cat_worker = None
        self.stream_worker = None
        self.series_info_worker = None
        
        # Track where the player widget is currently docked
        # "mini" (Live TV sidebar) or "theater" (Movies/Series theater mode)
        self.player_dock_state = None 

        self.setup_ui()
        
        # Trigger initial loading of Live TV categories
        self.show_live_tv()

    def on_batch_limit_changed(self, text):
        for combo in [self.batch_combo, self.live_batch_combo, self.movie_batch_combo, self.series_batch_combo]:
            if combo is not None and combo.currentText() != text:
                combo.blockSignals(True)
                combo.setCurrentText(text)
                combo.blockSignals(False)
        self.reload_active_tab_streams()

    def reload_active_tab_streams(self):
        if not hasattr(self, 'content_stack') or self.content_stack is None:
            return
        active_tab = self.content_stack.currentIndex()
        if active_tab == 0:
            if hasattr(self, 'live_cat_list') and self.live_cat_list is not None:
                self.on_live_category_changed(self.live_cat_list.currentRow())
        elif active_tab == 1:
            if hasattr(self, 'movie_cat_list') and self.movie_cat_list is not None:
                self.on_movie_category_changed(self.movie_cat_list.currentRow())
        elif active_tab == 2:
            if hasattr(self, 'series_cat_list') and self.series_cat_list is not None:
                self.on_series_category_changed(self.series_cat_list.currentRow())

    def get_batch_size(self):
        text = None
        for combo in [self.batch_combo, self.live_batch_combo, self.movie_batch_combo, self.series_batch_combo]:
            if combo is not None:
                text = combo.currentText()
                break
        if not text:
            text = "50"
            
        text = text.strip().lower()
        if "all" in text:
            return 9999999
        digits = "".join([c for c in text if c.isdigit()])
        if digits:
            try:
                return max(1, int(digits))
            except ValueError:
                pass
        return 50  # fallback default

    def setup_ui(self):
        self.setObjectName("DashboardWidget")
        self.setStyleSheet("""
            #DashboardWidget {
                background-color: #07090e;
            }
            /* Sidebar Styling */
            QFrame#sidebar {
                background-color: #0a0c14;
                border-right: 1px solid #1c2133;
            }
            QLabel#logoText {
                color: #00f0ff;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 5px;
            }
            QPushButton.nav-btn {
                background-color: transparent;
                color: #9ca3af;
                border: none;
                border-left: 3px solid transparent;
                padding: 12px 15px;
                text-align: left;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton.nav-btn:hover {
                color: #ffffff;
                background-color: #151a25;
            }
            QPushButton.nav-btn.active {
                color: #00f0ff;
                background-color: #151a25;
                border-left: 3px solid #00f0ff;
            }
            /* Main Content Panels */
            QFrame#contentPanel {
                background-color: #07090e;
            }
            QListWidget {
                background-color: #10141e;
                color: #ffffff;
                border: 1px solid #1e2538;
                border-radius: 6px;
                padding: 5px;
                outline: 0;
            }
            #live_cat_widget, #movie_cat_widget, #series_cat_widget {
                background-color: #10141e;
                border: 1px solid #1e2538;
                border-radius: 6px;
            }
            #live_cat_widget QListWidget, #movie_cat_widget QListWidget, #series_cat_widget QListWidget {
                background-color: transparent;
                border: none;
                padding: 0px 5px 5px 5px;
            }
            QListWidget::item {
                border-radius: 4px;
                padding: 8px 10px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #1a2030;
                color: #00f0ff;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 240, 255, 0.15);
                color: #00f0ff;
                font-weight: bold;
                border-left: 3px solid #00f0ff;
                padding-left: 7px;
            }
            /* Search input */
            QLineEdit.search-bar {
                background-color: #10141e;
                color: #ffffff;
                border: 1px solid #1e2538;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit.search-bar:focus {
                border-color: #00f0ff;
            }
            /* Detail Panes */
            QFrame.detail-pane {
                background-color: #10141e;
                border: 1px solid #1e2538;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel.pane-title {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel.meta-label {
                color: #9ca3af;
                font-size: 12px;
            }
            QLabel.plot-label {
                color: #d1d5db;
                font-size: 13px;
                line-height: 1.4;
            }
            QPushButton.action-btn {
                background-color: #00f0ff;
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton.action-btn:hover {
                background-color: #5bf7ff;
            }
            QPushButton.action-btn:pressed {
                background-color: #00b5cc;
            }
            /* QSplitter handle */
            QSplitter::handle {
                background-color: #1c2133;
                width: 2px;
            }
            /* Custom Scrollbars */
            QScrollBar:vertical {
                border: none;
                background: #0f0f12;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #2c2c35;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00f0ff;
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
                background: #0f0f12;
                height: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #2c2c35;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #00f0ff;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        # Main Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Sidebar Frame
        self.sidebar = QFrame(self)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App Logo
        import os
        brand_widget = QWidget(self.sidebar)
        brand_layout = QHBoxLayout(brand_widget)
        brand_layout.setContentsMargins(20, 15, 15, 15)
        brand_layout.setSpacing(10)
        
        logo_icon = QLabel(brand_widget)
        icon_path = os.path.join(os.path.dirname(__file__), "favicon.png")
        logo_icon.setPixmap(QPixmap(icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        logo = QLabel("Super Stream", brand_widget)
        logo.setObjectName("logoText")
        logo.setStyleSheet("padding: 0px;")
        
        brand_layout.addWidget(logo_icon)
        brand_layout.addWidget(logo)
        brand_layout.addStretch()
        
        sidebar_layout.addWidget(brand_widget)
        
        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            ("Live TV", self.show_live_tv, "tv"),
            ("Movies", self.show_movies, "film"),
            ("Series", self.show_series, "clapperboard"),
        ]
        
        import os
        for idx, (label, callback, icon_name) in enumerate(nav_items):
            btn = QPushButton("  " + label, self.sidebar)
            icon_path = os.path.join(os.path.dirname(__file__), "icons", f"{icon_name}.svg")
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            btn.setObjectName(f"nav_{idx}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet("text-align: left; padding-left: 20px;")
            btn.clicked.connect(callback)
            
            # Use property to toggle active stylesheet
            btn.setProperty("class", "nav-btn")
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Settings button
        settings_btn = QPushButton("  Settings", self.sidebar)
        settings_icon_path = os.path.join(os.path.dirname(__file__), "icons", "settings.svg")
        settings_btn.setIcon(QIcon(settings_icon_path))
        settings_btn.setIconSize(QSize(18, 18))
        settings_btn.setCheckable(True)
        settings_btn.setObjectName("nav_3")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        settings_btn.setStyleSheet("text-align: left; padding-left: 20px;")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setProperty("class", "nav-btn")
        sidebar_layout.addWidget(settings_btn)
        self.nav_buttons.append(settings_btn)

        # Expiry Badge
        exp_date = self.client.user_info.get("exp_date")
        if exp_date:
            try:
                exp_timestamp = int(exp_date)
                if exp_timestamp == 0:
                    exp_text = "Expires: Unlimited"
                    exp_remain = ""
                    color = "#05ffc5"
                else:
                    import time, datetime
                    now = int(time.time())
                    diff = exp_timestamp - now
                    dt = datetime.datetime.fromtimestamp(exp_timestamp)
                    exp_text = f"Expires: {dt.strftime('%m/%d/%Y')}"
                    if diff <= 0:
                        exp_text = f"Expired ({dt.strftime('%m/%d/%Y')})"
                        exp_remain = "Expired"
                        color = "#f87171"
                    else:
                        days = diff // 86400
                        hours = (diff % 86400) // 3600
                        minutes = (diff % 3600) // 60
                        if days > 0:
                            exp_remain = f"{days}d {hours}h {minutes}m remaining"
                        else:
                            exp_remain = f"{hours}h {minutes}m remaining"
                        color = "#05ffc5" if days > 7 else "#f87171"
                
                expiry_widget = QWidget(self.sidebar)
                expiry_widget.setObjectName("expiry_widget")
                expiry_layout = QVBoxLayout(expiry_widget)
                expiry_layout.setContentsMargins(8, 8, 8, 8)
                expiry_layout.setSpacing(2)
                
                expiry_widget.setStyleSheet("""
                    #expiry_widget {
                        background-color: rgba(18, 18, 21, 0.4);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 6px;
                    }
                    QLabel {
                        border: none;
                        background: transparent;
                    }
                """)
                
                # Top row: Neon Dot + Portal Label
                portal_row = QWidget(expiry_widget)
                portal_layout = QHBoxLayout(portal_row)
                portal_layout.setContentsMargins(0, 0, 0, 0)
                portal_layout.setSpacing(4)
                
                neon_dot = QLabel("●", portal_row)
                neon_dot.setStyleSheet("color: #10b981; font-size: 10px;")
                
                portal_label = QLabel("XTREAM PORTAL", portal_row)
                portal_label.setStyleSheet("color: #d1d5db; font-size: 9px; font-weight: 900; letter-spacing: 1px;")
                
                portal_layout.addWidget(neon_dot)
                portal_layout.addWidget(portal_label)
                portal_layout.addStretch()
                
                expiry_layout.addWidget(portal_row)
                
                # Server URL
                host_str = getattr(self.client, 'host', 's1.dnspass.xyz:80')
                host_str = host_str.replace("http://", "").replace("https://", "").strip("/")
                
                server_url_label = QLabel(host_str, expiry_widget)
                server_url_label.setStyleSheet("color: #6b7280; font-size: 11px; font-family: monospace;")
                expiry_layout.addWidget(server_url_label)
                
                # Expiry Details
                exp_label = QLabel(exp_text, expiry_widget)
                exp_label.setStyleSheet("color: #6b7280; font-size: 10px;")
                expiry_layout.addWidget(exp_label)
                
                if exp_remain:
                    remain_row = QWidget(expiry_widget)
                    remain_layout = QHBoxLayout(remain_row)
                    remain_layout.setContentsMargins(0, 0, 0, 0)
                    remain_layout.setSpacing(4)
                    
                    remain_dot = QLabel("●", remain_row)
                    remain_dot.setStyleSheet(f"color: {color}; font-size: 9px;")
                    
                    remain_label = QLabel(exp_remain, remain_row)
                    remain_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
                    
                    remain_layout.addWidget(remain_dot)
                    remain_layout.addWidget(remain_label)
                    remain_layout.addStretch()
                    
                    expiry_layout.addWidget(remain_row)
                
                sidebar_layout.addWidget(expiry_widget)
            except Exception as e:
                pass

        # Logout button
        logout_btn = QPushButton("  Logout", self.sidebar)
        logout_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "logout.svg")))
        logout_btn.setProperty("class", "nav-btn")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)

        # 2. Main Content Panels (using QStackedWidget)
        self.content_stack = QStackedWidget(self)
        self.content_stack.setObjectName("contentPanel")

        self.setup_live_tv_panel()
        self.setup_movies_panel()
        self.setup_series_panel()
        self.setup_settings_panel()

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_stack)

    # --- Panel Setups ---

    def setup_live_tv_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Splitter to allow resizing of Category / Channel lists
        self.live_splitter = QSplitter(Qt.Orientation.Horizontal, panel)
        
        # Left: Categories
        self.live_cat_widget = QWidget(self)
        self.live_cat_widget.setObjectName("live_cat_widget")
        self.live_cat_widget.setMinimumWidth(120)
        cat_layout = QVBoxLayout(self.live_cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        
        cat_title = QLabel("CATEGORIES", self)
        cat_title.setStyleSheet("color: #6b7280; font-size: 10px; font-weight: bold; padding: 10px 12px 4px 12px; letter-spacing: 1px; border: none; background: transparent;")
        self.live_cat_list = QListWidget(self)
        self.live_cat_list.currentRowChanged.connect(self.on_live_category_changed)
        
        cat_layout.addWidget(cat_title)
        cat_layout.addWidget(self.live_cat_list)

        # Center: Channel list & search bar
        self.live_channel_widget = QWidget(self)
        self.live_channel_widget.setMinimumWidth(120)
        channel_layout = QVBoxLayout(self.live_channel_widget)
        channel_layout.setContentsMargins(0, 0, 0, 0)
        
        self.live_channel_list = QListWidget(self)
        self.live_channel_list.setIconSize(QSize(28, 28))
        self.live_channel_list.itemClicked.connect(self.on_live_channel_clicked)
        self.live_channel_list.verticalScrollBar().valueChanged.connect(
            lambda val: self.load_visible_icons(self.live_channel_list)
        )
        
        channel_layout.addWidget(self.live_channel_list)

        # Right: Mini Player and Channel Info Details
        self.live_detail_pane = QFrame(self)
        self.live_detail_pane.setMinimumWidth(320)
        self.live_detail_pane.setProperty("class", "detail-pane")
        self.live_detail_layout = QVBoxLayout(self.live_detail_pane)
        self.live_detail_layout.setContentsMargins(8, 8, 8, 8)
        self.live_detail_layout.setSpacing(10)

        # Toggle layout row for panel visibilities
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(5)
        
        self.sidebar_toggle_btn = QPushButton("  Menu", self)
        self.sidebar_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "menu.svg")))
        self.sidebar_toggle_btn.setCheckable(True)
        self.sidebar_toggle_btn.setChecked(True)
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #141824;
                color: #e0e0e2;
                border: 1px solid #1e2538;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(156, 163, 175, 0.15);
                border-color: #9ca3af;
                color: #ffffff;
            }
            QPushButton:checked {
                color: #d1d5db;
                border-color: #9ca3af;
                background-color: rgba(156, 163, 175, 0.08);
            }
        """)
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        
        self.cat_toggle_btn = QPushButton("  Categories", self)
        self.cat_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "folder.svg")))
        self.cat_toggle_btn.setCheckable(True)
        self.cat_toggle_btn.setChecked(True)
        self.cat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cat_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.cat_toggle_btn.clicked.connect(self.toggle_categories)
        
        self.channel_toggle_btn = QPushButton("  Channels", self)
        self.channel_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))
        self.channel_toggle_btn.setCheckable(True)
        self.channel_toggle_btn.setChecked(True)
        self.channel_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.channel_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.channel_toggle_btn.clicked.connect(self.toggle_channels)
        
        toggle_layout.addWidget(self.sidebar_toggle_btn)
        toggle_layout.addWidget(self.cat_toggle_btn)
        toggle_layout.addWidget(self.channel_toggle_btn)
        toggle_layout.addStretch()
        
        self.live_detail_layout.addLayout(toggle_layout)

        # Layout for the mini-player container (we will dock player widget here)
        self.mini_player_container = QFrame(self)
        self.mini_player_container.setMinimumHeight(240)
        self.mini_player_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mini_player_container.setStyleSheet("background-color: #000000; border-radius: 6px;")
        self.mini_player_layout = QVBoxLayout(self.mini_player_container)
        self.mini_player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.live_channel_info_label = QLabel("Select a channel to play", self)
        self.live_channel_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_channel_info_label.setProperty("class", "plot-label")
        self.mini_player_layout.addWidget(self.live_channel_info_label)
        
        # Details below player
        self.live_meta_container = QWidget(self)
        live_meta_layout = QHBoxLayout(self.live_meta_container)
        live_meta_layout.setContentsMargins(0, 5, 0, 5)
        live_meta_layout.setSpacing(15)

        # Channel Logo Label
        self.live_logo_label = QLabel(self)
        self.live_logo_label.setFixedSize(80, 80)
        self.live_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_logo_label.setStyleSheet("border: 1px solid #1e2538; border-radius: 6px; background-color: #10141e; font-size: 36px; color: #9ca3af;")
        self.live_logo_label.setText("")
        self.live_logo_label.setStyleSheet("border: none; background-color: transparent;")
        self.live_logo_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "icons", "tv_large.svg")))
        live_meta_layout.addWidget(self.live_logo_label)

        # Text details layout
        live_text_layout = QVBoxLayout()
        live_text_layout.setSpacing(4)
        live_text_layout.setContentsMargins(0, 0, 0, 0)

        self.live_info_title = QLabel("", self)
        self.live_info_title.setProperty("class", "pane-title")
        self.live_info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        
        self.live_info_desc = QLabel("", self)
        self.live_info_desc.setWordWrap(True)
        self.live_info_desc.setProperty("class", "plot-label")
        self.live_info_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")

        live_text_layout.addWidget(self.live_info_title)
        live_text_layout.addWidget(self.live_info_desc)
        live_text_layout.addStretch()

        live_meta_layout.addLayout(live_text_layout)
        live_meta_layout.addStretch()

        self.live_detail_layout.addWidget(self.mini_player_container, stretch=9)
        self.live_detail_layout.addWidget(self.live_meta_container)
        self.live_spacer = QWidget(self)
        self.live_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.live_detail_layout.addWidget(self.live_spacer, stretch=1)

        # Search bar and lists wrapper
        self.live_lists_wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(self.live_lists_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(10)

        self.live_search = QLineEdit(self)
        self.live_search.setPlaceholderText("🔍 Search channels...")
        self.live_search.setProperty("class", "search-bar")
        self.live_search.textChanged.connect(self.filter_live_channels)
        wrapper_layout.addWidget(self.live_search)

        self.live_lists_splitter = QSplitter(Qt.Orientation.Horizontal, self.live_lists_wrapper)
        self.live_lists_splitter.addWidget(self.live_cat_widget)
        self.live_lists_splitter.addWidget(self.live_channel_widget)
        self.live_lists_splitter.setSizes([215, 215])
        wrapper_layout.addWidget(self.live_lists_splitter)

        # Bottom load amount bar matching webapp style
        saved_limit = self.default_batch_limit
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(5, 0, 5, 0)
        load_label = QLabel("Load amount:", self)
        load_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        
        self.live_batch_combo = QComboBox(self)
        self.live_batch_combo.setEditable(True)
        self.live_batch_combo.addItems(["50", "100", "200", "500", "1000", "Show All"])
        self.live_batch_combo.setStyleSheet("""
            QComboBox {
                color: white;
                background-color: #1e2538;
                padding: 4px 8px;
                border: 1px solid #2c354f;
                border-radius: 4px;
                font-size: 11px;
                min-width: 90px;
                max-width: 120px;
            }
            QComboBox QAbstractItemView {
                background-color: #10141e;
                color: white;
                selection-background-color: #00f0ff;
                selection-color: black;
            }
            QLineEdit {
                color: white;
                background-color: transparent;
                border: none;
            }
        """)
        self.live_batch_combo.setCurrentText(saved_limit)
        self.live_batch_combo.currentTextChanged.connect(self.on_batch_limit_changed)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(load_label)
        bottom_layout.addWidget(self.live_batch_combo)
        wrapper_layout.addLayout(bottom_layout)

        # Add to splitter in new order: Player (left/middle), Lists wrapper (right)
        self.live_splitter.addWidget(self.live_detail_pane)
        self.live_splitter.addWidget(self.live_lists_wrapper)
        
        # Set default splitter sizes
        self.live_splitter.setSizes([470, 430])

        layout.addWidget(self.live_splitter)
        self.content_stack.addWidget(panel)

    def setup_movies_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.movie_splitter = QSplitter(Qt.Orientation.Horizontal, panel)

        # 1. Left/Middle: Movie Details View (with player)
        self.movie_detail_pane = QFrame(self)
        self.movie_detail_pane.setMinimumWidth(320)
        self.movie_detail_pane.setProperty("class", "detail-pane")
        self.movie_detail_layout = QVBoxLayout(self.movie_detail_pane)
        self.movie_detail_layout.setContentsMargins(8, 8, 8, 8)
        self.movie_detail_layout.setSpacing(10)

        # Toggle Layout
        movie_toggle_layout = QHBoxLayout()
        movie_toggle_layout.setContentsMargins(0, 0, 0, 0)
        movie_toggle_layout.setSpacing(5)
        
        self.movie_sidebar_toggle_btn = QPushButton("  Menu", self)
        self.movie_sidebar_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "menu.svg")))
        self.movie_sidebar_toggle_btn.setCheckable(True)
        self.movie_sidebar_toggle_btn.setChecked(True)
        self.movie_sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_sidebar_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.movie_sidebar_toggle_btn.clicked.connect(self.toggle_movie_sidebar)
        
        self.movie_cat_toggle_btn = QPushButton("  Categories", self)
        self.movie_cat_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "folder.svg")))
        self.movie_cat_toggle_btn.setCheckable(True)
        self.movie_cat_toggle_btn.setChecked(True)
        self.movie_cat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_cat_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.movie_cat_toggle_btn.clicked.connect(self.toggle_movie_categories)
        
        self.movie_list_toggle_btn = QPushButton("  Movies", self)
        self.movie_list_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))
        self.movie_list_toggle_btn.setCheckable(True)
        self.movie_list_toggle_btn.setChecked(True)
        self.movie_list_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_list_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.movie_list_toggle_btn.clicked.connect(self.toggle_movie_list)
        
        movie_toggle_layout.addWidget(self.movie_sidebar_toggle_btn)
        movie_toggle_layout.addWidget(self.movie_cat_toggle_btn)
        movie_toggle_layout.addWidget(self.movie_list_toggle_btn)
        movie_toggle_layout.addStretch()
        
        self.movie_detail_layout.addLayout(movie_toggle_layout)

        # Movie Player Container
        self.movie_player_container = QFrame(self)
        self.movie_player_container.setMinimumHeight(240)
        self.movie_player_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.movie_player_container.setStyleSheet("background-color: #000000; border-radius: 6px;")
        self.movie_player_layout = QVBoxLayout(self.movie_player_container)
        self.movie_player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.movie_info_label = QLabel("Select a movie to play", self)
        self.movie_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie_info_label.setProperty("class", "plot-label")
        self.movie_player_layout.addWidget(self.movie_info_label)

        # Movie details layout (horizontal)
        self.movie_meta_container = QWidget(self)
        movie_meta_layout = QHBoxLayout(self.movie_meta_container)
        movie_meta_layout.setContentsMargins(0, 5, 0, 5)
        movie_meta_layout.setSpacing(15)

        # Movie Poster Label
        self.movie_logo_label = QLabel(self)
        self.movie_logo_label.setFixedSize(80, 120)
        self.movie_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie_logo_label.setStyleSheet("border: 1px solid #1e2538; border-radius: 6px; background-color: #10141e; font-size: 36px; color: #9ca3af;")
        self.movie_logo_label.setText("")
        self.movie_logo_label.setStyleSheet("border: none; background-color: transparent;")
        self.movie_logo_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "icons", "film_large.svg")))
        movie_meta_layout.addWidget(self.movie_logo_label)

        # Text details layout
        movie_text_layout = QVBoxLayout()
        movie_text_layout.setSpacing(4)
        movie_text_layout.setContentsMargins(0, 0, 0, 0)

        self.movie_title_label = QLabel("Select a Movie", self)
        self.movie_title_label.setProperty("class", "pane-title")
        self.movie_title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        
        self.movie_rating_label = QLabel("", self)
        self.movie_rating_label.setStyleSheet("color: #00d2d3; font-weight: bold; font-size: 12px;")
        
        self.movie_desc_label = QLabel("", self)
        self.movie_desc_label.setWordWrap(True)
        self.movie_desc_label.setProperty("class", "plot-label")
        self.movie_desc_label.setStyleSheet("color: #d1d5db; font-size: 12px;")

        movie_text_layout.addWidget(self.movie_title_label)
        movie_text_layout.addWidget(self.movie_rating_label)
        movie_text_layout.addWidget(self.movie_desc_label)
        movie_text_layout.addStretch()

        movie_meta_layout.addLayout(movie_text_layout)
        movie_meta_layout.addStretch()

        self.movie_play_btn = QPushButton("🎬 PLAY MOVIE", self)
        self.movie_play_btn.setProperty("class", "action-btn")
        self.movie_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_play_btn.clicked.connect(self.play_selected_movie)
        self.movie_play_btn.hide()
        
        self.movie_detail_layout.addWidget(self.movie_player_container, stretch=9)
        self.movie_detail_layout.addWidget(self.movie_meta_container)
        self.movie_detail_layout.addSpacing(15)
        self.movie_detail_layout.addWidget(self.movie_play_btn)
        self.movie_spacer = QWidget(self)
        self.movie_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.movie_detail_layout.addWidget(self.movie_spacer, stretch=1)

        # Center: Categories
        self.movie_cat_widget = QWidget(self)
        self.movie_cat_widget.setObjectName("movie_cat_widget")
        self.movie_cat_widget.setMinimumWidth(120)
        cat_layout = QVBoxLayout(self.movie_cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.movie_cat_list = QListWidget(self)
        self.movie_cat_list.currentRowChanged.connect(self.on_movie_category_changed)
        
        movie_cat_title = QLabel("CATEGORIES", self)
        movie_cat_title.setStyleSheet("color: #6b7280; font-size: 10px; font-weight: bold; padding: 10px 12px 4px 12px; letter-spacing: 1px; border: none; background: transparent;")
        cat_layout.addWidget(movie_cat_title)
        cat_layout.addWidget(self.movie_cat_list)

        # Right: Movies List
        self.movie_list_widget = QWidget(self)
        self.movie_list_widget.setMinimumWidth(120)
        movies_layout = QVBoxLayout(self.movie_list_widget)
        movies_layout.setContentsMargins(0, 0, 0, 0)
        
        self.movie_list = QListWidget(self)
        self.movie_list.setIconSize(QSize(28, 28))
        self.movie_list.itemClicked.connect(self.on_movie_clicked)
        self.movie_list.verticalScrollBar().valueChanged.connect(
            lambda val: self.load_visible_icons(self.movie_list)
        )
        
        movies_layout.addWidget(self.movie_list)

        # Search bar and lists wrapper
        self.movie_lists_wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(self.movie_lists_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(10)

        self.movie_search = QLineEdit(self)
        self.movie_search.setPlaceholderText("🔍 Search movies...")
        self.movie_search.setProperty("class", "search-bar")
        self.movie_search.textChanged.connect(self.filter_movies)
        wrapper_layout.addWidget(self.movie_search)

        self.movie_lists_splitter = QSplitter(Qt.Orientation.Horizontal, self.movie_lists_wrapper)
        self.movie_lists_splitter.addWidget(self.movie_cat_widget)
        self.movie_lists_splitter.addWidget(self.movie_list_widget)
        self.movie_lists_splitter.setSizes([215, 215])
        wrapper_layout.addWidget(self.movie_lists_splitter)

        # Bottom load amount bar matching webapp style
        saved_limit = self.default_batch_limit
        movie_bottom_layout = QHBoxLayout()
        movie_bottom_layout.setContentsMargins(5, 0, 5, 0)
        movie_load_label = QLabel("Load amount:", self)
        movie_load_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        
        self.movie_batch_combo = QComboBox(self)
        self.movie_batch_combo.setEditable(True)
        self.movie_batch_combo.addItems(["50", "100", "200", "500", "1000", "Show All"])
        self.movie_batch_combo.setStyleSheet(self.live_batch_combo.styleSheet())
        self.movie_batch_combo.setCurrentText(saved_limit)
        self.movie_batch_combo.currentTextChanged.connect(self.on_batch_limit_changed)
        
        movie_bottom_layout.addStretch()
        movie_bottom_layout.addWidget(movie_load_label)
        movie_bottom_layout.addWidget(self.movie_batch_combo)
        wrapper_layout.addLayout(movie_bottom_layout)

        self.movie_splitter.addWidget(self.movie_detail_pane)
        self.movie_splitter.addWidget(self.movie_lists_wrapper)
        self.movie_splitter.setSizes([470, 430])

        layout.addWidget(self.movie_splitter)
        self.content_stack.addWidget(panel)

    def setup_series_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.series_splitter = QSplitter(Qt.Orientation.Horizontal, panel)

        # Left/Middle: Series Details Pane (with player)
        self.series_detail_pane = QFrame(self)
        self.series_detail_pane.setMinimumWidth(320)
        self.series_detail_pane.setProperty("class", "detail-pane")
        self.series_detail_layout = QVBoxLayout(self.series_detail_pane)
        self.series_detail_layout.setContentsMargins(8, 8, 8, 8)
        self.series_detail_layout.setSpacing(10)

        # Toggle Layout
        series_toggle_layout = QHBoxLayout()
        series_toggle_layout.setContentsMargins(0, 0, 0, 0)
        series_toggle_layout.setSpacing(5)
        
        self.series_sidebar_toggle_btn = QPushButton("  Menu", self)
        self.series_sidebar_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "menu.svg")))
        self.series_sidebar_toggle_btn.setCheckable(True)
        self.series_sidebar_toggle_btn.setChecked(True)
        self.series_sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.series_sidebar_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.series_sidebar_toggle_btn.clicked.connect(self.toggle_series_sidebar)
        
        self.series_cat_toggle_btn = QPushButton("  Categories", self)
        self.series_cat_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "folder.svg")))
        self.series_cat_toggle_btn.setCheckable(True)
        self.series_cat_toggle_btn.setChecked(True)
        self.series_cat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.series_cat_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.series_cat_toggle_btn.clicked.connect(self.toggle_series_categories)
        
        self.series_list_toggle_btn = QPushButton("  Series", self)
        self.series_list_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))
        self.series_list_toggle_btn.setCheckable(True)
        self.series_list_toggle_btn.setChecked(True)
        self.series_list_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.series_list_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.series_list_toggle_btn.clicked.connect(self.toggle_series_list)
        
        series_toggle_layout.addWidget(self.series_sidebar_toggle_btn)
        series_toggle_layout.addWidget(self.series_cat_toggle_btn)
        series_toggle_layout.addWidget(self.series_list_toggle_btn)
        series_toggle_layout.addStretch()
        
        self.series_detail_layout.addLayout(series_toggle_layout)

        # Series Player Container
        self.series_player_container = QFrame(self)
        self.series_player_container.setMinimumHeight(240)
        self.series_player_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.series_player_container.setStyleSheet("background-color: #000000; border-radius: 6px;")
        self.series_player_layout = QVBoxLayout(self.series_player_container)
        self.series_player_layout.setContentsMargins(0, 0, 0, 0)
        
        self.series_info_label = QLabel("Select an episode to play", self)
        self.series_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.series_info_label.setProperty("class", "plot-label")
        self.series_player_layout.addWidget(self.series_info_label)

        # Series details layout (horizontal)
        self.series_meta_container = QWidget(self)
        series_meta_layout = QHBoxLayout(self.series_meta_container)
        series_meta_layout.setContentsMargins(0, 5, 0, 5)
        series_meta_layout.setSpacing(15)

        # Series Poster Label
        self.series_logo_label = QLabel(self)
        self.series_logo_label.setFixedSize(80, 120)
        self.series_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.series_logo_label.setStyleSheet("border: 1px solid #1e2538; border-radius: 6px; background-color: #10141e; font-size: 36px; color: #9ca3af;")
        self.series_logo_label.setText("")
        self.series_logo_label.setStyleSheet("border: none; background-color: transparent;")
        self.series_logo_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "icons", "clapperboard_large.svg")))
        series_meta_layout.addWidget(self.series_logo_label)

        # Text details layout
        series_text_layout = QVBoxLayout()
        series_text_layout.setSpacing(4)
        series_text_layout.setContentsMargins(0, 0, 0, 0)

        self.series_title_label = QLabel("Select a Series", self)
        self.series_title_label.setProperty("class", "pane-title")
        self.series_title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        
        self.series_desc_label = QLabel("", self)
        self.series_desc_label.setWordWrap(True)
        self.series_desc_label.setProperty("class", "plot-label")
        self.series_desc_label.setStyleSheet("color: #d1d5db; font-size: 12px;")

        series_text_layout.addWidget(self.series_title_label)
        series_text_layout.addWidget(self.series_desc_label)
        series_text_layout.addStretch()

        series_meta_layout.addLayout(series_text_layout)
        series_meta_layout.addStretch()
        
        # Season Selector Combobox
        self.season_combo_label = QLabel("Select Season:", self)
        self.season_combo_label.hide()
        self.season_combo = QComboBox(self)
        self.season_combo.currentIndexChanged.connect(self.on_season_changed)
        self.season_combo.hide()
        
        # Episodes List
        self.episodes_list_label = QLabel("Episodes:", self)
        self.episodes_list_label.hide()
        self.episodes_list = QListWidget(self)
        self.episodes_list.itemDoubleClicked.connect(self.play_selected_episode)
        self.episodes_list.hide()

        self.series_detail_layout.addWidget(self.series_player_container, stretch=9)
        self.series_detail_layout.addWidget(self.series_meta_container)
        self.series_detail_layout.addSpacing(10)
        self.series_detail_layout.addWidget(self.season_combo_label)
        self.series_detail_layout.addWidget(self.season_combo)
        self.series_detail_layout.addSpacing(10)
        self.series_detail_layout.addWidget(self.episodes_list_label)
        self.series_detail_layout.addWidget(self.episodes_list)
        self.series_spacer = QWidget(self)
        self.series_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.series_detail_layout.addWidget(self.series_spacer, stretch=1)

        # Center: Categories
        self.series_cat_widget = QWidget(self)
        self.series_cat_widget.setObjectName("series_cat_widget")
        self.series_cat_widget.setMinimumWidth(120)
        cat_layout = QVBoxLayout(self.series_cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.series_cat_list = QListWidget(self)
        self.series_cat_list.currentRowChanged.connect(self.on_series_category_changed)
        
        series_cat_title = QLabel("CATEGORIES", self)
        series_cat_title.setStyleSheet("color: #6b7280; font-size: 10px; font-weight: bold; padding: 10px 12px 4px 12px; letter-spacing: 1px; border: none; background: transparent;")
        cat_layout.addWidget(series_cat_title)
        cat_layout.addWidget(self.series_cat_list)

        # Right: Series List
        self.series_list_widget = QWidget(self)
        self.series_list_widget.setMinimumWidth(120)
        series_layout = QVBoxLayout(self.series_list_widget)
        series_layout.setContentsMargins(0, 0, 0, 0)
        
        self.series_list = QListWidget(self)
        self.series_list.setIconSize(QSize(28, 28))
        self.series_list.itemClicked.connect(self.on_series_clicked)
        self.series_list.verticalScrollBar().valueChanged.connect(
            lambda val: self.load_visible_icons(self.series_list)
        )
        
        series_layout.addWidget(self.series_list)

        # Search bar and lists wrapper
        self.series_lists_wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(self.series_lists_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(10)

        self.series_search = QLineEdit(self)
        self.series_search.setPlaceholderText("🔍 Search series...")
        self.series_search.setProperty("class", "search-bar")
        self.series_search.textChanged.connect(self.filter_series)
        wrapper_layout.addWidget(self.series_search)

        self.series_lists_splitter = QSplitter(Qt.Orientation.Horizontal, self.series_lists_wrapper)
        self.series_lists_splitter.addWidget(self.series_cat_widget)
        self.series_lists_splitter.addWidget(self.series_list_widget)
        self.series_lists_splitter.setSizes([215, 215])
        wrapper_layout.addWidget(self.series_lists_splitter)

        # Bottom load amount bar matching webapp style
        saved_limit = self.default_batch_limit
        series_bottom_layout = QHBoxLayout()
        series_bottom_layout.setContentsMargins(5, 0, 5, 0)
        series_load_label = QLabel("Load amount:", self)
        series_load_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        
        self.series_batch_combo = QComboBox(self)
        self.series_batch_combo.setEditable(True)
        self.series_batch_combo.addItems(["50", "100", "200", "500", "1000", "Show All"])
        self.series_batch_combo.setStyleSheet(self.live_batch_combo.styleSheet())
        self.series_batch_combo.setCurrentText(saved_limit)
        self.series_batch_combo.currentTextChanged.connect(self.on_batch_limit_changed)
        
        series_bottom_layout.addStretch()
        series_bottom_layout.addWidget(series_load_label)
        series_bottom_layout.addWidget(self.series_batch_combo)
        wrapper_layout.addLayout(series_bottom_layout)

        self.series_splitter.addWidget(self.series_detail_pane)
        self.series_splitter.addWidget(self.series_lists_wrapper)
        self.series_splitter.setSizes([470, 430])

        layout.addWidget(self.series_splitter)
        self.content_stack.addWidget(panel)

    def setup_settings_panel(self):
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Settings Card Frame
        card = QFrame(self)
        card.setObjectName("settingsCard")
        card.setStyleSheet("""
            #settingsCard {
                background-color: #10141e;
                border: 1px solid #1e2538;
                border-radius: 12px;
                padding: 30px;
            }
            QLabel#settingsTitle {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#settingsKey {
                color: #9ca3af;
                font-size: 13px;
                font-weight: bold;
            }
            QLabel#settingsVal {
                color: #ffffff;
                font-size: 13px;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)

        title = QLabel("SYSTEM & ACCOUNT DETAILS", card)
        title.setObjectName("settingsTitle")
        card_layout.addWidget(title)

        # Account Details Table/Labels
        host_url = self.client.host.replace("http://", "").replace("https://", "")
        details = [
            ("Host / Source:", host_url),
            ("Username:", self.client.username),
            ("Status:", self.client.user_info.get("status", "Unknown")),
            ("Connections (Active / Max):", f"{self.client.user_info.get('active_cons', '0')} / {self.client.user_info.get('max_connections', 'Unlimited')}"),
        ]
        
        # Format date expiration
        exp_timestamp = self.client.user_info.get("exp_date")
        if exp_timestamp and str(exp_timestamp) != '0':
            try:
                date = datetime.datetime.fromtimestamp(int(exp_timestamp))
                now = datetime.datetime.now()
                diff = date - now
                if diff.total_seconds() <= 0:
                    details.append(("Subscription Expiry:", f"Expired ({date.strftime('%m/%d/%Y')})"))
                else:
                    days = diff.days
                    hours, remainder = divmod(diff.seconds, 3600)
                    mins, _ = divmod(remainder, 60)
                    if days > 0:
                        remaining = f"{days}d {hours}h {mins}m remaining"
                    elif hours > 0:
                        remaining = f"{hours}h {mins}m remaining"
                    else:
                        remaining = f"{mins}m remaining"
                    
                    details.append(("Subscription Expiry:", f"{date.strftime('%m/%d/%Y')} ({remaining})"))
            except Exception:
                details.append(("Subscription Expiry:", "Never"))
        else:
            details.append(("Subscription Expiry:", "Unlimited"))

        # Add Details to card
        for key, val in details:
            row = QHBoxLayout()
            kl = QLabel(key, card)
            kl.setObjectName("settingsKey")
            kl.setFixedWidth(200)
            vl = QLabel(val, card)
            vl.setObjectName("settingsVal")
            row.addWidget(kl)
            row.addWidget(vl)
            row.addStretch()
            card_layout.addLayout(row)

        card_layout.addSpacing(25)
        
        # Stream Loading & Batching
        batch_title = QLabel("STREAM LOADING & BATCHING", card)
        batch_title.setObjectName("settingsTitle")
        card_layout.addWidget(batch_title)
        
        batch_layout = QHBoxLayout()
        batch_label = QLabel("Load Limit / Batch Size:", card)
        batch_label.setObjectName("settingsKey")
        batch_label.setFixedWidth(200)
        
        self.batch_combo = QComboBox(card)
        self.batch_combo.setEditable(True)
        self.batch_combo.addItems(["50", "100", "200", "500", "1000", "Show All"])
        self.batch_combo.setStyleSheet("""
            QComboBox {
                color: white;
                background-color: #1e2538;
                padding: 5px;
                border: 1px solid #2c354f;
                border-radius: 4px;
                min-width: 120px;
            }
            QComboBox QAbstractItemView {
                background-color: #10141e;
                color: white;
                selection-background-color: #00f0ff;
                selection-color: black;
                border: 1px solid #1e2538;
            }
            QComboBox:focus {
                border-color: #00f0ff;
            }
            QLineEdit {
                color: white;
                background-color: transparent;
                border: none;
            }
        """)
        
        saved_limit = self.default_batch_limit
        self.batch_combo.setCurrentText(saved_limit)
        self.batch_combo.currentTextChanged.connect(self.on_batch_limit_changed)
        
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.batch_combo)
        batch_layout.addStretch()
        card_layout.addLayout(batch_layout)
        
        batch_desc = QLabel("Controls the number of channels/VOD items loaded per page.", card)
        batch_desc.setStyleSheet("color: #9ca3af; font-size: 11px;")
        card_layout.addWidget(batch_desc)
        
        card_layout.addSpacing(25)

        # Cache & Data Management
        data_title = QLabel("CACHE & DATA MANAGEMENT", card)
        data_title.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: bold;")
        card_layout.addWidget(data_title)
        
        data_layout = QHBoxLayout()
        data_layout.setSpacing(15)
        
        self.disconnect_btn = QPushButton("Disconnect Active Playlist", card)
        self.disconnect_btn.setStyleSheet("color: #f87171; border: 1px solid rgba(239,68,68,0.2); padding: 8px 15px; border-radius: 4px; background: transparent;")
        self.disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disconnect_btn.clicked.connect(self.logout)
        
        data_layout.addWidget(self.disconnect_btn)
        data_layout.addStretch()
        
        card_layout.addLayout(data_layout)
        
        card_layout.addSpacing(25)
        
        # Audio Codec support info
        codec_info = QLabel(" Dolby Audio AC3 & EAC3 decoders are loaded and fully supported.", card)
        codec_info.setStyleSheet("color: #00d2d3; font-weight: bold; border: 1px solid #00d2d3; border-radius: 6px; padding: 10px; background-color: rgba(0, 210, 211, 0.05);")
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(codec_info)
        codec_layout.addStretch()
        card_layout.addLayout(codec_layout)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        
        self.content_stack.addWidget(panel)

    # --- Navigation & Tab Switching ---

    def set_nav_active(self, index):
        for idx, btn in enumerate(self.nav_buttons):
            if idx == index:
                btn.setChecked(True)
                btn.setProperty("class", "nav-btn active")
                # Force style update
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            else:
                btn.setChecked(False)
                btn.setProperty("class", "nav-btn")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    def switch_tab(self, index):
        self.set_nav_active(index)
        self.content_stack.setCurrentIndex(index)
        
        # Stop background workers to prevent interference
        self.abort_active_workers()

    def show_live_tv(self):
        self.switch_tab(0)
        if self.player_dock_state is None:
            self.dock_player_to_live()
        
        if not self.categories_cache["live"]:
            self.load_categories("live", self.live_cat_list)

    def show_movies(self):
        self.switch_tab(1)
        if not self.categories_cache["vod"]:
            self.load_categories("vod", self.movie_cat_list)

    def show_series(self):
        self.switch_tab(2)
        if not self.categories_cache["series"]:
            self.load_categories("series", self.series_cat_list)

    def show_settings(self):
        self.switch_tab(3)

    def logout(self):
        self.player_widget.stop()
        self.logout_requested.emit()

    # --- Background Workers & Data Fetching ---

    def abort_active_workers(self):
        if self.cat_worker and self.cat_worker.isRunning():
            self.cat_worker.terminate()
            self.cat_worker.wait()
        if self.stream_worker and self.stream_worker.isRunning():
            self.stream_worker.terminate()
            self.stream_worker.wait()
        if self.series_info_worker and self.series_info_worker.isRunning():
            self.series_info_worker.terminate()
            self.series_info_worker.wait()

    def load_categories(self, mode, list_widget):
        list_widget.clear()
        list_widget.addItem("Loading categories...")
        list_widget.setEnabled(False)

        self.cat_worker = FetchCategoriesWorker(self.client, mode)
        
        # Capture variables for callback via lambda
        def on_finished(categories):
            try:
                list_widget.clear()
            except RuntimeError:
                return # Widget deleted, user likely navigated away

            list_widget.setEnabled(True)
            self.categories_cache[mode] = categories
            
            if not categories:
                list_widget.addItem("No categories found.")
                return
                
            # Add an 'All Channels / Streams' top item
            if mode == "live":
                all_text = "All Channels"
            elif mode == "vod":
                all_text = "All Movies"
            elif mode == "series":
                all_text = "All Series"
            else:
                all_text = "All Channels"

            all_item = QListWidgetItem(all_text)
            all_item.setData(Qt.ItemDataRole.UserRole, None)
            list_widget.addItem(all_item)
            
            # For Live TV: add virtual Sports category chip (webapp parity)
            if mode == "live":
                sports_item = QListWidgetItem("🏆 Sport")
                sports_item.setData(Qt.ItemDataRole.UserRole, "__sport__")
                sports_item.setForeground(QColor("#00f0ff"))
                sports_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                list_widget.addItem(sports_item)
            
            for cat in categories:
                item = QListWidgetItem(cat["category_name"])
                item.setData(Qt.ItemDataRole.UserRole, cat["category_id"])
                list_widget.addItem(item)
            
            # Select first item
            list_widget.setCurrentRow(0)

        self.cat_worker.finished.connect(on_finished)
        self.cat_worker.start()

    def load_streams(self, mode, category_id, list_widget):
        list_widget.clear()
        
        # Check cache first to load instantly
        if category_id in self.streams_cache[mode]:
            streams = self.streams_cache[mode][category_id]
            self.streams_data[mode] = streams
            self.streams_loaded_count[mode] = 0
            list_widget.setEnabled(True)
            if not streams:
                list_widget.addItem("No streams available.")
                return
            self.show_more_streams(mode, list_widget)
            return

        list_widget.addItem("Loading streams...")
        list_widget.setEnabled(False)
        
        # Abort previous stream worker if running
        if self.stream_worker and self.stream_worker.isRunning():
            self.stream_worker.terminate()
            self.stream_worker.wait()

        if category_id is None:
            self.stream_worker = FetchStreamsWorker(self.client, mode, None)

            def on_finished(streams):
                try:
                    list_widget.setEnabled(True)
                    list_widget.clear()
                except RuntimeError:
                    return # Widget deleted

                # Populate category_name for each stream
                cat_map = {cat["category_id"]: cat["category_name"] for cat in self.categories_cache.get(mode, []) if "category_id" in cat and "category_name" in cat}
                for s in streams:
                    s["category_name"] = cat_map.get(s.get("category_id"), "")

                self.streams_data[mode] = streams
                self.streams_loaded_count[mode] = 0

                # Cache the loaded streams under None
                self.streams_cache[mode][None] = streams

                if not streams:
                    list_widget.addItem("No streams available.")
                    return

                self.show_more_streams(mode, list_widget)

            self.stream_worker.finished.connect(on_finished)
            self.stream_worker.start()
        else:
            self.stream_worker = FetchStreamsWorker(self.client, mode, category_id)

            def on_finished(streams):
                try:
                    list_widget.setEnabled(True)
                    list_widget.clear()
                except RuntimeError:
                    return # Widget deleted, user likely navigated away
                    
                cat_map = {cat["category_id"]: cat["category_name"] for cat in self.categories_cache.get(mode, []) if "category_id" in cat and "category_name" in cat}
                for s in streams:
                    s["category_name"] = cat_map.get(s.get("category_id"), "")
                    
                self.streams_data[mode] = streams
                self.streams_loaded_count[mode] = 0
                
                # Cache the loaded streams
                self.streams_cache[mode][category_id] = streams
                
                if not streams:
                    list_widget.addItem("No streams available.")
                    return

                self.show_more_streams(mode, list_widget)

            self.stream_worker.finished.connect(on_finished)
            self.stream_worker.start()

    def load_next_lazy_category(self, mode, list_widget):
        categories = self.categories_cache.get(mode, [])
        idx = self.lazy_cat_index[mode]
        
        # If we have run out of categories, finish loading
        if idx >= len(categories):
            self.on_lazy_loading_finished(mode, list_widget)
            return
            
        cat = categories[idx]
        cat_id = cat.get("category_id")
        
        # Target size is the currently loaded count in UI plus the batch page size
        batch_size = self.get_batch_size()
        target_size = self.streams_loaded_count[mode] + batch_size
        
        # Check if this category's streams are already cached
        if cat_id in self.streams_cache[mode]:
            streams = self.streams_cache[mode][cat_id]
            self.streams_data[mode].extend(streams)
            self.lazy_cat_index[mode] += 1
            
            # Check if we have loaded enough channels
            if len(self.streams_data[mode]) >= target_size:
                self.on_lazy_loading_finished(mode, list_widget)
            else:
                self.load_next_lazy_category(mode, list_widget)
            return

        # Fetch from server
        self.stream_worker = FetchStreamsWorker(self.client, mode, cat_id)
        
        def on_finished(streams):
            try:
                cat_name = cat.get("category_name", "")
                for s in streams:
                    s["category_name"] = cat_name
                # Cache the loaded streams
                self.streams_cache[mode][cat_id] = streams
                self.streams_data[mode].extend(streams)
                self.lazy_cat_index[mode] += 1
                
                if len(self.streams_data[mode]) >= target_size or self.lazy_cat_index[mode] >= len(categories):
                    self.on_lazy_loading_finished(mode, list_widget)
                else:
                    self.load_next_lazy_category(mode, list_widget)
            except RuntimeError:
                return # Widget deleted
                
        self.stream_worker.finished.connect(on_finished)
        self.stream_worker.start()

    def on_lazy_loading_finished(self, mode, list_widget):
        try:
            list_widget.setEnabled(True)
            if list_widget.count() > 0:
                last_item = list_widget.item(list_widget.count() - 1)
                if last_item.data(Qt.ItemDataRole.UserRole + 2) == "load_more" or last_item.text().startswith("⏳") or last_item.text().startswith("Loading"):
                    list_widget.takeItem(list_widget.count() - 1)
        except RuntimeError:
            return
            
        streams = self.streams_data[mode]
        # Cache the current accumulated list under None (All Categories)
        self.streams_cache[mode][None] = streams
        
        if not streams and list_widget.count() == 0:
            list_widget.addItem("No streams available.")
            return
            
        self.show_more_streams(mode, list_widget)

    # --- Live TV Event Handlers ---

    def on_live_category_changed(self, row):
        if row < 0:
            return
        item = self.live_cat_list.currentItem()
        category_id = item.data(Qt.ItemDataRole.UserRole)
        
        if category_id == "__sport__":
            self.load_sport_streams(keywords=["sport", "esporte", "desporto", "liga", "futbol", "football", "nfl", "nba", "mlb", "nhl", "ufc", "mma", "racing"])
        else:
            self.load_streams("live", category_id, self.live_channel_list)
    
    def load_sport_streams(self, keywords):
        """Fetch all live streams, then filter client-side by sport-related keywords."""
        self.live_channel_list.clear()
        
        # Check cache (all channels fetched with category_id=None)
        if None in self.streams_cache["live"]:
            streams = self.streams_cache["live"][None]
            self.live_channel_list.setEnabled(True)
            matched = [
                s for s in streams
                if any(
                    kw in (s.get("category_name", "") + " " + s.get("name", "")).lower()
                    for kw in keywords
                )
            ]
            if not matched:
                self.live_channel_list.addItem("No sport channels found.")
                return
                
            self.streams_data["live"] = matched
            self.streams_loaded_count["live"] = 0
            self.show_more_streams("live", self.live_channel_list)
            return

        self.live_channel_list.addItem("Loading sport channels...")
        self.live_channel_list.setEnabled(False)
        
        if self.stream_worker and self.stream_worker.isRunning():
            self.stream_worker.terminate()
            self.stream_worker.wait()
        
        # Match the webapp: fetch all live streams directly, then filter locally.
        self.stream_worker = FetchStreamsWorker(self.client, "live", None)
        
        def on_finished(streams):
            try:
                self.live_channel_list.setEnabled(True)
                self.live_channel_list.clear()
            except RuntimeError:
                return
                
            cat_map = {cat["category_id"]: cat["category_name"] for cat in self.categories_cache.get("live", []) if "category_id" in cat and "category_name" in cat}
            for s in streams:
                s["category_name"] = cat_map.get(s.get("category_id"), "")

            # Cache the loaded streams
            self.streams_cache["live"][None] = streams
            
            # Filter by any matching keyword in category_name or stream name
            matched = [
                s for s in streams
                if any(
                    kw in (s.get("category_name", "") + " " + s.get("name", "")).lower()
                    for kw in keywords
                )
            ]
            
            if not matched:
                self.live_channel_list.addItem("No sport channels found.")
                return
            
            self.streams_data["live"] = matched
            self.streams_loaded_count["live"] = 0
            self.show_more_streams("live", self.live_channel_list)
        
        self.stream_worker.finished.connect(on_finished)
        self.stream_worker.start()

    def filter_live_channels(self, query):
        self.filter_list_items("live", query, self.live_channel_list)

    def on_live_channel_clicked(self, item):
        if item.data(Qt.ItemDataRole.UserRole + 2) == "load_more":
            self.show_more_streams("live", self.live_channel_list)
            return
        stream_data = item.data(Qt.ItemDataRole.UserRole)
        if not stream_data:
            return
            
        stream_id = stream_data["stream_id"]
        channel_name = stream_data["name"]
        
        # Dock player back to the live container if not already there
        self.dock_player_to_live()
        
        # Set text details and load logo
        self.live_info_title.setText(channel_name)
        self.live_info_desc.setText(f"Streaming live now. Stream ID: {stream_id}")
        self.load_logo_image(stream_data.get("stream_icon", ""), self.live_logo_label, "📺")
        
        # Construct Live TS stream URL
        stream_url = self.client.get_live_stream_url(stream_id)
        
        # Play in Player
        self.player_widget.play(stream_url, channel_name)

    # --- Movies Event Handlers ---

    def on_movie_category_changed(self, row):
        if row < 0:
            return
        item = self.movie_cat_list.currentItem()
        category_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_streams("vod", category_id, self.movie_list)

    def filter_movies(self, query):
        self.filter_list_items("vod", query, self.movie_list)

    def on_movie_clicked(self, item):
        if item.data(Qt.ItemDataRole.UserRole + 2) == "load_more":
            self.show_more_streams("vod", self.movie_list)
            return
        movie_data = item.data(Qt.ItemDataRole.UserRole)
        if not movie_data:
            return
            
        self.movie_title_label.setText(movie_data.get("name", "Unknown Movie"))
        rating = movie_data.get("rating", "N/A")
        self.movie_rating_label.setText(f"Rating: ⭐ {rating}")
        
        desc = (
            f"Release Date: {movie_data.get('added', 'N/A')}\n"
            f"Container Format: {movie_data.get('container_extension', 'mp4')}\n"
            f"Plot: This is a placeholder description for the movie '{movie_data.get('name')}' streamed via Xtream Codes."
        )
        self.movie_desc_label.setText(desc)
        self.load_logo_image(movie_data.get("stream_icon", ""), self.movie_logo_label, "🎬")
        self.movie_play_btn.show()

    def play_selected_movie(self):
        item = self.movie_list.currentItem()
        if not item:
            return
        movie_data = item.data(Qt.ItemDataRole.UserRole)
        if not movie_data:
            return

        movie_id = movie_data["stream_id"]
        movie_name = movie_data["name"]
        container_ext = movie_data.get("container_extension", "mp4")
        
        # Generate Movie playback URL
        stream_url = self.client.get_vod_stream_url(movie_id, container_ext)
        
        self.player_widget.stop()
        self.dock_player_to_movie()
        self.player_widget.play(stream_url, movie_name)

    # --- Series Event Handlers ---

    def on_series_category_changed(self, row):
        if row < 0:
            return
        item = self.series_cat_list.currentItem()
        category_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_streams("series", category_id, self.series_list)

    def filter_series(self, query):
        self.filter_list_items("series", query, self.series_list)

    def on_series_clicked(self, item):
        if item.data(Qt.ItemDataRole.UserRole + 2) == "load_more":
            self.show_more_streams("series", self.series_list)
            return
        series_data = item.data(Qt.ItemDataRole.UserRole)
        if not series_data:
            return
            
        series_id = series_data["series_id"]
        self.series_title_label.setText(series_data.get("name", "Unknown Series"))
        self.series_desc_label.setText(series_data.get("plot", "No description available."))
        self.load_logo_image(series_data.get("cover", ""), self.series_logo_label, "🍿")
        
        # Load seasons and episodes in background
        self.load_series_episodes(series_id)

    def load_series_episodes(self, series_id):
        self.season_combo.clear()
        self.season_combo.hide()
        self.season_combo_label.hide()
        
        self.episodes_list.clear()
        self.episodes_list.addItem("Loading seasons & episodes...")
        self.episodes_list.show()
        self.episodes_list_label.show()

        if self.series_info_worker and self.series_info_worker.isRunning():
            self.series_info_worker.terminate()
            self.series_info_worker.wait()

        self.series_info_worker = FetchSeriesInfoWorker(self.client, series_id)

        def on_finished(info_data):
            self.episodes_list.clear()
            
            seasons = info_data.get("seasons", [])
            episodes = info_data.get("episodes", {})
            
            if not seasons or not episodes:
                self.episodes_list.addItem("No episodes available for this series.")
                return
                
            # Store full episodes dictionary on the combo box
            self.season_combo.setProperty("episodes", episodes)
            
            # Populate Season combo box
            self.season_combo.currentIndexChanged.disconnect(self.on_season_changed)
            for season in seasons:
                name = season.get("name", f"Season {season.get('season_number')}")
                num = season.get("season_number")
                self.season_combo.addItem(name, num)
            self.season_combo.currentIndexChanged.connect(self.on_season_changed)
            
            # Show combo and trigger first load
            self.season_combo_label.show()
            self.season_combo.show()
            self.on_season_changed(0)

        self.series_info_worker.finished.connect(on_finished)
        self.series_info_worker.start()

    def on_season_changed(self, index):
        if index < 0:
            return
        
        season_num = self.season_combo.currentData()
        episodes_map = self.season_combo.property("episodes")
        
        self.episodes_list.clear()
        
        if not episodes_map:
            return
            
        # Series episodes map returns items keyed by season index string, e.g. "1"
        season_eps = episodes_map.get(str(season_num)) or episodes_map.get(season_num)
        
        if not season_eps:
            self.episodes_list.addItem("No episodes found in this season.")
            return

        for ep in season_eps:
            title = f"Ep {ep.get('episode_num')}: {ep.get('title', 'Unknown Episode')}"
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, ep)
            self.episodes_list.addItem(item)

    def play_selected_episode(self, item):
        ep_data = item.data(Qt.ItemDataRole.UserRole)
        if not ep_data:
            return
            
        ep_id = ep_data["id"]
        ep_name = ep_data.get("title", "Episode")
        container_ext = ep_data.get("container_extension", "mp4")
        
        # Build stream URL
        stream_url = self.client.get_series_stream_url(ep_id, container_ext)
        
        self.player_widget.stop()
        self.dock_player_to_series()
        self.player_widget.play(stream_url, ep_name)

    # --- Docking Video Player Controller (Mini-player vs Full Theater Panel) ---

    def dock_player_to_live(self):
        if self.player_dock_state == "live":
            return
        self.live_channel_info_label.hide()
        self.mini_player_layout.addWidget(self.player_widget)
        self.player_dock_state = "live"
        self.player_widget.full_program_btn.setChecked(False)
        self.player_widget.update_full_program_button()
        self.on_player_full_program_changed(False)
        logging.info("VLC Player: Docked to Live TV Panel")

    def dock_player_to_movie(self):
        if self.player_dock_state == "movie":
            return
        self.movie_info_label.hide()
        self.movie_player_layout.addWidget(self.player_widget)
        self.player_dock_state = "movie"
        self.player_widget.full_program_btn.setChecked(False)
        self.player_widget.update_full_program_button()
        self.on_player_full_program_changed(False)
        logging.info("VLC Player: Docked to Movie Details Panel")

    def dock_player_to_series(self):
        if self.player_dock_state == "series":
            return
        self.series_info_label.hide()
        self.series_player_layout.addWidget(self.player_widget)
        self.player_dock_state = "series"
        self.player_widget.full_program_btn.setChecked(False)
        self.player_widget.update_full_program_button()
        self.on_player_full_program_changed(False)
        logging.info("VLC Player: Docked to Series Details Panel")

    def toggle_sidebar(self):
        visible = self.sidebar_toggle_btn.isChecked()
        self.sidebar.setVisible(visible)
        text = "▶ Menu" if not visible else "◀ Menu"
        self.sidebar_toggle_btn.setText(text)
        self.movie_sidebar_toggle_btn.setChecked(visible)
        self.movie_sidebar_toggle_btn.setText(text)
        self.series_sidebar_toggle_btn.setChecked(visible)
        self.series_sidebar_toggle_btn.setText(text)

    def toggle_movie_sidebar(self):
        visible = self.movie_sidebar_toggle_btn.isChecked()
        self.sidebar.setVisible(visible)
        text = "▶ Menu" if not visible else "◀ Menu"
        self.sidebar_toggle_btn.setChecked(visible)
        self.sidebar_toggle_btn.setText(text)
        self.movie_sidebar_toggle_btn.setText(text)
        self.series_sidebar_toggle_btn.setChecked(visible)
        self.series_sidebar_toggle_btn.setText(text)

    def toggle_series_sidebar(self):
        visible = self.series_sidebar_toggle_btn.isChecked()
        self.sidebar.setVisible(visible)
        text = "▶ Menu" if not visible else "◀ Menu"
        self.sidebar_toggle_btn.setChecked(visible)
        self.sidebar_toggle_btn.setText(text)
        self.movie_sidebar_toggle_btn.setChecked(visible)
        self.movie_sidebar_toggle_btn.setText(text)
        self.series_sidebar_toggle_btn.setText(text)

    def update_live_search_visibility(self):
        self.live_search.setVisible(self.channel_toggle_btn.isChecked())

    def update_movie_search_visibility(self):
        self.movie_search.setVisible(self.movie_list_toggle_btn.isChecked())

    def update_series_search_visibility(self):
        self.series_search.setVisible(self.series_list_toggle_btn.isChecked())

    def adjust_live_splitter_sizes(self):
        cat_visible = self.cat_toggle_btn.isChecked()
        chan_visible = self.channel_toggle_btn.isChecked()
        self.live_lists_wrapper.setVisible(cat_visible or chan_visible)
        if cat_visible and chan_visible:
            self.live_splitter.setSizes([470, 430])
        elif cat_visible or chan_visible:
            self.live_splitter.setSizes([685, 215])

    def adjust_movie_splitter_sizes(self):
        cat_visible = self.movie_cat_toggle_btn.isChecked()
        list_visible = self.movie_list_toggle_btn.isChecked()
        self.movie_lists_wrapper.setVisible(cat_visible or list_visible)
        if cat_visible and list_visible:
            self.movie_splitter.setSizes([470, 430])
        elif cat_visible or list_visible:
            self.movie_splitter.setSizes([685, 215])

    def adjust_series_splitter_sizes(self):
        cat_visible = self.series_cat_toggle_btn.isChecked()
        list_visible = self.series_list_toggle_btn.isChecked()
        self.series_lists_wrapper.setVisible(cat_visible or list_visible)
        if cat_visible and list_visible:
            self.series_splitter.setSizes([470, 430])
        elif cat_visible or list_visible:
            self.series_splitter.setSizes([685, 215])

    def toggle_categories(self):
        visible = self.cat_toggle_btn.isChecked()
        self.live_cat_widget.setVisible(visible)
        self.adjust_live_splitter_sizes()

    def toggle_channels(self):
        visible = self.channel_toggle_btn.isChecked()
        self.live_channel_widget.setVisible(visible)
        self.update_live_search_visibility()
        self.adjust_live_splitter_sizes()

    def toggle_movie_categories(self):
        visible = self.movie_cat_toggle_btn.isChecked()
        self.movie_cat_widget.setVisible(visible)
        self.adjust_movie_splitter_sizes()

    def toggle_movie_list(self):
        visible = self.movie_list_toggle_btn.isChecked()
        self.movie_list_widget.setVisible(visible)
        self.update_movie_search_visibility()
        self.adjust_movie_splitter_sizes()

    def toggle_series_categories(self):
        visible = self.series_cat_toggle_btn.isChecked()
        self.series_cat_widget.setVisible(visible)
        self.adjust_series_splitter_sizes()

    def toggle_series_list(self):
        visible = self.series_list_toggle_btn.isChecked()
        self.series_list_widget.setVisible(visible)
        self.update_series_search_visibility()
        self.adjust_series_splitter_sizes()

    def on_player_full_program_changed(self, is_full):
        # Determine panel visibility (if player is full window size, panels are hidden)
        visible = not is_full
        
        # 1. Update sidebar
        self.sidebar.setVisible(visible)
        text = "▶ Menu" if not visible else "◀ Menu"
        self.sidebar_toggle_btn.setChecked(visible)
        self.sidebar_toggle_btn.setText(text)
        self.movie_sidebar_toggle_btn.setChecked(visible)
        self.movie_sidebar_toggle_btn.setText(text)
        self.series_sidebar_toggle_btn.setChecked(visible)
        self.series_sidebar_toggle_btn.setText(text)

        # 2. Update Categories, Main lists, and details layout widgets depending on current active index of content stack
        active_tab = self.content_stack.currentIndex()
        margin = 0 if is_full else 8
        
        if active_tab == 0:
            # Live TV
            self.live_cat_widget.setVisible(visible)
            self.live_channel_widget.setVisible(visible)
            self.cat_toggle_btn.setChecked(visible)
            self.channel_toggle_btn.setChecked(visible)
            
            # Hide/show toggle buttons and details to make player full client size
            self.sidebar_toggle_btn.setVisible(visible)
            self.cat_toggle_btn.setVisible(visible)
            self.channel_toggle_btn.setVisible(visible)
            self.live_meta_container.setVisible(visible)
            self.live_spacer.setVisible(visible)
            self.live_detail_layout.setContentsMargins(margin, margin, margin, margin)
            self.update_live_search_visibility()
            self.adjust_live_splitter_sizes()
            
        elif active_tab == 1:
            # Movies
            self.movie_cat_widget.setVisible(visible)
            self.movie_list_widget.setVisible(visible)
            self.movie_cat_toggle_btn.setChecked(visible)
            self.movie_list_toggle_btn.setChecked(visible)
            
            self.movie_sidebar_toggle_btn.setVisible(visible)
            self.movie_cat_toggle_btn.setVisible(visible)
            self.movie_list_toggle_btn.setVisible(visible)
            self.movie_meta_container.setVisible(visible)
            self.movie_play_btn.setVisible(visible and self.movie_list.currentItem() is not None)
            self.movie_spacer.setVisible(visible)
            self.movie_detail_layout.setContentsMargins(margin, margin, margin, margin)
            self.update_movie_search_visibility()
            self.adjust_movie_splitter_sizes()
            
        elif active_tab == 2:
            # Series
            self.series_cat_widget.setVisible(visible)
            self.series_list_widget.setVisible(visible)
            self.series_cat_toggle_btn.setChecked(visible)
            self.series_list_toggle_btn.setChecked(visible)
            
            self.series_sidebar_toggle_btn.setVisible(visible)
            self.series_cat_toggle_btn.setVisible(visible)
            self.series_list_toggle_btn.setVisible(visible)
            self.series_meta_container.setVisible(visible)
            self.season_combo_label.setVisible(visible)
            self.season_combo.setVisible(visible)
            self.episodes_list_label.setVisible(visible)
            self.episodes_list.setVisible(visible)
            self.series_spacer.setVisible(visible)
            self.series_detail_layout.setContentsMargins(margin, margin, margin, margin)
            self.update_series_search_visibility()
            self.adjust_series_splitter_sizes()

    def load_logo_image(self, url, label_widget, default_emoji="📺"):
        # Reset and display centered default emoji placeholder
        label_widget.setText(default_emoji)
        label_widget.setStyleSheet("border: 1px solid #1e2538; border-radius: 6px; background-color: #10141e; font-size: 36px; color: #9ca3af;")
        label_widget.setPixmap(QPixmap())
        
        if not url:
            return
            
        qurl = QUrl(url)
        request = QNetworkRequest(qurl)
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0")
        
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda r=reply, l=label_widget: self.on_logo_download_finished(r, l))

    def on_logo_download_finished(self, reply, label_widget):
        reply.deleteLater()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled = pixmap.scaled(
                    label_widget.width(), 
                    label_widget.height(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                label_widget.setPixmap(scaled)
                label_widget.setText("") # Clear emoji
                label_widget.setStyleSheet("border: 1px solid #1e2538; border-radius: 6px; background-color: #10141e;")
            else:
                logging.warning("Logo download succeeded but image format is invalid.")
        else:
            logging.warning(f"Failed to download logo: {reply.errorString()}")

    def load_visible_icons(self, list_widget):
        viewport_rect = list_widget.viewport().rect()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.isHidden():
                continue
                
            # Check if visual rect of item is currently inside the list viewport
            item_rect = list_widget.visualItemRect(item)
            if viewport_rect.intersects(item_rect):
                logo_url = item.data(Qt.ItemDataRole.UserRole + 1)
                # If it has a logo URL and no icon has been set yet, trigger download
                if logo_url and item.icon().isNull():
                    self.load_list_icon(logo_url, item)

    def load_list_icon(self, url, item):
        if not url:
            return
            
        # Check cache
        if url in self.logo_cache:
            item.setIcon(self.logo_cache[url])
            return
            
        # Avoid duplicate requests for the same image URL in flight
        if url in self.downloading_urls:
            return
            
        self.downloading_urls.add(url)
            
        qurl = QUrl(url)
        request = QNetworkRequest(qurl)
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0")
        
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda r=reply, it=item, u=url: self.on_list_icon_download_finished(r, it, u))

    def on_list_icon_download_finished(self, reply, item, url):
        reply.deleteLater()
        if url in self.downloading_urls:
            self.downloading_urls.remove(url)
            
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled = pixmap.scaled(
                    28, 
                    28, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                icon = QIcon(scaled)
                self.logo_cache[url] = icon
                
                # Apply icon to all items in any list sharing this exact URL
                for lw in [self.live_channel_list, self.movie_list, self.series_list]:
                    for idx in range(lw.count()):
                        it = lw.item(idx)
                        if it.data(Qt.ItemDataRole.UserRole + 1) == url:
                            try:
                                it.setIcon(icon)
                            except RuntimeError:
                                pass
            else:
                logging.warning("Logo download succeeded but image format is invalid.")

    def show_more_streams(self, mode, list_widget):
        if list_widget.count() > 0:
            last_item = list_widget.item(list_widget.count() - 1)
            if last_item.data(Qt.ItemDataRole.UserRole + 2) == "load_more":
                list_widget.takeItem(list_widget.count() - 1)

        # Get active category ID
        active_cat_id = None
        if mode == "live":
            active_cat_id = self.live_cat_list.currentItem().data(Qt.ItemDataRole.UserRole) if self.live_cat_list.currentItem() else None
        elif mode == "vod":
            active_cat_id = self.movie_cat_list.currentItem().data(Qt.ItemDataRole.UserRole) if self.movie_cat_list.currentItem() else None
        elif mode == "series":
            active_cat_id = self.series_cat_list.currentItem().data(Qt.ItemDataRole.UserRole) if self.series_cat_list.currentItem() else None

        all_streams = self.streams_data.get(mode, [])
        current_count = self.streams_loaded_count.get(mode, 0)
        PAGE_SIZE = self.get_batch_size()

        next_count = min(len(all_streams), current_count + PAGE_SIZE)
        
        for i in range(current_count, next_count):
            stream = all_streams[i]
            name = stream.get("name", "Unknown Stream")
            
            rating = stream.get("rating")
            if rating:
                name += f"  (⭐ {rating})"
                
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, stream)
            
            logo_url = stream.get("stream_icon") or stream.get("cover") or ""
            item.setData(Qt.ItemDataRole.UserRole + 1, logo_url)
                
            list_widget.addItem(item)
            
        self.streams_loaded_count[mode] = next_count
        
        # Determine if we should show 'Load More'
        if next_count < len(all_streams):
            remaining = len(all_streams) - next_count
            label_text = f"➕ Load More ({remaining} remaining)"
            more_item = QListWidgetItem(label_text)
            more_item.setData(Qt.ItemDataRole.UserRole + 2, "load_more")
            more_item.setForeground(QColor("#00f0ff"))
            more_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            list_widget.addItem(more_item)
        QTimer.singleShot(50, lambda: self.load_visible_icons(list_widget))

    def filter_list_items(self, mode, query, list_widget):
        query = query.lower().strip()
        if not query:
            list_widget.clear()
            self.streams_loaded_count[mode] = 0
            self.show_more_streams(mode, list_widget)
            return
            
        list_widget.clear()
        all_streams = self.streams_data.get(mode, [])
        matches = [s for s in all_streams if query in s.get("name", "").lower()]
        
        for stream in matches[:100]:
            name = stream.get("name", "Unknown Stream")
            rating = stream.get("rating")
            if rating:
                name += f"  (⭐ {rating})"
                
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, stream)
            
            logo_url = stream.get("stream_icon") or stream.get("cover") or ""
            item.setData(Qt.ItemDataRole.UserRole + 1, logo_url)
            
            list_widget.addItem(item)
            
        QTimer.singleShot(50, lambda: self.load_visible_icons(list_widget))

    def closeEvent(self, event):
        self.abort_active_workers()
        self.player_widget.stop()
        event.accept()
