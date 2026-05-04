# modules/zyphria_nexus/gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, subprocess, logging
from modules.zyphria_nexus import file_operations, dialogs
import shutil
from modules.zyphria_nexus.styles import text_highlight_color # NEW: Import text_highlight_color for consistency

gui_logger = logging.getLogger(__name__)

class ZyphriaDashboard(ttk.Frame):
    def __init__(self, parent, data_manager, main_app_instance):
        super().__init__(parent)
        self.dm = data_manager
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)
        self.split = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.split.pack(fill=tk.BOTH, expand=True)

        # Sidebar: Games List
        self.side = ttk.Frame(self.split, width=200, padding=10)
        self.split.add(self.side, weight=1)

        # Holgram Ghost Selection for game_list
        self.game_list = tk.Listbox(self.side,
                                    bg="#2A2A2A",
                                    fg="white",
                                    font=("Segoe UI", 10),
                                    highlightthickness=0,
                                    selectbackground=text_highlight_color,
                                    selectforeground="#00FFFF",
                                    borderwidth=0,
                                    activestyle="none")
        self.game_list.pack(fill=tk.BOTH, expand=True)
        self.game_list.bind("<<ListboxSelect>>", self.on_game_select)

        # Sidebar Buttons (+ and -) and Move Up/Down buttons
        btn_f = ttk.Frame(self.side)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="+ Add Game", command=self.add_game).pack(side=tk.LEFT, expand=True)
        ttk.Button(btn_f, text="- Delete", command=self.del_game).pack(side=tk.LEFT, expand=True)

        # NEW: Move Up/Down buttons for game_list
        move_buttons_f = ttk.Frame(self.side)
        move_buttons_f.pack(fill=tk.X, pady=(0, 5))
        self.move_profile_up_button = ttk.Button(move_buttons_f, text="Move Up ↑", command=self._move_profile_up, state=tk.DISABLED)
        self.move_profile_up_button.pack(side=tk.LEFT, expand=True, padx=2)
        self.move_profile_down_button = ttk.Button(move_buttons_f, text="Move Down ↓", command=self._move_profile_down, state=tk.DISABLED)
        self.move_profile_down_button.pack(side=tk.LEFT, expand=True, padx=2)


        # Workspace (Right Pane)
        self.work = ttk.Frame(self.split, padding=10)
        self.split.add(self.work, weight=4)

        # Configuration: Game Save Location Path Entry
        path_f = ttk.LabelFrame(self.work, text=" Game Save Location ")
        path_f.pack(fill=tk.X, pady=5)
        self.save_p = tk.StringVar()
        ttk.Entry(path_f, textvariable=self.save_p).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=10)
        ttk.Button(path_f, text="Browse", command=self.browse_save).pack(side=tk.LEFT, padx=5)

        # Default Backup Location Configuration
        backup_path_f = ttk.LabelFrame(self.work, text=" Default Backup Location ")
        backup_path_f.pack(fill=tk.X, pady=5)
        self.default_backup_p = tk.StringVar()
        ttk.Entry(backup_path_f, textvariable=self.default_backup_p).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=10)
        ttk.Button(backup_path_f, text="Browse", command=self.browse_default_backup).pack(side=tk.LEFT, padx=5)


        # Dashboard Split: Saves vs Tools
        self.c_split = ttk.PanedWindow(self.work, orient=tk.HORIZONTAL)
        self.c_split.pack(fill=tk.BOTH, expand=True)

        # Left Column (within Dashboard Split): Saves & Permissions
        self.s_col = ttk.LabelFrame(self.c_split, text=" Saves & Permissions ")
        self.c_split.add(self.s_col, weight=1)

        self.s_tree = ttk.Treeview(self.s_col, columns=("S", "P"), show="tree headings", selectmode="extended")

        self.s_tree.column("#0", width=250, anchor="w", stretch=True)
        self.s_tree.heading("#0", text="File Name")

        self.s_tree.heading("S", text="Status")
        self.s_tree.heading("P", text="Path")
        self.s_tree.column("S", width=120, stretch=False)
        self.s_tree.column("P", width=0, stretch=False)

        self.s_tree.pack(fill=tk.BOTH, expand=True)

        # Backup/Restore Buttons
        backup_restore_f = ttk.Frame(self.s_col)
        backup_restore_f.pack(fill=tk.X, pady=5)
        ttk.Button(backup_restore_f, text="Backup Saves", command=self.backup_saves).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(backup_restore_f, text="Restore Saves", command=self.restore_saves).pack(side=tk.LEFT, expand=True, padx=2)

        # Existing ACL buttons frame
        acl_f = ttk.Frame(self.s_col)
        acl_f.pack(fill=tk.X)
        ttk.Button(acl_f, text="LOCK (ACL)", command=lambda: self.run_acl(True)).pack(side=tk.LEFT, expand=True, padx=2, pady=5)
        ttk.Button(acl_f, text="UNLOCK", command=lambda: self.run_acl(False)).pack(side=tk.LEFT, expand=True, padx=2, pady=5)

        # Right Column (within Dashboard Split): Tool Launcher
        self.e_col = ttk.LabelFrame(self.c_split, text=" Tool Launcher ")
        self.c_split.add(self.e_col, weight=1)

        self.e_tree = ttk.Treeview(self.e_col, show="tree headings", columns=("P",))
        self.e_tree.heading("#0", text="Tool Name")
        self.e_tree.heading("P", text="Path")
        self.e_tree.column("P", width=0, stretch=False)
        self.e_tree.pack(fill=tk.BOTH, expand=True)

        ttk.Button(self.e_col, text="LAUNCH TOOL", command=self.launch).pack(fill=tk.X, pady=2)
        ttk.Button(self.e_col, text="+ Add Tool", command=self.add_tool).pack(fill=tk.X, pady=2)
        ttk.Button(self.e_col, text="- Delete Tool", command=self.delete_tool).pack(fill=tk.X, pady=2)


    # --- GUI Refresh and Event Handlers ---

    def refresh_games(self):
        gui_logger.debug("Refreshing game list.")
        self.game_list.delete(0, tk.END)
        # Get profiles from DM
        profiles = self.dm.get_profiles() 
        for p in profiles:
            self.game_list.insert(tk.END, p['name'])
        
        # Reselect the previously selected game if it still exists
        current_selection_index = -1
        if self.game_list.size() > 0 and hasattr(self, '_last_selected_game_name'):
            for i, profile in enumerate(profiles):
                if profile['name'] == self._last_selected_game_name:
                    current_selection_index = i
                    break
        
        if current_selection_index != -1:
            self.game_list.selection_set(current_selection_index)
            self.game_list.see(current_selection_index) # Scroll to it
            # Manually trigger on_game_select to refresh details
            self.on_game_select(None) 
        elif self.game_list.size() > 0: # If previous selection gone, or no previous selection, select first
            self.game_list.selection_set(0)
            self.on_game_select(None)
        else: # No games in list
            self.on_game_select(None) # Clear details
            
        self._update_profile_move_button_states() # Update button states after refresh
        self.main_app_instance.update_status_message(f"Game list refreshed. {len(self.dm.profiles)} profiles loaded.", level="info")

    def on_game_select(self, e):
        sel = self.game_list.curselection()
        if not sel:
            self.save_p.set('')
            self.default_backup_p.set('')
            self.s_tree.delete(*self.s_tree.get_children())
            self.e_tree.delete(*self.e_tree.get_children())
            self._last_selected_game_name = None # Clear last selected game name
            gui_logger.debug("No game selected, clearing details.")
            self.main_app_instance.update_status_message("No game selected, clearing details.", level="info")
            self._update_profile_move_button_states() # Update button states
            return

        selected_index = sel[0]
        game_name = self.game_list.get(selected_index)
        self._last_selected_game_name = game_name # Store last selected game name
        p = self.dm.get_profile(game_name)

        if p:
            self.save_p.set(p.get('saves_path', ''))
            self.default_backup_p.set(p.get('default_backup_path', ''))
            self.refresh_files()
            self.refresh_tools(p)
            gui_logger.info(f"Game '{game_name}' selected. Details loaded.")
            self.main_app_instance.update_status_message(f"Game '{game_name}' selected. Details loaded.", level="info")
        else:
            self.save_p.set('')
            self.default_backup_p.set('')
            self.s_tree.delete(*self.s_tree.get_children())
            self.e_tree.delete(*self.e_tree.get_children())
            gui_logger.warning(f"Profile for '{game_name}' not found, clearing details.")
            self.main_app_instance.update_status_message(f"Error: Profile for '{game_name}' not found.", level="error")
        self._update_profile_move_button_states() # Update button states after selection

    def _move_profile_up(self):
        sel = self.game_list.curselection()
        if sel:
            index = sel[0]
            if self.dm.move_profile_up(index):
                self.refresh_games() # Refresh list to reflect new order
                # Reselect the moved item at its new index
                self.game_list.selection_set(index - 1)
                self.game_list.see(index - 1)
                self.main_app_instance.update_status_message("Game profile moved up.", level="info")
            else:
                self.main_app_instance.update_status_message("Cannot move game profile up further.", level="warning")
        else:
            messagebox.showwarning("No Profile Selected", "Please select a game profile to move.", parent=self)

    def _move_profile_down(self):
        sel = self.game_list.curselection()
        if sel:
            index = sel[0]
            if self.dm.move_profile_down(index):
                self.refresh_games() # Refresh list to reflect new order
                # Reselect the moved item at its new index
                self.game_list.selection_set(index + 1)
                self.game_list.see(index + 1)
                self.main_app_instance.update_status_message("Game profile moved down.", level="info")
            else:
                self.main_app_instance.update_status_message("Cannot move game profile down further.", level="warning")
        else:
            messagebox.showwarning("No Profile Selected", "Please select a game profile to move.", parent=self)

    def _update_profile_move_button_states(self):
        sel = self.game_list.curselection()
        if sel:
            index = sel[0]
            num_profiles = len(self.dm.get_profiles())
            
            can_move_up = index > 0
            can_move_down = index < num_profiles - 1

            self.move_profile_up_button.config(state=tk.NORMAL if can_move_up else tk.DISABLED)
            self.move_profile_down_button.config(state=tk.NORMAL if can_move_down else tk.DISABLED)
        else:
            self.move_profile_up_button.config(state=tk.DISABLED)
            self.move_profile_down_button.config(state=tk.DISABLED)

    def refresh_files(self):
        gui_logger.debug("Refreshing save files list.")
        self.s_tree.delete(*self.s_tree.get_children())
        current_save_path = self.save_p.get()
        if not os.path.isdir(current_save_path):
            gui_logger.warning(f"Save path '{current_save_path}' is not a valid directory.")
            self.main_app_instance.update_status_message(f"Warning: Save path '{current_save_path}' is not valid.", level="warning")
            return

        file_count = 0
        for f_info in file_operations.get_save_files_in_directory(current_save_path):
            s = "🔒 LOCKED" if f_info['is_readonly'] else "🔓 UNLOCKED"
            self.s_tree.insert("", "end", text=f_info['filename'], values=(s, f_info['full_path']))
            file_count += 1
        self.main_app_instance.update_status_message(f"Refreshed save files: {file_count} found.", level="info")

    def refresh_tools(self, profile):
        gui_logger.debug(f"Refreshing tools for profile: {profile['name']}.")
        self.e_tree.delete(*self.e_tree.get_children())
        tool_count = 0
        for ed in profile['editors']:
            self.e_tree.insert("", "end", text=ed['name'], values=(ed['path'],))
            tool_count += 1
        self.main_app_instance.update_status_message(f"Refreshed tools: {tool_count} found for {profile['name']}.", level="info")

    def run_acl(self, lock):
        sel = self.s_tree.selection()
        if not sel:
            messagebox.showwarning("No File Selected", "Please select a file to lock/unlock.", parent=self)
            gui_logger.warning("ACL operation attempted without file selection.")
            self.main_app_instance.update_status_message("No file selected for ACL operation.", level="warning")
            return

        selected_file_paths = []
        for item_id in sel:
            full_path = self.s_tree.item(item_id, "values")[1]
            selected_file_paths.append(full_path)

        if not selected_file_paths:
             messagebox.showwarning("No File Selected", "Please select a valid file to lock/unlock.", parent=self)
             gui_logger.warning("ACL operation attempted with invalid file selection.")
             self.main_app_instance.update_status_message("No valid file selected for ACL operation.", level="warning")
             return

        action_word = "LOCK" if lock else "UNLOCK"
        gui_logger.info(f"Starting ACL {action_word} for {len(selected_file_paths)} files.")
        self.main_app_instance.update_status_message(f"Attempting to {action_word.lower()} {len(selected_file_paths)} file(s)...", level="info")

        success_count = 0
        failed_files = []

        for file_path in selected_file_paths:
            try:
                file_operations.set_read_only_status(file_path, lock)
                success_count += 1
            except PermissionError as e:
                failed_files.append(f"{os.path.basename(file_path)} (Permission Error: {e.args[0]})")
                gui_logger.error(f"Permission error during ACL {action_word} for '{file_path}': {e}")
            except NotImplementedError as e:
                messagebox.showerror("ACL Error", str(e), parent=self)
                gui_logger.critical(f"ACL operation not implemented on this OS: {e}")
                self.main_app_instance.update_status_message(f"ACL operation not implemented on this OS: {e}", level="error")
                break
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)} (Error: {e})")
                gui_logger.error(f"Unexpected error during ACL {action_word} for '{file_path}': {e}")

        if success_count > 0:
            self.main_app_instance.update_status_message(f"Successfully {action_word.lower()}ed {success_count} file(s).", level="info")
            gui_logger.info(f"Successfully ACL {action_word}ed {success_count} files.")

        if failed_files:
            messagebox.showerror(
                f"ACL {action_word} Errors",
                f"Failed to {action_word.lower()} some files:\n" + "\n".join(failed_files) +
                "\n\nNOTE: For ACL operations, ensure the Zyphria Nexus Multi Use Tool is run as Administrator.", parent=self.winfo_toplevel()
            )
            self.main_app_instance.update_status_message(f"ACL {action_word} failed for {len(failed_files)} file(s). See error dialog.", level="error")

        self.refresh_files()

    def launch(self):
        sel = self.e_tree.selection()
        if sel:
            tool_path = self.e_tree.item(sel[0], "values")[0]
            tool_name = self.e_tree.item(sel[0], "text")
            if os.path.exists(tool_path):
                try:
                    subprocess.Popen([tool_path], shell=True)
                    self.main_app_instance.update_status_message(f"Launching '{tool_name}'...", level="info")
                    gui_logger.info(f"Launched tool '{tool_name}' from '{tool_path}'.")
                except Exception as ex:
                    messagebox.showerror("Launch Error", f"Failed to launch tool: {ex}", parent=self.winfo_toplevel())
                    self.main_app_instance.update_status_message(f"Failed to launch '{tool_name}': {ex}", level="error")
                    gui_logger.error(f"Failed to launch tool '{tool_name}' from '{tool_path}': {ex}")
            else:
                messagebox.showwarning("Tool Not Found", f"The executable for '{tool_name}' was not found at:\n{tool_path}", parent=self.winfo_toplevel())
                self.main_app_instance.update_status_message(f"Tool '{tool_name}' not found at: {tool_path}", level="warning")
                gui_logger.warning(f"Tool '{tool_name}' not found at expected path: {tool_path}")
        else:
            self.main_app_instance.update_status_message("No tool selected for launch.", level="warning")


    def browse_save(self):
        path = filedialog.askdirectory(title="Select Game Save Location", parent=self)
        sel = self.game_list.curselection()

        if path and sel:
            game_name = self.game_list.get(sel[0])
            self.save_p.set(path)
            self.dm.update_paths(game_name, path)
            self.refresh_files()
            gui_logger.info(f"Save path for '{game_name}' updated to: {path}")
            self.main_app_instance.update_status_message(f"Save path for '{game_name}' updated to: {path}", level="info")
        elif not sel:
            messagebox.showwarning("No Game Selected", "Please select a game first.", parent=self.winfo_toplevel())
            gui_logger.warning("Browse save path attempted without game selection.")
            self.main_app_instance.update_status_message("No game selected for save path update.", level="warning")

    def browse_default_backup(self):
        path = filedialog.askdirectory(title="Select Default Backup Folder", parent=self)
        sel = self.game_list.curselection()
        if path and sel:
            game = self.game_list.get(sel[0])
            self.default_backup_p.set(path)
            self.dm.update_default_backup_path(game, path)
            self.main_app_instance.update_status_message(f"Default backup path for '{game}' set to:\n{path}", level="info")
            gui_logger.info(f"Default backup path for '{game}' updated to: {path}")
        elif not sel:
            messagebox.showwarning("No Game Selected", "Please select a game first to set its default backup path.", parent=self.winfo_toplevel())
            gui_logger.warning("Browse default backup path attempted without game selection.")
            self.main_app_instance.update_status_message("No game selected for default backup path update.", level="warning")

    def add_tool(self):
        sel = self.game_list.curselection()
        if not sel:
            messagebox.showwarning("No Game Selected", "Please select a game to add a tool to.", parent=self.winfo_toplevel())
            gui_logger.warning("Add tool attempted without game selection.")
            self.main_app_instance.update_status_message("No game selected to add tool.", level="warning")
            return

        game_name = self.game_list.get(sel[0])
        res = dialogs.AddEditorDialog(self.winfo_toplevel(), game_name).show()
        if res:
            if self.dm.add_editor(game_name, res[0], res[1]):
                self.on_game_select(None)
                gui_logger.info(f"Added tool '{res[0]}' to game '{game_name}'.")
                self.main_app_instance.update_status_message(f"Added tool '{res[0]}' to '{game_name}'.", level="info")
            else:
                messagebox.showerror("Add Tool Failed", "A tool with this name already exists for this game.", parent=self.winfo_toplevel())
                gui_logger.warning(f"Failed to add tool '{res[0]}' to game '{game_name}': already exists.")
                self.main_app_instance.update_status_message(f"Failed to add tool: '{res[0]}' already exists for '{game_name}'.", level="error")
        else:
            self.main_app_instance.update_status_message("Add tool cancelled.", level="info")

    def delete_tool(self):
        game_sel = self.game_list.curselection()
        tool_sel = self.e_tree.selection()

        if not game_sel:
            messagebox.showwarning("No Game Selected", "Please select a game first.", parent=self.winfo_toplevel())
            gui_logger.warning("Delete tool attempted without game selection.")
            self.main_app_instance.update_status_message("No game selected.", level="warning")
            return
        if not tool_sel:
            messagebox.showwarning("No Tool Selected", "Please select a tool to delete.", parent=self.winfo_toplevel())
            gui_logger.warning("Delete tool attempted without tool selection.")
            self.main_app_instance.update_status_message("No tool selected for deletion.", level="warning")
            return

        game_name = self.game_list.get(game_sel[0])
        tool_name = self.e_tree.item(tool_sel[0], "text")

        confirm = messagebox.askyesno(
            "Confirm Delete Tool",
            f"Are you sure you want to delete the tool '{tool_name}' from '{game_name}'?", parent=self.winfo_toplevel()
        )
        if confirm:
            if self.dm.delete_editor(game_name, tool_name):
                self.on_game_select(None)
                self.main_app_instance.update_status_message(f"Tool '{tool_name}' deleted from '{game_name}'.", level="info")
                gui_logger.info(f"Deleted tool '{tool_name}' from '{game_name}'.")
            else:
                messagebox.showerror("Delete Tool Failed", f"Could not delete tool '{tool_name}'.", parent=self.winfo_toplevel())
                gui_logger.warning(f"Failed to delete tool '{tool_name}'.")
                self.main_app_instance.update_status_message(f"Failed to delete tool '{tool_name}' from '{game_name}'.", level="error")
        else:
            self.main_app_instance.update_status_message("Tool deletion cancelled.", level="info")


    def add_game(self):
        new_game_name = dialogs.AddGameDialog(self.winfo_toplevel()).show()
        if new_game_name:
            if self.dm.add_game(new_game_name):
                self.refresh_games()
                # Select the newly added game
                profiles = self.dm.get_profiles()
                new_game_index = -1
                for i, p in enumerate(profiles):
                    if p['name'].lower() == new_game_name.lower():
                        new_game_index = i
                        break
                if new_game_index != -1:
                    self.game_list.selection_clear(0, tk.END)
                    self.game_list.selection_set(new_game_index)
                    self.game_list.see(new_game_index)
                    self.on_game_select(None) # Trigger selection handler
                self.main_app_instance.update_status_message(f"Game '{new_game_name}' added successfully!", level="info")
                gui_logger.info(f"Game '{new_game_name}' added.")
            else:
                messagebox.showerror("Add Game Failed", f"A game named '{new_game_name}' already exists.", parent=self.winfo_toplevel())
                gui_logger.warning(f"Failed to add game '{new_game_name}': already exists.")
                self.main_app_instance.update_status_message(f"Failed to add game: '{new_game_name}' already exists.", level="error")
        else:
            self.main_app_instance.update_status_message("Add game cancelled.", level="info")

    def del_game(self):
        sel = self.game_list.curselection()
        if not sel:
            messagebox.showwarning("No Game Selected", "Please select a game to delete.", parent=self.winfo_toplevel())
            gui_logger.warning("Delete game attempted without selection.")
            self.main_app_instance.update_status_message("No game selected for deletion.", level="warning")
            return

        game_name = self.game_list.get(sel[0])
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the game profile for '{game_name}'?\nThis will NOT delete save files on your disk.", parent=self.winfo_toplevel()
        )
        if confirm:
            if self.dm.delete_game(game_name):
                self.refresh_games()
                self.main_app_instance.update_status_message(f"Game profile for '{game_name}' deleted.", level="info")
                # Clear all details if no games left, or re-select the first if any left
                if self.game_list.size() > 0:
                    self.game_list.selection_set(0)
                    self.on_game_select(None)
                else:
                    self.save_p.set('')
                    self.default_backup_p.set('')
                    self.s_tree.delete(*self.s_tree.get_children())
                    self.e_tree.delete(*self.e_tree.get_children())
                gui_logger.info(f"Game '{game_name}' deleted.")
            else:
                messagebox.showerror("Delete Game Failed", f"Could not delete game profile for '{game_name}'.", parent=self.winfo_toplevel())
                gui_logger.warning(f"Failed to delete game '{game_name}'.")
                self.main_app_instance.update_status_message(f"Failed to delete game profile for '{game_name}'.", level="error")
        else:
            self.main_app_instance.update_status_message("Game deletion cancelled.", level="info")

    # --- Backup and Restore Methods (Game Saves) ---

    def backup_saves(self):
        sel = self.game_list.curselection()
        if not sel:
            messagebox.showwarning("No Game Selected", "Please select a game to backup its saves.", parent=self.winfo_toplevel())
            gui_logger.warning("Backup saves attempted without game selection.")
            self.main_app_instance.update_status_message("No game selected for backup.", level="warning")
            return

        current_game_name = self.game_list.get(sel[0])
        game_saves_path = self.save_p.get()

        if not os.path.isdir(game_saves_path):
            messagebox.showerror("Invalid Path", f"Game save path for '{current_game_name}' is not valid or does not exist:\n{game_saves_path}", parent=self.winfo_toplevel())
            gui_logger.error(f"Invalid game save path for '{current_game_name}': {game_saves_path}")
            self.main_app_instance.update_status_message(f"Error: Invalid save path for '{current_game_name}'.", level="error")
            return

        selected_save_item_ids = self.s_tree.selection()
        files_to_backup_full_paths = []
        files_to_backup_names = []

        if selected_save_item_ids:
            for item_id in selected_save_item_ids:
                f_name = self.s_tree.item(item_id, "text")
                f_path = self.s_tree.item(item_id, "values")[1]
                files_to_backup_full_paths.append(f_path)
                files_to_backup_names.append(f_name)
            action_description = f"selected {len(files_to_backup_names)} file(s)"
            gui_logger.info(f"Backing up {len(files_to_backup_names)} selected files for '{current_game_name}'.")
            self.main_app_instance.update_status_message(f"Backing up {len(files_to_backup_names)} selected file(s) for '{current_game_name}'...", level="info")
        else:
            confirm_all = messagebox.askyesno(
                "Backup All Files?",
                f"No specific save files were selected for '{current_game_name}'.\n"
                f"Do you want to backup ALL save files ('.sav', '.dat') in the game's save folder:\n{game_saves_path}?", parent=self.winfo_toplevel()
            )
            if not confirm_all:
                gui_logger.info(f"Backup all files for '{current_game_name}' cancelled by user.")
                self.main_app_instance.update_status_message(f"Backup cancelled for '{current_game_name}'.", level="info")
                return

            all_save_files_info = file_operations.get_save_files_in_directory(game_saves_path)
            files_to_backup_full_paths = [f['full_path'] for f in all_save_files_info]
            files_to_backup_names = [f['filename'] for f in all_save_files_info]
            action_description = "ALL save files"
            gui_logger.info(f"Backing up ALL save files for '{current_game_name}'.")
            self.main_app_instance.update_status_message(f"Backing up ALL save files for '{current_game_name}'...", level="info")


        if not files_to_backup_full_paths:
            messagebox.showwarning("Backup Info", f"No save files ('.sav', '.dat') found in '{game_saves_path}' to backup.", parent=self.winfo_toplevel())
            gui_logger.warning(f"No relevant save files found in '{game_saves_path}' for backup.")
            self.main_app_instance.update_status_message(f"No save files found in '{current_game_name}'s directory.", level="warning")
            return

        backup_dest_folder = self.default_backup_p.get().strip()
        if not (backup_dest_folder and os.path.isdir(backup_dest_folder)):
            self.main_app_instance.update_status_message("No valid default backup path. Please select a folder.", level="warning")
            backup_dest_folder = filedialog.askdirectory(title=f"Select Folder to Save Backups for '{current_game_name}'", parent=self)

        if not backup_dest_folder:
            gui_logger.info("Backup destination selection cancelled by user.")
            self.main_app_instance.update_status_message("Backup destination selection cancelled.", level="info")
            return

        successful_backups = []
        failed_backups = []

        for source_path in files_to_backup_full_paths:
            try:
                file_operations.backup_save_file(source_path, backup_dest_folder, current_game_name)
                successful_backups.append(os.path.basename(source_path))
            except Exception as ex:
                failed_backups.append(f"{os.path.basename(source_path)}: {ex}")
                gui_logger.error(f"Failed to backup '{source_path}': {ex}")

        if successful_backups:
            self.main_app_instance.update_status_message(f"Backup complete! {len(successful_backups)} file(s) for '{current_game_name}'.", level="info")
            gui_logger.info(f"Successfully backed up {len(successful_backups)} files for '{current_game_name}'.")
        if failed_backups:
            messagebox.showerror(
                "Backup Errors",
                f"Failed to backup {len(failed_backups)} file(s):\n" + "\n".join(failed_backups), parent=self.winfo_toplevel()
            )
            self.main_app_instance.update_status_message(f"Backup failed for {len(failed_backups)} file(s). See error dialog.", level="error")

    def restore_saves(self):
        sel = self.game_list.curselection()
        if not sel:
            messagebox.showwarning("No Game Selected", "Please select a game to restore its saves.", parent=self.winfo_toplevel())
            gui_logger.warning("Restore saves attempted without game selection.")
            self.main_app_instance.update_status_message("No game selected for restore.", level="warning")
            return

        current_game_name = self.game_list.get(sel[0])
        game_saves_folder = self.save_p.get()

        if not os.path.isdir(game_saves_folder):
            messagebox.showerror("Invalid Path", f"Game save path for '{current_game_name}' is not valid or does not exist:\n{game_saves_folder}", parent=self.winfo_toplevel())
            gui_logger.error(f"Invalid game saves folder for '{current_game_name}': {game_saves_folder}")
            self.main_app_instance.update_status_message(f"Error: Invalid game saves folder for '{current_game_name}'.", level="error")
            return

        backup_dest_folder = self.default_backup_p.get().strip()
        if not (backup_dest_folder and os.path.isdir(backup_dest_folder)):
            self.main_app_instance.update_status_message("No valid default backup path. Please select a folder.", level="warning")
            backup_dest_folder = filedialog.askdirectory(title=f"Select Folder to Save Backups for '{current_game_name}'", parent=self)

        if not backup_dest_folder:
            gui_logger.info("Backup destination selection cancelled by user.")
            self.main_app_instance.update_status_message("Restore cancelled.", level="info")
            return

        game_specific_backup_folder = os.path.join(backup_dest_folder, current_game_name)

        if not os.path.isdir(game_specific_backup_folder):
            messagebox.showwarning("No Backups Found", f"No backups found for '{current_game_name}' in:\n{game_specific_backup_folder}", parent=self.winfo_toplevel())
            gui_logger.warning(f"No backups found for '{current_game_name}' in: {game_specific_backup_folder}")
            self.main_app_instance.update_status_message(f"No backups found for '{current_game_name}'.", level="warning")
            return

        available_backup_files = [f for f in os.listdir(game_specific_backup_folder) if os.path.isfile(os.path.join(game_specific_backup_folder, f))]

        if not available_backup_files:
            messagebox.showwarning("No Backups Found", f"No backup files found for '{current_game_name}' in:\n{game_specific_backup_folder}", parent=self.winfo_toplevel())
            gui_logger.warning(f"No backup files found in {game_specific_backup_folder}.")
            self.main_app_instance.update_status_message(f"No backup files found for '{current_game_name}'.", level="warning")
            return

        chosen_backup_filename = dialogs.SelectBackupFileDialog(
            self.winfo_toplevel(), current_game_name, available_backup_files
        ).show()

        if not chosen_backup_filename:
            gui_logger.info("Backup file selection for restore cancelled by user.")
            self.main_app_instance.update_status_message("Restore cancelled.", level="info")
            return

        backup_source_path = os.path.join(game_specific_backup_folder, chosen_backup_filename)
        original_filename = chosen_backup_filename

        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Restoring save file '{original_filename}' for '{current_game_name}' from:\n{backup_source_path}\n\n"
            f"This will OVERWRITE the existing save file in:\n{game_saves_folder}\n\n"
            "Do you want to continue?", parent=self.winfo_toplevel()
        )
        if not confirm:
            gui_logger.info("Restore confirmation cancelled by user.")
            self.main_app_instance.update_status_message("Restore cancelled by user.", level="info")
            return

        try:
            file_operations.restore_save_file(
                backup_source_path=backup_source_path,
                game_saves_folder=game_saves_folder,
                original_filename=original_filename
            )
            self.main_app_instance.update_status_message(f"Restored '{original_filename}' for '{current_game_name}'.", level="info")
            self.refresh_files()
            gui_logger.info(f"Successfully restored '{original_filename}' for '{current_game_name}'.")
        except FileNotFoundError as ex:
            messagebox.showerror("Restore Error", str(ex), parent=self.winfo_toplevel())
            gui_logger.error(f"Restore FileNotFoundError: {ex}")
            self.main_app_instance.update_status_message(f"Restore error: {ex}", level="error")
        except ValueError as ex:
            messagebox.showerror("Restore Error", str(ex), parent=self.winfo_toplevel())
            gui_logger.error(f"Restore ValueError: {ex}")
            self.main_app_instance.update_status_message(f"Restore error: {ex}", level="error")
        except Exception as ex:
            messagebox.showerror("Restore Error", f"An error occurred during restore: {ex}", parent=self.winfo_toplevel())
            gui_logger.critical(f"Unexpected error during restore: {ex}")
            self.main_app_instance.update_status_message(f"An unexpected error occurred during restore: {ex}", level="error")

    # --- Profile Data Export/Import Methods ---
    def export_profile_data(self):
        """Exports the config.json profile data to a user-specified folder."""
        current_config_path = self.dm.get_config_path()
        if not os.path.exists(current_config_path):
            messagebox.showwarning("Export Failed", "No profile data (config.json) found to export.", parent=self.winfo_toplevel())
            gui_logger.warning("Export failed: config.json not found.")
            self.main_app_instance.update_status_message("Export failed: config.json not found.", level="warning")
            return

        destination_folder = filedialog.askdirectory(title="Select Destination Folder for Profile Data Backup", parent=self)
        if not destination_folder:
            gui_logger.info("Export profile data cancelled by user.")
            self.main_app_instance.update_status_message("Export cancelled.", level="info")
            return

        try:
            shutil.copy2(current_config_path, destination_folder)
            self.main_app_instance.update_status_message(f"Profile data exported to:\n{destination_folder}", level="info")
            gui_logger.info(f"Profile data exported to: {destination_folder}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export profile data: {e}", parent=self.winfo_toplevel())
            gui_logger.error(f"Failed to export profile data: {e}")
            self.main_app_instance.update_status_message(f"Failed to export profile data: {e}", level="error")

    def import_profile_data(self):
        """Imports config.json profile data from a user-specified file."""
        source_file = filedialog.askopenfilename(
            title="Select Profile Data File (config.json) to Import",
            filetypes=[("JSON files", "*.json")], parent=self
        )
        if not source_file:
            gui_logger.info("Import profile data cancelled by user.")
            self.main_app_instance.update_status_message("Import cancelled.", level="info")
            return

        if not source_file.lower().endswith('.json'):
            messagebox.showwarning("Invalid File", "Please select a 'config.json' file.", parent=self.winfo_toplevel())
            gui_logger.warning(f"Invalid file selected for import: {source_file}")
            self.main_app_instance.update_status_message("Invalid file selected for import. Must be .json.", level="warning")
            return

        confirm = messagebox.askyesno(
            "Confirm Import",
            "Importing profile data will OVERWRITE your current application settings and game profiles.\n"
            "Do you want to continue?", parent=self.winfo_toplevel()
        )
        if not confirm:
            gui_logger.info("Import profile data confirmation cancelled by user.")
            self.main_app_instance.update_status_message("Import cancelled by user.", level="info")
            return

        try:
            destination_path = self.dm.get_config_path()
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            shutil.copy2(source_file, destination_path)
            self.dm.reload_profiles()
            self.refresh_games()
            self.on_game_select(None)

            self.main_app_instance.update_status_message(f"Profile data imported successfully from:\n{source_file}. Profiles reloaded.", level="info")
            gui_logger.info(f"Profile data imported from: {source_file}")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import profile data: {e}", parent=self.winfo_toplevel())
            gui_logger.error(f"Failed to import profile data: {e}")
            self.main_app_instance.update_status_message(f"Failed to import profile data: {e}", level="error")


    def show_about_dialog(self):
        print("DEBUG: show_about_dialog called in gui.py")
        """Displays the 'About' dialog."""
        about_text = (
            "Save Manager\n"
            "Version 1.0.0\n"
            "\n"
            "Developed by Z.\n"
            "Your ultimate game save management solution for Zyphria Nexus Multi Use Tool.\n"
            "Features include game profile management, save file ACL locking, \n"
            "single-file backups, restores, and external tool launching.\n"
            "\n"
            "Thank you for using Save Manager!"
        )
        messagebox.showinfo("About Save Manager", about_text, parent=self.winfo_toplevel())
        gui_logger.info("About dialog shown.")

    def show_help_dialog(self):
        print("DEBUG: show_help_dialog called in gui.py")
        """Displays the 'Help' content dialog."""
        help_text = (
            "Save Manager Help Guide:\n"
            "\n"
            "Zyphria Nexus Multi Use Tool's Save Manager helps you manage your game saves securely.\n"
            "\n"
            "Game List (Left Panel):\n"
            "  - Add Game: Create a new game profile.\n"
            "  - Delete: Remove an existing game profile.\n"
            "  - Click a game to load its settings.\n"
            "  - Move Up ↑ / Move Down ↓: Reorder game profiles in the list.\n" # NEW HELP TEXT
            "\n"
            "Game Save Location (Top-Right):\n"
            "  - Path: The directory where the game saves are located.\n"
            "  - Browse: Select the game save directory.\n"
            "\n"
            "Default Backup Location:\n"
            "  - Path: The default directory for backups. Backups are stored in a game-specific subfolder here.\n"
            "  - Browse: Select the default backup directory.\n"
            "\n"
            "Saves & Permissions (Bottom-Left):\n"
            "  - File Name: Lists your game save files.\n"
            "  - Status: Shows if a file is 'LOCKED' (write-protected via ACL) or 'UNLOCKED'.\n"
            "  - Backup Saves: Backs up selected files (or all if none are selected) to the default backup location.\n"
            "  - Restore Saves: Restores a selected backup file. You will be prompted to choose a specific backup.\n"
            "  - LOCK (ACL): Applies write protection (Deny Write) to selected files for standard user accounts.\n"
            "                NOTE: Requires running the Zyphria Nexus Multi Use Tool as Administrator.\n"
            "  - UNLOCK: Removes write protection from selected files.\n"
            "                NOTE: Requires running the Zyphria Nexus Multi Use Tool as Administrator.\n"
            "\n"
            "Tool Launcher (Bottom-Right):\n"
            "  - Lists external tools (e.g., save editors) associated with the selected game.\n"
            "  - LAUNCH TOOL: Opens the selected external tool.\n"
            "  - + Add Tool: Add a new tool executable to the game profile.\n"
            "  - - Delete Tool: Remove a selected tool from the game profile.\n"
            "\n"
            "File Menu (Top-Left):\n"
            "  - Export Profile Data: Save your application's settings and game profiles (config.json) to a chosen location.\n"
            "  - Import Profile Data: Load application settings and game profiles from a config.json file. This will OVERWRITE your current settings!\n"
        )
        messagebox.showinfo("Save Manager Help Guide", help_text, parent=self.winfo_toplevel())
        gui_logger.info("Help dialog shown.")