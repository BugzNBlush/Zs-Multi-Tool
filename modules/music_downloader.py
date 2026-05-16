# modules/music_downloader.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import threading
import logging
import json # Used for robust deepcopy of ydl_opts
import re
import sys # Import sys for checking PyInstaller bundle environment
import time # Import time for Discord RPC timestamps
import settings_manager # Added to handle saving settings

# Dynamically import youtube_dl or yt-dlp
try:
    import yt_dlp as youtube_dl
except ImportError:
    try:
        import youtube_dl
    except ImportError:
        youtube_dl = None

downloader_logger = logging.getLogger(__name__)

class MusicDownloaderModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        self.youtube_dl_present = youtube_dl is not None
        if not self.youtube_dl_present:
            messagebox.showerror("Dependency Error", "yt-dlp or youtube-dl not found. Please install it using 'pip install yt-dlp' or 'pip install youtube-dl'.", parent=self)
            self.main_app_instance.update_status_message("Error: yt-dlp/youtube-dl not installed.", level="error")
            downloader_logger.critical("yt-dlp/youtube-dl library is not installed.")
        
        # Determine FFmpeg bin directory (should contain both ffmpeg.exe and ffprobe.exe)
        self.ffmpeg_bin_dir = self._determine_ffmpeg_path()
        
        if self.ffmpeg_bin_dir == 'ffmpeg': # This means it's relying on PATH, might fail for exe
            downloader_logger.warning("FFmpeg binaries not found locally. Download functionality may be limited or fail if FFmpeg is not in system PATH.")
        else:
            downloader_logger.info(f"FFmpeg binaries found in: {self.ffmpeg_bin_dir}")
        
        # Initialize Tkinter StringVars for UI elements with current settings or defaults
        self.url_var = tk.StringVar()
        downloader_settings = self.app_settings.get("music_downloader", settings_manager.DEFAULT_SETTINGS["music_downloader"])
        self.output_dir_var = tk.StringVar(value=downloader_settings.get("output_directory", settings_manager.DEFAULT_SETTINGS["music_downloader"]["output_directory"]))
        self.download_type_var = tk.StringVar(value=downloader_settings.get("download_type", settings_manager.DEFAULT_SETTINGS["music_downloader"]["download_type"])) 
        self.format_var = tk.StringVar(value=downloader_settings.get("download_format", settings_manager.DEFAULT_SETTINGS["music_downloader"]["download_format"])) 
        self.cookie_file_var = tk.StringVar(value=downloader_settings.get("cookie_file_path", settings_manager.DEFAULT_SETTINGS["music_downloader"]["cookie_file_path"])) 

        self.create_widgets()
        # load_settings is typically called after create_widgets to populate UI, 
        # but initial values are already set via StringVar init
        self.main_app_instance.update_status_message("Music Downloader module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update after widget creation

    def _determine_ffmpeg_path(self):
        possible_bin_dirs = []

        # 1. Check if running inside a PyInstaller bundle (sys._MEIPASS)
        # This is where PyInstaller unpacks temporary files.
        if hasattr(sys, '_MEIPASS'):
            bundle_bin_dir = os.path.join(sys._MEIPASS, 'bin')
            possible_bin_dirs.append(bundle_bin_dir)
            
        # 2. Check the 'bin' folder relative to the current script (development environment)
        # Assuming 'modules/music_downloader.py' is in 'project_root/modules/'
        # So 'bin' folder is 'project_root/bin/'
        dev_bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
        possible_bin_dirs.append(dev_bin_dir)
        
        # Iterate through possible directories and check for both ffmpeg.exe and ffprobe.exe
        for bin_dir in possible_bin_dirs:
            ffmpeg_exe = os.path.join(bin_dir, 'ffmpeg.exe')
            ffprobe_exe = os.path.join(bin_dir, 'ffprobe.exe')
            if os.path.isdir(bin_dir) and os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
                downloader_logger.info(f"Found FFmpeg binaries in: {bin_dir}")
                return bin_dir # Return the directory path if both are found

        # 3. Fallback to just 'ffmpeg' which relies on system PATH or yt-dlp's internal search logic
        downloader_logger.warning("FFmpeg binaries (ffmpeg.exe and ffprobe.exe) not found in expected bundled or development locations. Relying on system PATH or default yt-dlp search for 'ffmpeg'.")
        return 'ffmpeg' # This string tells yt-dlp to try finding it via PATH

    def create_widgets(self):
        ttk.Label(self, text="🎵 Music Downloader 🎵", font=("Arial", 20, "bold")).pack(pady=20)

        # URL Entry
        url_frame = ttk.LabelFrame(self, text=" YouTube URL ")
        url_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Entry(url_frame, textvariable=self.url_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Download Type Selector
        # Note: self.download_type_var is initialized in __init__
        ttk.Radiobutton(url_frame, text="Single Video", variable=self.download_type_var, value="video") \
           .pack(side=tk.LEFT, padx=(10, 2), pady=5)
        ttk.Radiobutton(url_frame, text="Playlist", variable=self.download_type_var, value="playlist") \
           .pack(side=tk.LEFT, padx=(2, 5), pady=5)

        # Download Button
        self.download_button = ttk.Button(url_frame, text="Download", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Output Directory
        output_frame = ttk.LabelFrame(self, text=" Output Directory ")
        output_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Entry(output_frame, textvariable=self.output_dir_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.LEFT, padx=5, pady=5)

        # Cookie File Selection
        cookie_frame = ttk.LabelFrame(self, text=" Cookie File (Optional) ")
        cookie_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Entry(cookie_frame, textvariable=self.cookie_file_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        ttk.Button(cookie_frame, text="Browse Cookies", command=self.browse_cookie_file).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(cookie_frame, text="Clear", command=lambda: self.cookie_file_var.set("")).pack(side=tk.LEFT, padx=(0,5), pady=5) # Clear button

        # Format Selector (Audio/Video formats)
        format_frame = ttk.LabelFrame(self, text=" Format ")
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        # Note: self.format_var is initialized in __init__
        ttk.Radiobutton(format_frame, text="MP3", variable=self.format_var, value="mp3").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="MP4", variable=self.format_var, value="mp4").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="WEBM", variable=self.format_var, value="webm").pack(side=tk.LEFT, padx=5, pady=5) # ADDED WEBM
        ttk.Radiobutton(format_frame, text="Best Audio", variable=self.format_var, value="bestaudio").pack(side=tk.LEFT, padx=5, pady=5) # ADDED BEST AUDIO


        # Download Log/Progress
        log_frame = ttk.LabelFrame(self, text=" Download Log ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED, bg="#2A2A2A", fg="#FFFFFF", relief="flat")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        self.download_status_label = ttk.Label(log_frame, text="Status: Idle")
        self.download_status_label.pack(fill=tk.X, padx=5, pady=2)


    def load_settings(self):
        # Retrieve music_downloader settings, falling back to DEFAULT_SETTINGS structure
        downloader_settings = self.app_settings.get("music_downloader", settings_manager.DEFAULT_SETTINGS["music_downloader"])
        
        self.output_dir_var.set(downloader_settings.get("output_directory", settings_manager.DEFAULT_SETTINGS["music_downloader"]["output_directory"]))
        
        # Validate format and type against known values, falling back to default
        default_format = downloader_settings.get("download_format", settings_manager.DEFAULT_SETTINGS["music_downloader"]["download_format"])
        if default_format not in ["mp3", "mp4", "webm", "bestaudio"]: default_format = "mp3" # Ensure robust fallback
        self.format_var.set(default_format)

        default_type = downloader_settings.get("download_type", settings_manager.DEFAULT_SETTINGS["music_downloader"]["download_type"])
        if default_type not in ["video", "playlist"]: default_type = "video" # Ensure robust fallback to "video"
        self.download_type_var.set(default_type)

        self.cookie_file_var.set(downloader_settings.get("cookie_file_path", settings_manager.DEFAULT_SETTINGS["music_downloader"]["cookie_file_path"]))

        self.main_app_instance.update_status_message("Music Downloader settings loaded.", level="info")
        downloader_logger.info("Music Downloader settings loaded.")


    def save_settings(self):
        # This is primarily called from browse_output_dir and browse_cookie_file to save immediate changes.
        # Other settings (format, type) are also updated here for consistency, as they are part of the module's state.
        if "music_downloader" not in self.app_settings: self.app_settings["music_downloader"] = {}
        self.app_settings["music_downloader"]["output_directory"] = self.output_dir_var.get()
        self.app_settings["music_downloader"]["cookie_file_path"] = self.cookie_file_var.get()
        self.app_settings["music_downloader"]["download_format"] = self.format_var.get()
        self.app_settings["music_downloader"]["download_type"] = self.download_type_var.get()
        
        settings_manager.save_settings(self.app_settings)
        self.main_app_instance.update_status_message("Music Downloader settings saved.", level="info")
        downloader_logger.info("Music Downloader settings saved.")


    def browse_output_dir(self):
        directory = filedialog.askdirectory(parent=self, initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
            self.save_settings() 
            self.main_app_instance.update_status_message(f"Output directory set to: {directory}", level="info")
            downloader_logger.info(f"Output directory set to: {directory}")

    def browse_cookie_file(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Select Cookies File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.cookie_file_var.get()) if self.cookie_file_var.get() else os.path.expanduser("~")
        )
        if file_path:
            self.cookie_file_var.set(file_path)
            self.save_settings() 
            self.main_app_instance.update_status_message(f"Cookie file set to: {file_path}", level="info")
            downloader_logger.info(f"Cookie file set to: {file_path}")
        else:
            self.main_app_instance.update_status_message("Cookie file selection cancelled.", level="info")
            downloader_logger.info("Cookie file selection cancelled.")


    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        downloader_logger.debug(message)

    def start_download(self):
        if not self.youtube_dl_present:
            self.log_message("Error: yt-dlp or youtube-dl is not installed.")
            self.main_app_instance.update_status_message("Download failed: Dependency missing.", level="error")
            return

        url = self.url_var.get().strip()
        output_dir = self.output_dir_var.get()
        download_format = self.format_var.get()
        download_type = self.download_type_var.get()
        cookie_file_path = self.cookie_file_var.get() 

        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube URL.", parent=self)
            self.main_app_instance.update_status_message("Download failed: No URL provided.", level="warning")
            return
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("Input Error", "Please select a valid output directory.", parent=self)
            self.main_app_instance.update_status_message("Download failed: Invalid output directory.", level="warning")
            return
        
        if self.ffmpeg_bin_dir == 'ffmpeg': 
            if not messagebox.askokcancel(
                "FFmpeg Warning",
                "FFmpeg binaries (ffmpeg.exe and ffprobe.exe) were not found locally.\n"
                "The downloader will attempt to use FFmpeg from your system's PATH.\n"
                "If downloads fail, please ensure FFmpeg is installed and added to PATH, or place its binaries in the 'bin' folder next to the app.\n\n"
                "Do you wish to continue?",
                parent=self.winfo_toplevel()
            ):
                self.main_app_instance.update_status_message("Download cancelled due to FFmpeg warning.", level="warning")
                return

        if cookie_file_path: 
            if not os.path.exists(cookie_file_path):
                messagebox.showwarning("Cookie File Error", f"The specified cookie file does not exist: {cookie_file_path}", parent=self)
                self.main_app_instance.update_status_message("Download failed: Cookie file not found.", level="warning")
                return
            
        self.log_message(f"Starting download of {download_type} as {download_format} from: {url}")
        if cookie_file_path: 
            self.log_message(f"Using cookie file: {cookie_file_path}")
        self.download_status_label.config(text="Status: Downloading...")
        self.main_app_instance.update_status_message("Download in progress...", level="info")
        
        self.download_button.config(state=tk.DISABLED)
        
        download_thread = threading.Thread(target=self._download_worker, args=(url, output_dir, download_format, download_type, cookie_file_path))
        download_thread.daemon = True
        download_thread.start()
        self._update_discord_rpc() 

    def _sanitize_filename(self, filename):
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        return filename.strip()

    def _download_worker(self, url, output_dir, download_format, download_type, cookie_file_path):
        try:
            self.log_message("Fetching video/playlist info...")
            
            # --- Base yt-dlp Options ---
            # Exclude progress_hooks from this base dictionary as it's not JSON serializable
            base_ydl_opts_json_safe = {
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'noplaylist': False, 
                'quiet': True,          
                'no_warnings': True,    
                'ffmpeg_location': self.ffmpeg_bin_dir 
            }

            # Use json.loads(json.dumps()) for a robust deep copy for the JSON-safe parts.
            # Then add the non-JSON-serializable 'progress_hooks' separately.
            ydl_opts = json.loads(json.dumps(base_ydl_opts_json_safe))
            ydl_opts['progress_hooks'] = [self._progress_hook] # Add the hook back

            ydl_info_opts = json.loads(json.dumps(base_ydl_opts_json_safe))
            ydl_info_opts['progress_hooks'] = [self._progress_hook] # Add the hook back for info extraction as well
            
            # Add cookiefile option if provided and valid
            if cookie_file_path and os.path.exists(cookie_file_path):
                ydl_opts['cookiefile'] = cookie_file_path
                ydl_info_opts['cookiefile'] = cookie_file_path # Also pass cookies for info extraction
                downloader_logger.info(f"yt-dlp will use cookie file: {cookie_file_path}")
            else:
                downloader_logger.info("No valid cookie file specified or found.")


            # Configure format-specific options
            if download_format == "mp3":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.mp3')
            elif download_format == "mp4":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferredformat': 'mp4',
                }, {
                    'key': 'FFmpegMetadata',
                }]
                ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.mp4')
            elif download_format == "webm": 
                ydl_opts['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo+bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferredformat': 'webm',
                }, {
                    'key': 'FFmpegMetadata',
                }]
                ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.webm')
            elif download_format == "bestaudio": 
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3', # default to mp3 for "bestaudio" if no preferred provided by ydlp
                    'preferredquality': '0', # best quality
                }]
                ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.mp3') # default to mp3 extension

            # Handle playlist vs single video downloads
            if download_type == "playlist":
                ydl_opts['noplaylist'] = False # Ensure this is false for playlists

                # First, get playlist info to determine the subfolder name
                with youtube_dl.YoutubeDL(ydl_info_opts) as ydl_info: 
                    info_dict = ydl_info.extract_info(url, download=False)
                    playlist_title = info_dict.get('title', 'Unknown Playlist')
                    sanitized_playlist_title = self._sanitize_filename(playlist_title)
                    final_playlist_dir = os.path.join(output_dir, sanitized_playlist_title)
                    os.makedirs(final_playlist_dir, exist_ok=True)
                    self.log_message(f"Detected Playlist: {playlist_title} ({len(info_dict.get('entries', []))} videos)")
                    self.log_message(f"Downloading to: {final_playlist_dir}")

                # Adjust outtmpl for playlist to include playlist_index and use the created subfolder
                if download_format in ["mp3", "bestaudio"]: # Use .mp3 for bestaudio by default
                    ydl_opts['outtmpl'] = os.path.join(final_playlist_dir, '%(playlist_index)s - %(title)s.mp3')
                elif download_format == "mp4":
                    ydl_opts['outtmpl'] = os.path.join(final_playlist_dir, '%(playlist_index)s - %(title)s.mp4')
                elif download_format == "webm":
                    ydl_opts['outtmpl'] = os.path.join(final_playlist_dir, '%(playlist_index)s - %(title)s.webm')
                
                with youtube_dl.YoutubeDL(ydl_opts) as ydl_final: 
                    ydl_final.download([url])

            else: # Single video
                ydl_opts['noplaylist'] = True # Ensure this is true for single videos
                
                with youtube_dl.YoutubeDL(ydl_opts) as ydl_final: 
                    info_dict = ydl_final.extract_info(url, download=False) # Extract info first to log title
                    video_title = info_dict.get('title', 'Unknown Video')
                    self.log_message(f"Detected Video: {video_title}")
                    ydl_final.download([url])

            self.log_message("Download finished successfully!")
            self.download_status_label.config(text="Status: Complete", foreground="green")
            self.main_app_instance.update_status_message(f"Download complete for {url}", level="info")

        except youtube_dl.DownloadError as e:
            error_message = f"Download Error: {e}"
            self.log_message(error_message)
            self.download_status_label.config(text="Status: Failed", foreground="red")
            self.main_app_instance.update_status_message(f"Download failed: {e}", level="error")
            downloader_logger.error(error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            self.log_message(error_message)
            self.download_status_label.config(text="Status: Failed", foreground="red")
            self.main_app_instance.update_status_message(f"Download failed: {e}", level="error")
            downloader_logger.error(error_message)
        finally:
            self.download_button.config(state=tk.NORMAL)
            self._update_discord_rpc() 

    def _progress_hook(self, d):
        def update_ui_safe():
            if d['status'] == 'downloading':
                p_str = d.get('_percent_str', d.get('percent_str', 'N/A')).replace('\x1b[0K', '').strip()
                e_str = d.get('_eta_str', d.get('eta_str', 'N/A')).replace('\x1b[0K', '').strip()
                s_str = d.get('_speed_str', d.get('speed_str', 'N/A')).replace('\x1b[0K', '').strip()
                
                status_message = f"Downloading: {p_str} at {s_str} ETA {e_str}"
                self.download_status_label.config(text=f"Status: {status_message}")
                self.main_app_instance.update_status_message(status_message, level="info")
            elif d['status'] == 'finished':
                filename = d.get('filename', 'Unknown File')
                self.download_status_label.config(text=f"Status: Post-processing '{filename}'...", foreground="orange")
                self.main_app_instance.update_status_message(f"Post-processing: {filename}", level="info")
            
            self._update_discord_rpc()

        self.after(0, update_ui_safe) # Schedule update_ui_safe to run on the main Tkinter thread

    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self):
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status()
            # Generic buttons can be passed from main_app or defined here
            rpc_buttons = [
                {"label": "GitHub Repo", "url": "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool"},
                {"label": "Support Discord", "url": "https://discord.gg/vSX49HJMHS"}
            ]
            self.main_app_instance.discord_rpc_manager.update_activity(
                details=rpc_data["details"],
                state=rpc_data["state"],
                large_image=rpc_data["large_image"],
                large_text=rpc_data["large_text"],
                small_image=rpc_data.get("small_image", "app_logo"), 
                small_text=self.main_app_instance.base_title, # Use main_app's base_title for consistency
                start=int(time.time()),
                buttons=rpc_buttons
            )

    def get_discord_rpc_status(self):
        # Retrieve default RPC data from main_app_instance
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="downloader")
        
        details_text = "Browsing Music Downloader"
        state_text = "Idle"

        if self.download_button["state"] == tk.DISABLED: # Check if download is active
            details_text = "Downloading Music"
            # Get only the text content without "Status: " prefix
            current_status = self.download_status_label.cget("text")
            if current_status.startswith("Status: "):
                state_text = current_status[len("Status: "):]
            else:
                state_text = current_status
            if state_text == "Idle": # If it's disabled but status is "Idle", it means it just started
                state_text = "Starting download..."


        return {
            "details": details_text,
            "state": state_text,
            "large_image": default_rpc.get("large_image", "music_downloader_icon"),
            "large_text": "Music Downloader",
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": self.main_app_instance.base_title, # Use main_app's base_title for consistency
        }
    
    def get_menubar_commands(self):
        """
        Returns a dictionary of commands specific to this module for the menubar.
        """
        return {
            "help_commands": [
                ("About Music Downloader", self.show_about_dialog),
                ("Music Downloader Help", self.show_help_dialog),
            ]
        }

    def show_about_dialog(self):
        messagebox.showinfo(
            "About Music Downloader",
            f"{settings_manager.APP_NAME} Music Downloader v1.0\n" # Use APP_NAME for consistency
            "Download audio from various online sources (e.g., YouTube).\n"
            "Powered by yt-dlp and FFmpeg.\n"
            "Developed by Z.\n\n"
            "Note: Requires yt-dlp and FFmpeg to function correctly.",
            parent=self.winfo_toplevel()
        )
        downloader_logger.info("About dialog shown for Music Downloader.")

    def show_help_dialog(self):
        help_text = (
            "Music Downloader Help Guide:\n\n"
            "1. Enter a YouTube video or playlist URL.\n"
            "2. Select 'Single Video' or 'Playlist' download type.\n"
            "3. Choose the desired format (MP3, MP4, WEBM, or Best Audio).\n" # Updated help text
            "4. Use 'Browse' to select an output directory.\n"
            "5. Use 'Browse Cookies' to optionally select a Netscape-format cookies file for sites requiring login.\n"
            "6. Click 'Download' to start. Progress will be shown in the log.\n\n"
            "Note: Ensure yt-dlp is installed (`pip install yt-dlp`) and FFmpeg is accessible (in PATH or in the 'bin' folder next to the app)."
        )
        messagebox.showinfo(
            "Music Downloader Help",
            help_text,
            parent=self.winfo_toplevel()
        )
        downloader_logger.info("Help dialog shown for Music Downloader.")

    def refresh_settings_ui(self):
        # Retrieve music_downloader settings, falling back to DEFAULT_SETTINGS structure
        downloader_settings = self.app_settings.get("music_downloader", settings_manager.DEFAULT_SETTINGS["music_downloader"])
        
        self.output_dir_var.set(downloader_settings.get("output_directory", settings_manager.DEFAULT_SETTINGS["music_downloader"]["output_directory"]))
        
        # Validate format and type against known values, falling back to default
        default_format = downloader_settings.get("download_format", settings_manager.DEFAULT_SETTINGS["music_downloader"]["download_format"])
        if default_format not in ["mp3", "mp4", "webm", "bestaudio"]: default_format = "mp3" # Ensure robust fallback
        self.format_var.set(default_format)

        default_type = downloader_settings.get("download_type", settings_manager.DEFAULT_SETTINGS["music_downloader"]["download_type"])
        if default_type not in ["video", "playlist"]: default_type = "video" # Ensure robust fallback
        self.download_type_var.set(default_type)

        self.cookie_file_var.set(downloader_settings.get("cookie_file_path", settings_manager.DEFAULT_SETTINGS["music_downloader"]["cookie_file_path"]))
        
        self.main_app_instance.update_status_message("Music Downloader UI refreshed.", level="info")
        self._update_discord_rpc()

    def before_hide(self, closing_app=False):
        self.save_settings() # ensure settings are saved
        return True