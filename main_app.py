# main_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import logging
import ctypes  # Needed for the Taskbar fix
from PIL import Image, ImageTk
import time # For Discord RPC timestamps

# --- RECONFIGURE STDOUT FOR UTF-8 ---
# This is a robust way to handle Unicode output to console on Windows
# for Python 3.7+. It should be placed very early in the script.
# Added checks for `sys.stdout is not None` to prevent AttributeError if stdout is somehow uninitialized
if sys.stdout is not None and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older Python versions or environments that don't support reconfigure
        pass 
if sys.stderr is not None and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ------------------------------------


# --- Taskbar Icon Fix (App User Model ID) ---
try:
    myappid = 'mycompany.myproduct.subproduct.version' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception as e:
    pass
# ------------------------------------------------

# Configure global logging once at the application's entry point
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log")

# Create a FileHandler with UTF-8 encoding
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create a StreamHandler (will now use the reconfigured sys.stdout which is UTF-8)
# Only add StreamHandler if sys.stdout is available
stream_handlers = [file_handler]
if sys.stdout is not None:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handlers.append(stream_handler)


# Set up the basic configuration with the handlers
logging.basicConfig(
    level=logging.DEBUG,
    handlers=stream_handlers
)
main_app_logger = logging.getLogger(__name__)

# --- ALL CUSTOM MODULE IMPORTS ---
# Ensure all modules used in show_module are imported here
from modules.music_player import MusicPlayerModule
from modules.music_downloader import MusicDownloaderModule
from modules.settings_module import SettingsModule
from modules.notes_module import NotesModule
from modules.hash_codec_module import HashCodecModule
from modules.unit_converter_module import UnitConverterModule
from modules.game_management_module import GameManagementModule
from modules.file_shredder_module import FileShredderModule
from modules.system_monitor_module import SystemMonitorModule 
from modules.discord_rpc_manager import DiscordRPCManager 
# --- Games Imports (Removed) ---
# Keeping this commented out as you requested to remove the games
# from modules.games.clicker_game import ClickerGameModule 
# from modules.games.elemental_nexus import ElementalNexusModule 

import settings_manager

# Import Zyphria Nexus styles directly to apply globally
from modules.zyphria_nexus import styles as zyphria_styles
from modules.zyphria_nexus.styles import bg_medium, bg_dark

