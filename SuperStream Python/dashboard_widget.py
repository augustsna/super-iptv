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
        self.switch_tab(0)

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
                background-color: #6c5ce7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton.action-btn:hover {
                background-color: #5b4cc4;
            }
            /* QSplitter handle */
            QSplitter::handle {
                background-color: #1c1c22;
                width: 2px;
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
        self.setup_theater_panel() # Added theater mode panel for Movies/Series fullscreen media player

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
        cat_widget = QWidget(self)
        cat_layout = QVBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        
        cat_title = QLabel("Categories", self)
        cat_title.setStyleSheet("color: #8f8f9e; font-weight: bold; margin-bottom: 5px;")
        self.live_cat_list = QListWidget(self)
        self.live_cat_list.currentRowChanged.connect(self.on_live_category_changed)
        
        cat_layout.addWidget(cat_title)
        cat_layout.addWidget(self.live_cat_list)
        splitter.addWidget(cat_widget)

        # Center: Channel list & search bar
        channel_widget = QWidget(self)
        channel_layout = QVBoxLayout(channel_widget)
        channel_layout.setContentsMargins(0, 0, 0, 0)
        
        self.live_search = QLineEdit(self)
        self.live_search.setPlaceholderText("🔍 Search channels...")
        self.live_search.setProperty("class", "search-bar")
        self.live_search.textChanged.connect(self.filter_live_channels)
        
        self.live_channel_list = QListWidget(self)
        self.live_channel_list.itemClicked.connect(self.on_live_channel_clicked)
        
        channel_layout.addWidget(self.live_search)
        channel_layout.addWidget(self.live_channel_list)
        splitter.addWidget(channel_widget)

        # Right: Mini Player and Channel Info Details
        self.live_detail_pane = QFrame(self)
        self.live_detail_pane.setProperty("class", "detail-pane")
        self.live_detail_layout = QVBoxLayout(self.live_detail_pane)
        self.live_detail_layout.setContentsMargins(5, 5, 5, 5)
        self.live_detail_layout.setSpacing(10)

        # Layout for the mini-player container (we will dock player widget here)
        self.mini_player_container = QFrame(self)
        self.mini_player_container.setMinimumHeight(240)
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
        
        self.live_detail_layout.addWidget(self.mini_player_container)
        self.live_detail_layout.addWidget(self.live_info_title)
        self.live_detail_layout.addWidget(self.live_info_desc)
        self.live_detail_layout.addStretch()

        splitter.addWidget(self.live_detail_pane)
        
        # Set default splitter sizes (Categories: 15%, Streams: 30%, Player: 55%)
        splitter.setSizes([180, 250, 470])

        layout.addWidget(splitter)
        self.content_stack.addWidget(panel)

    def setup_movies_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal, panel)

        # Left: Categories
        cat_widget = QWidget(self)
        cat_layout = QVBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.movie_cat_list = QListWidget(self)
        self.movie_cat_list.currentRowChanged.connect(self.on_movie_category_changed)
        
        cat_layout.addWidget(QLabel("Categories", self))
        cat_layout.addWidget(self.movie_cat_list)
        splitter.addWidget(cat_widget)

        # Center: Movie search & list
        movies_widget = QWidget(self)
        movies_layout = QVBoxLayout(movies_widget)
        movies_layout.setContentsMargins(0, 0, 0, 0)
        
        self.movie_search = QLineEdit(self)
        self.movie_search.setPlaceholderText("🔍 Search movies...")
        self.movie_search.setProperty("class", "search-bar")
        self.movie_search.textChanged.connect(self.filter_movies)
        
        self.movie_list = QListWidget(self)
        self.movie_list.itemClicked.connect(self.on_movie_clicked)
        
        movies_layout.addWidget(self.movie_search)
        movies_layout.addWidget(self.movie_list)
        splitter.addWidget(movies_widget)

        # Right: Movie Details View
        self.movie_detail_pane = QFrame(self)
        self.movie_detail_pane.setProperty("class", "detail-pane")
        self.movie_detail_layout = QVBoxLayout(self.movie_detail_pane)
        
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
        
        self.movie_detail_layout.addWidget(self.movie_title_label)
        self.movie_detail_layout.addWidget(self.movie_rating_label)
        self.movie_detail_layout.addWidget(self.movie_desc_label)
        self.movie_detail_layout.addSpacing(15)
        self.movie_detail_layout.addWidget(self.movie_play_btn)
        self.movie_detail_layout.addStretch()

        splitter.addWidget(self.movie_detail_pane)
        splitter.setSizes([180, 250, 470])

        layout.addWidget(splitter)
        self.content_stack.addWidget(panel)

    def setup_series_panel(self):
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal, panel)

        # Left: Categories
        cat_widget = QWidget(self)
        cat_layout = QVBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.series_cat_list = QListWidget(self)
        self.series_cat_list.currentRowChanged.connect(self.on_series_category_changed)
        
        cat_layout.addWidget(QLabel("Categories", self))
        cat_layout.addWidget(self.series_cat_list)
        splitter.addWidget(cat_widget)

        # Center: Series List
        series_widget = QWidget(self)
        series_layout = QVBoxLayout(series_widget)
        series_layout.setContentsMargins(0, 0, 0, 0)
        
        self.series_search = QLineEdit(self)
        self.series_search.setPlaceholderText("🔍 Search series...")
        self.series_search.setProperty("class", "search-bar")
        self.series_search.textChanged.connect(self.filter_series)
        
        self.series_list = QListWidget(self)
        self.series_list.itemClicked.connect(self.on_series_clicked)
        
        series_layout.addWidget(self.series_search)
        series_layout.addWidget(self.series_list)
        splitter.addWidget(series_widget)

        # Right: Series Info & Episodes Navigator
        self.series_detail_pane = QFrame(self)
        self.series_detail_pane.setProperty("class", "detail-pane")
        self.series_detail_layout = QVBoxLayout(self.series_detail_pane)
        
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

        self.series_detail_layout.addWidget(self.series_title_label)
        self.series_detail_layout.addWidget(self.series_desc_label)
        self.series_detail_layout.addSpacing(10)
        self.series_detail_layout.addWidget(self.season_combo_label)
        self.series_detail_layout.addWidget(self.season_combo)
        self.series_detail_layout.addSpacing(10)
        self.series_detail_layout.addWidget(self.episodes_list_label)
        self.series_detail_layout.addWidget(self.episodes_list)
        
        splitter.addWidget(self.series_detail_pane)
        splitter.setSizes([180, 250, 470])

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

    def setup_theater_panel(self):
        # Full-width player view for Movies and Series playback
        panel = QWidget(self)
        self.theater_layout = QVBoxLayout(panel)
        self.theater_layout.setContentsMargins(10, 10, 10, 10)
        self.theater_layout.setSpacing(10)

        # Top Bar
        top_bar = QHBoxLayout()
        
        back_btn = QPushButton("⬅ Back to Browser", panel)
        back_btn.setStyleSheet("""
            background-color: #1a1a1f;
            color: #f1f1f1;
            border: 1px solid #2d2d35;
            border-radius: 6px;
            padding: 8px 15px;
            font-weight: bold;
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.exit_theater_mode)
        
        self.theater_title = QLabel("", panel)
        self.theater_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; margin-left: 10px;")
        
        top_bar.addWidget(back_btn)
        top_bar.addWidget(self.theater_title)
        top_bar.addStretch()

        # Dedicated layout where we will dock the player widget
        self.theater_player_container = QVBoxLayout()
        
        self.theater_layout.addLayout(top_bar)
        self.theater_layout.addLayout(self.theater_player_container)
        
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
        # Undock player from theater and dock back to mini-player if playing live stream
        self.dock_player_to_mini()
        
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
        
        # Dock player back to the mini container if not already there
        self.dock_player_to_mini()
        
        # Set text details
        self.live_info_title.setText(channel_name)
        self.live_info_desc.setText(f"Streaming live now. Stream ID: {stream_id}")
        
        # Construct Live TS stream URL
        stream_url = self.client.get_live_stream_url(stream_id)
        
        # Play in Player
        self.player_widget.play(stream_url)

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
        
        # Launch Theater View
        self.enter_theater_mode(movie_name, stream_url)

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
        
        # Launch Theater View
        self.enter_theater_mode(ep_name, stream_url)

    # --- Docking Video Player Controller (Mini-player vs Full Theater Panel) ---

    def dock_player_to_mini(self):
        if self.player_dock_state == "mini":
            return
            
        # Hide layout message placeholder
        self.live_channel_info_label.hide()
        
        # Reparent & add to mini layout
        self.mini_player_layout.addWidget(self.player_widget)
        self.player_dock_state = "mini"
        logging.info("VLC Player: Docked to Live TV Mini Panel")

    def enter_theater_mode(self, title, url):
        # Stop playback if any
        self.player_widget.stop()
        
        # Update title details
        self.theater_title.setText(f"Playing: {title}")
        
        # Shift widget to the theater layout
        self.theater_player_container.addWidget(self.player_widget)
        self.player_dock_state = "theater"
        
        # Switch tab index to the Theater tab page (index 4)
        self.content_stack.setCurrentIndex(4)
        logging.info(f"VLC Player: Docked to Theater View for {title}")
        
        # Start Playback
        self.player_widget.play(url)

    def exit_theater_mode(self):
        # Stop playback on exit
        self.player_widget.stop()
        
        # Go back to whichever index was active (Movies=1, Series=2)
        btn_live = self.nav_buttons[0]
        btn_movies = self.nav_buttons[1]
        btn_series = self.nav_buttons[2]
        
        if btn_movies.isChecked():
            self.content_stack.setCurrentIndex(1)
        elif btn_series.isChecked():
            self.content_stack.setCurrentIndex(2)
        else:
            # Fallback
            self.content_stack.setCurrentIndex(0)
            self.dock_player_to_mini()

    def closeEvent(self, event):
        self.abort_active_workers()
        self.player_widget.stop()
        event.accept()
