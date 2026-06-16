import sys
import os
import vlc
import logging
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, 
    QSlider, QLabel, QMenu, QSizePolicy, QStyle, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QPoint, QPropertyAnimation
from PyQt6.QtGui import QColor, QPalette, QIcon, QAction, QCursor, QGuiApplication

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PlayerWidget(QWidget):
    # Signals for media state
    playback_state_changed = pyqtSignal(str) # "playing", "paused", "stopped"
    time_changed = pyqtSignal(int, int)      # current_ms, total_ms
    full_program_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vlc_instance = vlc.Instance("--no-mouse-events", "--no-video-title-show")
        self.media_player = self.vlc_instance.media_player_new()
        
        try:
            self.media_player.video_set_mouse_input(False)
            self.media_player.video_set_key_input(False)
        except AttributeError:
            pass
        
        self.is_seeking = False
        self.tracks_loaded = False
        self.badges_loaded = False
        self.badge_update_count = 0
        self.stream_url = ""
        self.fullscreen_mode = False
        self.normal_geometry = None
        self.normal_parent = None
        
        self.prev_volume = 70
        self.controls_visible = True
        self.settings_menu_open = False
        
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.toggle_play)
        
        self.setup_ui()
        self.setup_timer()
        self.setup_hover_logic()

    def setup_ui(self):
        self.setObjectName("PlayerWidget")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.update_styles()

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Header Bar (Overlay styled panel)
        self.header_panel = QFrame(self)
        self.header_panel.setObjectName("header_panel")
        self.header_panel.setFixedHeight(40)
        header_layout = QHBoxLayout(self.header_panel)
        header_layout.setContentsMargins(15, 0, 15, 0)
        header_layout.setSpacing(10)

        self.title_label = QLabel("Not Playing", self.header_panel)
        self.title_label.setObjectName("title_label")
        header_layout.addWidget(self.title_label)

        # Metadata Badges Container
        self.meta_badges_layout = QHBoxLayout()
        self.meta_badges_layout.setSpacing(6)
        header_layout.addLayout(self.meta_badges_layout)
        
        header_layout.addStretch()
        self.main_layout.addWidget(self.header_panel)

        # 2. Video Frame Container
        self.video_frame = QFrame(self)
        self.video_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Background color for video frame
        palette = self.video_frame.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.video_frame.setAutoFillBackground(True)
        self.main_layout.addWidget(self.video_frame)

        # 2b. Buffering / Loading HUD Overlay
        self.loading_overlay = QFrame(self.video_frame)
        self.loading_overlay.setStyleSheet("background-color: rgba(8, 8, 10, 0.85); border-radius: 0px;")
        loading_layout = QVBoxLayout(self.loading_overlay)
        
        self.loading_label = QLabel("⚡ BUFFERING STREAM...", self.loading_overlay)
        self.loading_label.setStyleSheet("color: #00f0ff; font-size: 13px; font-weight: bold; background: transparent;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        self.loading_overlay.hide()

        # 3. Control Panel Container (QFrame for bottom control bar)
        self.controls_panel = QFrame(self)
        self.controls_panel.setObjectName("controls_panel")
        self.controls_layout = QVBoxLayout(self.controls_panel)
        self.controls_layout.setContentsMargins(15, 8, 15, 10)
        self.controls_layout.setSpacing(6)
        
        # 3a. Timeline Row
        self.timeline_layout = QHBoxLayout()
        self.timeline_layout.setSpacing(10)
        
        self.slider = QSlider(Qt.Orientation.Horizontal, self.controls_panel)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        
        self.time_label = QLabel("00:00:00 / 00:00:00", self.controls_panel)
        self.time_label.setStyleSheet("font-weight: bold; font-family: Consolas, monospace;")
        
        self.timeline_layout.addWidget(self.slider)
        self.timeline_layout.addWidget(self.time_label)
        self.controls_layout.addLayout(self.timeline_layout)

        # 3b. Controls Buttons Row
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 2, 0, 0)
        self.buttons_layout.setSpacing(8)

        # Play/Pause Circle Button
        self.play_btn = QPushButton("▶", self.controls_panel)
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.toggle_play)
        self.buttons_layout.addWidget(self.play_btn)

        # Stop Button
        self.stop_btn = QPushButton("⏹", self.controls_panel)
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop)
        self.buttons_layout.addWidget(self.stop_btn)

        # Mute / Volume Toggle Button
        self.volume_btn = QPushButton("🔊", self.controls_panel)
        self.volume_btn.setObjectName("volume_btn")
        self.volume_btn.setToolTip("Mute/Unmute")
        self.volume_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_btn.clicked.connect(self.toggle_mute)
        self.buttons_layout.addWidget(self.volume_btn)

        # Volume Slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self.controls_panel)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.media_player.audio_set_volume(70) # Init volume in VLC
        
        self.volume_label = QLabel("70%", self.controls_panel)
        self.volume_label.setStyleSheet("color: #8f8f9e; font-weight: bold; min-width: 32px;")
        
        self.buttons_layout.addWidget(self.volume_slider)
        self.buttons_layout.addWidget(self.volume_label)

        # Spacer
        self.buttons_layout.addStretch()

        # Settings Gear Menu
        self.settings_btn = QPushButton("⚙", self.controls_panel)
        self.settings_btn.setObjectName("settings_btn")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.show_settings_menu)
        self.buttons_layout.addWidget(self.settings_btn)

        # Full Program Size Button
        self.full_program_btn = QPushButton("⧉", self.controls_panel)
        self.full_program_btn.setObjectName("full_program_btn")
        self.full_program_btn.setToolTip("Toggle Full Window Size")
        self.full_program_btn.setCheckable(True)
        self.full_program_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.full_program_btn.clicked.connect(self.toggle_full_program)
        self.buttons_layout.addWidget(self.full_program_btn)

        # Fullscreen Button
        self.fullscreen_btn = QPushButton("⛶", self.controls_panel)
        self.fullscreen_btn.setObjectName("fullscreen_btn")
        self.fullscreen_btn.setToolTip("Fullscreen")
        self.fullscreen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.buttons_layout.addWidget(self.fullscreen_btn)

        self.controls_layout.addLayout(self.buttons_layout)
        self.main_layout.addWidget(self.controls_panel)

        # Event filter for click & gestures on video frame
        self.video_frame.installEventFilter(self)

        # Link VLC to video_frame window handle on Windows
        if sys.platform == "win32":
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        else:
            if sys.platform.startswith("linux"):
                self.media_player.set_xwindow(int(self.video_frame.winId()))

        # Setup opacity effects for smooth transitions
        self.header_opacity_effect = QGraphicsOpacityEffect(self.header_panel)
        self.header_opacity_effect.setOpacity(1.0)
        self.header_panel.setGraphicsEffect(self.header_opacity_effect)
        
        self.controls_opacity_effect = QGraphicsOpacityEffect(self.controls_panel)
        self.controls_opacity_effect.setOpacity(1.0)
        self.controls_panel.setGraphicsEffect(self.controls_opacity_effect)

        # Create opacity property animations
        self.header_animation = QPropertyAnimation(self.header_opacity_effect, b"opacity")
        self.header_animation.setDuration(250) # 250ms smooth transition
        
        self.controls_animation = QPropertyAnimation(self.controls_opacity_effect, b"opacity")
        self.controls_animation.setDuration(250)

        # Create height animations for smooth layout resizes
        self.header_height_animation = QPropertyAnimation(self.header_panel, b"maximumHeight")
        self.header_height_animation.setDuration(250)

        self.controls_height_animation = QPropertyAnimation(self.controls_panel, b"maximumHeight")
        self.controls_height_animation.setDuration(250)

        # Initialize maximum heights for layout
        self.header_panel.setMaximumHeight(40)
        self.controls_panel.setMaximumHeight(self.get_target_controls_height())

    def get_target_controls_height(self):
        if hasattr(self, 'controls_layout') and self.controls_layout:
            h = self.controls_layout.sizeHint().height()
            return h if h > 0 else 80
        return 80

    def update_styles(self):
        # Remove borders and rounded corners when in fullscreen mode to make it completely full screen
        radius = "0px" if self.fullscreen_mode else "12px"
        border = "none" if self.fullscreen_mode else "1px solid #1c1c24"
        
        self.setStyleSheet(f"""
            #PlayerWidget {{
                background-color: #08080a;
                border: {border};
                border-radius: {radius};
            }}
            #header_panel {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(13, 13, 15, 0.95), stop:1 rgba(13, 13, 15, 0.7));
                border-bottom: 1px solid #1c1c24;
                border-top-left-radius: {radius};
                border-top-right-radius: {radius};
            }}
            #controls_panel {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(13, 13, 15, 0.7), stop:1 rgba(13, 13, 15, 0.95));
                border-top: 1px solid #1c1c24;
                border-bottom-left-radius: {radius};
                border-bottom-right-radius: {radius};
            }}
            QLabel {{
                color: #e0e0e2;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
            }}
            #title_label {{
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: rgba(30, 30, 38, 0.6);
                color: #ffffff;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-family: "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(108, 92, 231, 0.2);
                border-color: #00f0ff;
                color: #00f0ff;
            }}
            QPushButton:pressed {{
                background-color: #00f0ff;
                color: #000000;
            }}
            #play_btn, #stop_btn, #volume_btn, #fullscreen_btn, #full_program_btn, #settings_btn {{
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                border-radius: 6px;
                font-size: 16px;
                padding: 0px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: #23232e;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6c5ce7, stop:1 #00f0ff);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #ffffff;
                width: 10px;
                height: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
                border: 1px solid #00f0ff;
            }}
            QSlider::handle:horizontal:hover {{
                background: #00f0ff;
                border-color: #ffffff;
                width: 12px;
                height: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }}
        """)

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.update_player_status)

    def setup_hover_logic(self):
        self.setMouseTracking(True)
        self.video_frame.setMouseTracking(True)
        self.controls_panel.setMouseTracking(True)
        self.header_panel.setMouseTracking(True)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(3000) # Hide controls after 3 seconds of idle mouse
        self.hide_timer.timeout.connect(self.hide_controls)

        # Polling timer for mouse moves when VLC window intercepts hover events
        self.last_cursor_pos = QCursor.pos()
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(200) # Poll every 200ms
        self.poll_timer.timeout.connect(self.poll_mouse_activity)
        self.poll_timer.start()

    def poll_mouse_activity(self):
        current_pos = QCursor.pos()
        if current_pos != self.last_cursor_pos:
            self.last_cursor_pos = current_pos
            # Map global position to local coordinates of this player widget
            local_pos = self.mapFromGlobal(current_pos)
            if self.rect().contains(local_pos):
                self.show_controls()

    def play(self, url=None, title=None):
        if url:
            self.stream_url = url
            logging.info(f"VLC Player: Playing URL {url}")
            media = self.vlc_instance.media_new(url)
            self.media_player.set_media(media)
            self.tracks_loaded = False
            
            if title:
                self.title_label.setText(title)
            else:
                self.title_label.setText("Playing Media")
            
            self.clear_badges()
            self.badges_loaded = False
            
            self.show_controls()
            self.loading_overlay.show()
            
        self.media_player.play()
        self.timer.start()
        self.play_btn.setText("⏸")
        self.playback_state_changed.emit("playing")
        
        # Focus on player widget so keyboard shortcuts work immediately
        self.setFocus()

    def toggle_play(self):
        state = self.media_player.get_state()
        if state == vlc.State.Playing:
            self.media_player.pause()
            self.play_btn.setText("▶")
            self.playback_state_changed.emit("paused")
            self.show_controls()
        else:
            self.play()

    def stop(self):
        self.media_player.stop()
        self.timer.stop()
        self.hide_timer.stop()
        self.slider.setValue(0)
        self.time_label.setText("00:00:00 / 00:00:00")
        self.play_btn.setText("▶")
        self.playback_state_changed.emit("stopped")
        self.tracks_loaded = False
        self.badges_loaded = False
        self.badge_update_count = 0
        self.clear_badges()
        self.loading_overlay.hide()
        self.show_controls()

    def set_volume(self, value):
        self.media_player.audio_set_volume(value)
        self.volume_label.setText(f"{value}%")
        if value == 0:
            self.volume_btn.setText("🔇")
        elif value <= 33:
            self.volume_btn.setText("🔈")
        elif value <= 66:
            self.volume_btn.setText("🔉")
        else:
            self.volume_btn.setText("🔊")

    def toggle_mute(self):
        if self.media_player.audio_get_mute():
            self.media_player.audio_set_mute(False)
            self.volume_slider.setValue(self.prev_volume)
            self.set_volume(self.prev_volume)
        else:
            self.prev_volume = self.volume_slider.value()
            self.media_player.audio_set_mute(True)
            self.volume_slider.setValue(0)
            self.volume_btn.setText("🔇")
            self.volume_label.setText("0%")

    def format_time(self, ms):
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        hours = int((ms / (1000 * 60 * 60)) % 24)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def update_player_status(self):
        # Update timeline position
        if not self.is_seeking:
            length = self.media_player.get_length() # in ms
            current = self.media_player.get_time()   # in ms
            
            if length > 0:
                pos = int((current / length) * 1000)
                self.slider.setValue(pos)
                self.time_label.setText(f"{self.format_time(current)} / {self.format_time(length)}")
                self.time_changed.emit(current, length)
            elif current > 0:
                # Live stream timeline
                self.time_label.setText(f"{self.format_time(current)} / Live Stream")
                self.slider.setValue(0)

        # Detect audio tracks once they are loaded
        state = self.media_player.get_state()
        if state == vlc.State.Playing:
            self.loading_overlay.hide()
            if not self.tracks_loaded:
                tracks = self.media_player.audio_get_track_description()
                if tracks and len(tracks) > 1:
                    logging.info(f"VLC Player: Audio tracks parsed dynamically: {tracks}")
                    self.tracks_loaded = True
            
            # Fetch badges slightly after playing starts so VLC has time to decode headers
            # We poll for the first few seconds because audio/video tracks may appear asynchronously
            if not self.badges_loaded or self.badge_update_count < 30:
                self.update_meta_badges()
                self.badge_update_count += 1
        elif state in (vlc.State.Opening, vlc.State.Buffering):
            self.loading_overlay.show()
            self.loading_overlay.setGeometry(0, 0, self.video_frame.width(), self.video_frame.height())

        # Check if playback ended
        if state == vlc.State.Ended:
            self.stop()

    def clear_badges(self):
        for i in reversed(range(self.meta_badges_layout.count())):
            widget = self.meta_badges_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def update_meta_badges(self):
        w, h = self.media_player.video_get_size(0)
        fps = self.media_player.get_fps()
        length = self.media_player.get_length()
        
        # We need video dimension or length to build badges, if missing, skip and retry later
        if h <= 0 and fps <= 0 and length == 0:
            return
            
        self.badges_loaded = True
        self.clear_badges()
        badges = []
        
        # Live Badge
        if length <= 0:
            badges.append(("● LIVE", "#ff4757"))
            
        # Resolution
        if w > 0 and h > 0:
            res = f"{h}p"
            if h >= 2160: res = "4K"
            elif h >= 1080: res = "1080p"
            elif h >= 720: res = "720p"
            badges.append((res, "#00f0ff"))
            
        # FPS
        if fps > 0:
            badges.append((f"{round(fps)} fps", "#00f0ff"))
            
        # Codecs
        media = self.media_player.get_media()
        if media:
            tracks = media.tracks_get()
            if tracks:
                for track in tracks:
                    try:
                        codec_val = track.codec
                        codec_str = ""
                        if isinstance(codec_val, int):
                            codec_str = codec_val.to_bytes(4, byteorder='little').decode('ascii', 'ignore').strip()
                        else:
                            codec_str = str(codec_val)
                            
                        # Normalize known names for aesthetics
                        c_lower = codec_str.lower().strip()
                        if "264" in c_lower: codec_str = "H264"
                        elif "265" in c_lower or "hevc" in c_lower: codec_str = "HEVC"
                        elif "eac3" in c_lower: codec_str = "EAC3"
                        elif "ac3" in c_lower or "a52" in c_lower: codec_str = "AC3"
                        elif "mp4a" in c_lower: codec_str = "MP4A"
                        elif "aac" in c_lower: codec_str = "AAC"
                        elif "mpga" in c_lower or "mp3" in c_lower: codec_str = "MP3"
                        else: codec_str = codec_str.upper()
                        
                        # Python-vlc track.type can be an int (1=audio, 2=video) or Enum
                        if track.type == getattr(vlc.TrackType, 'video', 2) or track.type == 2:
                            badges.append((codec_str, "#00f0ff"))
                        elif track.type == getattr(vlc.TrackType, 'audio', 1) or track.type == 1:
                            try:
                                channels = track.audio.contents.channels
                            except Exception:
                                channels = 2
                            ch_str = "5.1" if channels >= 6 else ("2.0" if channels == 2 else str(channels))
                            badges.append((f"{codec_str} {ch_str}", "#00f0ff"))
                    except Exception:
                        pass
                        
        for text, color in badges:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                color: {color}; 
                border: 1px solid rgba({255 if color == '#ff4757' else 0}, {71 if color == '#ff4757' else 240}, {87 if color == '#ff4757' else 255}, 0.3); 
                border-radius: 3px; 
                padding: 1px 4px; 
                font-weight: bold; 
                font-size: 9px; 
                background: rgba({255 if color == '#ff4757' else 0}, {71 if color == '#ff4757' else 240}, {87 if color == '#ff4757' else 255}, 0.1);
            """)
            self.meta_badges_layout.addWidget(lbl)

    def show_settings_menu(self):
        self.settings_menu_open = True
        self.hide_timer.stop()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #121215;
                color: #ffffff;
                border: 1px solid #2a2a35;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
                color: #e0e0e0;
                font-family: "Segoe UI", sans-serif;
                font-size: 11px;
            }
            QMenu::item:selected {
                background-color: #6c5ce7;
                color: #ffffff;
            }
            QMenu::item:checked {
                font-weight: bold;
                color: #00f0ff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2a2a35;
                margin: 4px 8px;
            }
        """)

        # Submenu 1: Audio Tracks
        audio_menu = menu.addMenu("🎵 Audio Tracks")
        audio_menu.setStyleSheet(menu.styleSheet())
        
        tracks = self.media_player.audio_get_track_description()
        active_track = self.media_player.audio_get_track()
        
        if not tracks or len(tracks) <= 1:
            no_tracks = audio_menu.addAction("Default Track")
            no_tracks.setCheckable(True)
            no_tracks.setChecked(True)
            no_tracks.setEnabled(False)
        else:
            for track_id, track_name_bytes in tracks:
                track_name = track_name_bytes.decode('utf-8', errors='ignore')
                action = audio_menu.addAction(track_name)
                action.setCheckable(True)
                action.setChecked(track_id == active_track)
                # Capture variable using parameter default binding
                action.triggered.connect(lambda checked, t_id=track_id: self.select_audio_track(t_id))

        # Submenu 2: Playback Speed
        speed_menu = menu.addMenu("⚡ Playback Speed")
        speed_menu.setStyleSheet(menu.styleSheet())
        
        current_speed = self.media_player.get_rate()
        speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        
        for s in speeds:
            lbl = f"{s}x" if s != 1.0 else "1.0x (Normal)"
            action = speed_menu.addAction(lbl)
            action.setCheckable(True)
            action.setChecked(abs(current_speed - s) < 0.05)
            action.triggered.connect(lambda checked, val=s: self.set_playback_speed(val))

        # Display the menu positioned dynamically centered directly above settings button
        button_pos = self.settings_btn.mapToGlobal(QPoint(0, 0))
        menu_size = menu.sizeHint()
        menu_x = button_pos.x() + (self.settings_btn.width() - menu_size.width()) // 2
        menu_y = button_pos.y() - menu_size.height() - 6
        
        menu.exec(QPoint(menu_x, menu_y))
        
        self.settings_menu_open = False
        if self.media_player.get_state() == vlc.State.Playing and self.fullscreen_mode:
            self.hide_timer.start()

    def select_audio_track(self, track_id):
        logging.info(f"VLC Player: Select audio track ID={track_id}")
        self.media_player.audio_set_track(track_id)

    def set_playback_speed(self, rate):
        logging.info(f"VLC Player: Adjusting playback speed to {rate}x")
        self.media_player.set_rate(rate)

    # Slider interactions
    def on_slider_pressed(self):
        self.is_seeking = True
        self.hide_timer.stop()

    def on_slider_released(self):
        if self.is_seeking:
            val = self.slider.value()
            length = self.media_player.get_length()
            if length > 0:
                pos_ratio = val / 1000.0
                target_time_ms = int(pos_ratio * length)
                self.media_player.set_time(target_time_ms)
                logging.info(f"VLC Player: Seeking to position {pos_ratio:.2f} ({target_time_ms} ms)")
            self.is_seeking = False
        
        if self.media_player.get_state() == vlc.State.Playing and self.fullscreen_mode:
            self.hide_timer.start()

    def on_slider_moved(self, value):
        length = self.media_player.get_length()
        if length > 0:
            current = int((value / 1000.0) * length)
            self.time_label.setText(f"{self.format_time(current)} / {self.format_time(length)}")

    # Fullscreen controls
    def toggle_fullscreen(self):
        if not self.fullscreen_mode:
            # Get the screen where the player is currently shown (before detaching)
            target_screen = None
            try:
                target_screen = self.screen()
            except AttributeError:
                if self.window() and self.window().windowHandle():
                    target_screen = self.window().windowHandle().screen()
            
            if not target_screen:
                target_screen = QGuiApplication.primaryScreen()

            # Enter fullscreen
            self.normal_parent = self.parent()
            self.normal_geometry = self.geometry()
            
            # Detach from parent and configure as a frameless top-level window
            self.setParent(None)
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            
            # Move to the correct screen before going fullscreen
            if target_screen:
                self.move(target_screen.geometry().topLeft())
                
            self.showFullScreen()
            self.fullscreen_btn.setText("🗗")
            self.fullscreen_btn.setToolTip("Exit Fullscreen")
            self.fullscreen_mode = True
        else:
            # Exit fullscreen
            self.setWindowState(Qt.WindowState.WindowNoState)
            if self.normal_parent:
                self.setParent(self.normal_parent)
                self.normal_parent.layout().addWidget(self)
            else:
                self.setWindowFlags(Qt.WindowType.Widget)
            self.showNormal()
            self.setGeometry(self.normal_geometry)
            self.fullscreen_btn.setText("⛶")
            self.fullscreen_btn.setToolTip("Fullscreen")
            self.fullscreen_mode = False
        
        self.update_styles()
        self.show_controls()
        self.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay') and self.loading_overlay:
            self.loading_overlay.setGeometry(0, 0, self.video_frame.width(), self.video_frame.height())

    def eventFilter(self, obj, event):
        if obj == self.video_frame:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.click_timer.stop() # Cancel the single click action
                    self.toggle_fullscreen()
                    return True
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Delay the play toggle to see if it's a double click
                    self.click_timer.start(250)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                self.show_controls()
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        self.show_controls()
        super().mouseMoveEvent(event)

    def show_controls(self):
        if not self.controls_visible:
            self.header_panel.show()
            self.controls_panel.show()
            
            # Stop any running animations
            self.header_animation.stop()
            self.controls_animation.stop()
            if hasattr(self, 'header_height_animation'):
                self.header_height_animation.stop()
            if hasattr(self, 'controls_height_animation'):
                self.controls_height_animation.stop()
            
            # Start fade-in animation
            self.header_animation.setStartValue(self.header_opacity_effect.opacity())
            self.header_animation.setEndValue(1.0)
            self.header_animation.start()
            
            self.controls_animation.setStartValue(self.controls_opacity_effect.opacity())
            self.controls_animation.setEndValue(1.0)
            self.controls_animation.start()

            # Start height expand animation
            if hasattr(self, 'header_height_animation'):
                self.header_height_animation.setStartValue(self.header_panel.height())
                self.header_height_animation.setEndValue(40)
                self.header_height_animation.start()
            
            if hasattr(self, 'controls_height_animation'):
                self.controls_height_animation.setStartValue(self.controls_panel.height())
                self.controls_height_animation.setEndValue(self.get_target_controls_height())
                self.controls_height_animation.start()
            
            self.controls_visible = True
            
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        if self.media_player.get_state() == vlc.State.Playing and not self.settings_menu_open and not self.is_seeking and self.fullscreen_mode:
            self.hide_timer.start()
        else:
            self.hide_timer.stop()

    def hide_controls(self):
        if not self.fullscreen_mode:
            return
        if self.media_player.get_state() == vlc.State.Playing and self.controls_visible:
            # Stop any running animations
            self.header_animation.stop()
            self.controls_animation.stop()
            if hasattr(self, 'header_height_animation'):
                self.header_height_animation.stop()
            if hasattr(self, 'controls_height_animation'):
                self.controls_height_animation.stop()
            
            # Start fade-out animation
            self.header_animation.setStartValue(self.header_opacity_effect.opacity())
            self.header_animation.setEndValue(0.0)
            
            self.controls_animation.setStartValue(self.controls_opacity_effect.opacity())
            self.controls_animation.setEndValue(0.0)
            
            # Start height collapse animation
            if hasattr(self, 'header_height_animation'):
                self.header_height_animation.setStartValue(self.header_panel.height())
                self.header_height_animation.setEndValue(0)
                self.header_height_animation.start()

            if hasattr(self, 'controls_height_animation'):
                self.controls_height_animation.setStartValue(self.controls_panel.height())
                self.controls_height_animation.setEndValue(0)
                self.controls_height_animation.start()

            # Disconnect previous finished connections
            try:
                self.header_animation.finished.disconnect()
            except TypeError:
                pass
                
            self.header_animation.finished.connect(self.on_fade_out_finished)
            
            self.header_animation.start()
            self.controls_animation.start()
            
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.controls_visible = False
            self.hide_timer.stop()

    def on_fade_out_finished(self):
        # Only hide from layout if the controls are still supposed to be invisible
        if not self.controls_visible and self.header_opacity_effect.opacity() == 0.0:
            self.header_panel.hide()
            self.controls_panel.hide()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Space:
            self.toggle_play()
            event.accept()
        elif key == Qt.Key.Key_Left:
            # Jump 10 seconds back
            self.seek_relative(-10000)
            event.accept()
        elif key == Qt.Key.Key_Right:
            # Jump 10 seconds forward
            self.seek_relative(10000)
            event.accept()
        elif key == Qt.Key.Key_Up:
            # Volume Up
            self.adjust_volume(5)
            event.accept()
        elif key == Qt.Key.Key_Down:
            # Volume Down
            self.adjust_volume(-5)
            event.accept()
        elif key == Qt.Key.Key_M:
            self.toggle_mute()
            event.accept()
        elif key == Qt.Key.Key_F:
            self.toggle_fullscreen()
            event.accept()
        elif key == Qt.Key.Key_Escape and self.fullscreen_mode:
            self.toggle_fullscreen()
            event.accept()
        else:
            super().keyPressEvent(event)

    def seek_relative(self, ms_offset):
        length = self.media_player.get_length()
        if length > 0:
            current = self.media_player.get_time()
            target = max(0, min(length, current + ms_offset))
            self.media_player.set_time(target)
            logging.info(f"VLC Player: Seeking relative to {target} ms")
            self.show_controls()

    def adjust_volume(self, delta):
        current = self.volume_slider.value()
        target = max(0, min(100, current + delta))
        self.volume_slider.setValue(target)
        self.set_volume(target)
        self.show_controls()

    def toggle_full_program(self):
        is_full = self.full_program_btn.isChecked()
        self.full_program_state_changed.emit(is_full)

    def closeEvent(self, event):
        self.stop()
        self.media_player.release()
        event.accept()
