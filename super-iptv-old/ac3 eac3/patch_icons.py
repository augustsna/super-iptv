import re
import os

path = os.path.join(os.path.dirname(__file__), "dashboard_widget.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace Nav Items
content = content.replace(
'''        nav_items = [
            ("📺 Live TV", self.show_live_tv),
            ("🎬 Movies", self.show_movies),
            ("🍿 Series", self.show_series),
            ("⚙ Settings", self.show_settings),
        ]
        
        for idx, (label, callback) in enumerate(nav_items):
            btn = QPushButton(label, self.sidebar)''',
'''        nav_items = [
            ("Live TV", self.show_live_tv, "tv"),
            ("Movies", self.show_movies, "film"),
            ("Series", self.show_series, "clapperboard"),
            ("Settings", self.show_settings, "settings"),
        ]
        
        import os
        for idx, (label, callback, icon_name) in enumerate(nav_items):
            btn = QPushButton("  " + label, self.sidebar)
            icon_path = os.path.join(os.path.dirname(__file__), "icons", f"{icon_name}.svg")
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(18, 18))'''
)

# Replace Logout Button
content = content.replace(
'''        # Logout button
        logout_btn = QPushButton("🚪 Logout", self.sidebar)''',
'''        # Logout button
        logout_btn = QPushButton("  Logout", self.sidebar)
        logout_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "logout.svg")))'''
)

# Replace Toggles
toggles = {
    '("◀ Menu", self)': '("  Menu", self)\n        self.{var}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "menu.svg")))',
    '("📂 Categories", self)': '("  Categories", self)\n        self.{var}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "folder.svg")))',
    '("📋 Channels", self)': '("  Channels", self)\n        self.{var}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))',
    '("🎬 Movies", self)': '("  Movies", self)\n        self.{var}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))',
    '("🍿 Series", self)': '("  Series", self)\n        self.{var}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))'
}

for var_name in ['sidebar_toggle_btn', 'movie_sidebar_toggle_btn', 'series_sidebar_toggle_btn']:
    content = content.replace(f'self.{var_name} = QPushButton("◀ Menu", self)', f'self.{var_name} = QPushButton("  Menu", self)\n        self.{var_name}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "menu.svg")))')

for var_name in ['cat_toggle_btn', 'movie_cat_toggle_btn', 'series_cat_toggle_btn']:
    content = content.replace(f'self.{var_name} = QPushButton("📂 Categories", self)', f'self.{var_name} = QPushButton("  Categories", self)\n        self.{var_name}.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "folder.svg")))')

content = content.replace('self.channel_toggle_btn = QPushButton("📋 Channels", self)', 'self.channel_toggle_btn = QPushButton("  Channels", self)\n        self.channel_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))')
content = content.replace('self.movie_list_toggle_btn = QPushButton("🎬 Movies", self)', 'self.movie_list_toggle_btn = QPushButton("  Movies", self)\n        self.movie_list_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))')
content = content.replace('self.series_list_toggle_btn = QPushButton("🍿 Series", self)', 'self.series_list_toggle_btn = QPushButton("  Series", self)\n        self.series_list_toggle_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "list.svg")))')

# Replace large detail logos
content = content.replace('self.live_logo_label.setText("📺")', 'self.live_logo_label.setText("")\n        self.live_logo_label.setStyleSheet("border: none; background-color: transparent;")\n        self.live_logo_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "icons", "tv_large.svg")))')
content = content.replace('self.movie_logo_label.setText("🎬")', 'self.movie_logo_label.setText("")\n        self.movie_logo_label.setStyleSheet("border: none; background-color: transparent;")\n        self.movie_logo_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "icons", "film_large.svg")))')
content = content.replace('self.series_logo_label.setText("🍿")', 'self.series_logo_label.setText("")\n        self.series_logo_label.setStyleSheet("border: none; background-color: transparent;")\n        self.series_logo_label.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "icons", "clapperboard_large.svg")))')

# Fix dynamically set logos
content = content.replace('self.live_logo_label.setText("📺")', '')
content = content.replace('self.live_logo_label.setText("📺")', '')

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Dashboard widget updated!")
