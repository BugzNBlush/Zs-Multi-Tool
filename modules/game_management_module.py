# modules/game_management_module.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess # NEW: For more robust game launching
import logging
import time # For Discord RPC timestamps

# Assuming these are correct based on your previous files
from modules.game_loader_data_manager import GameLoaderDataManager
from modules.zyphria_nexus_module import ZyphriaNexusModule
from modules.zyphria_nexus.styles import text_highlight_color
# Removed 'import settings_manager' as it's no longer directly saving global app_settings here

game_management_logger = logging.getLogger(__name__)

class GameManagementModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings # Keep app_settings for ZyphriaNexusModule
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True) # Ensure the frame fills its parent

        # --- Game Launcher specific attributes ---
        # CORRECTED: Initialize GameLoaderDataManager without app_settings
        self.game_loader_dm = GameLoaderDataManager() 
        self.games = [] # Store a local copy of games list for UI display
        self.selected_game_index = -1

        # --- Save Manager specific attributes ---
        self.zyphria_nexus_instance = None # Will be instantiated in create_widgets
        
        self.create_widgets() 
        
        # Load UI after widgets are created
        self._load_game_list_to_ui() 

        game_management_logger.info("GameManagementModule initialized.")
        self.main_app_instance.update_status_message("Game Management module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update now that the module is loaded

    # --- Game Launcher methods (using GameLoaderDataManager) ---
    def _load_game_list_to_ui(self):
        self.game_listbox.delete(0, tk.END)
        # Ensure self.games is updated from the GameLoaderDataManager's internal list
        self.games = self.game_loader_dm.get_games() 
        for i, game in enumerate(self.games):
            self.game_listbox.insert(tk.END, game.get("name", f"Unnamed Game {i+1}"))
        self._update_game_button_states()

    def _add_game(self):
        name = self.game_name_var.get().strip()
        path = self.game_path_var.get().strip()

        if not name or not path:
            messagebox.showwarning("Warning", "Game Name and Path cannot be empty.", parent=self)
            return
        if not os.path.exists(path):
            messagebox.showwarning("Warning", "The specified game path does not exist.", parent=self)
            return

        if self.game_loader_dm.add_game(name, path):
            self._load_game_list_to_ui()
            self.game_name_var.set("")
            self.game_path_var.set("")
            game_management_logger.info(f"Game added: {name}")
            self.main_app_instance.update_status_message(f"Game '{name}' added successfully.", level="info")
            self._update_discord_rpc() # Update RPC after adding game
        else:
            messagebox.showwarning("Warning", f"Game '{name}' already exists.", parent=self)
            self.main_app_instance.update_status_message(f"Game '{name}' already exists. Not added.", level="warning")

    def _remove_game(self):
        if self.selected_game_index != -1:
            game_name = self.games[self.selected_game_index]["name"]
            if self.game_loader_dm.delete_game(game_name):
                self._load_game_list_to_ui()
                self.selected_game_index = -1 # Reset selection
                game_management_logger.info(f"Game removed: {game_name}")
                self.main_app_instance.update_status_message(f"Game '{game_name}' removed.", level="info")
                self._update_discord_rpc() # Update RPC after removing game
            else:
                messagebox.showwarning("Warning", f"Failed to remove game '{game_name}'.", parent=self)
                self.main_app_instance.update_status_message(f"Failed to remove game '{game_name}'.", level="warning")
        else:
            messagebox.showwarning("Warning", "No game selected to remove.", parent=self)
            self.main_app_instance.update_status_message("No game selected to remove.", level="warning")

    def _edit_game(self):
        if self.selected_game_index != -1:
            old_game = self.games[self.selected_game_index]
            old_name = old_game["name"]
            name = self.game_name_var.get().strip()
            path = self.game_path_var.get().strip()

            if not name or not path:
                messagebox.showwarning("Warning", "Game Name and Path cannot be empty.", parent=self)
                return
            if not os.path.exists(path):
                messagebox.showwarning("Warning", "The specified game path does not exist.", parent=self)
                return
            
            if self.game_loader_dm.update_game(old_name, name, path):
                self._load_game_list_to_ui()
                self.selected_game_index = -1 # Reset selection
                self.game_name_var.set("")
                self.game_path_var.set("")
                game_management_logger.info(f"Game edited: {old_name} -> {name}")
                self.main_app_instance.update_status_message(f"Game '{old_name}' updated to '{name}'.", level="info")
                self._update_discord_rpc() # Update RPC after editing game
            else:
                messagebox.showwarning("Warning", f"Failed to update game '{old_name}'.", parent=self)
                self.main_app_instance.update_status_message(f"Failed to update game '{old_name}'.", level="warning")
        else:
            messagebox.showwarning("Warning", "No game selected to edit.", parent=self)
            self.main_app_instance.update_status_message("No game selected to edit.", level="warning")

    def _select_game_path(self):
        file_path = filedialog.askopenfilename(parent=self, title="Select Game Executable",
                                              filetypes=[("Executables", "*.exe"), ("All Files", "*.*")])
        if file_path:
            self.game_path_var.set(file_path)
            if not self.game_name_var.get().strip():
                base_name = os.path.basename(file_path)
                game_name = os.path.splitext(base_name)[0]
                self.game_name_var.set(game_name.replace('_', ' ').replace('-', ' ').title())
            self.main_app_instance.update_status_message(f"Selected executable path: {file_path}", level="info")
        else:
            self.main_app_instance.update_status_message("Game executable path selection cancelled.", level="info")

    def _launch_game(self):
        if self.selected_game_index != -1:
            game = self.games[self.selected_game_index]
            game_name = game.get("name")
            game_path = game.get("path")
            
            if os.path.exists(game_path):
                try:
                    game_dir = os.path.dirname(game_path) # Get directory of the executable
                    subprocess.Popen([game_path], cwd=game_dir, shell=False) # Launch with correct working directory
                    
                    self.main_app_instance.update_status_message(f"Launched {game_name}.", level="info")
                    game_management_logger.info(f"Launched game: {game_name} from {game_path} with CWD: {game_dir}")
                    self._update_discord_rpc(game_name=game_name) # Update RPC to show "Playing Game"
                except Exception as e:
                    messagebox.showerror("Launch Error", f"Could not launch {game_name}: {e}", parent=self)
                    game_management_logger.error(f"Error launching {game_name}: {e}")
                    self.main_app_instance.update_status_message(f"Error launching game '{game_name}'.", level="error")
            else:
                messagebox.showerror("Error", f"Game executable not found at: {game_path}", parent=self)
                game_management_logger.error(f"Game executable not found: {game_path}")
                self.main_app_instance.update_status_message(f"Game executable for '{game_name}' not found.", level="error")
        else:
            messagebox.showwarning("Warning", "No game selected to launch.", parent=self)
            self.main_app_instance.update_status_message("No game selected to launch.", level="warning")

    def _on_game_select(self, event):
        selection = self.game_listbox.curselection()
        if selection:
            self.selected_game_index = selection[0]
            game = self.games[self.selected_game_index]
            self.game_name_var.set(game.get("name", ""))
            self.game_path_var.set(game.get("path", ""))
            self.game_listbox.see(self.selected_game_index) 
        else:
            self.selected_game_index = -1
            self.game_name_var.set("")
            self.game_path_var.set("")
        self._update_game_button_states()
        self._update_discord_rpc() # Update RPC on game selection

    def _move_game_up(self):
        if self.selected_game_index != -1:
            if self.game_loader_dm.move_game_up(self.selected_game_index):
                self._load_game_list_to_ui()
                self.selected_game_index -= 1
                self.game_listbox.selection_set(self.selected_game_index)
                self.game_listbox.see(self.selected_game_index)
                self.main_app_instance.update_status_message("Game moved up.", level="info")
                self._update_discord_rpc() # Update RPC after moving game
            else:
                self.main_app_instance.update_status_message("Cannot move game up further.", level="warning")
        else:
            messagebox.showwarning("Warning", "No game selected to move.", parent=self)

    def _move_game_down(self):
        if self.selected_game_index != -1:
            if self.game_loader_dm.move_game_down(self.selected_game_index):
                self._load_game_list_to_ui()
                self.selected_game_index += 1
                self.game_listbox.selection_set(self.selected_game_index)
                self.game_listbox.see(self.selected_game_index)
                self.main_app_instance.update_status_message("Game moved down.", level="info")
                self._update_discord_rpc() # Update RPC after moving game
            else:
                self.main_app_instance.update_status_message("Cannot move game down further.", level="warning")
        else:
            messagebox.showwarning("Warning", "No game selected to move.", parent=self)

    def _update_game_button_states(self):
        is_selected = self.selected_game_index != -1
        self.edit_game_button.config(state=tk.NORMAL if is_selected else tk.DISABLED)
        self.remove_game_button.config(state=tk.NORMAL if is_selected else tk.DISABLED)
        self.launch_game_button.config(state=tk.NORMAL if is_selected else tk.DISABLED)
        
        can_move_up = is_selected and self.selected_game_index > 0
        can_move_down = is_selected and self.selected_game_index < len(self.games) - 1
        self.move_up_button.config(state=tk.NORMAL if can_move_up else tk.DISABLED)
        self.move_down_button.config(state=tk.NORMAL if can_move_down else tk.DISABLED)

    # --- Unified Widget Creation ---
    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # Game Launcher Tab
        self.game_launcher_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.game_launcher_tab, text="Game Launcher")
        self._create_game_launcher_widgets(self.game_launcher_tab)

        # Save Manager Tab
        self.save_manager_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.save_manager_tab, text="Save Manager")
        
        # ZyphriaNexusModule is now passed the same app_settings as GameManagementModule
        self.zyphria_nexus_instance = ZyphriaNexusModule(self.save_manager_tab, self.app_settings, self.main_app_instance)
        self.zyphria_nexus_instance.pack(fill=tk.BOTH, expand=True)


    def _create_game_launcher_widgets(self, parent_frame):
        entry_frame = ttk.LabelFrame(parent_frame, text=" Add/Edit Game ")
        entry_frame.pack(fill=tk.X, padx=10, pady=5)

        self.game_name_var = tk.StringVar()
        ttk.Label(entry_frame, text="Game Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.game_name_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        self.game_path_var = tk.StringVar()
        ttk.Label(entry_frame, text="Executable Path:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        # Kept as readonly based on your previous code/preference
        ttk.Entry(entry_frame, textvariable=self.game_path_var, state="readonly").grid(row=1, column=1, padx=5, pady=2, sticky="ew") 
        ttk.Button(entry_frame, text="Browse", command=self._select_game_path).grid(row=1, column=2, padx=5, pady=2)

        entry_frame.grid_columnconfigure(1, weight=1)

        button_frame = ttk.Frame(entry_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=5)
        ttk.Button(button_frame, text="Add Game", command=self._add_game).pack(side=tk.LEFT, padx=5)
        self.edit_game_button = ttk.Button(button_frame, text="Update Game", command=self._edit_game, state=tk.DISABLED)
        self.edit_game_button.pack(side=tk.LEFT, padx=5)
        self.remove_game_button = ttk.Button(button_frame, text="Remove Game", command=self._remove_game, state=tk.DISABLED)
        self.remove_game_button.pack(side=tk.LEFT, padx=5)

        list_frame = ttk.LabelFrame(parent_frame, text=" Your Games ")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.game_listbox = tk.Listbox(list_frame, height=10, bg="#2A2A2A", fg="#00FFFF", selectbackground=text_highlight_color, activestyle="none")
        self.game_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.game_listbox.bind("<<ListboxSelect>>", self._on_game_select)

        game_list_scroll = ttk.Scrollbar(list_frame, command=self.game_listbox.yview)
        game_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.game_listbox.config(yscrollcommand=game_list_scroll.set)

        move_buttons_frame = ttk.Frame(parent_frame)
        move_buttons_frame.pack(fill=tk.X, padx=10, pady=(0,5))
        self.move_up_button = ttk.Button(move_buttons_frame, text="Move Up ↑", command=self._move_game_up, state=tk.DISABLED)
        self.move_up_button.pack(side=tk.LEFT, expand=True, padx=5)
        self.move_down_button = ttk.Button(move_buttons_frame, text="Move Down ↓", command=self._move_game_down, state=tk.DISABLED)
        self.move_down_button.pack(side=tk.LEFT, expand=True, padx=5)

        self.launch_game_button = ttk.Button(parent_frame, text="Launch Selected Game", command=self._launch_game, state=tk.DISABLED)
        self.launch_game_button.pack(fill=tk.X, padx=10, pady=10)

    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self, game_name=None):
        """Helper method to update Discord RPC based on current module status."""
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status(game_name=game_name)
            
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
                start=int(time.time()), # Reset activity timer
                buttons=rpc_buttons
            )

    def get_discord_rpc_status(self, game_name=None):
        """
        Returns a dictionary with current details, state, and image assets for Discord Rich Presence.
        """
        # Fallback to the main app's RPC getter for default values like small_image/text
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="game_management")
        
        details_text = "Managing Game Library"
        state_text = "Idle"
        if game_name: # If a game name is passed, assume it's currently launching/playing
            details_text = f"Playing {game_name}"
            state_text = "Having fun!"
        elif self.selected_game_index != -1 and self.games: # Check if a game is selected in the UI
            selected_game_display_name = self.games[self.selected_game_index].get("name", "Unknown Game")
            details_text = f"Selected: {selected_game_display_name}"
            state_text = "Ready to launch"
            
        return {
            "details": details_text,
            "state": state_text,
            "large_image": default_rpc.get("large_image", "game_management_icon"), # Use specific icon if available, else app_logo
            "large_text": "Game Management",
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": default_rpc.get("small_text", "Zyphria Nexus"),
        }
    
    # --- Menubar Commands for the Module ---
    def get_menubar_commands(self):
        # Initialize with the overall module's help commands
        all_help_commands = [
            ("Game Management About", self._show_about_dialog),
            ("Game Launcher Help", self._show_game_launcher_help_dialog),
        ]
        
        combined_file_commands = [] # For file menu (e.g., Export/Import)

        if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'get_menubar_commands'):
            save_manager_specific_commands = self.zyphria_nexus_instance.get_menubar_commands()
            
            # Extract specific Save Manager help and file commands
            sm_about = None
            sm_help = None
            
            if "help_commands" in save_manager_specific_commands and save_manager_specific_commands["help_commands"]:
                for label, command in save_manager_specific_commands["help_commands"]:
                    if label == "About Save Manager":
                        sm_about = (label, command)
                    elif label == "Save Manager Help":
                        sm_help = (label, command)

            # Add Save Manager's specific help content 
            if sm_help:
                all_help_commands.append(sm_help)
            
            # Add a separator before more specific 'About' for the embedded component
            if sm_about:
                all_help_commands.append(None) # Separator
                all_help_commands.append(sm_about)
            
            # Aggregate file commands from Save Manager
            if "file_commands" in save_manager_specific_commands and save_manager_specific_commands["file_commands"]:
                combined_file_commands.extend(save_manager_specific_commands["file_commands"])
        
        return {
            "file_commands": combined_file_commands if combined_file_commands else None,
            "help_commands": all_help_commands
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About Game Management",
            "This module provides tools for managing your games and their associated save files or other related documents.\n\n"
            "The Game Launcher tab allows you to quickly launch configured games.\n"
            "The Save Manager tab helps you keep track of game projects and their important files.",
            parent=self.winfo_toplevel()
        )
        game_management_logger.info("About dialog shown for Game Management.")

    def _show_game_launcher_help_dialog(self):
        help_text = (
            "Game Launcher Help Guide:\n\n"
            "1. Enter the 'Game Name' and 'Executable Path' for a game.\n"
            "2. Use 'Browse' to find the game's executable file.\n"
            "3. Click 'Add Game' to save it to your list.\n"
            "4. Select a game from the list to 'Update Game', 'Remove Game', or 'Launch Selected Game'.\n"
            "5. Use 'Move Up ↑' and 'Move Down ↓' buttons to reorder games in the list.\n\n"
            "Tip: You can use the 'Update Game' button to change the name or path of an existing game."
        )
        messagebox.showinfo(
            "Game Launcher Help",
            help_text,
            parent=self.winfo_toplevel()
        )
        game_management_logger.info("Game Launcher help dialog shown.")

    # Removed _show_game_scanner_help_dialog (as Scanner is removed)
    
    def before_hide(self, closing_app=False):
        # CORRECTED: Call GameLoaderDataManager's specific save method
        self.game_loader_dm.save_all_games()
        game_management_logger.info("GameLoaderDataManager state saved via DM's method.")
        
        # Call before_hide for the embedded ZyphriaNexusModule if it exists
        if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'before_hide'):
            self.zyphria_nexus_instance.before_hide(closing_app)
        
        return True # Always allow hiding

    def refresh_settings_ui(self):
        # Refresh the game list in the UI (reloads from GameLoaderDataManager's internal state)
        self._load_game_list_to_ui()
        
        # Refresh embedded ZyphriaNexusModule if it exists
        if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'refresh_settings_ui'):
            self.zyphria_nexus_instance.refresh_settings_ui()
        
        self._update_discord_rpc() # Update RPC on refresh