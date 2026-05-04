# modules/settings_module.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import logging
import settings_manager
import webbrowser # Keep for Discord invite link
import time # For Discord RPC timestamps

settings_logger = logging.getLogger(__name__)

class SettingsModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance

        # --- Variables for Music Downloader Settings ---
        downloader_settings = self.app_settings.get("music_downloader", {})
        self.downloader_output_dir_var = tk.StringVar(value=downloader_settings.get("output_directory", os.path.expanduser("~/Downloads")))
        self.downloader_download_format_var = tk.StringVar(value=downloader_settings.get("download_format", "mp3"))
        self.downloader_download_type_var = tk.StringVar(value=downloader_settings.get("download_type", "video"))
        self.downloader_use_cookies_var = tk.BooleanVar(value=downloader_settings.get("use_cookies", False))
        self.downloader_cookies_file_var = tk.StringVar(value=downloader_settings.get("cookie_file_path", "")) # Use "cookie_file_path" key


        # --- Variable for Music Player Default Volume ---
        self.player_default_volume_var = tk.DoubleVar(value=self.app_settings.get("music_player_default_volume", 0.7))


        self.create_widgets()
        settings_logger.info("SettingsModule initialized.")
        self.main_app_instance.update_status_message("Settings module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update

    def create_widgets(self):
        ttk.Label(self, text="⚙️ Application Settings ⚙️", font=("Arial", 20, "bold")).pack(pady=20)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General Tab (Now also contains About/Contact info)
        general_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(general_tab, text="General")
        self._create_general_settings(general_tab)

        # Music Downloader Tab
        downloader_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(downloader_tab, text="Music Downloader")
        self._create_downloader_settings(downloader_tab)

        # Music Player Tab
        music_player_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(music_player_tab, text="Music Player")
        self._create_music_player_settings(music_player_tab)


        # Apply Button (Centralized)
        ttk.Button(self, text="Apply Settings", command=self.apply_settings).pack(pady=10)

    def _create_general_settings(self, parent_frame):
        # --- About the Hub / Contact Info ---
        about_frame = ttk.LabelFrame(parent_frame, text="About Zyphria Nexus Multi Use Tool")
        about_frame.pack(pady=10, padx=10, fill="x", expand=False)
        
        about_frame.grid_columnconfigure(1, weight=1) 

        ttk.Label(about_frame, text="Developed by:").grid(row=0, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(about_frame, text="Z (Discord: BugzNBlush)").grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(about_frame, text="Join the Community:").grid(row=1, column=0, padx=10, pady=2, sticky="w")
        self.discord_link_button = ttk.Button(about_frame, text="Discord Server", command=self._open_discord_invite)
        self.discord_link_button.grid(row=1, column=1, padx=5, pady=2, sticky="w")


    def _create_downloader_settings(self, parent_frame):
        # Output Directory
        output_frame = ttk.LabelFrame(parent_frame, text=" Download Location ")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Entry(output_frame, textvariable=self.downloader_output_dir_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        ttk.Button(output_frame, text="Browse", command=self._browse_downloader_output_directory).pack(side="left", padx=5, pady=5)

        # Default Format
        format_frame = ttk.LabelFrame(parent_frame, text=" Default Download Format ")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="MP3", variable=self.downloader_download_format_var, value="mp3").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="MP4", variable=self.downloader_download_format_var, value="mp4").pack(side=tk.LEFT, padx=5, pady=5)

        # Default Download Type
        type_frame = ttk.LabelFrame(parent_frame, text=" Default Download Type ")
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Radiobutton(type_frame, text="Single Video", variable=self.downloader_download_type_var, value="video").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(type_frame, text="Playlist", variable=self.downloader_download_type_var, value="playlist").pack(side=tk.LEFT, padx=5, pady=5)

        # Cookies Settings
        cookies_frame = ttk.LabelFrame(parent_frame, text=" Cookie Settings ")
        cookies_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Checkbutton(cookies_frame, text="Use Cookies for Downloading", variable=self.downloader_use_cookies_var).pack(anchor="w", padx=5, pady=2)

        ttk.Label(cookies_frame, text="Cookies File (cookies.txt):").pack(anchor="w", padx=5)
        ttk.Entry(cookies_frame, textvariable=self.downloader_cookies_file_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        ttk.Button(cookies_frame, text="Browse Cookies", command=self._browse_cookies_file).pack(side="left", padx=5, pady=5)

    # Removed: _create_discord_notifier_settings

    def _create_music_player_settings(self, parent_frame):
        # --- Default Volume ---
        volume_frame = ttk.LabelFrame(parent_frame, text=" Default Music Volume ")
        volume_frame.pack(pady=5, padx=5, fill="x")
        
        ttk.Label(volume_frame, text="Default Volume:").pack(side="left", padx=10, pady=5, sticky="w")
        self.player_volume_scale = ttk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.player_default_volume_var,
            length=200
        )
        self.player_volume_scale.pack(side="left", padx=5, pady=5, expand=True, fill="x")
        self.player_volume_scale.bind("<Motion>", self._update_volume_label_live) # Bind for live update
        self.player_volume_label = ttk.Label(volume_frame, text="0%") # Initialize label
        self.player_volume_label.pack(side="left", padx=10, pady=5, sticky="w")

        # Removed: Song Timezone Conversion Display

    def _browse_downloader_output_directory(self): 
        directory = filedialog.askdirectory(parent=self)
        if directory:
            self.downloader_output_dir_var.set(directory)
            self.main_app_instance.update_status_message(f"Downloader output directory set to: {directory}", level="info")

    def _browse_cookies_file(self):
        file_path = filedialog.askopenfilename(parent=self, title="Select Cookies File", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file_path:
            self.downloader_cookies_file_var.set(file_path)
            self.main_app_instance.update_status_message(f"Cookies file selected: {file_path}", level="info")

    def _open_discord_invite(self):
        """Opens the Discord invite link in the default web browser."""
        discord_invite_link = "https://discord.gg/vSX49HJMHS" # Use your actual invite link
        try:
            webbrowser.open_new_tab(discord_invite_link)
            settings_logger.info(f"Opened Discord invite link: {discord_invite_link}")
            self.main_app_instance.update_status_message("Opened Discord invite link.", level="info")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Discord invite link: {e}", parent=self.winfo_toplevel())
            settings_logger.error(f"Failed to open Discord invite link: {e}")
            self.main_app_instance.update_status_message(f"Failed to open Discord invite: {e}", level="error")

    def _update_volume_label_live(self, event=None):
        """Updates the volume percentage label as the slider is dragged."""
        self.player_volume_label.config(text=f"{int(self.player_default_volume_var.get() * 100)}%")


    def apply_settings(self):
        # Music Downloader Settings
        self.app_settings["music_downloader"] = {
            "output_directory": self.downloader_output_dir_var.get(),
            "download_format": self.downloader_download_format_var.get(),
            "download_type": self.downloader_download_type_var.get(),
            "use_cookies": self.downloader_use_cookies_var.get(),
            "cookies_file": self.downloader_cookies_file_var.get()
        }
        
        # Music Player Settings
        self.app_settings["music_player_default_volume"] = self.player_default_volume_var.get() 

        # Save all settings
        settings_manager.save_settings(self.app_settings)
        
        # Notify relevant modules to refresh their UI/logic with new settings
        self.main_app_instance.refresh_all_modules_settings()
        
        self.main_app_instance.update_status_message("Settings applied successfully!", level="info")
        settings_logger.info("Application settings applied.")

    def _load_current_settings_into_ui(self):
        """Loads the values from self.app_settings into the UI elements."""
        downloader_settings = self.app_settings.get("music_downloader", {})
        self.downloader_output_dir_var.set(downloader_settings.get("output_directory", os.path.expanduser("~/Downloads")))
        self.downloader_download_format_var.set(downloader_settings.get("download_format", "mp3"))
        self.downloader_download_type_var.set(downloader_settings.get("download_type", "video"))
        self.downloader_use_cookies_var.set(downloader_settings.get("use_cookies", False))
        self.downloader_cookies_file_var.set(downloader_settings.get("cookie_file_path", "")) # Use "cookie_file_path" key
        
        # Set music player volume
        self.player_default_volume_var.set(self.app_settings.get("music_player_default_volume", 0.7))
        self.player_volume_label.config(text=f"{int(self.player_default_volume_var.get() * 100)}%")
        
    def refresh_settings_ui(self):
        """Public method to refresh the UI from current app_settings."""
        self._load_current_settings_into_ui()
        settings_logger.debug("SettingsModule UI refreshed.")
        self.main_app_instance.update_status_message("Settings UI refreshed.", level="info")
        self._update_discord_rpc()


    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self):
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status()
            rpc_buttons = [
                {"label": "GitHub Repo", "url": "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool"},
                {"label": "Support Discord", "url": "https://discord.gg/YOUR_INVITE_CODE_HERE"}
            ]
            self.main_app_instance.discord_rpc_manager.update_activity(
                details=rpc_data["details"],
                state=rpc_data["state"],
                large_image=rpc_data["large_image"],
                large_text=rpc_data["large_text"],
                small_image=rpc_data["small_image"],
                small_text=rpc_data["small_text"],
                start=int(time.time()),
                buttons=rpc_buttons
            )

    def get_discord_rpc_status(self):
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="settings")
        
        details_text = "Adjusting Application Settings"
        state_text = "Customizing experience"
        
        return {
            "details": details_text,
            "state": state_text,
            "large_image": default_rpc.get("large_image", "settings_icon"),
            "large_text": "Settings Module",
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": "Zyphria Nexus",
        }
    
    def get_menubar_commands(self):
        return {
            "help_commands": [
                ("About Settings", self._show_about_dialog),
                ("Settings Help", self._show_help_dialog),
            ]
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About Settings",
            "Zyphria Nexus Settings Module v1.0\n"
            "Configure various aspects of the application.\n"
            "Developed by Z.",
            parent=self.winfo_toplevel()
        )

    def _show_help_dialog(self):
        help_text = (
            "Settings Help Guide:\n\n"
            "Use the tabs to navigate between different categories of settings.\n"
            "After making changes, click 'Apply Settings' to save them and update the application."
        )
        messagebox.showinfo(
            "Settings Help",
            help_text,
            parent=self.winfo_toplevel()
        )

    def before_hide(self, closing_app=False):
        settings_logger.info("SettingsModule before_hide executed.")
        return True