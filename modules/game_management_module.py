import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess 
import logging
import time 

from modules.game_loader_data_manager import GameLoaderDataManager
from modules.zyphria_nexus_module import ZyphriaNexusModule
from modules.zyphria_nexus.styles import text_highlight_color
import settings_manager # Added for APP_NAME consistency in dialogs and RPC

game_management_logger = logging.getLogger(__name__)

class GameManagementModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings 
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True) 

        # --- Application Launcher specific attributes ---
        self.game_loader_dm = GameLoaderDataManager() 
        self.games = [] 
        self.selected_game_index = -1

        # --- Save Manager specific attributes ---
        self.zyphria_nexus_instance = None 
        
        self.create_widgets() 
        
        # Load UI after widgets are created
        self._load_game_list_to_ui() 

        game_management_logger.info("GameManagementModule initialized.")
        self.main_app_instance.update_status_message("Application Management module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update now that the module is loaded

    # --- Application Launcher methods (using GameLoaderDataManager) ---
    def _load_game_list_to_ui(self):
        self.game_listbox.delete(0, tk.END)
        self.games = self.game_loader_dm.get_games() 
        for i, game in enumerate(self.games):
            self.game_listbox.insert(tk.END, game.get("name", f"Unnamed Application {i+1}"))
        self._update_game_button_states()

    def _add_game(self):
        name = self.game_name_var.get().strip()
        path = self.game_path_var.get().strip()

        if not name or not path:
            messagebox.showwarning("Warning", "Application Name and Path cannot be empty.", parent=self)
            return
        if not os.path.exists(path):
            messagebox.showwarning("Warning", "The specified application path does not exist.", parent=self)
            return

        if self.game_loader_dm.add_game(name, path):
            self._load_game_list_to_ui()
            self.game_name_var.set("")
            self.game_path_var.set("")
            game_management_logger.info(f"Application added: {name}")
            self.main_app_instance.update_status_message(f"Application '{name}' added successfully.", level="info")
            self._update_discord_rpc() 
        else:
            messagebox.showwarning("Warning", f"Application '{name}' already exists.", parent=self)
            self.main_app_instance.update_status_message(f"Application '{name}' already exists. Not added.", level="warning")

    def _remove_game(self):
        if self.selected_game_index != -1:
            game_name = self.games[self.selected_game_index]["name"]
            if self.game_loader_dm.delete_game(game_name):
                self._load_game_list_to_ui()
                self.selected_game_index = -1 
                game_management_logger.info(f"Application removed: {game_name}")
                self.main_app_instance.update_status_message(f"Application '{game_name}' removed.", level="info")
                self._update_discord_rpc() 
            else:
                messagebox.showwarning("Warning", f"Failed to remove application '{game_name}'.", parent=self)
                self.main_app_instance.update_status_message(f"Failed to remove application '{game_name}'.", level="warning")
        else:
            messagebox.showwarning("Warning", "No application selected to remove.", parent=self)
            self.main_app_instance.update_status_message("No application selected to remove.", level="warning")

    def _edit_game(self):
        if self.selected_game_index != -1:
            old_game = self.games[self.selected_game_index]
            old_name = old_game["name"]
            name = self.game_name_var.get().strip()
            path = self.game_path_var.get().strip()

            if not name or not path:
                messagebox.showwarning("Warning", "Application Name and Path cannot be empty.", parent=self)
                return
            if not os.path.exists(path):
                messagebox.showwarning("Warning", "The specified application path does not exist.", parent=self)
                return
            
            if self.game_loader_dm.update_game(old_name, name, path):
                self._load_game_list_to_ui()
                self.selected_game_index = -1 
                self.game_name_var.set("")
                self.game_path_var.set("")
                game_management_logger.info(f"Application edited: {old_name} -> {name}")
                self.main_app_instance.update_status_message(f"Application '{old_name}' updated to '{name}'.", level="info")
                self._update_discord_rpc() 
            else:
                messagebox.showwarning("Warning", f"Failed to update application '{old_name}'.", parent=self)
                self.main_app_instance.update_status_message(f"Failed to update application '{old_name}'.", level="warning")
        else:
            messagebox.showwarning("Warning", "No application selected to edit.", parent=self)
            self.main_app_instance.update_status_message("No application selected to edit.", level="warning")

    def _select_game_path(self):
        file_path = filedialog.askopenfilename(parent=self, title="Select Application Executable",
                                              filetypes=[("Executables", "*.exe"), ("All Files", "*.*")])
        if file_path:
            self.game_path_var.set(file_path)
            if not self.game_name_var.get().strip():
                base_name = os.path.basename(file_path)
                game_name = os.path.splitext(base_name)[0]
                self.game_name_var.set(game_name.replace('_', ' ').replace('-', ' ').title())
            self.main_app_instance.update_status_message(f"Selected executable path: {file_path}", level="info")
        else:
            self.main_app_instance.update_status_message("Application executable path selection cancelled.", level="info")

    def _launch_game(self):
        if self.selected_game_index != -1:
            game = self.games[self.selected_game_index]
            game_name = game.get("name")
            game_path = game.get("path")
            
            if os.path.exists(game_path):
                try:
                    game_dir = os.path.dirname(game_path) # Get directory of the executable
                    subprocess.Popen([game_path], cwd=game_dir, shell=False) 
                    
                    self.main_app_instance.update_status_message(f"Launched {game_name}.", level="info")
                    game_management_logger.info(f"Launched application: {game_name} from {game_path} with CWD: {game_dir}")
                    self._update_discord_rpc(game_name=game_name) 
                except Exception as e:
                    messagebox.showerror("Launch Error", f"Could not launch {game_name}: {e}", parent=self)
                    game_management_logger.error(f"Error launching {game_name}: {e}")
                    self.main_app_instance.update_status_message(f"Error launching application '{game_name}'.", level="error")
            else:
                messagebox.showerror("Error", f"Application executable not found at: {game_path}", parent=self)
                game_management_logger.error(f"Application executable not found: {game_path}")
                self.main_app_instance.update_status_message(f"Application executable for '{game_name}' not found.", level="error")
        else:
            messagebox.showwarning("Warning", "No application selected to launch.", parent=self)
            self.main_app_instance.update_status_message("No application selected to launch.", level="warning")

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
        self._update_discord_rpc() 

    def _move_game_up(self):
        if self.selected_game_index != -1:
            if self.game_loader_dm.move_game_up(self.selected_game_index):
                self._load_game_list_to_ui()
                self.selected_game_index -= 1
                self.game_listbox.selection_set(self.selected_game_index)
                self.game_listbox.see(self.selected_game_index)
                self.main_app_instance.update_status_message("Application moved up.", level="info")
                self._update_discord_rpc() 
            else:
                self.main_app_instance.update_status_message("Cannot move application up further.", level="warning")
        else:
            messagebox.showwarning("Warning", "No application selected to move.", parent=self)

    def _move_game_down(self):
        if self.selected_game_index != -1:
            if self.game_loader_dm.move_game_down(self.selected_game_index):
                self._load_game_list_to_ui()
                self.selected_game_index += 1
                self.game_listbox.selection_set(self.selected_game_index)
                self.game_listbox.see(self.selected_game_index)
                self.main_app_instance.update_status_message("Application moved down.", level="info")
                self._update_discord_rpc() 
            else:
                self.main_app_instance.update_status_message("Cannot move application down further.", level="warning")
        else:
            messagebox.showwarning("Warning", "No application selected to move.", parent=self)

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
        # NEW: Bind to tab change event for RPC updates
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Application Launcher Tab
        self.game_launcher_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.game_launcher_tab, text="Application Launcher")
        self._create_game_launcher_widgets(self.game_launcher_tab)

        # Save Manager Tab
        self.save_manager_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.save_manager_tab, text="Save Manager")
        
        self.zyphria_nexus_instance = ZyphriaNexusModule(self.save_manager_tab, self.app_settings, self.main_app_instance)
        self.zyphria_nexus_instance.pack(fill=tk.BOTH, expand=True)

    def _create_game_launcher_widgets(self, parent_frame):
        entry_frame = ttk.LabelFrame(parent_frame, text=" Add/Edit Application ")
        entry_frame.pack(fill=tk.X, padx=10, pady=5)

        self.game_name_var = tk.StringVar()
        ttk.Label(entry_frame, text="Application Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.game_name_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        self.game_path_var = tk.StringVar()
        ttk.Label(entry_frame, text="Executable Path:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(entry_frame, textvariable=self.game_path_var, state="readonly").grid(row=1, column=1, padx=5, pady=2, sticky="ew") 
        ttk.Button(entry_frame, text="Browse", command=self._select_game_path).grid(row=1, column=2, padx=5, pady=2)

        entry_frame.grid_columnconfigure(1, weight=1)

        button_frame = ttk.Frame(entry_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=5)
        ttk.Button(button_frame, text="Add Application", command=self._add_game).pack(side=tk.LEFT, padx=5)
        self.edit_game_button = ttk.Button(button_frame, text="Update Application", command=self._edit_game, state=tk.DISABLED)
        self.edit_game_button.pack(side=tk.LEFT, padx=5)
        self.remove_game_button = ttk.Button(button_frame, text="Remove Application", command=self._remove_game, state=tk.DISABLED)
        self.remove_game_button.pack(side=tk.LEFT, padx=5)

        list_frame = ttk.LabelFrame(parent_frame, text=" My Library ")
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

        self.launch_game_button = ttk.Button(parent_frame, text="Launch Selected Application", command=self._launch_game, state=tk.DISABLED)
        self.launch_game_button.pack(fill=tk.X, padx=10, pady=10)

    # NEW: Handle tab changes for Discord RPC
    def _on_tab_change(self, event):
        self._update_discord_rpc()

    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self, game_name=None):
        """Helper method to update Discord RPC based on current module status."""
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status(game_name=game_name)
            
            rpc_buttons = [
                {"label": "GitHub Repo", "url": "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool"},
                {"label": "Support Discord", "url": "https://discord.gg/vSX49HJMHS"}
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

    def get_discord_rpc_status(self, game_name=None):
        """
        Returns a dictionary with current details, state, and image assets for Discord Rich Presence.
        """
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="game_management")
        
        # Determine which tab is currently selected
        selected_tab_id = self.notebook.select()
        selected_tab_text = self.notebook.tab(selected_tab_id, "text")

        details_text = "Managing Applications"
        state_text = ""
        large_image_asset = default_rpc.get("large_image", "game_management_icon")
        large_text_asset = "Application Management"

        if selected_tab_text == "Application Launcher":
            details_text = "Browsing Applications"
            if game_name: 
                details_text = f"Playing {game_name}"
                state_text = "Having fun!"
            elif self.selected_game_index != -1 and self.games:
                selected_game_display_name = self.games[self.selected_game_index].get("name", "Unknown Application")
                details_text = f"Selected: {selected_game_display_name}"
                state_text = "Ready to launch"
            else:
                state_text = "Idle"
            large_image_asset = "game_management_icon" 
            large_text_asset = "Application Launcher"

        elif selected_tab_text == "Save Manager":
            details_text = "Managing Save Files"
            state_text = "Organizing projects"
            large_image_asset = "save_manager_icon" 
            large_text_asset = "Save Manager"
            # Delegate to ZyphriaNexusModule's RPC if available and more specific
            if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'get_discord_rpc_status'):
                 sm_rpc = self.zyphria_nexus_instance.get_discord_rpc_status()
                 details_text = sm_rpc.get("details", details_text)
                 state_text = sm_rpc.get("state", state_text)
                 large_image_asset = sm_rpc.get("large_image", large_image_asset)
                 large_text_asset = sm_rpc.get("large_text", large_text_asset)
            
        return {
            "details": details_text,
            "state": state_text,
            "large_image": large_image_asset,
            "large_text": large_text_asset,
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": self.main_app_instance.base_title, 
        }
    
    # --- Menubar Commands for the Module ---
    def get_menubar_commands(self):
        all_help_commands = [
            ("Application Management About", self._show_about_dialog),
            ("Application Launcher Help", self._show_game_launcher_help_dialog),
        ]
        
        combined_file_commands = [] 

        if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'get_menubar_commands'):
            save_manager_specific_commands = self.zyphria_nexus_instance.get_menubar_commands()
            
            sm_about = None
            
            if "help_commands" in save_manager_specific_commands and save_manager_specific_commands["help_commands"]:
                for label, command in save_manager_specific_commands["help_commands"]:
                    if label == "About Save Manager":
                        sm_about = (label, command)
                    elif label == "Save Manager Help":
                        all_help_commands.append((label, command)) 

            if sm_about:
                all_help_commands.append(None) # Separator
                all_help_commands.append(sm_about)
            
            if "file_commands" in save_manager_specific_commands and save_manager_specific_commands["file_commands"]:
                combined_file_commands.extend(save_manager_specific_commands["file_commands"])

        return {
            "file_commands": combined_file_commands if combined_file_commands else None,
            "help_commands": all_help_commands
        }


    def _show_about_dialog(self):
        messagebox.showinfo(
            "About Application Management",
            f"This module provides tools for managing your applications and their associated save files or other related documents for {settings_manager.APP_NAME}.\n\n" # CHANGED: Using settings_manager.APP_NAME
            "The Application Launcher tab allows you to quickly launch configured applications.\n"
            "The Save Manager tab helps you keep track of application projects and their important files.",
            parent=self.winfo_toplevel()
        )
        game_management_logger.info("About dialog shown for Application Management.")

    def _show_game_launcher_help_dialog(self):
        help_text = (
            "Application Launcher Help Guide:\n\n" 
            "1. Enter the 'Application Name' and 'Executable Path' for an application.\n" 
            "2. Use 'Browse' to find the application's executable file.\n" 
            "3. Click 'Add Application' to save it to your library.\n" 
            "4. Select an application from the list to 'Update Application', 'Remove Application', or 'Launch Selected Application'.\n" 
            "5. Use 'Move Up ↑' and 'Move Down ↓' buttons to reorder applications in the list.\n\n" 
            "Tip: You can use the 'Update Application' button to change the name or path of an existing application." 
        )
        messagebox.showinfo(
            "Application Launcher Help", 
            help_text,
            parent=self.winfo_toplevel()
        )
        game_management_logger.info("Application Launcher help dialog shown.")

    def before_hide(self, closing_app=False):
        self.game_loader_dm.save_all_games()
        game_management_logger.info("GameLoaderDataManager state saved via DM's method.")
        
        if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'before_hide'):
            self.zyphria_nexus_instance.before_hide(closing_app)
        
        self._update_discord_rpc() # Update RPC to reflect module is no longer active (or changed status)
        return True 

    def refresh_settings_ui(self):
        self._load_game_list_to_ui()
        
        if self.zyphria_nexus_instance and hasattr(self.zyphria_nexus_instance, 'refresh_settings_ui'):
            self.zyphria_nexus_instance.refresh_settings_ui()
        
        self._update_discord_rpc()