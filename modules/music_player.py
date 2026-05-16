import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import pygame
import settings_manager
import logging
import json
import random
import time
# NEW IMPORTS FOR TAG EDITING
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError, ID3, TIT2, TPE1, TALB, TCON
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

# Import the styles to get consistent colors
from modules.zyphria_nexus import styles as zyphria_styles_defs

player_logger = logging.getLogger(__name__)

class MusicPlayerModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.parent = parent # Keep reference to parent for after() method
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        self.playlist = []
        self.current_song_index = -1
        self.paused = False
        self.playing = False
        self.current_playback_pos = 0 # To store position for resuming after tag edit

        # Load shuffle and repeat settings from app settings, falling back to default
        player_sub_settings = self.app_settings.get("music_player", settings_manager.DEFAULT_SETTINGS["music_player"])
        self.shuffle_enabled = tk.BooleanVar(value=player_sub_settings.get("shuffle_enabled", settings_manager.DEFAULT_SETTINGS["music_player"]["shuffle_enabled"]))
        self.repeat_mode = tk.StringVar(value=player_sub_settings.get("repeat_mode", settings_manager.DEFAULT_SETTINGS["music_player"]["repeat_mode"]))

        # Load initial volume from app settings, falling back to default
        self.volume = self.app_settings.get("music_player_default_volume", settings_manager.DEFAULT_SETTINGS["music_player_default_volume"])

        # Variables to hold current song details for Discord RPC and idle status bar
        self.current_rpc_song_title = "No song playing"
        self.current_rpc_artist = "Unknown Artist"

        self.initialized_mixer = False # Flag to track mixer initialization status
        try:
            pygame.init() # Initialize all pygame modules
            pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume)
            self.parent.after(100, self._check_music_end) # Start the continuous check
            player_logger.info("Pygame mixer initialized successfully.")
            self.main_app_instance.update_status_message("Music player initialized.", level="info")
            self.initialized_mixer = True
        except Exception as e:
            messagebox.showerror("Audio Error", f"Could not initialize audio mixer: {e}")
            player_logger.error(f"Failed to initialize Pygame mixer: {e}")
            self.main_app_instance.update_status_message(f"Audio error: {e}", level="error")


        # --- Player Variables (for UI elements) ---
        # Note: self.volume is directly used for the slider value below

        self.current_track_name = tk.StringVar(value="No track playing")
        self.current_time_str = tk.StringVar(value="00:00")
        self.total_time_str = tk.StringVar(value="00:00")
        self.progress_value = tk.DoubleVar(value=0)

        self.create_widgets()
        self._load_playlist_from_settings() # This also loads volume/shuffle/repeat into the UI elements
        player_logger.info("MusicPlayerModule initialized.")
        self.main_app_instance.update_status_message("Music Player module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update after widget creation


    def create_widgets(self):
        ttk.Label(self, text="🎵 Music Player 🎵", font=("Arial", 18, "bold")).pack(pady=20)

        playlist_manage_frame = ttk.Frame(self)
        playlist_manage_frame.pack(pady=5)
        ttk.Button(playlist_manage_frame, text="Save Playlist", command=self._save_playlist).pack(side="left", padx=5)
        ttk.Button(playlist_manage_frame, text="Load Playlist", command=self._load_playlist).pack(side="left", padx=5)
        # NEW: Edit Tags Button
        self.edit_tags_button = ttk.Button(playlist_manage_frame, text="Edit Tags", command=self._open_tag_editor)
        self.edit_tags_button.pack(side="left", padx=5)


        browse_buttons_frame = ttk.Frame(self)
        browse_buttons_frame.pack(pady=10)

        ttk.Button(browse_buttons_frame, text="Add Music File", command=self._browse_single_music_file).pack(side="left", padx=5)
        ttk.Button(browse_buttons_frame, text="Add Music Folder", command=self._browse_music_folder).pack(side="left", padx=5)

        ttk.Label(self, text="Playlist:").pack(pady=(10, 5))

        self.music_listbox = tk.Listbox(self,
                                        selectmode=tk.SINGLE,
                                        height=10,
                                        bg=zyphria_styles_defs.alt_gray,
                                        fg=zyphria_styles_defs.fg_white,
                                        selectbackground=zyphria_styles_defs.ghost_selection,
                                        selectforeground=zyphria_styles_defs.hologram_glow,
                                        highlightthickness=0,
                                        borderwidth=0,
                                        activestyle="none")

        self.music_listbox.pack(pady=5, fill="both", expand=True, padx=10)
        self.music_listbox.bind("<Double-Button-1>", self._play_selected_song)

        control_frame = ttk.Frame(self)
        control_frame.pack(pady=10)

        ttk.Button(control_frame, text="⏮️ Prev", command=self._play_previous).pack(side="left", padx=5)
        self.play_pause_button = ttk.Button(control_frame, text="▶️ Play", command=self._play_pause_music)
        self.play_pause_button.pack(side="left", padx=5)
        ttk.Button(control_frame, text="⏹️ Stop", command=self._stop_music).pack(side="left", padx=5)
        ttk.Button(control_frame, text="⏭️ Next", command=self._play_next).pack(side="left", padx=5)

        self.current_song_label = ttk.Label(self, text="Now Playing: -", font=("Arial", 10, "italic"))
        self.current_song_label.pack(pady=10)

        playback_mode_frame = ttk.Frame(self)
        playback_mode_frame.pack(pady=5)

        self.shuffle_button = ttk.Checkbutton(playback_mode_frame, text="🔀 Shuffle",
                                              variable=self.shuffle_enabled,
                                              command=self._toggle_shuffle_mode,
                                              style="TButton") # Use TButton style for visual consistency
        self.shuffle_button.pack(side="left", padx=5)

        self.repeat_button = ttk.Button(playback_mode_frame, text="Repeat: Off", command=self._cycle_repeat_mode)
        self.repeat_button.pack(side="left", padx=5)


        volume_frame = ttk.Frame(self)
        volume_frame.pack(pady=10)
        ttk.Label(volume_frame, text="Volume:").pack(side="left", padx=5)
        self.volume_slider = ttk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            command=self._update_volume_display,
            length=200,
            value=self.volume
        )
        self.volume_slider.pack(side="left", padx=5)
        self.volume_slider.bind("<ButtonRelease-1>", self._save_volume_on_release)

        self.volume_label = ttk.Label(volume_frame, text=f"{int(self.volume * 100)}%")
        self.volume_label.pack(side="left", padx=5)

        ttk.Button(self, text="Clear Playlist", command=self._clear_playlist).pack(pady=5)

    def _update_discord_rpc(self):
        """Helper method to update Discord RPC based on current module status."""
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status()

            # Pass rpc_buttons from the main app instance to maintain global buttons
            rpc_buttons = [
                {"label": "GitHub Repo", "url": "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool"},
                {"label": "Support Discord", "url": "https://discord.gg/vSX49HJMHS"}
            ]

            # Store the start timestamp for RPC. If not playing, or paused, it should be None.
            # Only if playing and not paused, set start time to current.
            rpc_start_timestamp = None
            if self.playing and not self.paused:
                rpc_start_timestamp = int(time.time())

            self.main_app_instance.discord_rpc_manager.update_activity(
                details=rpc_data["details"],
                state=rpc_data["state"],
                large_image=rpc_data["large_image"],
                large_text=rpc_data["large_text"],
                small_image=rpc_data["small_image"],
                small_text=rpc_data["small_text"],
                start=rpc_start_timestamp, # Use the pre-calculated variable
                buttons=rpc_buttons
            )

    # Discord Rich Presence Status Method
    def get_discord_rpc_status(self):
        """
        Returns a dictionary with current details, state, and image assets for Discord Rich Presence.
        """
        # Get default RPC data for this module from MultiAppScreen (for module-specific icons, etc.)
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="player")

        details = "Music Player" # Default if nothing else applies
        state = "Idle"           # Default if nothing else applies

        if self.playlist and self.current_song_index != -1 and 0 <= self.current_song_index < len(self.playlist):
            # Music is loaded (potentially playing or paused)

            # --- MODIFIED SECTION START ---
            if self.current_rpc_artist and self.current_rpc_artist != "Unknown Artist":
                # Combine title and artist into the details field
                details = f"Listening to: {self.current_rpc_song_title} by {self.current_rpc_artist}"
                state = "Currently playing" # More generic state, or could be empty ("")
            else:
                # If no artist is found, just use the title in details
                details = f"Listening to: {self.current_rpc_song_title}"
                state = "Music Player" # Fallback state when no artist is known
            # --- MODIFIED SECTION END ---

            if self.paused:
                state = f"Paused - {state}" # Indicate paused state explicitly
            elif not self.playing: # Not paused, but not actively playing either (e.g. just loaded or stopped)
                 state = f"Stopped - {state}"
            # If playing is True, the 'state' already contains the artist or default "Music Player"
        elif not self.playlist:
            details = "Music Player"
            state = "Playlist Empty"
        else: # Module is active, but no song loaded/playing, and playlist isn't empty
            details = "Music Player"
            state = "No song playing"

        return {
            "details": details,
            "state": state,
            "large_image": default_rpc["large_image"], # Uses the module-specific icon
            "large_text": default_rpc["large_text"],
            "small_image": default_rpc["small_image"], # Uses the main app logo
            "small_text": self.main_app_instance.base_title, # Changed to use main_app's base_title for consistency
        }

    def _check_music_end(self):
        """Checks if music has ended and plays the next song, respecting repeat mode."""
        if not self.initialized_mixer:
            self.parent.after(100, self._check_music_end) # Reschedule even if not initialized
            return

        # Only proceed if there's a playlist, a song is meant to be playing, and it's not paused
        # and pygame mixer is NOT busy (meaning song truly ended)
        if self.playlist and self.current_song_index != -1 and not self.paused and self.playing and not pygame.mixer.music.get_busy():
            player_logger.debug(f"Music ended. Repeat mode: {self.repeat_mode.get()}")
            if self.repeat_mode.get() == "one":
                self._play_music(self.current_song_index) # Replay current song
            else:
                self._play_next() # Go to next song (or loop all, or stop)

        # Schedule the next check
        self.parent.after(100, self._check_music_end)

    def _update_volume_display(self, value):
        """Updates the music playback volume in mixer and UI."""
        if not self.initialized_mixer: return
        self.volume = float(value)
        pygame.mixer.music.set_volume(self.volume)
        self.volume_label.config(text=f"{int(self.volume * 100)}%")
        player_logger.debug(f"Volume set to {self.volume:.2f}")
        # RPC only needs to be updated when actual playback changes, not just volume
        # self._update_discord_rpc()

    def _save_volume_on_release(self, event=None):
        """Saves the current volume setting to the settings file when slider is released."""
        self.app_settings["music_player_default_volume"] = self.volume
        settings_manager.save_settings(self.app_settings)
        player_logger.info(f"Volume setting saved on slider release: {self.volume:.2f}")
        self.main_app_instance.update_status_message(f"Volume set to {int(self.volume * 100)}% and saved.", level="info")

    def _add_to_playlist(self, file_path):
        """Adds a single file to the playlist and updates the listbox."""
        if file_path and os.path.exists(file_path):
            if file_path not in self.playlist:
                self.playlist.append(file_path)
                self._update_listbox()
                player_logger.info(f"Added '{os.path.basename(file_path)}' to playlist.")
                self.main_app_instance.update_status_message(f"Added '{os.path.basename(file_path)}' to playlist.", level="info")
            else:
                player_logger.debug(f"Attempted to add '{os.path.basename(file_path)}' but it's already in the playlist.")
                self.main_app_instance.update_status_message(f"'{os.path.basename(file_path)}' is already in the playlist.", level="info")
        elif file_path: # Path exists but not added due to non-existence
            player_logger.warning(f"Attempted to add '{os.path.basename(file_path)}' but it does not exist.")
            self.main_app_instance.update_status_message(f"File not found: '{os.path.basename(file_path)}'.", level="warning")


    def _update_listbox(self):
        """Refreshes the listbox display to reflect the current playlist."""
        self.music_listbox.delete(0, tk.END)
        for song_path in self.playlist:
            # Display filename for simplicity in the listbox.
            # You could add tag info here, but it's more complex with varying tag availability.
            self.music_listbox.insert(tk.END, os.path.basename(song_path))
        if self.current_song_index != -1 and 0 <= self.current_song_index < len(self.playlist):
            self.music_listbox.selection_set(self.current_song_index)
            self.music_listbox.see(self.current_song_index)

    def _save_playlist(self):
        if not self.playlist:
            messagebox.showwarning("Empty Playlist", "There is no music in the playlist to save.", parent=self.winfo_toplevel())
            self.main_app_instance.update_status_message("Cannot save empty playlist.", level="warning")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Playlist Files", "*.json"), ("All Files", "*.*")],
            title="Save Playlist As",
            parent=self.winfo_toplevel()
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f: # Ensure UTF-8 encoding
                    json.dump(self.playlist, f, indent=4)
                self.main_app_instance.update_status_message(f"Playlist saved to {os.path.basename(file_path)}.", level="info")
                player_logger.info(f"Playlist saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save playlist: {e}", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Error saving playlist: {e}", level="error")
                player_logger.error(f"Error saving playlist to {file_path}: {e}")

    def _load_playlist(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("Playlist Files", "*.json"), ("All Files", "*.*")],
            title="Load Playlist",
            parent=self.winfo_toplevel()
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f: # Ensure UTF-8 encoding
                    loaded_playlist = json.load(f)

                valid_songs = [song for song in loaded_playlist if os.path.exists(song)]
                invalid_songs_count = len(loaded_playlist) - len(valid_songs)

                if valid_songs:
                    self.playlist = valid_songs
                    self._update_listbox()
                    self._stop_music()
                    status_msg = f"Playlist loaded from {os.path.basename(file_path)}."
                    if invalid_songs_count > 0:
                        status_msg += f" ({invalid_songs_count} non-existent songs skipped)."
                        self.main_app_instance.update_status_message(status_msg, level="warning")
                    else:
                        self.main_app_instance.update_status_message(status_msg, level="info")
                    player_logger.info(f"Playlist loaded from {file_path}. {invalid_songs_count} songs skipped.")
                else:
                    messagebox.showwarning("Empty Playlist", "The loaded playlist file contains no valid music files.", parent=self.winfo_toplevel())
                    self.main_app_instance.update_status_message(f"Loaded playlist from {os.path.basename(file_path)} but found no valid songs.", level="warning")
                    player_logger.warning(f"Loaded playlist from {file_path} but found no valid songs.")

            except json.JSONDecodeError:
                messagebox.showerror("Load Error", "Failed to load playlist: Invalid JSON format.", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Error loading playlist: Invalid JSON format.", level="error")
                player_logger.error(f"Error loading playlist from {file_path}: {e}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load playlist: {e}", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Error loading playlist: {e}", level="error")
                player_logger.error(f"Error loading playlist from {file_path}: {e}")

    def _load_playlist_from_settings(self):
        """Loads the saved playlist and volume from app settings on startup."""
        player_settings = self.app_settings.get("music_player", settings_manager.DEFAULT_SETTINGS["music_player"])

        saved_playlist = player_settings.get("playlist", settings_manager.DEFAULT_SETTINGS["music_player"]["playlist"])
        for path in saved_playlist:
            if os.path.exists(path):
                self.playlist.append(path)
        self._update_listbox()
        player_logger.info(f"Loaded {len(self.playlist)} songs from settings.")

        # Volume is handled by self.volume init and set on slider and mixer
        self.volume_slider.set(self.volume) # Update slider position
        self._update_volume_display(self.volume) # Update mixer and label

        # Set initial value for shuffle and repeat from settings if saved
        self.shuffle_enabled.set(player_settings.get("shuffle_enabled", settings_manager.DEFAULT_SETTINGS["music_player"]["shuffle_enabled"]))
        self.repeat_mode.set(player_settings.get("repeat_mode", settings_manager.DEFAULT_SETTINGS["music_player"]["repeat_mode"]))
        # Update UI for repeat button
        current_mode = self.repeat_mode.get()
        if current_mode == "none": self.repeat_button.config(text="Repeat: Off")
        elif current_mode == "one": self.repeat_button.config(text="Repeat: One")
        elif current_mode == "all": self.repeat_button.config(text="Repeat: All")


    def _toggle_shuffle_mode(self):
        """Toggles shuffle mode and shuffles/unshuffles the playlist display."""
        if self.shuffle_enabled.get():
            self.main_app_instance.update_status_message("Shuffle mode enabled.", level="info")
            player_logger.info("Shuffle mode enabled.")
        else:
            self.main_app_instance.update_status_message("Shuffle mode disabled.", level="info")
            player_logger.info("Shuffle mode disabled.")
        self.save_settings() # Save shuffle state

    def _cycle_repeat_mode(self):
        """Cycles through repeat modes: none -> one -> all -> none."""
        current_mode = self.repeat_mode.get()
        if current_mode == "none":
            self.repeat_mode.set("one")
            self.repeat_button.config(text="Repeat: One")
            self.main_app_instance.update_status_message("Repeat mode set to 'one song'.", level="info")
            player_logger.info("Repeat mode set to 'one'.")
        elif current_mode == "one":
            self.repeat_mode.set("all")
            self.repeat_button.config(text="Repeat: All")
            self.main_app_instance.update_status_message("Repeat mode set to 'all songs'.", level="info")
            player_logger.info("Repeat mode set to 'all'.")
        else:
            self.repeat_mode.set("none")
            self.repeat_button.config(text="Repeat: Off")
            self.main_app_instance.update_status_message("Repeat mode set to 'off'.", level="info")
            player_logger.info("Repeat mode set to 'none'.")
        self.save_settings() # Save repeat state


    def _browse_single_music_file(self):
        """Opens a file dialog to select a single music file."""
        # Use last_played_directory from app_settings as initialdir
        player_sub_settings = self.app_settings.get("music_player", settings_manager.DEFAULT_SETTINGS["music_player"])
        initial_dir = player_sub_settings.get("last_played_directory", "")
        if not os.path.isdir(initial_dir): # Check if it's a valid directory before using
            initial_dir = os.path.expanduser("~")

        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.aac"), ("All files", "*.*")],
            parent=self,
            initialdir=initial_dir
        )
        if file_path:
            self._add_to_playlist(file_path)
            # Update last_played_directory to the directory of the first selected file
            if "music_player" not in self.app_settings:
                self.app_settings["music_player"] = {}
            self.app_settings["music_player"]["last_played_directory"] = os.path.dirname(file_path)
            self.save_settings() # Save this change immediately

    def _browse_music_folder(self):
        """Opens a directory dialog to select a folder and adds all found music files."""
        # Use last_played_directory from app_settings as initialdir
        player_sub_settings = self.app_settings.get("music_player", settings_manager.DEFAULT_SETTINGS["music_player"])
        initial_dir = player_sub_settings.get("last_played_directory", "")
        if not os.path.isdir(initial_dir): # Check if it's a valid directory before using
            initial_dir = os.path.expanduser("~")

        folder_path = filedialog.askdirectory(parent=self, initialdir=initial_dir)
        if folder_path:
            count = 0
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".aac")):
                        full_path = os.path.join(root, file)
                        self._add_to_playlist(full_path)
                        count += 1
            if count > 0:
                self.main_app_instance.update_status_message(f"Added {count} music files from '{os.path.basename(folder_path)}'.", level="info")
                player_logger.info(f"Added {count} files from folder '{folder_path}'.")
                # Update last_played_directory to the selected folder
                if "music_player" not in self.app_settings:
                    self.app_settings["music_player"] = {}
                self.app_settings["music_player"]["last_played_directory"] = folder_path
                self.save_settings() # Save this change immediately
            else:
                self.main_app_instance.update_status_message(f"No supported music files found in '{os.path.basename(folder_path)}'.", level="warning")
                player_logger.info(f"No music files found in folder '{folder_path}'.")

    def _clear_playlist(self):
        """Clears the playlist and the listbox."""
        if messagebox.askyesno("Clear Playlist", "Are you sure you want to clear the entire playlist?", parent=self.winfo_toplevel()):
            self.playlist = []
            self.music_listbox.delete(0, tk.END)
            self._stop_music() # This will reset current_song_index and RPC status
            self.current_song_label.config(text="Now Playing: -")
            self.main_app_instance.update_status_message("Playlist has been cleared.", level="info")
            player_logger.info("Playlist cleared.")
            self._update_discord_rpc() # Explicitly update RPC after clearing playlist
            self.save_settings() # Save the empty playlist

    def _play_selected_song(self, event=None):
        """Plays the song selected in the listbox."""
        if not self.initialized_mixer:
            self.main_app_instance.update_status_message("Mixer not initialized. Cannot play music.", level="error")
            return
        selected_index_tuple = self.music_listbox.curselection()
        if selected_index_tuple:
            self.current_song_index = selected_index_tuple[0]
            self._play_music(self.current_song_index)

    def _play_music(self, index):
        """Handles actual music playback."""
        if not self.initialized_mixer:
            self.main_app_instance.update_status_message("Mixer not initialized. Cannot play music.", level="error")
            return

        if 0 <= index < len(self.playlist):
            song_path = self.playlist[index]
            self.current_song_index = index

            # Get MP3 tags for display and RPC
            title, artist = self._get_audio_tags(song_path)
            self.current_rpc_song_title = title
            self.current_rpc_artist = artist

            # Set in-app label text
            if self.current_rpc_artist and self.current_rpc_artist != "Unknown Artist":
                self.current_song_label.config(text=f"Now Playing: {title} by {artist}")
            else:
                self.current_song_label.config(text=f"Now Playing: {title}")

            self.play_pause_button.config(text="⏸️ Pause")
            self.paused = False
            self.playing = True # Set playing state to True

            self.music_listbox.selection_clear(0, tk.END)
            self.music_listbox.selection_set(self.current_song_index)
            self.music_listbox.see(self.current_song_index)

            try:
                pygame.mixer.music.load(song_path)
                pygame.mixer.music.play()
                pygame.mixer.music.set_volume(self.volume)
                player_logger.info(f"Playing: {os.path.basename(song_path)}")
                self.main_app_instance.update_status_message(f"Playing: '{title}' by '{artist}'.", level="info")
                self._update_discord_rpc() # Update RPC after playing
            except pygame.error as e:
                messagebox.showerror("Playback Error", f"Could not play {os.path.basename(song_path)}: {e}", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Error playing '{os.path.basename(song_path)}': {e}", level="error")
                player_logger.error(f"Error playing '{os.path.basename(song_path)}': {e}")
                self._stop_music() # Stop and reset if error
            except Exception as e:
                messagebox.showerror("Playback Error", f"An unexpected error occurred trying to play {os.path.basename(song_path)}: {e}", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Error playing '{os.path.basename(song_path)}': {e}", level="error")
                player_logger.error(f"Unexpected error playing '{os.path.basename(song_path)}': {e}")
                self._stop_music() # Stop and reset if error
        else:
            self.current_song_label.config(text="Now Playing: -")
            self._stop_music() # Ensure stop logic is applied
            self.main_app_instance.update_status_message("Invalid song index or playlist empty.", level="warning")
            self._update_discord_rpc() # Update RPC if cannot play

    def _play_pause_music(self):
        """Toggles play/pause."""
        if not self.initialized_mixer:
            self.main_app_instance.update_status_message("Mixer not initialized. Cannot play music.", level="error")
            return
        if not self.playlist:
            messagebox.showwarning("No Music", "Please add music to the playlist first.", parent=self.winfo_toplevel())
            self.main_app_instance.update_status_message("No music in playlist to play.", level="warning")
            return

        if self.current_song_index == -1:
             if self.playlist:
                 self._play_music(0)
             else:
                 messagebox.showwarning("No Music", "Playlist is empty, add music to play.", parent=self.winfo_toplevel())
                 self.main_app_instance.update_status_message("Playlist empty.", level="warning")
             return

        if pygame.mixer.music.get_busy(): # Music is currently playing
            pygame.mixer.music.pause()
            self.paused = True
            self.playing = False # Set playing state to False when paused
            self.play_pause_button.config(text="▶️ Play")
            player_logger.info("Music paused.")
            self.main_app_instance.update_status_message("Music paused.", level="info")
            self._update_discord_rpc() # Update RPC after pausing
        elif self.paused: # Music was paused, now unpause
            pygame.mixer.music.unpause()
            self.paused = False
            self.playing = True # Set playing state to True when unpaused
            self.play_pause_button.config(text="⏸️ Pause")
            player_logger.info("Music unpaused.")
            self.main_app_instance.update_status_message("Music unpaused.", level="info")
            self._update_discord_rpc() # Update RPC after unpausing
        else: # Attempting to play (e.g. after a stop, or if something went wrong)
            if self.current_song_index == -1 and self.playlist:
                self._play_music(0)
            elif self.current_song_index != -1:
                self._play_music(self.current_song_index)

    def _stop_music(self):
        """Stops current music playback."""
        if not self.initialized_mixer: return
        if pygame.mixer.music.get_busy() or self.paused:
            pygame.mixer.music.stop()
            # Explicitly unload to release file handle and prevent errors on next load
            try:
                pygame.mixer.music.unload()
                player_logger.debug("Pygame mixer music unloaded.")
            except pygame.error as e:
                player_logger.warning(f"Error unloading pygame mixer music: {e}")
        self.play_pause_button.config(text="▶️ Play")
        self.current_song_label.config(text="Now Playing: -")
        self.paused = False
        self.playing = False # Set playing state to False when stopped
        self.current_song_index = -1
        self.current_playback_pos = 0 # Reset playback position
        # Reset RPC song info
        self.current_rpc_song_title = "No song playing"
        self.current_rpc_artist = "Unknown Artist"
        player_logger.info("Music stopped.")
        self.main_app_instance.update_status_message("Music stopped.", level="info")
        self._update_discord_rpc() # Update RPC after stopping


    def _play_next(self):
        """Plays the next song in the playlist, respecting shuffle and repeat modes."""
        if not self.initialized_mixer:
            self.main_app_instance.update_status_message("Mixer not initialized. Cannot play music.", level="error")
            return
        if not self.playlist:
            return

        next_index = self.current_song_index

        if self.shuffle_enabled.get():
            next_index = random.randrange(len(self.playlist))
            player_logger.debug(f"Shuffle enabled, playing random song at index {next_index}")
        else:
            if self.repeat_mode.get() == "all":
                next_index = (self.current_song_index + 1) % len(self.playlist)
                player_logger.debug(f"Repeat all enabled, playing next song at index {next_index}")
            elif self.repeat_mode.get() == "none":
                next_index = self.current_song_index + 1
                if next_index >= len(self.playlist):
                    self._stop_music()
                    player_logger.info("End of playlist (no repeat), stopping music.")
                    self.main_app_instance.update_status_message("End of playlist. Music stopped.", level="info")
                    return
                player_logger.debug(f"No repeat, playing next song at index {next_index}")

        self._play_music(next_index)


    def _play_previous(self):
        """Plays the previous song in the playlist."""
        if not self.initialized_mixer:
            self.main_app_instance.update_status_message("Mixer not initialized. Cannot play music.", level="error")
            return
        if not self.playlist:
            messagebox.showwarning("No Music", "Playlist is empty.", parent=self.winfo_toplevel())
            self.main_app_instance.update_status_message("Playlist is empty.", level="warning")
            return

        if self.current_song_index == -1:
            self._play_music(len(self.playlist) - 1)
        else:
            prev_index = (self.current_song_index - 1 + len(self.playlist)) % len(self.playlist)
            self._play_music(prev_index)
            player_logger.debug(f"Playing previous song: index {prev_index}")

    def _get_audio_tags(self, path):
        """
        Extracts title and artist from various audio file tags.
        Returns a tuple (title, artist).
        """
        filename = os.path.basename(path)
        title = os.path.splitext(filename)[0] # Default to filename without extension
        artist = "Unknown Artist"

        try:
            audio = None
            file_extension = os.path.splitext(path)[1].lower()

            if file_extension == ".mp3":
                try:
                    audio = EasyID3(path)
                except ID3NoHeaderError:
                    # Create ID3 tags if the file has none
                    mp3_file = MP3(path)
                    mp3_file.add_tags()
                    mp3_file.save()
                    audio = EasyID3(path)

            elif file_extension == ".flac":
                audio = FLAC(path)

            elif file_extension == ".ogg":
                audio = OggVorbis(path)

            elif file_extension == ".wav":
                audio = WAVE(path)

            else:
                player_logger.debug(
                    f"Unsupported format for full tag read: {file_extension}. Using filename."
                )

            if audio:
                if 'title' in audio and audio['title']:
                    title = str(audio['title'][0]).strip()

                if 'artist' in audio and audio['artist']:
                    artist = str(audio['artist'][0]).strip()

        except Exception as e:
            player_logger.warning(f"Error reading tags for '{filename}': {e}. Using filename and 'Unknown Artist'.")

        # Ensure title is not empty
        if not title:
            title = os.path.splitext(filename)[0]

        return title, artist

    # NEW: ID3 Tag Editor logic
    def _open_tag_editor(self):
        """Opens a Toplevel window to edit ID3 tags of the selected song."""
        selected_index_tuple = self.music_listbox.curselection()
        if not selected_index_tuple:
            messagebox.showwarning("No Song Selected", "Please select a song in the playlist to edit its tags.", parent=self.winfo_toplevel())
            return

        selected_index_in_listbox = selected_index_tuple[0]
        song_path = self.playlist[selected_index_in_listbox]

        if not os.path.exists(song_path):
            messagebox.showerror("File Not Found", f"The selected song file does not exist: {os.path.basename(song_path)}", parent=self.winfo_toplevel())
            return

        editor_window = tk.Toplevel(self.winfo_toplevel())
        editor_window.title(f"Edit Tags: {os.path.basename(song_path)}")
        editor_window.transient(self.winfo_toplevel()) # Make it appear on top of main window
        editor_window.grab_set() # Make it modal (user must interact with it)

        # Get current tags
        current_title, current_artist = self._get_audio_tags(song_path)
        current_album = ""
        try:
            audio_file_extension = os.path.splitext(song_path)[1].lower()
            audio = None
            if audio_file_extension == ".mp3":
                # CORRECTED: Used EasyID3 instead of EasyMP3
                try:
                    audio = EasyID3(song_path)
                    if audio and 'album' in audio and audio['album']:
                        current_album = str(audio['album'][0]).strip()
                except ID3NoHeaderError:
                    player_logger.debug(f"No ID3 header found for album read in {os.path.basename(song_path)}")
                except Exception as e:
                    player_logger.debug(f"Error reading MP3 album tag: {e}")
            elif audio_file_extension == ".flac":
                audio = FLAC(song_path)
                if audio and 'album' in audio and audio['album']:
                    current_album = str(audio['album'][0]).strip()
            elif audio_file_extension == ".ogg":
                audio = OggVorbis(song_path)
                if audio and 'album' in audio and audio['album']:
                    current_album = str(audio['album'][0]).strip()
            # WAV doesn't typically have album tags

        except Exception as e:
            player_logger.debug(f"Could not read album tag for {os.path.basename(song_path)}: {e}")

        title_var = tk.StringVar(value=current_title)
        artist_var = tk.StringVar(value=current_artist)
        album_var = tk.StringVar(value=current_album)

        padding = {'padx': 5, 'pady': 5}

        ttk.Label(editor_window, text="Title:").grid(row=0, column=0, **padding, sticky="w")
        ttk.Entry(editor_window, textvariable=title_var, width=40).grid(row=0, column=1, **padding, sticky="ew")

        ttk.Label(editor_window, text="Artist:").grid(row=1, column=0, **padding, sticky="w")
        ttk.Entry(editor_window, textvariable=artist_var, width=40).grid(row=1, column=1, **padding, sticky="ew")

        ttk.Label(editor_window, text="Album:").grid(row=2, column=0, **padding, sticky="w")
        ttk.Entry(editor_window, textvariable=album_var, width=40).grid(row=2, column=1, **padding, sticky="ew")

        button_frame = ttk.Frame(editor_window)
        button_frame.grid(row=3, column=0, columnspan=2, **padding)
        ttk.Button(button_frame, text="Save", command=lambda: self._save_tags(song_path, title_var.get(), artist_var.get(), album_var.get(), editor_window, selected_index_in_listbox)).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=editor_window.destroy).pack(side="left", padx=5)

        editor_window.grid_columnconfigure(1, weight=1)
        editor_window.update_idletasks() # Ensure window size is calculated
        editor_window.geometry(f"+{self.winfo_x() + (self.winfo_width() // 2) - (editor_window.winfo_width() // 2)}+{self.winfo_y() + (self.winfo_height() // 2) - (editor_window.winfo_height() // 2)}") # Center the window

        editor_window.wait_window() # Wait until window is closed

    def _save_tags(self, path, new_title, new_artist, new_album, editor_window, edited_song_listbox_index):
        """Saves the new tag information to the audio file."""
        player_logger.debug(f"Attempting to save tags for: {os.path.basename(path)}")

        was_playing = False
        was_paused = False
        current_playback_pos_ms = 0

        # Check if the edited song is currently playing or paused
        is_current_song = (self.current_song_index != -1 and self.playlist[self.current_song_index] == path)

        if is_current_song and self.initialized_mixer:
            current_playback_pos_ms = pygame.mixer.music.get_pos() # Get current position in milliseconds
            if pygame.mixer.music.get_busy(): # If currently playing
                was_playing = True
                player_logger.info(f"Song is playing, stopping temporarily at {current_playback_pos_ms}ms to save tags.")
            elif self.paused: # If currently paused
                was_paused = True
                player_logger.info(f"Song is paused, stopping temporarily at {current_playback_pos_ms}ms to save tags.")

            pygame.mixer.music.stop() # Explicitly stop to release file handle

            # Explicitly unload to ensure the file handle is released
            try:
                pygame.mixer.music.unload()
                player_logger.debug("Pygame mixer music unloaded for tag editing.")
            except pygame.error as e:
                player_logger.warning(f"Error unloading pygame mixer music before tag edit: {e}")

            self.playing = False # Update internal state
            self.paused = False # Assume stopped for now, will reset to original state

            # A small delay is crucial to ensure file handle is released by pygame
            time.sleep(0.1)

        try:
            audio = None
            file_extension = os.path.splitext(path)[1].lower()
            player_logger.debug(f"File extension for tag saving: {file_extension}")

            if file_extension == ".mp3":
                try:
                    audio = EasyID3(path)
                    player_logger.debug("Attempted to load MP3 with EasyID3.")
                except ID3NoHeaderError:
                    player_logger.debug("MP3 has no ID3 header, attempting to add tags.")
                    try:
                        mp3_file = MP3(path)
                        mp3_file.add_tags()
                        mp3_file.save()
                        audio = EasyID3(path) # Reload EasyID3 after adding tags
                        player_logger.debug("Added ID3 tags and reloaded EasyID3 successfully.")
                    except Exception as add_tag_e:
                        player_logger.error(f"Error adding new ID3 tags to {os.path.basename(path)}: {add_tag_e}")
                        messagebox.showerror("Tag Error", f"Failed to add ID3 tags to the MP3 file. Error: {add_tag_e}", parent=editor_window)
                        editor_window.destroy()
                        return False
                except Exception as easyid3_e:
                    player_logger.error(f"Error loading MP3 with EasyID3 for {os.path.basename(path)}: {easyid3_e}")
                    messagebox.showerror("Tag Error", f"Failed to load MP3 file for tag editing (EasyID3 error). Error: {easyid3_e}", parent=editor_window)
                    editor_window.destroy()
                    return False
            elif file_extension == ".flac":
                audio = FLAC(path)
                player_logger.debug("Loaded FLAC.")
            elif file_extension == ".ogg":
                audio = OggVorbis(path)
                player_logger.debug("Loaded OGG.")
            elif file_extension == ".wav":
                messagebox.showwarning("Limited Support", "WAV files have very limited tag support. Changes may not be visible or saved.", parent=editor_window)
                player_logger.warning(f"Attempted to edit WAV tags: {path}. Mutagen WAVE does not support generic tag access.")
                audio = None # Mutagen WAVE does not support direct tag assignments like audio['title']
            else:
                messagebox.showwarning("Unsupported Format", f"Tag editing for '{file_extension}' files is not fully supported.", parent=editor_window)
                player_logger.warning(f"Attempted to edit tags on unsupported format: {path}")
                audio = None

            # --- Explicit check for audio object ---
            if audio is None: # Changed to 'is None' for clarity
                messagebox.showerror("Tag Edit Error", "Could not load the audio file for tag editing. It might be corrupted or an unsupported format for writing tags.", parent=editor_window)
                player_logger.error(f"Failed to load audio object for writing tags to {path}. Aborting save.")
                editor_window.destroy() # Close the editor window if we can't proceed
                return False
            # --- End explicit check ---

            player_logger.debug(f"Setting new tags: Title='{new_title}', Artist='{new_artist}', Album='{new_album}'")
            # Assign tags as lists for broader compatibility across mutagen types
            audio['title'] = [new_title]
            audio['artist'] = [new_artist]
            audio['album'] = [new_album]

            audio.save()
            player_logger.info(f"Tags successfully saved for '{os.path.basename(path)}'")
            self_message = f"Tags updated for '{os.path.basename(path)}'."
            self.main_app_instance.update_status_message(self_message, level="info")

            # If the edited song is currently playing/paused, update the main UI and RPC
            if is_current_song:
                self.current_rpc_song_title = new_title
                self.current_rpc_artist = new_artist
                # Refresh the main song label
                if self.current_rpc_artist and self.current_rpc_artist != "Unknown Artist":
                    self.current_song_label.config(text=f"Now Playing: {new_title} by {new_artist}")
                else:
                    self.current_song_label.config(text=f"Now Playing: {new_title}")

                # Restart if it was playing, or reload and pause if it was paused
                if self.initialized_mixer:
                    try:
                        pygame.mixer.music.load(path) # Reload the file to get new tags
                        if was_playing:
                            # Use play(start=...) for initial seeking
                            pygame.mixer.music.play(start=current_playback_pos_ms / 1000.0)
                            self.playing = True
                            self.paused = False
                            self.play_pause_button.config(text="⏸️ Pause") # Ensure button text is correct
                            player_logger.info(f"Resumed playback of {os.path.basename(path)} from {current_playback_pos_ms}ms after tag edit.")
                        elif was_paused:
                            # Use play(start=...) then pause for initial seeking and pausing
                            pygame.mixer.music.play(start=current_playback_pos_ms / 1000.0)
                            pygame.mixer.music.pause()
                            self.playing = False
                            self.paused = True
                            self.play_pause_button.config(text="▶️ Play") # Button should still say Play if paused
                            player_logger.info(f"Reloaded and paused {os.path.basename(path)} with new tags at {current_playback_pos_ms}ms.")
                        # If it was neither playing nor paused (e.g., just selected), do nothing special,
                        # just let the _stop_music (called below) ensure clean state if it was somehow active
                    except pygame.error as e:
                        player_logger.critical(f"CRITICAL PYGAME ERROR reloading/resuming playback after tag edit: {e}. Pygame message: {e}")
                        self.main_app_instance.update_status_message(f"CRITICAL ERROR reloading/resuming playback: {e}", level="error")
                        self._stop_music() # Fallback to stop if cannot reload/resume

                self._update_discord_rpc() # Update RPC with new tags

            # Refresh the entire listbox display to ensure all song entries reflect new tags (if they are displayed in listbox)
            self._update_listbox()

            # Close the editor window
            editor_window.destroy()
            return True

        except FileNotFoundError:
            messagebox.showerror("File Error", f"The audio file was not found: {path}", parent=editor_window)
            player_logger.error(f"File not found during tag save: {path}")
            editor_window.destroy() # Close on error
        except PermissionError:
             messagebox.showerror("Permission Error", f"Permission denied to write to file: {os.path.basename(path)}. Ensure it's not locked by another application.", parent=editor_window)
             player_logger.error(f"Permission denied when saving tags to '{path}'.")
             editor_window.destroy() # Close on error
        except Exception as e:
            messagebox.showerror("Error Saving Tags", f"Failed to save tags: {e}", parent=editor_window)
            player_logger.error(f"General error saving tags for '{path}': {e}")
            editor_window.destroy() # Close on error
        finally:
            # If the song was playing and we stopped it, but it failed to resume, ensure state is clean
            # This catch is mainly for unexpected failures that don't trigger the specific except blocks
            if is_current_song and (was_playing or was_paused) and not (self.playing or self.paused):
                player_logger.warning("Playback was not resumed after tag edit due to an error.")
                self._stop_music() # Ensure clean state

        return False


    # --- NEW: Methods for idle status bar integration ---
    def is_playing(self):
        """
        Returns True if music is currently playing and not paused, False otherwise.
        This uses pygame's internal state and our 'playing' flag.
        """
        return self.playing and self.initialized_mixer and pygame.mixer.music.get_busy() and not self.paused

    def get_current_track_info(self):
        """
        Returns a formatted string with current track info (e.g., 'Artist - Title')
        or None if no music is playing.
        """
        if self.is_playing():
            title_part = self.current_rpc_song_title
            artist_part = self.current_rpc_artist if self.current_rpc_artist and self.current_rpc_artist != "Unknown Artist" else None

            if artist_part:
                return f"{artist_part} - {title_part}"
            else:
                return title_part
        return None
    # --- END NEW METHODS ---


    def get_menubar_commands(self):
        """
        Returns a dictionary of commands specific to this module for the menubar.
        """
        return {
            "help_commands": [
                ("About Music Player", self.show_about_dialog),
                ("Music Player Help", self.show_help_dialog),
            ]
        }

    def refresh_settings_ui(self):
        """Called by main_app.py to refresh the UI when the module becomes active."""
        # Reload volume (if changed via settings)
        self.volume = self.app_settings.get("music_player_default_volume", settings_manager.DEFAULT_SETTINGS["music_player_default_volume"])
        if self.initialized_mixer:
            pygame.mixer.music.set_volume(self.volume)
        self.volume_slider.set(self.volume) # Update slider position
        self._update_volume_display(self.volume) # Update mixer and label

        # Also refresh last played directory from settings (if it was cleared in Settings)
        # We need to explicitly update app_settings here as the settings module updates the global app_settings
        player_sub_settings = self.app_settings.get("music_player", settings_manager.DEFAULT_SETTINGS["music_player"])
        if "music_player" not in self.app_settings: self.app_settings["music_player"] = {}
        self.app_settings["music_player"]["last_played_directory"] = player_sub_settings.get("last_played_directory", settings_manager.DEFAULT_SETTINGS["music_player"]["last_played_directory"])

        # Reload shuffle and repeat settings from app_settings
        self.shuffle_enabled.set(player_sub_settings.get("shuffle_enabled", settings_manager.DEFAULT_SETTINGS["music_player"]["shuffle_enabled"]))
        self.repeat_mode.set(player_sub_settings.get("repeat_mode", settings_manager.DEFAULT_SETTINGS["music_player"]["repeat_mode"]))
        # Update UI for repeat button
        current_mode = self.repeat_mode.get()
        if current_mode == "none": self.repeat_button.config(text="Repeat: Off")
        elif current_mode == "one": self.repeat_button.config(text="Repeat: One")
        elif current_mode == "all": self.repeat_button.config(text="Repeat: All")


        player_logger.debug("MusicPlayerModule UI refreshed.")
        self.main_app_instance.update_status_message("Music Player settings UI refreshed.", level="info")
        self._update_discord_rpc() # Update RPC after refresh

    def save_settings(self):
        """Saves current player-specific settings to the app_settings dictionary."""
        # Ensure music_player sub-dict exists for saving nested settings
        if "music_player" not in self.app_settings:
            self.app_settings["music_player"] = {}

        self.app_settings["music_player"]["playlist"] = self.playlist
        self.app_settings["music_player_default_volume"] = self.volume # Top-level volume setting

        # Save shuffle and repeat state
        self.app_settings["music_player"]["shuffle_enabled"] = self.shuffle_enabled.get()
        self.app_settings["music_player"]["repeat_mode"] = self.repeat_mode.get()

        settings_manager.save_settings(self.app_settings)
        player_logger.info("Music Player playlist, volume, shuffle, and repeat settings saved.")

    def before_hide(self, closing_app=False):
        """Called by main_app.py before the module is hidden or app is closed."""
        self.save_settings() # Ensure all current player settings are saved.

        # Stop music playback if app is closing
        if closing_app:
            if self.initialized_mixer:
                pygame.mixer.music.stop()
            player_logger.info("Music playback stopped due to app closing.")

        player_logger.info("MusicPlayerModule before_hide executed.")
        self._update_discord_rpc() # Update RPC state to idle
        return True

    def show_about_dialog(self):
        about_text = (
            "Music Player Module\n"
            "Version 1.0.0\n"
            "\n"
            "Simple local music playback functionality.\n"
            "Developed by Z.\n"
            "\n"
            f"Thank you for using {settings_manager.APP_NAME}!"
        )
        messagebox.showinfo("About Music Player", about_text, parent=self.winfo_toplevel())
        player_logger.info("About dialog shown for Music Player.")

    def show_help_dialog(self):
        help_text = (
            "Music Player Help Guide:\n"
            "\n"
            "Controls:\n"
            "  - Add Music File: Select individual audio files to add to the playlist.\n"
            "  - Add Music Folder: Add all supported audio files from a selected folder and its subfolders.\n"
            "  - Playlist: Double-click a song to play it. Currently playing song is highlighted.\n"
            "  - Play/Pause (▶️/⏸️): Toggles playback of the current song.\n"
            "  - Stop (⏹️): Stops current playback.\n"
            "  - Prev (⏮️): Plays the previous song in the playlist.\n"
            "  - Next (⏭️): Plays the next song in the playlist.\n"
            "  - Volume Slider: Adjusts the playback volume (setting is saved automatically).\n"
            "  - Save Playlist: Saves your current playlist to a JSON file.\n"
            "  - Load Playlist: Loads a playlist from a JSON file, replacing the current one.\n"
            "  - Edit Tags: Opens a window to edit the Title, Artist, and Album tags of the selected song.\n"
            "  - Shuffle (🔀): Toggles random playback order (state is saved automatically).\n"
            "  - Repeat: Cycles through 'Repeat Off', 'Repeat One Song', and 'Repeat All Songs' (state is saved automatically).\n"
            "  - Clear Playlist: Removes all songs from the playlist (after confirmation).\n"
            "\n"
            "Supported formats: MP3, WAV, OGG, FLAC, AAC. Tag editing primarily supported for MP3, FLAC, OGG."
        )
        messagebox.showinfo("Music Player Help", help_text, parent=self.winfo_toplevel())
        player_logger.info("Music Player Help dialog shown for Music Player.")