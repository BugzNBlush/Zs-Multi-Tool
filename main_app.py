# main_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import logging
import ctypes  # Needed for the Taskbar fix
from PIL import Image, ImageTk
import time # For Discord RPC timestamps, and now for idle detection

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
from modules.file_encryptor_decryptor import FileEncryptorDecryptorModule
# NEW IMPORT: AppUpdater Module
from modules.app_updater import AppUpdater


import settings_manager

# Import Zyphria Nexus styles directly to apply globally
from modules.zyphria_nexus import styles as zyphria_styles
from modules.zyphria_nexus.styles import bg_medium, bg_dark

class MultiAppScreen(tk.Tk):
    def __init__(self, discord_client_id=None):
        super().__init__()
        self.base_title = "Z's Multi Tool"
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
        # ADDED: Check for Updates command to the File menu
        # Initialize AppUpdater first, then add this command
        # This will be done below, so temporarily removing it from here
        # self.file_menu.add_command(label="Check for Updates", command=lambda: self.app_updater.check_for_updates(silent=False))
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

        self.btn_file_encryptor_decryptor = ttk.Button(self.left_panel, text="🔒 Encrypt/Decrypt", command=lambda: self.show_module("file_encryptor_decryptor"))
        self.btn_file_encryptor_decryptor.pack(pady=5, fill="x", padx=10)

        self.btn_settings = ttk.Button(self.left_panel, text="Settings", command=lambda: self.show_module("settings"))
        self.btn_settings.pack(pady=5, fill="x", padx=10)

        self.right_panel = ttk.Frame(self.main_content_frame, relief="sunken", borderwidth=2, style="TFrame")
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.status_bar = ttk.Label(self, text="Ready.", anchor="w", style="StatusBar.TLabel")
        self.status_bar.pack(side="bottom", fill="x", padx=5, pady=5)
        self.original_status_message = "Ready." # Store the default/current module status message

        self.current_module_name = None
        self.modules = {}

        # NEW: Initialize AppUpdater
        self.app_updater = AppUpdater(self) # Pass self for main_app_instance reference
        main_app_logger.info("AppUpdater initialized.")

        # ADDED: Check for Updates command to the File menu after app_updater is initialized
        # Also added a separator for better menu organization
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Check for Updates", command=lambda: self.app_updater.check_for_updates(silent=False))


        # --- Idle Detection Attributes ---
        self.last_activity_time = time.time()
        self.idle_check_interval_ms = 1000  # Check for idle status every 1 second
        self.idle_timer_id = None
        self.idle_music_status_displayed = False # Track if music status is currently displayed due to idle

        # Bind events to detect user activity
        self.bind_all("<Motion>", self._reset_idle_timer)   # Mouse movement
        self.bind_all("<Key>", self._reset_idle_timer)      # Keyboard input
        self.bind_all("<Button>", self._reset_idle_timer)   # Mouse clicks

        self.show_welcome_screen()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Start the idle checker loop
        self._check_idle_status()

        # NEW: Automatically check for updates on startup (silently)
        self.after(5000, lambda: self.app_updater.check_for_updates(silent=True)) # Check 5 seconds after startup


    def _reset_idle_timer(self, event=None):
        """Re sets the last activity time whenever a user interaction occurs, and reverts status bar if needed."""
        self.last_activity_time = time.time()
        if self.idle_music_status_displayed:
            self.update_status_message(self.original_status_message, level="info")
            self.idle_music_status_displayed = False
        # main_app_logger.debug("Idle timer reset.") # Uncomment for debugging idle detection


    def _check_idle_status(self):
        """
        Checks if the application has been idle for the configured time
        and displays music info in the status bar if enabled.
        """
        # Load fresh idle settings from app_settings to pick up changes from Settings module
        idle_settings = self.app_settings.get("idle_management", {})
        idle_enabled = idle_settings.get("enabled", False)
        idle_timeout_seconds = idle_settings.get("timeout_seconds", 60) # Default to 60s as per settings_manager

        if idle_enabled:
            current_idle_time = time.time() - self.last_activity_time
            # main_app_logger.debug(f"Current idle time: {current_idle_time:.0f}s")

            if current_idle_time >= idle_timeout_seconds:
                music_player_module = self.modules.get("player")
                if music_player_module and hasattr(music_player_module, 'is_playing') and music_player_module.is_playing():
                    # get_current_track_info is assumed to exist in MusicPlayerModule
                    track_info = music_player_module.get_current_track_info()
                    if track_info and not self.idle_music_status_displayed:
                        self.update_status_message(f"Playing: {track_info}", level="info")
                        self.idle_music_status_displayed = True
                elif self.idle_music_status_displayed: # If music was playing but stopped, or player gone
                    self.update_status_message(self.original_status_message, level="info")
                    self.idle_music_status_displayed = False
            elif self.idle_music_status_displayed: # Not idle anymore (activity reset the timer before check)
                self.update_status_message(self.original_status_message, level="info")
                self.idle_music_status_displayed = False
        elif self.idle_music_status_displayed: # Idle management disabled, but music status still displayed
            self.update_status_message(self.original_status_message, level="info")
            self.idle_music_status_displayed = False

        # Reschedule the check
        self.idle_timer_id = self.after(self.idle_check_interval_ms, self._check_idle_status)

    # NEW METHOD: To gracefully quit the Tkinter application, called by AppUpdater
    def quit_app(self):
        main_app_logger.info("Main application received quit_app command from updater. Exiting without saving/cleanup.")
        self.destroy()
        sys.exit(0)

    def _on_closing(self):
        # Cancel the idle timer to prevent errors if it tries to run after destroy
        if self.idle_timer_id:
            self.after_cancel(self.idle_timer_id)
            main_app_logger.debug("Idle timer cancelled.")

        if self.current_module_name and self.current_module_name in self.modules:
            current_module_instance = self.modules[self.current_module_name]
            if hasattr(current_module_instance, 'before_hide'):
                if not current_module_instance.before_hide(closing_app=True):
                    return

        if "player" in self.modules and self.modules["player"]:
            if hasattr(self.modules["player"], 'stop_music'): # Check for stop_music method
                self.modules["player"].stop_music()

        # Stop Discord RPC when closing
        if self.discord_rpc_manager:
            self.discord_rpc_manager.stop_rpc()

        # Only save settings and exit normally if not a quit initiated by the updater
        # The quit_app() method will bypass saving.
        settings_manager.save_settings(self.app_settings)
        main_app_logger.info("Application is closing. Settings saved.")
        self.destroy()
        sys.exit(0)

    def _clear_dynamic_menus(self):
        for menu, start_index in list(self.active_module_menus): # Use list() to iterate over a copy
            try:
                if menu.winfo_exists():
                    actual_end_index = None
                    try:
                        actual_end_index = menu.index(tk.END)
                    except tk.TclError:
                        pass # Menu might be empty, actual_end_index remains None

                    # Only proceed if actual_end_index is a valid number (not None or -1)
                    if actual_end_index is not None and actual_end_index >= start_index:
                        menu.delete(start_index, tk.END)
            except Exception as e: # Catch any other unexpected errors during menu clear
                main_app_logger.warning(f"Error clearing dynamic menu items for {menu} at start_index {start_index}: {e}")

        self.active_module_menus = []
        main_app_logger.debug("Dynamic menus cleared.")

    def _get_menu_start_index(self, menu):
        """Helper to get the correct starting index for adding new menu items."""
        try:
            end_index = menu.index(tk.END)

            # Empty menus can return None, or an index of -1 if completely empty
            if end_index is None or end_index == -1:
                return 0

            return end_index + 1

        except tk.TclError:
            return 0  # Menu is empty or invalid

    def _add_module_menus(self, module_instance):
        module_menus = None
        if hasattr(module_instance, 'get_menubar_commands'):
            module_menus = module_instance.get_menubar_commands()

        # Ensure module_menus is a dictionary before proceeding
        if not isinstance(module_menus, dict):
            main_app_logger.debug(f"Module {module_instance.__class__.__name__}'s get_menubar_commands() did not return a valid dictionary. Received: {module_menus}. Skipping menu addition.")
            return # Exit early if menu commands are not a dict

        # Handle file_commands
        file_commands = module_menus.get("file_commands")
        if file_commands is not None and isinstance(file_commands, list): # Explicitly check for list type
            current_menu = self.file_menu
            start_index = self._get_menu_start_index(current_menu)
            current_menu.add_separator()
            for item in file_commands:
                if item is None:
                    current_menu.add_separator()
                else:
                    label, command = item
                    current_menu.add_command(label=label, command=command)
            self.active_module_menus.append((current_menu, start_index))
            main_app_logger.debug(f"Added file commands for {self.current_module_name}.")

        # Handle edit_commands
        edit_commands = module_menus.get("edit_commands")
        if edit_commands is not None and isinstance(edit_commands, list): # Explicitly check for list type
            current_menu = self.edit_menu
            start_index = self._get_menu_start_index(current_menu)
            current_menu.add_separator()
            for item in edit_commands:
                if item is None:
                    current_menu.add_separator()
                else:
                    label, command = item
                    current_menu.add_command(label=label, command=command)
            self.active_module_menus.append((current_menu, start_index))
            main_app_logger.debug(f"Added edit commands for {self.current_module_name}.")

        # Handle help_commands
        help_commands = module_menus.get("help_commands")
        if help_commands is not None and isinstance(help_commands, list): # Explicitly check for list type
            current_menu = self.help_menu
            start_index = self._get_menu_start_index(current_menu)
            current_menu.add_separator()
            for item in help_commands:
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
        self._reset_idle_timer() # Reset idle timer on screen change

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

        # Use app_icon for the welcome image, if you have a separate logo.png, adjust path
        image_path = os.path.join(base_path, "resources", "app_icon.ico")
        if os.path.exists(image_path):
            try:
                # PIL can open ICO files, but it's better to convert to PNG if possible for consistent display
                pil_image = Image.open(image_path)
                pil_image = pil_image.resize((128, 128)) # Resize for welcome screen if needed
                self.welcome_image_tk = ImageTk.PhotoImage(pil_image)
                image_label = ttk.Label(welcome_frame, image=self.welcome_image_tk, style="TLabel")
                image_label.pack(pady=20)
                main_app_logger.info(f"Loaded and displayed image: {image_path}")
            except Exception as e:
                main_app_logger.error(f"Error loading welcome image '{image_path}': {e}")
                ttk.Label(welcome_frame, text="Error loading welcome image.", foreground="red", style="TLabel").pack(pady=20)
        else:
            main_app_logger.warning(f"Welcome image not found at: {image_path}")

        ttk.Label(welcome_frame, text="Welcome to Z's Multi Tool!", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(welcome_frame, text="Select an option from the left panel to begin.").pack()

        self.current_module_name = "welcome"
        self.update_status_message("Ready.", level="info")
        self.original_status_message = "Ready." # Reset original status message
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
                large_text=rpc_data.get("large_text", self.base_title),
                small_image=rpc_data.get("small_image"),
                small_text=rpc_data.get("small_text"),
                start=int(time.time()), # Reset activity timer
                buttons=rpc_buttons
            )


    def show_module(self, module_name):
        self._clear_dynamic_menus()
        self._reset_idle_timer() # Reset idle timer when explicitly switching modules

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


        # Logic to instantiate modules if not already created
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
            elif module_name == "file_encryptor_decryptor":
                self.modules["file_encryptor_decryptor"] = FileEncryptorDecryptorModule(self.right_panel, self.app_settings, self)
            elif module_name == "settings":
                self.modules["settings"] = SettingsModule(self.right_panel, self.app_settings, self)
            else:
                messagebox.showerror("Error", "Unknown module selected. This module is not implemented or has been removed.", parent=self.winfo_toplevel())
                self.show_welcome_screen() # Fallback to welcome screen on unknown module
                return

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

        # Update original_status_message to reflect the new module
        self.original_status_message = f"Loaded {display_module_name} Module."
        self.update_status_message(self.original_status_message, level="info")
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
                small_text=rpc_data.get("small_text", self.base_title), # Use base_title for app name
                start=int(time.time()),
                buttons=rpc_buttons
            )


    def set_window_title(self, title):
        self.title(title)

    def update_status_message(self, message, level='info'):
        # Only update the actual status bar if it's not currently displaying an idle music status
        # Or if the new message is an error/warning
        if not self.idle_music_status_displayed or level in ['error', 'warning']:
            self.status_bar.config(text=message)

            if level == 'error':
                self.status_bar.config(foreground=zyphria_styles.status_error_color)
            elif level == 'warning':
                self.status_bar.config(foreground=zyphria_styles.status_warning_color)
            else:
                self.status_bar.config(foreground=zyphria_styles.fg_white)

            # Update original_status_message only if it's not an idle message
            if not self.idle_music_status_displayed:
                self.original_status_message = message
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
            "welcome": "app_logo",
            "file_encryptor_decryptor": "encryption_icon",
        }
        return icon_map.get(module_name, "app_logo")

    def get_discord_rpc_status(self, module_name="welcome"):
        display_module_name = module_name.replace('_', ' ').title()
        if module_name == "welcome":
            return {
                "details": "Browsing Main Menu",
                "state": "Idle",
                "large_image": "app_logo",
                "large_text": self.base_title,
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
                "small_text": self.base_title,
            }

    def refresh_settings(self):
        """
        Reloads application settings and re-applies any configurations
        that need to be updated live. This also cascades to currently loaded modules.
        """
        # Reload the settings dictionary from file
        self.app_settings = settings_manager.load_settings()
        main_app_logger.info("Main application settings reloaded.")

        # Now, cascade this refresh to all active modules that have a refresh_settings_ui method
        for module_name, module_instance in self.modules.items():
            if hasattr(module_instance, 'refresh_settings_ui') and module_instance.winfo_exists():
                try:
                    module_instance.refresh_settings_ui()
                    main_app_logger.debug(f"Refreshed settings for {module_name}.")
                except Exception as e:
                    main_app_logger.error(f"Error refreshing settings for module {module_name}: {e}")

        # Apply theme immediately if changed
        current_theme = ttk.Style().theme_use()
        new_theme = self.app_settings.get("app_theme", settings_manager.DEFAULT_SETTINGS["app_theme"])
        if current_theme != new_theme:
            # We already warn user to restart for full theme application in settings_module
            # So, only partial application if possible, or just log.
            # No direct ttk.Style().theme_use(new_theme) here as it applies fully on next app start normally
            pass


if __name__ == "__main__":
    DISCORD_CLIENT_ID = "1491150039253258330"

    app = MultiAppScreen(discord_client_id=DISCORD_CLIENT_ID)
    app.mainloop()