import os

def replace_colors(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = os.path.dirname(__file__)

# main.py replacements
main_replacements = {
    '#0c0c0e': '#07090e',
    '#121215': '#10141e',
    '#2c2c35': '#1e2538',
    '#6c5ce7': '#00f0ff'
}
replace_colors(os.path.join(base_dir, 'main.py'), main_replacements)

# dashboard_widget.py replacements
dash_replacements = {
    '#0c0c0e': '#07090e',
    '#0d0d0f': '#0a0c14',
    '#1c1c22': '#1c2133',
    '#121215': '#10141e',
    '#202026': '#1e2538',
    '#1b1b22': '#1a2030',
    '#6c5ce7': '#00f0ff',
    '#16161a': '#151a25',
    '#8f8f9e': '#9ca3af',
    '#c5c5d2': '#d1d5db',
    '#1a1a24': '#141824',
    '#2d2d3d': '#1e2538',
    'rgba(108, 92, 231': 'rgba(0, 240, 255' # For the rgba hover effects using the old purple
}
replace_colors(os.path.join(base_dir, 'dashboard_widget.py'), dash_replacements)

# login_widget.py replacements
login_replacements = {
    '#0c0c0e': '#07090e',
    '#16161a': '#10141e',
    '#282830': '#1e2538',
    '#1e1e24': '#0a0c14',
    '#2d2d38': '#1e2538',
    '#22222b': '#151a25',
    '#8f8f9e': '#9ca3af',
    '#c5c5d2': '#d1d5db'
}
replace_colors(os.path.join(base_dir, 'login_widget.py'), login_replacements)

print("Color patch applied.")
