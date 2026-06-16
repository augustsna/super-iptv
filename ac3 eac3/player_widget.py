import sys
import os
import vlc
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, 
    QSlider, QLabel, QComboBox, QSizePolicy, QStyle
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QIcon, QAction

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PlayerWidget(QWidget):
    # Signals for media state
    playback_state_changed = pyqtSignal(str) # "playing", "paused", "stopped"
    time_changed = pyqtSignal(int, int)      # current_ms, total_ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vlc_instance = vlc.Instance("--no-mouse-events", "--no-video-title-show")
        self.media_player = self.vlc_instance.media_player_new()
        
        self.is_seeking = False
        self.tracks_loaded = False
        self.stream_url = ""
        self.fullscreen_mode = False
        self.normal_geometry = None
        self.normal_parent = None
        
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        self.setObjectName("PlayerWidget")
        self.setStyleSheet("""
            #PlayerWidget {
                background-color: #0d0d0f;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #1a1a1f;
                color: #f1f1f1;
                border: 1px solid #2d2d35;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2b2b35;
                border-color: #00f0ff;
            }
            QPushButton:pressed {
                background-color: #00f0ff;
                color: #000000;
            }
            QComboBox {
                background-color: #1a1a1f;
                color: #f1f1f1;
                border: 1px solid #2d2d35;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 130px;
            }
            QComboBox:hover {
                border-color: #00f0ff;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1f;
                color: #f1f1f1;
                selection-background-color: #00f0ff;
                selection-color: #000000;
                border: 1px solid #2d2d35;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2b2b35;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #00f0ff;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 14px;
                height: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
                border: 1px solid #00f0ff;
            }
            QSlider::handle:horizontal:hover {
                background: #00f0ff;
            }
        """)

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(6)

        # Video Frame Container
        self.video_frame = QFrame(self)
        self.video_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.video_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Background color for video frame
        palette = self.video_frame.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.video_frame.setPalette(palette)
        self.video_frame.setAutoFillBackground(True)
        self.main_layout.addWidget(self.video_frame)

        # Controls Container Layout
        self.controls_layout = QVBoxLayout()
        self.controls_layout.setSpacing(4)
        
        # 1. Timeline Row (Slider + Time label)
        self.timeline_layout = QHBoxLayout()
        
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        
        self.time_label = QLabel("00:00:00 / 00:00:00", self)
        
        self.timeline_layout.addWidget(self.slider)
        self.timeline_layout.addWidget(self.time_label)
        self.controls_layout.addLayout(self.timeline_layout)

        # 2. Buttons Row (Play, Pause, Stop, Volume, Audio Tracks, Fullscreen)
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(5, 0, 5, 0)
        self.buttons_layout.setSpacing(10)

        # Play/Pause Button
        self.play_btn = QPushButton("▶ Play", self)
        self.play_btn.clicked.connect(self.toggle_play)
        self.buttons_layout.addWidget(self.play_btn)

        # Stop Button
        self.stop_btn = QPushButton("⏹ Stop", self)
        self.stop_btn.clicked.connect(self.stop)
        self.buttons_layout.addWidget(self.stop_btn)

        # Volume Controls
        self.volume_label = QLabel("🔊 70%", self)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.media_player.audio_set_volume(70) # Init volume in VLC
        
        self.buttons_layout.addWidget(self.volume_label)
        self.buttons_layout.addWidget(self.volume_slider)

        # Spacer
        self.buttons_layout.addStretch()

        # Audio Track Combo (AC3/EAC3 selector)
        self.audio_track_label = QLabel("Audio Track:", self)
        self.audio_track_combo = QComboBox(self)
        self.audio_track_combo.addItem("Default Track", -1)
        self.audio_track_combo.currentIndexChanged.connect(self.on_audio_track_changed)
        
        self.buttons_layout.addWidget(self.audio_track_label)
        self.buttons_layout.addWidget(self.audio_track_combo)

        # Fullscreen Button
        self.fullscreen_btn = QPushButton("⛶ Fullscreen", self)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.buttons_layout.addWidget(self.fullscreen_btn)

        self.controls_layout.addLayout(self.buttons_layout)
        self.main_layout.addLayout(self.controls_layout)

        # Link VLC to video_frame window handle on Windows
        if sys.platform == "win32":
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        else:
            # Fallback for X11 / Wayland / macOS if executed on non-Windows
            if sys.platform.startswith("linux"):
                self.media_player.set_xwindow(int(self.video_frame.winId()))
            elif sys.platform == "darwin":
                # libvlc NSView requires additional bindings, but user is on Windows.
                pass

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(250) # Polling rate of 250ms
        self.timer.timeout.connect(self.update_player_status)

    def play(self, url=None):
        if url:
            self.stream_url = url
            logging.info(f"VLC Player: Playing URL {url}")
            media = self.vlc_instance.media_new(url)
            self.media_player.set_media(media)
            self.tracks_loaded = False
            self.audio_track_combo.clear()
            self.audio_track_combo.addItem("Loading Tracks...", -1)
            
        self.media_player.play()
        self.timer.start()
        self.play_btn.setText("⏸ Pause")
        self.playback_state_changed.emit("playing")

    def toggle_play(self):
        state = self.media_player.get_state()
        if state == vlc.State.Playing:
            self.media_player.pause()
            self.play_btn.setText("▶ Play")
            self.playback_state_changed.emit("paused")
        else:
            self.play()

    def stop(self):
        self.media_player.stop()
        self.timer.stop()
        self.slider.setValue(0)
        self.time_label.setText("00:00:00 / 00:00:00")
        self.play_btn.setText("▶ Play")
        self.playback_state_changed.emit("stopped")
        self.tracks_loaded = False
        self.audio_track_combo.clear()
        self.audio_track_combo.addItem("Default Track", -1)

    def set_volume(self, value):
        self.media_player.audio_set_volume(value)
        self.volume_label.setText(f"🔊 {value}%")

    # Time converters
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
        if state == vlc.State.Playing and not self.tracks_loaded:
            # Query track description lists
            tracks = self.media_player.audio_get_track_description()
            if tracks and len(tracks) > 1: # Index 0 is usually (-1, b'Disable')
                self.populate_audio_tracks(tracks)
                self.tracks_loaded = True

        # Check if playback ended
        if state == vlc.State.Ended:
            self.stop()

    def populate_audio_tracks(self, tracks):
        # Disconnect signal to avoid trigger during load
        self.audio_track_combo.currentIndexChanged.disconnect(self.on_audio_track_changed)
        self.audio_track_combo.clear()
        
        active_id = self.media_player.audio_get_track()
        
        logging.info(f"VLC Player: Detected audio tracks: {tracks}")
        
        for track_id, track_name_bytes in tracks:
            # Track names are returned as byte strings
            track_name = track_name_bytes.decode('utf-8', errors='ignore')
            
            # Highlight codecs if possible (VLC sometimes gives generic names like 'Audio Track 1')
            # Our generated media file will have names like "AC3 Audio (440Hz)" and "EAC3 Audio (880Hz)"
            self.audio_track_combo.addItem(track_name, track_id)
            
            # Select current active track
            if track_id == active_id:
                idx = self.audio_track_combo.count() - 1
                self.audio_track_combo.setCurrentIndex(idx)
                
        self.audio_track_combo.currentIndexChanged.connect(self.on_audio_track_changed)

    def on_audio_track_changed(self, index):
        if index < 0:
            return
        track_id = self.audio_track_combo.currentData()
        if track_id is not None:
            logging.info(f"VLC Player: Switching to audio track ID={track_id}")
            self.media_player.audio_set_track(track_id)

    # Slider interactions
    def on_slider_pressed(self):
        self.is_seeking = True

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

    def on_slider_moved(self, value):
        # Live time update while dragging
        length = self.media_player.get_length()
        if length > 0:
            current = int((value / 1000.0) * length)
            self.time_label.setText(f"{self.format_time(current)} / {self.format_time(length)}")

    # Fullscreen controls
    def toggle_fullscreen(self):
        if not self.fullscreen_mode:
            # Enter fullscreen
            self.normal_parent = self.parent()
            self.normal_geometry = self.geometry()
            
            # Set to window flags for overlay window
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint)
            self.showFullScreen()
            self.fullscreen_btn.setText("Exit Fullscreen")
            self.fullscreen_mode = True
        else:
            # Exit fullscreen
            self.setWindowFlags(Qt.WindowType.Widget)
            if self.normal_parent:
                # Add back to layout
                self.normal_parent.layout().addWidget(self)
            self.showNormal()
            self.setGeometry(self.normal_geometry)
            self.fullscreen_btn.setText("⛶ Fullscreen")
            self.fullscreen_mode = False

    def keyPressEvent(self, event):
        # Escape key exits fullscreen
        if event.key() == Qt.Key.Key_Escape and self.fullscreen_mode:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.stop()
        self.media_player.release()
        event.accept()
