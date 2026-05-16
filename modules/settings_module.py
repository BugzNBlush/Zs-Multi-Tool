import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import logging
import settings_manager
import webbrowser # Keep for Discord invite link
import time # For Discord RPC timestamps

# CORRECTED IMPORT: Import styles directly from zyphria_nexus
from modules.zyphria_nexus import styles 

settings_module_logger = logging.getLogger(__name__)

class SettingsModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        # --- FIX: Ensure readable text color for readonly spinbox ---
        style = ttk.Style()
        # Set the foreground color for TSpinbox when it's in 'readonly' state
        # You can choose 'black', 'darkgray', or any color that contrasts with your theme's background
        style.map('TSpinbox', foreground=[('readonly', 'black')]) 
        # If the background of the readonly spinbox also becomes unreadable, uncomment and adjust this:
        # style.map('TSpinbox', fieldbackground=[('readonly', 'lightgray')])
        # --- END FIX ---

        # --- Variables for Music Downloader Settings ---
        self.downloader_output_dir_var = tk.StringVar()
        self.download_format_var = tk.StringVar()
        self.download_type_var = tk.StringVar()
        self.cookies_file_path_var = tk.StringVar()

        # --- Variables for Music Player Settings ---
        self.player_default_volume_scale_var = tk.DoubleVar() # Use DoubleVar for scale, 0.0-1.0
        self.last_played_dir_var = tk.StringVar()

        # --- Variables for Notes Module Settings ---
        self.notes_autosave_interval_var = tk.IntVar()
        self.notes_font_size_var = tk.IntVar()

        # --- Variables for Idle Management Settings (NEW) ---
        self.idle_enabled_var = tk.BooleanVar()
        self.idle_timeout_var = tk.IntVar()


        self.create_widgets()
        self._load_current_settings_to_ui() # Load settings into UI after widgets are created
        settings_module_logger.info("SettingsModule initialized.")
        self.main_app_instance.update_status_message("Settings module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update

    def create_widgets(self):
        ttk.Label(self, text="⚙️ Application Settings ⚙️", font=("Arial", 20, "bold")).pack(pady=20)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General Settings Tab
        self.general_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.general_tab, text="General")
        self._create_general_settings_widgets(self.general_tab) # Renamed for consistency

        # Music Downloader Tab
        self.downloader_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.downloader_tab, text="Music Downloader")
        self._create_downloader_settings_widgets(self.downloader_tab) # Renamed for consistency

        # Music Player Tab
        self.player_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.player_tab, text="Music Player")
        self._create_player_settings_widgets(self.player_tab) # Renamed for consistency

        # Notes Module Tab
        self.notes_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.notes_tab, text="Notes Module")
        self._create_notes_settings_widgets(self.notes_tab)

        # --- Idle Management Tab ---
        self.idle_management_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.idle_management_tab, text="Idle Management")
        self._create_idle_management_settings_widgets(self.idle_management_tab)


        # Apply Button (outside notebook for persistence)
        # Using _apply_settings to keep consistent with internal methods
        apply_button = ttk.Button(self, text="Apply Settings", command=self._apply_settings)
        apply_button.pack(pady=10)

    def _create_general_settings_widgets(self, parent_frame): # Renamed
        # Theme selection (Moved here from my previous general tab recommendation)
        theme_frame = ttk.LabelFrame(parent_frame, text=" Application Theme ")
        theme_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(theme_frame, text="Select Theme:").pack(side=tk.LEFT, padx=5, pady=2)
        
        self.theme_var = tk.StringVar()
        self.theme_combobox = ttk.Combobox(theme_frame, textvariable=self.theme_var, state="readonly")
        self.theme_combobox['values'] = styles.get_all_themes() # CORRECTED CALL
        self.theme_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        
        self.theme_combobox.bind("<<ComboboxSelected>>", self._on_theme_selected)


        # --- About the Hub / Contact Info (from your existing general settings) ---
        about_frame = ttk.LabelFrame(parent_frame, text="About Zyphria Nexus Multi Use Tool")
        about_frame.pack(pady=10, padx=10, fill="x", expand=False)
        
        about_frame.grid_columnconfigure(1, weight=1) 

        ttk.Label(about_frame, text="Developed by:").grid(row=0, column=0, padx=10, pady=2, sticky="w")
        ttk.Label(about_frame, text="Z (Discord: BugzNBlush)").grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(about_frame, text="Join the Community:").grid(row=1, column=0, padx=10, pady=2, sticky="w")
        self.discord_link_button = ttk.Button(about_frame, text="Discord Server", command=self._open_discord_invite)
        self.discord_link_button.grid(row=1, column=1, padx=5, pady=2, sticky="w")


    def _create_downloader_settings_widgets(self, parent_frame): # Renamed
        # Output Directory
        output_dir_frame = ttk.LabelFrame(parent_frame, text=" Download Location ")
        output_dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(output_dir_frame, textvariable=self.downloader_output_dir_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        ttk.Button(output_dir_frame, text="Browse", command=self._browse_downloader_output_dir).pack(side="left", padx=5, pady=5) # Renamed helper

        # Default Format
        format_frame = ttk.LabelFrame(parent_frame, text=" Default Download Format ")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="MP3", variable=self.download_format_var, value="mp3").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="MP4", variable=self.download_format_var, value="mp4").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="WEBM", variable=self.download_format_var, value="webm").pack(side=tk.LEFT, padx=5, pady=5) # Added WEBM
        ttk.Radiobutton(format_frame, text="Best Audio", variable=self.download_format_var, value="bestaudio").pack(side=tk.LEFT, padx=5, pady=5) # Added Best Audio

        # Default Download Type
        type_frame = ttk.LabelFrame(parent_frame, text=" Default Download Type ")
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Radiobutton(type_frame, text="Single Video", variable=self.download_type_var, value="single").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(type_frame, text="Playlist", variable=self.download_type_var, value="playlist").pack(side=tk.LEFT, padx=5, pady=5)

        # Cookies Settings
        cookies_frame = ttk.LabelFrame(parent_frame, text=" Cookie Settings ")
        cookies_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(cookies_frame, text="Cookies File (cookies.txt):").pack(anchor="w", padx=5)
        ttk.Entry(cookies_frame, textvariable=self.cookies_file_path_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        ttk.Button(cookies_frame, text="Browse Cookies", command=self._browse_cookies_file).pack(side="left", padx=5, pady=5)
        ttk.Label(cookies_frame, text="(.txt file exported from browser extension like 'Get cookies.txt LOCALLY')").pack(anchor=tk.W, padx=5, pady=2)


    def _create_player_settings_widgets(self, parent_frame): # Renamed
        # --- Default Volume ---
        volume_frame = ttk.LabelFrame(parent_frame, text=" Default Music Volume ")
        volume_frame.pack(pady=5, padx=5, fill="x")
        
        ttk.Label(volume_frame, text="Default Volume:").pack(side="left", padx=10, pady=5, anchor="w") 
        self.player_volume_scale = ttk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.player_default_volume_scale_var, # Use the scale specific variable
            length=200,
            command=self._update_volume_label_live # Link command directly to the scale
        )
        self.player_volume_scale.pack(side="left", padx=5, pady=5, expand=True, fill="x")
        self.player_volume_label = ttk.Label(volume_frame, text="0%") # Initialize label
        self.player_volume_label.pack(side="left", padx=10, pady=5, anchor="w")

        # Last Played Directory (Informational/Clear) (NEW from previous settings_manager structure)
        last_dir_frame = ttk.LabelFrame(parent_frame, text=" Last Played Directory ")
        last_dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(last_dir_frame, textvariable=self.last_played_dir_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        ttk.Button(last_dir_frame, text="Clear", command=self._clear_last_played_dir).pack(side=tk.LEFT, padx=5, pady=2)


    def _create_notes_settings_widgets(self, parent_frame): # NEW: Notes Settings Widgets
        # Auto-save interval
        autosave_frame = ttk.LabelFrame(parent_frame, text=" Auto-Save Settings ")
        autosave_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(autosave_frame, text="Auto-Save Interval (seconds):").pack(side=tk.LEFT, padx=5, pady=2)
        self.notes_autosave_spinbox = ttk.Spinbox(autosave_frame, from_=10, to_=300, increment=10, textvariable=self.notes_autosave_interval_var, state="readonly", width=8)
        self.notes_autosave_spinbox.pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Label(autosave_frame, text="(10-300)").pack(side=tk.LEFT, padx=5, pady=2)

        # Default Font Size
        font_size_frame = ttk.LabelFrame(parent_frame, text=" Font Settings ")
        font_size_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(font_size_frame, text="Default Font Size:").pack(side=tk.LEFT, padx=5, pady=2)
        self.notes_font_size_spinbox = ttk.Spinbox(font_size_frame, from_=8, to_=24, textvariable=self.notes_font_size_var, state="readonly", width=8)
        self.notes_font_size_spinbox.pack(side=tk.LEFT, padx=5, pady=2)


    def _create_idle_management_settings_widgets(self, parent_frame): # NEW: Idle Management Widgets
        # Enable/Disable Checkbox
        idle_enabled_frame = ttk.LabelFrame(parent_frame, text=" Enable Idle Management ")
        idle_enabled_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Checkbutton(idle_enabled_frame, text="Display Music Info in Status Bar when idle", variable=self.idle_enabled_var, command=self._toggle_idle_timeout_state).pack(anchor=tk.W, padx=5, pady=2)

        # Idle Timeout Duration
        idle_timeout_frame = ttk.LabelFrame(parent_frame, text=" Idle Timeout Duration ")
        idle_timeout_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(idle_timeout_frame, text="Idle Timeout (seconds):").pack(side=tk.LEFT, padx=5, pady=2)
        # CHANGED: 'from_' parameter is now 5, increment is 5
        self.idle_timeout_spinbox = ttk.Spinbox(idle_timeout_frame, from_=5, to_=1800, increment=5, textvariable=self.idle_timeout_var, state="readonly", width=8)
        self.idle_timeout_spinbox.pack(side=tk.LEFT, padx=5, pady=2)
        # CHANGED: Updated the explanatory text
        ttk.Label(idle_timeout_frame, text="(5 - 1800 seconds)").pack(side=tk.LEFT, padx=5, pady=2)

        # Initial state setup
        self._toggle_idle_timeout_state()


    def _toggle_idle_timeout_state(self):
        """Enables/disables the idle timeout spinbox based on the checkbox state."""
        if self.idle_enabled_var.get():
            self.idle_timeout_spinbox.config(state="readonly")
        else:
            self.idle_timeout_spinbox.config(state="disabled")

    def _browse_downloader_output_dir(self): # Renamed
        directory = filedialog.askdirectory(parent=self)
        if directory:
            self.downloader_output_dir_var.set(directory)
            settings_module_logger.info(f"Downloader output directory set to: {directory}")
            self.main_app_instance.update_status_message(f"Downloader output directory set to: {directory}", level="info")

    def _browse_cookies_file(self):
        file_path = filedialog.askopenfilename(parent=self, title="Select cookies.txt file", filetypes=[("Text files", "*.txt")])
        if file_path:
            self.cookies_file_path_var.set(file_path)
            settings_module_logger.info(f"Cookies file path set to: {file_path}")
            self.main_app_instance.update_status_message(f"Cookies file path set to: {file_path}", level="info")

    def _open_discord_invite(self):
        """Opens the Discord invite link in the default web browser."""
        # Use your actual invite link
        discord_invite_link = "https://discord.gg/vSX49HJMHS" 
        try:
            webbrowser.open_new_tab(discord_invite_link)
            settings_module_logger.info(f"Opened Discord invite link: {discord_invite_link}")
            self.main_app_instance.update_status_message("Opened Discord invite link.", level="info")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Discord invite link: {e}", parent=self.winfo_toplevel())
            settings_module_logger.error(f"Failed to open Discord invite link: {e}")
            self.main_app_instance.update_status_message(f"Failed to open Discord invite: {e}", level="error")

    def _update_volume_label_live(self, value): # Takes value from scale directly
        """Updates the volume percentage label as the slider is dragged."""
        # Value comes as string from tkinter scale command, convert to float
        volume = float(value)
        self.player_volume_label.config(text=f"{int(volume * 100)}%")

    def _clear_last_played_dir(self):
        self.last_played_dir_var.set("")
        settings_module_logger.info("Last played directory cleared.")
        self.main_app_instance.update_status_message("Last played directory setting cleared.", level="info")


    def _apply_settings(self): # Renamed for consistency
        # General Settings (Theme is handled by _on_theme_selected for immediate feedback)
        # However, we need to save the theme choice here too in case user doesn't interact with combobox again.
        self.app_settings["app_theme"] = self.theme_var.get()

        # Music Downloader Settings
        self.app_settings["music_downloader"] = {
            "output_directory": self.downloader_output_dir_var.get(),
            "download_format": self.download_format_var.get(),
            "download_type": self.download_type_var.get(),
            "use_cookies": bool(self.cookies_file_path_var.get()), # Infer use_cookies from path presence
            "cookie_file_path": self.cookies_file_path_var.get()
        }
        
        # Music Player Settings
        self.app_settings["music_player"]["default_volume"] = self.player_default_volume_scale_var.get() 
        self.app_settings["music_player"]["last_played_directory"] = self.last_played_dir_var.get()

        # Notes Module Settings
        self.app_settings["notes_module"]["auto_save_interval"] = self.notes_autosave_interval_var.get()
        self.app_settings["notes_module"]["default_font_size"] = self.notes_font_size_var.get()

        # --- Idle Management Settings ---
        self.app_settings["idle_management"]["enabled"] = self.idle_enabled_var.get()
        self.app_settings["idle_management"]["timeout_seconds"] = self.idle_timeout_var.get()


        settings_manager.save_settings(self.app_settings)
        settings_module_logger.info("Settings applied and saved.")
        self.main_app_instance.update_status_message("Settings applied successfully!", level="info")
        
        # Notify main_app to refresh its internal settings (e.g., for idle timeout)
        self.main_app_instance.refresh_settings()


    def _on_theme_selected(self, event):
        selected_theme = self.theme_var.get()
        # Always update and save theme immediately, but inform user about restart
        self.main_app_instance.app_settings["app_theme"] = selected_theme
        settings_manager.save_settings(self.main_app_instance.app_settings) # Save immediately
        messagebox.showinfo("Theme Change", f"Theme set to '{selected_theme}'. Restart the application to fully apply the new theme.", parent=self)
        settings_module_logger.info(f"Theme changed to {selected_theme}. Restart required.")
        self.main_app_instance.update_status_message(f"Theme changed to {selected_theme}. Restart required.", level="info")
        
    def _load_current_settings_to_ui(self): # Renamed for consistency
        """Loads the values from self.app_settings into the UI elements."""
        # General
        # CORRECTED: Use settings_manager.DEFAULT_SETTINGS["app_theme"] for consistency
        self.theme_var.set(self.app_settings.get("app_theme", settings_manager.DEFAULT_SETTINGS["app_theme"])) 

        # Music Downloader
        # CORRECTED: Use settings_manager.DEFAULT_SETTINGS directly
        downloader_settings = self.app_settings.get("music_downloader", settings_manager.DEFAULT_SETTINGS["music_downloader"])
        self.downloader_output_dir_var.set(downloader_settings.get("output_directory", ""))
        self.download_format_var.set(downloader_settings.get("download_format", "mp3"))
        self.download_type_var.set(downloader_settings.get("download_type", "single"))
        self.cookies_file_path_var.set(downloader_settings.get("cookie_file_path", ""))
        
        # Music Player
        # CORRECTED: Use settings_manager.DEFAULT_SETTINGS directly
        player_settings = self.app_settings.get("music_player", settings_manager.DEFAULT_SETTINGS["music_player"])
        self.player_default_volume_scale_var.set(player_settings.get("default_volume", 0.7)) # This is already 0.0-1.0
        self._update_volume_label_live(self.player_default_volume_scale_var.get()) # Update the label next to the slider
        self.last_played_dir_var.set(player_settings.get("last_played_directory", ""))

        # Notes Module
        # CORRECTED: Use settings_manager.DEFAULT_SETTINGS directly
        notes_settings = self.app_settings.get("notes_module", settings_manager.DEFAULT_SETTINGS["notes_module"])
        self.notes_autosave_interval_var.set(notes_settings.get("auto_save_interval", 60))
        self.notes_font_size_var.set(notes_settings.get("default_font_size", 12))

        # --- Idle Management ---
        # CORRECTED: Use settings_manager.DEFAULT_SETTINGS directly
        idle_settings = self.app_settings.get("idle_management", settings_manager.DEFAULT_SETTINGS["idle_management"])
        self.idle_enabled_var.set(idle_settings.get("enabled", False))
        # Updated default to 60 as per settings_manager
        self.idle_timeout_var.set(idle_settings.get("timeout_seconds", 60)) 
        self._toggle_idle_timeout_state() # Ensure spinbox state is correct
        
    def refresh_settings_ui(self):
        """Public method to refresh the UI from current app_settings."""
        self._load_current_settings_to_ui()
        settings_module_logger.debug("SettingsModule UI refreshed.")
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
                ("General Settings Help", self._show_general_help_dialog),
                ("Music Downloader Settings Help", self._show_downloader_help_dialog),
                ("Music Player Settings Help", self._show_player_help_dialog),
                ("Notes Module Settings Help", self._show_notes_help_dialog),
                ("Idle Management Settings Help", self._show_idle_management_help_dialog), # NEW
            ]
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About Settings",
            "This module allows you to customize various aspects of the Zyphria Nexus Multi Use Tool.",
            parent=self.winfo_toplevel()
        )
        settings_module_logger.info("About dialog shown for Settings.")

    def _show_general_help_dialog(self):
        messagebox.showinfo(
            "General Settings Help",
            "In the General tab, you can select the overall visual theme for the application.\n\n"
            "Note: Theme changes often require a restart of the application to take full effect.",
            parent=self.winfo_toplevel()
        )
        settings_module_logger.info("General Settings help dialog shown.")

    def _show_downloader_help_dialog(self):
        messagebox.showinfo(
            "Music Downloader Settings Help",
            "Customize how music and videos are downloaded:\n\n"
            "- **Download Location**: Choose where downloaded files are saved.\n"
            "- **Default Download Format**: Select MP3 for audio, MP4/WEBM for video, or Best Audio for highest quality audio.\n"
            "- **Default Download Type**: Specify if you typically download single videos or entire playlists.\n"
            "- **Cookies File**: Provide a path to a browser cookies.txt file to download private or age-restricted content. Use a browser extension to export.",
            parent=self.winfo_toplevel()
        )
        settings_module_logger.info("Music Downloader Settings help dialog shown.")

    def _show_player_help_dialog(self):
        messagebox.showinfo(
            "Music Player Settings Help",
            "Configure your music playback experience:\n\n"
            "- **Default Volume**: Set the starting volume level for the music player.\n"
            "- **Last Played Directory**: (Informational) Shows the last folder from which music was loaded. You can clear this if you wish.",
            parent=self.winfo_toplevel()
        )
        settings_module_logger.info("Music Player Settings help dialog shown.")

    def _show_notes_help_dialog(self):
        messagebox.showinfo(
            "Notes Module Settings Help",
            "Customize the Notes module behavior:\n\n"
            "- **Auto-Save Interval**: Set how frequently (in seconds) your notes are automatically saved.\n"
            "- **Default Font Size**: Choose the default font size for your notes.",
            parent=self.winfo_toplevel()
        )
        settings_module_logger.info("Notes Module Settings help dialog shown.")
    
    def _show_idle_management_help_dialog(self):
        messagebox.showinfo(
            "Idle Management Settings Help",
            "Configure automatic display of music information when idle:\n\n" # Updated text
            "- **Display Music Info in Status Bar when idle**: Enable or disable this feature.\n" # Updated text
            "- **Idle Timeout (seconds)**: Set the duration of inactivity (in seconds) after which the application will automatically display the current music track in the status bar (minimum 5 seconds).", # Updated text
            parent=self.winfo_toplevel()
        )
        settings_module_logger.info("Idle Management Settings help dialog shown.")

    def before_hide(self, closing_app=False):
        # Save settings on hide if user forgot to click apply
        settings_manager.save_settings(self.app_settings)
        settings_module_logger.info("Settings saved implicitly via before_hide.")
        # When leaving settings, ensure main_app refreshes its context for current settings
        self.main_app_instance.refresh_settings() 
        return True