class MultiAppScreen(tk.Tk):
    def __init__(self, discord_client_id=None): 
        super().__init__()
        self.base_title = "Zyphria Nexus Multi Use Tool"
        self.title(self.base_title)
        self.geometry("1000x700")
        self.minsize(800, 600)

        # Determine base path for resources (PyInstaller friendly)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)

        # Set window icon
        icon_path = os.path.join(base_path, "resources", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, photo)
                main_app_logger.info(f"Window icon set successfully from: {icon_path}")
            except Exception as e:
                main_app_logger.error(f"Error setting window icon '{icon_path}': {e}")
        else:
            main_app_logger.warning(f"Window icon not found at: {icon_path}")

        self.welcome_image_tk = None

        self.config(background=bg_medium)
        main_app_logger.info(f"Root window background set to {bg_medium}.")

        zyphria_styles.setup_styles(self)
        main_app_logger.info("Hologram HUD theme applied globally.")

        self.app_settings = settings_manager.load_settings()
        main_app_logger.info("Application started and settings loaded.")

        # Discord RPC Manager
        self.discord_rpc_manager = None
        if discord_client_id:
            self.discord_rpc_manager = DiscordRPCManager(discord_client_id, self)
            self.discord_rpc_manager.start_rpc() 
            main_app_logger.info("Discord RPC Manager initialized and started.")
        else:
            main_app_logger.warning("Discord Client ID not provided. Rich Presence will not be active.")

        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Exit", command=self._on_closing)

        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        self.active_module_menus = []

        self.main_content_frame = ttk.Frame(self, style="TFrame")
        self.main_content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.left_panel = ttk.Frame(self.main_content_frame, width=200, relief="raised", borderwidth=2, style="TFrame")
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(self.left_panel, text="Select Module", font=("Arial", 14, "bold")).pack(pady=10)

        # --- Module Buttons ---
        self.btn_game_management = ttk.Button(self.left_panel, text="Game Management", command=lambda: self.show_module("game_management"))
        self.btn_game_management.pack(pady=5, fill="x", padx=10)

        self.btn_music_player = ttk.Button(self.left_panel, text="Music Player", command=lambda: self.show_module("player"))
        self.btn_music_player.pack(pady=5, fill="x", padx=10)

        self.btn_music_downloader = ttk.Button(self.left_panel, text="Music Downloader", command=lambda: self.show_module("downloader"))
        self.btn_music_downloader.pack(pady=5, fill="x", padx=10)

        self.btn_hash_codec = ttk.Button(self.left_panel, text="Hash & Codecs", command=lambda: self.show_module("hash_codec"))
        self.btn_hash_codec.pack(pady=5, fill="x", padx=10)

        self.btn_unit_converter = ttk.Button(self.left_panel, text="Unit Converter", command=lambda: self.show_module("unit_converter"))
        self.btn_unit_converter.pack(pady=5, fill="x", padx=10) 
        
        self.btn_file_shredder = ttk.Button(self.left_panel, text="File Shredder", command=lambda: self.show_module("file_shredder"))
        self.btn_file_shredder.pack(pady=5, fill="x", padx=10)

        self.btn_system_monitor = ttk.Button(self.left_panel, text="System Monitor", command=lambda: self.show_module("system_monitor"))
        self.btn_system_monitor.pack(pady=5, fill="x", padx=10)

        self.btn_notes = ttk.Button(self.left_panel, text="Notes", command=lambda: self.show_module("notes"))
        self.btn_notes.pack(pady=5, fill="x", padx=10)

        # --- Removed game buttons ---
        # self.btn_clicker_game = ttk.Button(self.left_panel, text="Clicker Game", command=lambda: self.show_module("clicker_game"))
        # self.btn_clicker_game.pack(pady=5, fill="x", padx=10)
        # self.btn_elemental_nexus = ttk.Button(self.left_panel, text="Elemental Nexus", command=lambda: self.show_module("elemental_nexus"))
        # self.btn_elemental_nexus.pack(pady=5, fill="x", padx=10)

        self.btn_settings = ttk.Button(self.left_panel, text="Settings", command=lambda: self.show_module("settings"))
        self.btn_settings.pack(pady=5, fill="x", padx=10)

        self.right_panel = ttk.Frame(self.main_content_frame, relief="sunken", borderwidth=2, style="TFrame")
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.status_bar = ttk.Label(self, text="Ready.", anchor="w", style="StatusBar.TLabel")
        self.status_bar.pack(side="bottom", fill="x", padx=5, pady=5)

        self.current_module_name = None
        self.modules = {}

        self.show_welcome_screen()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _on_closing(self):
        if self.current_module_name and self.current_module_name in self.modules:
            current_module_instance = self.modules[self.current_module_name]
            if hasattr(current_module_instance, 'before_hide'):
                if not current_module_instance.before_hide(closing_app=True):
                    return
        
        if "player" in self.modules and self.modules["player"]:
            if hasattr(self.modules["player"], '_stop_music'):
                self.modules["player"]._stop_music()

        # Stop Discord RPC when closing
        if self.discord_rpc_manager:
            self.discord_rpc_manager.stop_rpc()

        settings_manager.save_settings(self.app_settings)
        main_app_logger.info("Application is closing. Settings saved.")
        self.destroy()
        sys.exit(0)

    def _clear_dynamic_menus(self):
        for menu, start_index in self.active_module_menus:
            try:
                if menu.winfo_exists():
                    # Ensure current_menu is defined before accessing its index method
                    if menu.index(tk.END) is not None: 
                        current_end_index = menu.index(tk.END) 
                        if current_end_index >= start_index:
                            menu.delete(start_index, tk.END)
            except tk.TclError as e:
                main_app_logger.warning(f"Error clearing dynamic menu items for {menu}: {e}")
        self.active_module_menus = []
        main_app_logger.debug("Dynamic menus cleared.")


    def _add_module_menus(self, module_instance):
        if hasattr(module_instance, 'get_menubar_commands'):
            module_menus = module_instance.get_menubar_commands()

            if "file_commands" in module_menus and module_menus["file_commands"]:
                current_menu = self.file_menu
                start_index = current_menu.index(tk.END) if current_menu.index(tk.END) is not None else 0

                current_menu.add_separator()
                for item in module_menus["file_commands"]:
                    if item is None:
                        current_menu.add_separator()
                    else:
                        label, command = item
                        current_menu.add_command(label=label, command=command)
                self.active_module_menus.append((current_menu, start_index))
                main_app_logger.debug(f"Added file commands for {self.current_module_name}.")

            if "edit_commands" in module_menus and module_menus["edit_commands"]:
                current_menu = self.edit_menu
                start_index = current_menu.index(tk.END) if current_menu.index(tk.END) is not None else 0

                current_menu.add_separator()
                for item in module_menus["edit_commands"]:
                    if item is None:
                        current_menu.add_separator()
                    else:
                        label, command = item
                        current_menu.add_command(label=label, command=command)
                self.active_module_menus.append((current_menu, start_index))
                main_app_logger.debug(f"Added edit commands for {self.current_module_name}.")

            if "help_commands" in module_menus and module_menus["help_commands"]:
                current_menu = self.help_menu
                start_index = current_menu.index(tk.END) if current_menu.index(tk.END) is not None else 0

                current_menu.add_separator()
                for item in module_menus["help_commands"]:
                    if item is None:
                        current_menu.add_separator()
                    else:
                        label, command = item
                        current_menu.add_command(label=label, command=command)
                self.active_module_menus.append((current_menu, start_index))
                main_app_logger.debug(f"Added help commands for {self.current_module_name}.")
                
    def show_welcome_screen(self):
        self._clear_dynamic_menus()
        self.set_window_title(self.base_title)

        if self.current_module_name and self.current_module_name in self.modules:
            if hasattr(self.modules[self.current_module_name], 'before_hide'):
                self.modules[self.current_module_name].before_hide()
            self.modules[self.current_module_name].pack_forget()
        elif self.current_module_name == "welcome":
            for widget in self.right_panel.winfo_children():
                if widget.winfo_exists():
                    widget.destroy()

        welcome_frame = ttk.Frame(self.right_panel, style="TFrame")
        welcome_frame.pack(fill="both", expand=True)

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)
            
        image_path = os.path.join(base_path, "resources", "app_icon.ico")

        if os.path.exists(image_path): 
            try:
                pil_image = Image.open(image_path)
                self.welcome_image_tk = ImageTk.PhotoImage(pil_image)
                image_label = ttk.Label(welcome_frame, image=self.welcome_image_tk, style="TLabel")
                image_label.pack(pady=20)
                main_app_logger.info(f"Loaded and displayed image: {image_path}")
            except Exception as e:
                main_app_logger.error(f"Error loading welcome image '{image_path}': {e}")
                ttk.Label(welcome_frame, text="Error loading welcome image.", foreground="red", style="TLabel").pack(pady=20)
        else:
            main_app_logger.warning(f"Welcome image not found at: {image_path}")

        ttk.Label(welcome_frame, text="Welcome to Zyphria Nexus Multi Use Tool!", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(welcome_frame, text="Select an option from the left panel to begin.").pack()

        self.current_module_name = "welcome"
        self.update_status_message("Ready.", level="info")
        main_app_logger.info("Showing Welcome Screen.")
        
        # Update Discord Rich Presence for Welcome Screen
        if self.discord_rpc_manager:
            # Get RPC data for the welcome screen (from self's method)
            rpc_data = self.get_discord_rpc_status(module_name="welcome")
            
            # Define global buttons (e.g., GitHub, Discord Invite)
            rpc_buttons = [
                {"label": "GitHub Repo", "url": "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool"},
                {"label": "Support Discord", "url": "https://discord.gg/YOUR_INVITE_CODE_HERE"}
            ]
            
            self.discord_rpc_manager.update_activity(
                details=rpc_data.get("details", "Browsing Main Menu"), 
                state=rpc_data.get("state", "Idle"),
                large_image=rpc_data.get("large_image", "app_logo"), # Main app logo
                large_text=rpc_data.get("large_text", "Zyphria Nexus Multi Use Tool"),
                small_image=rpc_data.get("small_image"), # Small image could be None or specific
                small_text=rpc_data.get("small_text"),
                start=int(time.time()), # Reset activity timer
                buttons=rpc_buttons
            )


    def show_module(self, module_name):
        self._clear_dynamic_menus()

        if self.current_module_name and self.current_module_name in self.modules:
            current_module_instance = self.modules[self.current_module_name]
            if hasattr(current_module_instance, 'before_hide'):
                if not current_module_instance.before_hide():
                    return
            current_module_instance.pack_forget()
        elif self.current_module_name == "welcome":
            for widget in self.right_panel.winfo_children():
                if widget.winfo_exists():
                    widget.destroy()


        if module_name not in self.modules:
            main_app_logger.info(f"Instantiating new module: {module_name}")
            if module_name == "game_management":
                self.modules["game_management"] = GameManagementModule(self.right_panel, self.app_settings, self)
            elif module_name == "player":
                self.modules["player"] = MusicPlayerModule(self.right_panel, self.app_settings, self)
            elif module_name == "downloader":
                self.modules["downloader"] = MusicDownloaderModule(self.right_panel, self.app_settings, self)
            elif module_name == "notes":
                self.modules["notes"] = NotesModule(self.right_panel, self.app_settings, self)
            elif module_name == "hash_codec":
                self.modules["hash_codec"] = HashCodecModule(self.right_panel, self.app_settings, self)
            elif module_name == "unit_converter":
                self.modules["unit_converter"] = UnitConverterModule(self.right_panel, self.app_settings, self)
            elif module_name == "file_shredder":
                self.modules["file_shredder"] = FileShredderModule(self.right_panel, self.app_settings, self)
            elif module_name == "system_monitor":
                self.modules["system_monitor"] = SystemMonitorModule(self.right_panel, self.app_settings, self)
            # --- Removed game instantiations ---
            # elif module_name == "clicker_game":
            #     self.modules["clicker_game"] = ClickerGameModule(self.right_panel, self.app_settings, self)
            # elif module_name == "elemental_nexus":
            #     self.modules["elemental_nexus"] = ElementalNexusModule(self.right_panel, self.app_settings, self)
            elif module_name == "settings":
                self.modules["settings"] = SettingsModule(self.right_panel, self.app_settings, self)
            else:
                messagebox.showerror("Error", "Unknown module selected. This module is not implemented or has been removed.", parent=self.winfo_toplevel())
                self.show_welcome_screen() # Fallback to welcome screen on unknown module
                return

        # NEW: Added refresh_settings_ui call for all modules
        # This ensures modules can update their UI or start internal loops when activated.
        if hasattr(self.modules[module_name], 'refresh_settings_ui'):
            self.modules[module_name].refresh_settings_ui()


        self._add_module_menus(self.modules[module_name])

        self.modules[module_name].pack(fill="both", expand=True)
        self.current_module_name = module_name

        display_module_name = module_name.replace('_', ' ').title()

        if module_name != "notes":
            self.set_window_title(f"{self.base_title} - {display_module_name} Module")
        else:
            if self.current_module_name == "notes":
                 self.modules["notes"].update_window_title_status()

        self.update_status_message(f"Loaded {display_module_name} Module.", level="info")
        main_app_logger.info(f"Showing {display_module_name} Module.")

        # Update Discord Rich Presence
        if self.discord_rpc_manager:
            module_instance = self.modules[module_name]
            if hasattr(module_instance, 'get_discord_rpc_status'):
                rpc_data = module_instance.get_discord_rpc_status()
            else:
                rpc_data = self.get_discord_rpc_status(module_name=module_name)
            
            rpc_buttons = [
                {"label": "GitHub Repo", "url": "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool"},
                {"label": "Support Discord", "url": "https://discord.gg/YOUR_INVITE_CODE_HERE"}
            ]

            self.discord_rpc_manager.update_activity(
                details=rpc_data.get("details", f"Using {display_module_name} Module"),
                state=rpc_data.get("state", "Productivity Powerhouse!"),
                large_image=rpc_data.get("large_image", self._get_module_icon_asset(module_name)),
                large_text=rpc_data.get("large_text", display_module_name),
                small_image=rpc_data.get("small_image", "app_logo"),
                small_text=rpc_data.get("small_text", "Zyphria Nexus"),
                start=int(time.time()),
                buttons=rpc_buttons
            )


    def set_window_title(self, title):
        self.title(title)

    def update_status_message(self, message, level='info'):
        self.status_bar.config(text=message)

        if level == 'error':
            self.status_bar.config(foreground=zyphria_styles.status_error_color)
        elif level == 'warning':
            self.status_bar.config(foreground=zyphria_styles.status_warning_color)
        else:
            self.status_bar.config(foreground=zyphria_styles.fg_white)

        main_app_logger.debug(f"StatusBar: [{level.upper()}] {message}")

    def _get_module_icon_asset(self, module_name):
        icon_map = {
            "game_management": "game_management_icon",
            "player": "music_player_icon",
            "downloader": "music_downloader_icon",
            "hash_codec": "hash_codec_icon",
            "unit_converter": "converter_icon",
            "file_shredder": "shredder_icon",
            "system_monitor": "monitor_icon",
            "notes": "notes_icon",
            "settings": "settings_icon",
            # Removed game icons from here as they are not used
            # "clicker_game": "app_logo", 
            # "elemental_nexus": "app_logo", 
            "welcome": "app_logo",
        }
        return icon_map.get(module_name, "app_logo")

    def get_discord_rpc_status(self, module_name="welcome"):
        display_module_name = module_name.replace('_', ' ').title()
        if module_name == "welcome":
            return {
                "details": "Browsing Main Menu",
                "state": "Idle",
                "large_image": "app_logo",
                "large_text": "Zyphria Nexus Multi Use Tool",
                "small_image": None,
                "small_text": None,
            }
        else:
            return {
                "details": f"Using {display_module_name} Module",
                "state": "Productivity Powerhouse!",
                "large_image": self._get_module_icon_asset(module_name),
                "large_text": display_module_name,
                "small_image": "app_logo",
                "small_text": "Zyphria Nexus",
            }

if __name__ == "__main__":
    DISCORD_CLIENT_ID = "1491150039253258330" 

    app = MultiAppScreen(discord_client_id=DISCORD_CLIENT_ID)
    app.mainloop()