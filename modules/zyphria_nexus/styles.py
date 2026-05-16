# modules/zyphria_nexus/styles.py
import tkinter as tk
from tkinter import ttk

# Define colors for the Hologram HUD theme
bg_dark = "#2A2A2A"          # Dark background
bg_medium = "#3D3D3D"        # Medium dark background for frames
fg_white = "#FFFFFF"         # White foreground for most text
hologram_glow = "#00FFFF"    # Cyan/Aqua for accents, highlights, selected items
alt_gray = "#505050"         # Alternate gray for listboxes, etc.
ghost_selection = "#3D4D4D"  # Subtle selection background
border_color = "#00BFFF"     # Deep sky blue for borders (holographic effect)
button_bg = "#4A4A4A"        # Button background
button_fg = "#00FFFF"        # Button foreground text (hologram glow)
button_active_bg = "#00AADD" # Button active background (brighter blue)

# Define colors for status bar
status_error_color = "#FF6347"   # Tomato red
status_warning_color = "#FFD700" # Gold yellow
status_info_color = fg_white     # White (default)

# NEW: Define text_highlight_color for consistent use in Listbox selectbackground
text_highlight_color = ghost_selection


def setup_styles(root):
    s = ttk.Style(root)

    # Set the theme to 'clam' as a base, which is more customizable
    s.theme_use('clam')

    # General style for all widgets
    s.configure('.',
                background=bg_medium,
                foreground=fg_white,
                font=('Arial', 10))

    # Frame style
    s.configure('TFrame',
                background=bg_medium,
                borderwidth=1,
                relief="flat") 

    s.configure('TLabelframe',
                background=bg_medium,
                foreground=hologram_glow, # Label text color
                borderwidth=2,
                relief="solid", # Solid border for label frames
                font=('Arial', 11, 'bold'))

    s.configure('TLabelframe.Label',
                background=bg_medium,
                foreground=hologram_glow,
                font=('Arial', 11, 'bold'))

    # Label style
    s.configure('TLabel',
                background=bg_medium,
                foreground=fg_white)

    # Button style
    s.configure('TButton',
                background=button_bg,
                foreground=button_fg,
                font=('Arial', 10, 'bold'),
                borderwidth=2,
                relief="raised",
                padding=5)
    s.map('TButton',
          background=[('active', button_active_bg), ('!disabled', button_bg)],
          foreground=[('active', fg_white), ('!disabled', button_fg)],
          relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

    # Entry style
    s.configure('TEntry',
                fieldbackground=bg_dark,
                foreground=fg_white,
                insertcolor=hologram_glow, # Cursor color
                borderwidth=1,
                relief="solid")

    # Scrollbar style
    s.configure('Vertical.TScrollbar',
                background=bg_medium,
                troughcolor=bg_dark,
                bordercolor=border_color,
                arrowcolor=hologram_glow)
    s.map('Vertical.TScrollbar',
          background=[('active', button_active_bg)])

    s.configure('Horizontal.TScrollbar',
                background=bg_medium,
                troughcolor=bg_dark,
                bordercolor=border_color,
                arrowcolor=hologram_glow)
    s.map('Horizontal.TScrollbar',
          background=[('active', button_active_bg)])

    # Treeview style
    s.configure('Treeview',
                background=bg_dark,
                foreground=fg_white,
                fieldbackground=bg_dark,
                rowheight=25,
                borderwidth=0) 
    # Use ghost_selection for selected background, hologram_glow for text
    s.map('Treeview',
          background=[('selected', ghost_selection)], # Softer selected row background
          foreground=[('selected', hologram_glow)],       # Text color on selected row
          fieldbackground=[('selected', ghost_selection)]) # Ensure the actual "field" part is also ghost_selection
    
    # Flatten Treeview Heading relief
    s.configure('Treeview.Heading',
                background=bg_medium,
                foreground=hologram_glow,
                font=('Arial', 10, 'bold'),
                relief="flat")
    s.map('Treeview.Heading',
          background=[('active', button_active_bg)])

    # Combobox style
    s.configure('TCombobox',
                fieldbackground=bg_dark,
                background=bg_medium,
                foreground=fg_white,
                selectbackground=hologram_glow,
                selectforeground=bg_dark,
                borderwidth=1,
                relief="solid")
    s.map('TCombobox',
          fieldbackground=[('readonly', bg_dark)],
          selectbackground=[('readonly', hologram_glow)],
          selectforeground=[('readonly', bg_dark)],
          background=[('readonly', bg_medium)])

    # Progressbar style
    s.configure('TProgressbar',
                background=hologram_glow,
                troughcolor=bg_dark,
                bordercolor=border_color,
                lightcolor=hologram_glow,
                darkcolor=hologram_glow,
                thickness=10)

    # Menubar/Menu styles (ttk configuration - might not always apply to tk.Menu)
    s.configure('TMenu', 
                background=bg_medium,
                foreground=fg_white,
                relief="flat")
    s.configure('TMenubutton', 
                background=bg_medium,
                foreground=fg_white,
                font=('Arial', 10))
    s.map('TMenubutton',
          background=[('active', hologram_glow)],
          foreground=[('active', bg_dark)])

    # Status Bar style
    s.configure('StatusBar.TLabel',
                background=bg_dark, 
                foreground=fg_white,
                font=('Arial', 9, 'italic'),
                padding=2,
                relief="flat",
                borderwidth=0) 

    # --- Direct styling for tk.Menu widgets using option_add ---
    root.option_add('*Menu.background', bg_medium)          # Background of the menubar itself and dropdowns
    root.option_add('*Menu.foreground', fg_white)          # Text color of menubar items
    root.option_add('*Menu.activeBackground', hologram_glow) # Background when item is hovered
    root.option_add('*Menu.activeForeground', bg_dark)     # Text color when item is hovered
    root.option_add('*Menu.relief', 'flat')                 # Flat relief for menu items
    root.option_add('*Menu.borderWidth', 0)                 # No border for menu items

    root.option_add('*TCombobox*Listbox.background', bg_dark)
    root.option_add('*TCombobox*Listbox.foreground', fg_white)
    root.option_add('*TCombobox*Listbox.selectBackground', hologram_glow)
    root.option_add('*TCombobox*Listbox.selectForeground', bg_dark)

# NEW: Function to return available themes
def get_all_themes():
    """Returns a list of all available themes. Currently, only 'Hologram HUD' is explicitly styled."""
    return ["Hologram HUD"]