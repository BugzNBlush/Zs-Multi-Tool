# modules/music_player.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import pygame
import settings_manager
import logging
import json 
import random 
import time 
from mutagen.mp3 import MP3 
from mutagen.id3 import ID3NoHeaderError 

# Import the styles to get consistent colors
from modules.zyphria_nexus import styles as zyphria_styles_defs 

player_logger = logging.getLogger(__name__)

class MusicPlayerModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance): 
        super().__init__(parent)
        self.parent = parent
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance 
        self.playlist = []
        self.current_song_index = -1
        self.paused = False
        
        self.shuffle_enabled = tk.BooleanVar(value=False)
        self.repeat_mode = tk.StringVar(value="none") # "none", "one", "all"

        self.volume = self.app_settings.get("music_player_default_volume", 0.7)

        # Variables to hold current song details for Discord RPC
        self.current_rpc_song_title = "No song playing"
        self.current_rpc_artist = "Unknown" # Will be "Unknown Artist" if not found

        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume)
            self.parent.after(100, self._check_music_end) # Start the continuous check
            player_logger.info("Pygame mixer initialized successfully.")
            self.main_app_instance.update_status_message("Music player initialized.", level="info")
        except Exception as e:
            messagebox.showerror("Audio Error", f"Could not initialize audio mixer: {e}")
            player_logger.error(f"Failed to initialize Pygame mixer: {e}")
            self.main_app_instance.update_status_message(f"Audio error: {e}", level="error")

        self.create_widgets()
        self._load_playlist_from_settings()

    def create_widgets(self):
        ttk.Label(self, text="🎵 Music Player 🎵", font=("Arial", 18, "bold")).pack(pady=20)

        playlist_manage_frame = ttk.Frame(self)
        playlist_manage_frame.pack(pady=5)
        ttk.Button(playlist_manage_frame, text="Save Playlist", command=self._save_playlist).pack(side="left", padx=5)
        ttk.Button(playlist_manage_frame, text="Load Playlist", command=self._load_playlist).pack(side="left", padx=5)

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
                                              style="TButton")
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

    def _check_music_end(self):
        """Checks if music has ended and plays the next song, respecting repeat mode."""
        # Only proceed if there's a playlist, a song is meant to be playing, and it's not paused
        if self.playlist and self.current_song_index != -1 and pygame.mixer.music.get_busy() == 0 and not self.paused:
            player_logger.debug(f"Music ended. Repeat mode: {self.repeat_mode.get()}")
            if self.repeat_mode.get() == "one":
                self._play_music(self.current_song_index) # Replay current song
            else:
                self._play_next() # Go to next song (or loop all, or stop)
        
        # Schedule the next check
        self.parent.after(100, self._check_music_end)

    def _update_volume_display(self, value):
        """Updates the music playback volume in mixer and UI."""
        self.volume = float(value)
        pygame.mixer.music.set_volume(self.volume)
        self.volume_label.config(text=f"{int(self.volume * 100)}%")
        player_logger.debug(f"Volume set to {self.volume:.2f}")

    def _save_volume_on_release(self, event=None):
        """Saves the current volume setting to the settings file when slider is released."""
        self.app_settings["music_player_default_volume"] = self.volume
        settings_manager.save_settings(self.app_settings)
        player_logger.info(f"Volume setting saved on slider release: {self.volume:.2f}")
        self.main_app_instance.update_status_message(f"Volume set to {int(self.volume * 100)}% and saved.", level="info")

    def _add_to_playlist(self, file_path):
        """Adds a single file to the playlist and updates the listbox."""
        if file_path and os.path.exists(file_path) and file_path not in self.playlist:
            self.playlist.append(file_path)
            self._update_listbox() 
            player_logger.info(f"Added '{os.path.basename(file_path)}' to playlist.")
            self.main_app_instance.update_status_message(f"Added '{os.path.basename(file_path)}' to playlist.", level="info")
        elif file_path:
            if not os.path.exists(file_path): 
                player_logger.warning(f"Attempted to add '{os.path.basename(file_path)}' but it does not exist.")
                self.main_app_instance.update_status_message(f"File not found: '{os.path.basename(file_path)}'.", level="warning")
            else:
                player_logger.debug(f"Attempted to add '{os.path.basename(file_path)}' but it's already in the playlist.")
                self.main_app_instance.update_status_message(f"'{os.path.basename(file_path)}' is already in the playlist.", level="info")


    def _update_listbox(self):
        """Refreshes the listbox display to reflect the current playlist."""
        self.music_listbox.delete(0, tk.END)
        for song_path in self.playlist:
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
                with open(file_path, 'w') as f:
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
                with open(file_path, 'r') as f:
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
                player_logger.error(f"Error loading playlist from {file_path}: Invalid JSON format.")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load playlist: {e}", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Error loading playlist: {e}", level="error")
                player_logger.error(f"Error loading playlist from {file_path}: {e}")
    
    def _load_playlist_from_settings(self):
        """Loads the saved playlist and volume from app settings on startup."""
        saved_playlist = self.app_settings.get("music_player_playlist", [])
        for path in saved_playlist:
            if os.path.exists(path):
                self.playlist.append(path)
        self._update_listbox()
        player_logger.info(f"Loaded {len(self.playlist)} songs from settings.")
        
        saved_volume = self.app_settings.get("music_player_default_volume")
        if saved_volume is not None:
            self.volume = saved_volume
            self.volume_slider.set(self.volume) # Update slider position
            self._update_volume_display(self.volume) # Update mixer and label

    def _toggle_shuffle_mode(self):
        """Toggles shuffle mode and shuffles/unshuffles the playlist display."""
        if self.shuffle_enabled.get():
            self.main_app_instance.update_status_message("Shuffle mode enabled.", level="info")
            player_logger.info("Shuffle mode enabled.")
        else:
            self.main_app_instance.update_status_message("Shuffle mode disabled.", level="info")
            player_logger.info("Shuffle mode disabled.")

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


    def _browse_single_music_file(self):
        """Opens a file dialog to select a single music file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.aac"), ("All files", "*.*")],
            parent=self
        )
        if file_path:
            self._add_to_playlist(file_path)

    def _browse_music_folder(self):
        """Opens a directory dialog to select a folder and adds all found music files."""
        folder_path = filedialog.askdirectory(parent=self)
        if folder_path:
            count = 0
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".aac")):
                        full_path = os.path.join(root, file)
                        # Call _add_to_playlist directly, which now updates status bar
                        self._add_to_playlist(full_path) 
                        count += 1
            if count > 0:
                self.main_app_instance.update_status_message(f"Added {count} music files from '{os.path.basename(folder_path)}'.", level="info")
                player_logger.info(f"Added {count} files from folder '{folder_path}'.")
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
        else:
            self.main_app_instance.update_status_message("Playlist clear cancelled.", level="info")

    def _play_selected_song(self, event=None):
        """Plays the song selected in the listbox."""
        selected_index = self.music_listbox.curselection()
        if selected_index:
            self.current_song_index = selected_index[0]
            self._play_music(self.current_song_index)

    def _play_music(self, index):
        """Handles actual music playback."""
        if 0 <= index < len(self.playlist):
            song_path = self.playlist[index]
            self.current_song_index = index
            
            # Get MP3 tags for display and RPC
            title, artist = self._get_mp3_tags(song_path)
            self.current_rpc_song_title = title
            self.current_rpc_artist = artist

            # NEW: Conditionally set in-app label text
            if self.current_rpc_artist and self.current_rpc_artist != "Unknown Artist":
                self.current_song_label.config(text=f"Now Playing: {title} by {artist}")
            else:
                self.current_song_label.config(text=f"Now Playing: {title}")

            self.play_pause_button.config(text="⏸️ Pause")
            self.paused = False

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
            self.play_pause_button.config(text="▶️ Play")
            player_logger.info("Music paused.")
            self.main_app_instance.update_status_message("Music paused.", level="info")
            self._update_discord_rpc() # Update RPC after pausing
        elif self.paused: # Music was paused, now unpause
            pygame.mixer.music.unpause()
            self.paused = False
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
        if pygame.mixer.music.get_busy() or self.paused:
            pygame.mixer.music.stop()
        self.play_pause_button.config(text="▶️ Play")
        self.current_song_label.config(text="Now Playing: -")
        self.paused = False
        self.current_song_index = -1
        # Reset RPC song info
        self.current_rpc_song_title = "No song playing"
        self.current_rpc_artist = "Unknown" # Keep "Unknown" here for internal check
        player_logger.info("Music stopped.")
        self.main_app_instance.update_status_message("Music stopped.", level="info")
        self._update_discord_rpc() # Update RPC after stopping


    def _play_next(self):
        """Plays the next song in the playlist, respecting shuffle and repeat modes."""
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

    def _get_mp3_tags(self, path):
        """Extracts title and artist from MP3 tags, or uses filename as fallback."""
        try:
            audio = MP3(path)
            title = audio.get('TIT2', [os.path.basename(path)])[0] # TIT2 is song title
            artist = audio.get('TPE1', ['Unknown Artist'])[0]     # TPE1 is artist
            
            # Ensure they are strings, not objects
            title_str = str(title).strip() if title else os.path.basename(path)
            artist_str = str(artist).strip() if artist else 'Unknown Artist'
            return title_str, artist_str
        except ID3NoHeaderError:
            player_logger.warning(f"No ID3 tags found for '{os.path.basename(path)}'. Using filename.")
            return os.path.basename(path), "Unknown Artist"
        except Exception as e:
            player_logger.error(f"Error reading MP3 tags for '{os.path.basename(path)}': {e}")
            return os.path.basename(path), "Error reading tags"

    def _update_discord_rpc(self):
        """Helper method to update Discord RPC based on current module status."""
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status()
            
            # Pass rpc_buttons from the main app instance to maintain global buttons
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
                start=int(time.time()) if pygame.mixer.music.get_busy() and not self.paused else None, # Only reset time if actually playing
                buttons=rpc_buttons
            )

    # Discord Rich Presence Status Method
    def get_discord_rpc_status(self):
        """
        Returns a dictionary with current details, state, and image assets for Discord Rich Presence.
        """
        # Get default RPC data for this module from MultiAppScreen (for module-specific icons, etc.)
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="player")
        
        details = default_rpc["details"] 
        state = default_rpc["state"]     

        if self.current_song_index != -1 and self.playlist and 0 <= self.current_song_index < len(self.playlist):
            # Music is loaded (potentially playing or paused)
            details = f"Playing: {self.current_rpc_song_title}"
            
            # NEW: Conditionally set state based on artist
            if self.current_rpc_artist and self.current_rpc_artist != "Unknown Artist":
                state = f"by {self.current_rpc_artist}"
            else:
                state = "Music Player" # Fallback state when no artist is known

            if self.paused:
                state = "Paused" 
            elif not pygame.mixer.music.get_busy(): # Loaded but not playing and not paused (e.g. stopped, or just loaded)
                 state = "Stopped"

        elif not self.playlist:
            details = "Music Player"
            state = "Playlist Empty"
        else: # Module is active, but no song loaded/playing
            details = "Music Player"
            state = "No song playing"
            
        return {
            "details": details,
            "state": state,
            "large_image": default_rpc["large_image"], # Uses the module-specific icon
            "large_text": default_rpc["large_text"],
            "small_image": default_rpc["small_image"], # Uses the main app logo
            "small_text": default_rpc["small_text"],
        }


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
        player_logger.debug("MusicPlayerModule UI refreshed.")
        self.main_app_instance.update_status_message("Music Player settings UI refreshed.", level="info")
        # Trigger a Discord RPC update when the module is refreshed/shown
        self._update_discord_rpc()

    def before_hide(self, closing_app=False):
        """Called by main_app.py before the module is hidden or app is closed."""
        # Save the current playlist and volume to settings
        self.app_settings["music_player_playlist"] = self.playlist
        self.app_settings["music_player_default_volume"] = self.volume
        settings_manager.save_settings(self.app_settings)
        player_logger.info("Music Player playlist and volume saved.")
        
        # Stop music playback if app is closing
        if closing_app:
            pygame.mixer.music.stop()
            player_logger.info("Music playback stopped due to app closing.")
        
        player_logger.info("MusicPlayerModule before_hide executed.")
        return True

    def show_about_dialog(self):
        about_text = (
            "Music Player Module\n"
            "Version 1.0.0\n"
            "\n"
            "Simple local music playback functionality.\n"
            "Developed by Z.\n"
            "\n"
            "Thank you for using Zyphria Nexus Multi Use Tool!"
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
            "  - Shuffle (🔀): Toggles random playback order.\n"
            "  - Repeat: Cycles through 'Repeat Off', 'Repeat One Song', and 'Repeat All Songs'.\n"
            "  - Clear Playlist: Removes all songs from the playlist (after confirmation).\n"
            "\n"
            "Supported formats: MP3, WAV, OGG, FLAC, AAC."
        )
        messagebox.showinfo("Music Player Help", help_text, parent=self.winfo_toplevel())
        player_logger.info("Help dialog shown for Music Player.")