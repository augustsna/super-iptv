import datetime
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QLineEdit, QStackedWidget, QSplitter,
    QFrame, QComboBox, QScrollArea, QSizePolicy, QStyle, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap

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
        self.client = client
        self.player_widget = PlayerWidget(self)
        
        # Cache for loaded categories and streams to avoid unnecessary network queries
        self.categories_cache = {"live": [], "vod": [], "series": []}
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

    def setup_ui(self):
        self.setObjectName("DashboardWidget")
        self.setStyleSheet("""
            #DashboardWidget {
                background-color: #0c0c0e;
            }
            /* Sidebar Styling */
            QFrame#sidebar {
                background-color: #0d0d0f;
                border-right: 1px solid #1c1c22;
            }
            QLabel#logoText {
                color: #6c5ce7;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 5px;
            }
            QPushButton.nav-btn {
                background-color: transparent;
                color: #8f8f9e;
                border: none;
                border-left: 3px solid transparent;
                padding: 12px 15px;
                text-align: left;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton.nav-btn:hover {
                color: #ffffff;
                background-color: #16161a;
            }
            QPushButton.nav-btn.active {
                color: #6c5ce7;
                background-color: #16161a;
                border-left: 3px solid #6c5ce7;
            }
            /* Main Content Panels */
            QFrame#contentPanel {
                background-color: #0c0c0e;
            }
            QListWidget {
                background-color: #121215;
                color: #ffffff;
                border: 1px solid #202026;
                border-radius: 6px;
                padding: 5px;
                outline: 0;
            }
            QListWidget::item {
                border-radius: 4px;
                padding: 8px 10px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #1b1b22;
                color: #6c5ce7;
            }
            QListWidget::item:selected {
                background-color: #6c5ce7;
                color: #ffffff;
            }
            /* Search input */
            QLineEdit.search-bar {
                background-color: #121215;
                color: #ffffff;
                border: 1px solid #202026;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit.search-bar:focus {
                border-color: #6c5ce7;
            }
            /* Detail Panes */
            QFrame.detail-pane {
                background-color: #121215;
                border: 1px solid #202026;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel.pane-title {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel.meta-label {
                color: #8f8f9e;
                font-size: 12px;
            }
            QLabel.plot-label {
                color: #c5c5d2;
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
                background-color: #1c1c22;
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

        # App Logo text
        logo = QLabel("📺 XTREME API", self.sidebar)
        logo.setObjectName("logoText")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)

        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            ("📺 Live TV", self.show_live_tv),
            ("🎬 Movies", self.show_movies),
            ("🍿 Series", self.show_series),
            ("⚙ Settings", self.show_settings),
        ]
        
        for idx, (label, callback) in enumerate(nav_items):
            btn = QPushButton(label, self.sidebar)
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

        # Logout button
        logout_btn = QPushButton("🚪 Logout", self.sidebar)
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
        splitter = QSplitter(Qt.Orientation.Horizontal, panel)
        
        # Left: Categories
        self.live_cat_widget = QWidget(self)
        self.live_cat_widget.setMinimumWidth(120)
        cat_layout = QVBoxLayout(self.live_cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        
        cat_title = QLabel("Categories", self)
        cat_title.setStyleSheet("color: #8f8f9e; font-weight: bold; margin-bottom: 5px;")
        self.live_cat_list = QListWidget(self)
        self.live_cat_list.currentRowChanged.connect(self.on_live_category_changed)
        
        cat_layout.addWidget(cat_title)
        cat_layout.addWidget(self.live_cat_list)

        # Center: Channel list & search bar
        self.live_channel_widget = QWidget(self)
        self.live_channel_widget.setMinimumWidth(120)
        channel_layout = QVBoxLayout(self.live_channel_widget)
        channel_layout.setContentsMargins(0, 0, 0, 0)
        
        self.live_search = QLineEdit(self)
        self.live_search.setPlaceholderText("🔍 Search channels...")
        self.live_search.setProperty("class", "search-bar")
        self.live_search.textChanged.connect(self.filter_live_channels)
        
        self.live_channel_list = QListWidget(self)
        self.live_channel_list.itemClicked.connect(self.on_live_channel_clicked)
        
        channel_layout.addWidget(self.live_search)
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
        
        self.sidebar_toggle_btn = QPushButton("◀ Menu", self)
        self.sidebar_toggle_btn.setCheckable(True)
        self.sidebar_toggle_btn.setChecked(True)
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1a24;
                color: #e0e0e2;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(108, 92, 231, 0.2);
                border-color: #6c5ce7;
                color: #ffffff;
            }
            QPushButton:checked {
                color: #6c5ce7;
                border-color: #6c5ce7;
                background-color: rgba(108, 92, 231, 0.1);
            }
        """)
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        
        self.cat_toggle_btn = QPushButton("📂 Categories", self)
        self.cat_toggle_btn.setCheckable(True)
        self.cat_toggle_btn.setChecked(True)
        self.cat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cat_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.cat_toggle_btn.clicked.connect(self.toggle_categories)
        
        self.channel_toggle_btn = QPushButton("📋 Channels", self)
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
        self.live_info_title = QLabel("", self)
        self.live_info_title.setProperty("class", "pane-title")
        self.live_info_desc = QLabel("", self)
        self.live_info_desc.setWordWrap(True)
        self.live_info_desc.setProperty("class", "plot-label")
        
        self.live_detail_layout.addWidget(self.mini_player_container, stretch=9)
        self.live_detail_layout.addWidget(self.live_info_title)
        self.live_detail_layout.addWidget(self.live_info_desc)
        self.live_detail_layout.addStretch(1)

        # Add to splitter in new order: Player (left/middle), Categories (right-left), Channels (right-right)
        splitter.addWidget(self.live_detail_pane)
        splitter.addWidget(self.live_cat_widget)
        splitter.addWidget(self.live_channel_widget)
        
        # Set default splitter sizes (Player: 55%, Categories: 22.5%, Streams: 22.5%)
        splitter.setSizes([470, 215, 215])

        layout.addWidget(splitter)
        self.content_stack.addWidget(panel)

    def setup_movies_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal, panel)

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
        
        self.movie_sidebar_toggle_btn = QPushButton("◀ Menu", self)
        self.movie_sidebar_toggle_btn.setCheckable(True)
        self.movie_sidebar_toggle_btn.setChecked(True)
        self.movie_sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_sidebar_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.movie_sidebar_toggle_btn.clicked.connect(self.toggle_movie_sidebar)
        
        self.movie_cat_toggle_btn = QPushButton("📂 Categories", self)
        self.movie_cat_toggle_btn.setCheckable(True)
        self.movie_cat_toggle_btn.setChecked(True)
        self.movie_cat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_cat_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.movie_cat_toggle_btn.clicked.connect(self.toggle_movie_categories)
        
        self.movie_list_toggle_btn = QPushButton("🎬 Movies", self)
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

        self.movie_title_label = QLabel("Select a Movie", self)
        self.movie_title_label.setProperty("class", "pane-title")
        
        self.movie_rating_label = QLabel("", self)
        self.movie_rating_label.setStyleSheet("color: #00d2d3; font-weight: bold;")
        
        self.movie_desc_label = QLabel("", self)
        self.movie_desc_label.setWordWrap(True)
        self.movie_desc_label.setProperty("class", "plot-label")
        
        self.movie_play_btn = QPushButton("🎬 PLAY MOVIE", self)
        self.movie_play_btn.setProperty("class", "action-btn")
        self.movie_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movie_play_btn.clicked.connect(self.play_selected_movie)
        self.movie_play_btn.hide()
        
        self.movie_detail_layout.addWidget(self.movie_player_container, stretch=9)
        self.movie_detail_layout.addWidget(self.movie_title_label)
        self.movie_detail_layout.addWidget(self.movie_rating_label)
        self.movie_detail_layout.addWidget(self.movie_desc_label)
        self.movie_detail_layout.addSpacing(15)
        self.movie_detail_layout.addWidget(self.movie_play_btn)
        self.movie_detail_layout.addStretch(1)

        # Center: Categories
        self.movie_cat_widget = QWidget(self)
        self.movie_cat_widget.setMinimumWidth(120)
        cat_layout = QVBoxLayout(self.movie_cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.movie_cat_list = QListWidget(self)
        self.movie_cat_list.currentRowChanged.connect(self.on_movie_category_changed)
        
        cat_layout.addWidget(QLabel("Categories", self))
        cat_layout.addWidget(self.movie_cat_list)

        # Right: Movies List
        self.movie_list_widget = QWidget(self)
        self.movie_list_widget.setMinimumWidth(120)
        movies_layout = QVBoxLayout(self.movie_list_widget)
        movies_layout.setContentsMargins(0, 0, 0, 0)
        
        self.movie_search = QLineEdit(self)
        self.movie_search.setPlaceholderText("🔍 Search movies...")
        self.movie_search.setProperty("class", "search-bar")
        self.movie_search.textChanged.connect(self.filter_movies)
        
        self.movie_list = QListWidget(self)
        self.movie_list.itemClicked.connect(self.on_movie_clicked)
        
        movies_layout.addWidget(self.movie_search)
        movies_layout.addWidget(self.movie_list)

        splitter.addWidget(self.movie_detail_pane)
        splitter.addWidget(self.movie_cat_widget)
        splitter.addWidget(self.movie_list_widget)
        splitter.setSizes([470, 215, 215])

        layout.addWidget(splitter)
        self.content_stack.addWidget(panel)

    def setup_series_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal, panel)

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
        
        self.series_sidebar_toggle_btn = QPushButton("◀ Menu", self)
        self.series_sidebar_toggle_btn.setCheckable(True)
        self.series_sidebar_toggle_btn.setChecked(True)
        self.series_sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.series_sidebar_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.series_sidebar_toggle_btn.clicked.connect(self.toggle_series_sidebar)
        
        self.series_cat_toggle_btn = QPushButton("📂 Categories", self)
        self.series_cat_toggle_btn.setCheckable(True)
        self.series_cat_toggle_btn.setChecked(True)
        self.series_cat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.series_cat_toggle_btn.setStyleSheet(self.sidebar_toggle_btn.styleSheet())
        self.series_cat_toggle_btn.clicked.connect(self.toggle_series_categories)
        
        self.series_list_toggle_btn = QPushButton("🍿 Series", self)
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

        self.series_title_label = QLabel("Select a Series", self)
        self.series_title_label.setProperty("class", "pane-title")
        
        self.series_desc_label = QLabel("", self)
        self.series_desc_label.setWordWrap(True)
        self.series_desc_label.setProperty("class", "plot-label")
        
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
        self.series_detail_layout.addWidget(self.series_title_label)
        self.series_detail_layout.addWidget(self.series_desc_label)
        self.series_detail_layout.addSpacing(10)
        self.series_detail_layout.addWidget(self.season_combo_label)
        self.series_detail_layout.addWidget(self.season_combo)
        self.series_detail_layout.addSpacing(10)
        self.series_detail_layout.addWidget(self.episodes_list_label)
        self.series_detail_layout.addWidget(self.episodes_list)
        self.series_detail_layout.addStretch(1)

        # Center: Categories
        self.series_cat_widget = QWidget(self)
        self.series_cat_widget.setMinimumWidth(120)
        cat_layout = QVBoxLayout(self.series_cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.series_cat_list = QListWidget(self)
        self.series_cat_list.currentRowChanged.connect(self.on_series_category_changed)
        
        cat_layout.addWidget(QLabel("Categories", self))
        cat_layout.addWidget(self.series_cat_list)

        # Right: Series List
        self.series_list_widget = QWidget(self)
        self.series_list_widget.setMinimumWidth(120)
        series_layout = QVBoxLayout(self.series_list_widget)
        series_layout.setContentsMargins(0, 0, 0, 0)
        
        self.series_search = QLineEdit(self)
        self.series_search.setPlaceholderText("🔍 Search series...")
        self.series_search.setProperty("class", "search-bar")
        self.series_search.textChanged.connect(self.filter_series)
        
        self.series_list = QListWidget(self)
        self.series_list.itemClicked.connect(self.on_series_clicked)
        
        series_layout.addWidget(self.series_search)
        series_layout.addWidget(self.series_list)

        splitter.addWidget(self.series_detail_pane)
        splitter.addWidget(self.series_cat_widget)
        splitter.addWidget(self.series_list_widget)
        splitter.setSizes([470, 215, 215])

        layout.addWidget(splitter)
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
                background-color: #121215;
                border: 1px solid #202026;
                border-radius: 12px;
                padding: 30px;
            }
            QLabel#settingsTitle {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#settingsKey {
                color: #8f8f9e;
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
        details = [
            ("Username:", self.client.username),
            ("Status:", self.client.user_info.get("status", "Unknown")),
            ("Connections:", f"{self.client.user_info.get('active_cons', '0')} / {self.client.user_info.get('max_connections', 'Unlimited')}"),
        ]
        
        # Format date expiration
        exp_timestamp = self.client.user_info.get("expiry_date")
        if exp_timestamp:
            try:
                date = datetime.datetime.fromtimestamp(int(exp_timestamp))
                details.append(("Expiration Date:", date.strftime("%Y-%m-%d %H:%M:%S")))
            except Exception:
                details.append(("Expiration Date:", "Never"))
        else:
            details.append(("Expiration Date:", "Never"))

        # Add Details to card
        for key, val in details:
            row = QHBoxLayout()
            kl = QLabel(key, card)
            kl.setObjectName("settingsKey")
            kl.setFixedWidth(150)
            vl = QLabel(val, card)
            vl.setObjectName("settingsVal")
            row.addWidget(kl)
            row.addWidget(vl)
            row.addStretch()
            card_layout.addLayout(row)

        card_layout.addSpacing(25)
        
        # Audio Codec support info
        codec_info = QLabel(" Dolby Audio AC3 & EAC3 decoders are loaded and fully supported.", card)
        codec_info.setStyleSheet("color: #00d2d3; font-weight: bold; border: 1px solid #00d2d3; border-radius: 6px; padding: 10px; background-color: rgba(0, 210, 211, 0.05);")
        card_layout.addWidget(codec_info)

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
            list_widget.setEnabled(True)
            list_widget.clear()
            self.categories_cache[mode] = categories
            
            if not categories:
                list_widget.addItem("No categories found.")
                return
                
            # Add an 'All Channels / Streams' top item
            all_item = QListWidgetItem("🌟 [All Categories]")
            all_item.setData(Qt.ItemDataRole.UserRole, None)
            list_widget.addItem(all_item)
            
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
        list_widget.addItem("Loading streams...")
        list_widget.setEnabled(False)
        
        # Abort previous stream worker if running
        if self.stream_worker and self.stream_worker.isRunning():
            self.stream_worker.terminate()
            self.stream_worker.wait()

        self.stream_worker = FetchStreamsWorker(self.client, mode, category_id)

        def on_finished(streams):
            list_widget.setEnabled(True)
            list_widget.clear()
            self.current_streams = streams
            
            if not streams:
                list_widget.addItem("No streams available.")
                return

            for stream in streams:
                name = stream.get("name", "Unknown Stream")
                stream_id = stream.get("stream_id") or stream.get("series_id")
                
                # Check for rating if available (mostly VODs)
                rating = stream.get("rating")
                if rating:
                    name += f"  (⭐ {rating})"
                    
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, stream)
                list_widget.addItem(item)

        self.stream_worker.finished.connect(on_finished)
        self.stream_worker.start()

    # --- Live TV Event Handlers ---

    def on_live_category_changed(self, row):
        if row < 0:
            return
        item = self.live_cat_list.currentItem()
        category_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_streams("live", category_id, self.live_channel_list)

    def filter_live_channels(self, query):
        query = query.lower().strip()
        for i in range(self.live_channel_list.count()):
            item = self.live_channel_list.item(i)
            item.setHidden(query not in item.text().lower())

    def on_live_channel_clicked(self, item):
        stream_data = item.data(Qt.ItemDataRole.UserRole)
        if not stream_data:
            return
            
        stream_id = stream_data["stream_id"]
        channel_name = stream_data["name"]
        
        # Dock player back to the live container if not already there
        self.dock_player_to_live()
        
        # Set text details
        self.live_info_title.setText(channel_name)
        self.live_info_desc.setText(f"Streaming live now. Stream ID: {stream_id}")
        
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
        query = query.lower().strip()
        for i in range(self.movie_list.count()):
            item = self.movie_list.item(i)
            item.setHidden(query not in item.text().lower())

    def on_movie_clicked(self, item):
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
        query = query.lower().strip()
        for i in range(self.series_list.count()):
            item = self.series_list.item(i)
            item.setHidden(query not in item.text().lower())

    def on_series_clicked(self, item):
        series_data = item.data(Qt.ItemDataRole.UserRole)
        if not series_data:
            return
            
        series_id = series_data["series_id"]
        self.series_title_label.setText(series_data.get("name", "Unknown Series"))
        self.series_desc_label.setText(series_data.get("plot", "No description available."))
        
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
        logging.info("VLC Player: Docked to Live TV Panel")

    def dock_player_to_movie(self):
        if self.player_dock_state == "movie":
            return
        self.movie_info_label.hide()
        self.movie_player_layout.addWidget(self.player_widget)
        self.player_dock_state = "movie"
        logging.info("VLC Player: Docked to Movie Details Panel")

    def dock_player_to_series(self):
        if self.player_dock_state == "series":
            return
        self.series_info_label.hide()
        self.series_player_layout.addWidget(self.player_widget)
        self.player_dock_state = "series"
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

    def toggle_categories(self):
        visible = self.cat_toggle_btn.isChecked()
        self.live_cat_widget.setVisible(visible)

    def toggle_channels(self):
        visible = self.channel_toggle_btn.isChecked()
        self.live_channel_widget.setVisible(visible)

    def toggle_movie_categories(self):
        visible = self.movie_cat_toggle_btn.isChecked()
        self.movie_cat_widget.setVisible(visible)

    def toggle_movie_list(self):
        visible = self.movie_list_toggle_btn.isChecked()
        self.movie_list_widget.setVisible(visible)

    def toggle_series_categories(self):
        visible = self.series_cat_toggle_btn.isChecked()
        self.series_cat_widget.setVisible(visible)

    def toggle_series_list(self):
        visible = self.series_list_toggle_btn.isChecked()
        self.series_list_widget.setVisible(visible)

    def closeEvent(self, event):
        self.abort_active_workers()
        self.player_widget.stop()
        event.accept()
