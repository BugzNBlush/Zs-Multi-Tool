# modules/zyphria_nexus/dialogs.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging

dialogs_logger = logging.getLogger(__name__)

class CenteredToplevel(tk.Toplevel):
    """
    A base class for Toplevel windows that automatically centers itself
    over its parent window.
    """
    def __init__(self, parent, title="Dialog"):
        super().__init__(parent)
        self.parent = parent
        self.transient(parent)
        self.grab_set()
        self.title(title)
        self.result = None

        self.configure(background='#2A2A2A')
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        dialogs_logger.debug(f"CenteredToplevel '{title}' initialized.")

    def _center_window(self):
        self.update_idletasks()

        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        main_app_root = self.parent.winfo_toplevel()
        
        main_x = main_app_root.winfo_x()
        main_y = main_app_root.winfo_y()
        main_width = main_app_root.winfo_width()
        main_height = main_app_root.winfo_height()

        x = main_x + (main_width // 2) - (dialog_width // 2)
        y = main_y + (main_height // 2) - (dialog_height // 2)

        self.geometry(f"+{x}+{y}")
        dialogs_logger.debug(f"CenteredToplevel '{self.title()}' centered at {x},{y}.")

    def show(self):
        self._center_window()
        self.parent.wait_window(self)
        return self.result

class SelectBackupFileDialog(CenteredToplevel):
    def __init__(self, parent, game_name, backup_files):
        super().__init__(parent, title=f"Select Backup for {game_name}")
        
        content_frame = ttk.Frame(self, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content_frame, text=f"Select a backup file to restore for {game_name}:").pack(padx=10, pady=5)

        self.listbox = tk.Listbox(content_frame, height=10, width=50, bg="#2A2A2A", fg="white", selectbackground="#3D4D4D", selectforeground="#00FFFF")
        self.listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        for f in backup_files:
            self.listbox.insert(tk.END, f)
        
        self.listbox.bind("<Double-Button-1>", self._on_select)

        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=5)

        ttk.Button(button_frame, text="Select", command=self._on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        dialogs_logger.debug(f"SelectBackupFileDialog for '{game_name}' initialized.")


    def _on_select(self, event=None):
        selection = self.listbox.curselection()
        if selection:
            self.result = self.listbox.get(selection[0])
            dialogs_logger.info(f"Selected backup file: {self.result}")
        else:
            dialogs_logger.info("Backup file selection cancelled or no item selected.")
        self.destroy()


class AddEditorDialog(CenteredToplevel):
    def __init__(self, parent, game_name):
        super().__init__(parent, title=f"Add Tool for {game_name}")
        
        content_frame = ttk.Frame(self, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(content_frame, text="Tool Name:").pack(padx=10, pady=5)
        self.name_entry = ttk.Entry(content_frame)
        self.name_entry.pack(padx=10, pady=5)

        ttk.Label(content_frame, text="Tool Path:").pack(padx=10, pady=5)
        self.path_entry = ttk.Entry(content_frame)
        self.path_entry.pack(padx=10, pady=5)
        ttk.Button(content_frame, text="Browse", command=self._browse_path).pack(padx=10, pady=5)

        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add", command=self._on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        dialogs_logger.debug(f"AddEditorDialog for '{game_name}' initialized.")


    def _browse_path(self):
        file_path = filedialog.askopenfilename(title="Select Executable", filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")], parent=self)
        if file_path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)
            dialogs_logger.debug(f"Browsed tool path: {file_path}")

    def _on_add(self):
        tool_name = self.name_entry.get().strip()
        tool_path = self.path_entry.get().strip()
        if tool_name and tool_path:
            self.result = (tool_name, tool_path)
            dialogs_logger.info(f"Adding tool: '{tool_name}' at '{tool_path}'")
            self.destroy()
        else:
            messagebox.showwarning("Input Error", "Both tool name and path are required.", parent=self)
            dialogs_logger.warning("Add tool failed due to missing name or path.")


class AddGameDialog(CenteredToplevel):
    def __init__(self, parent):
        super().__init__(parent, title="Add New Game")

        content_frame = ttk.Frame(self, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content_frame, text="Game Name:").pack(padx=10, pady=10)
        self.name_entry = ttk.Entry(content_frame, width=30)
        self.name_entry.pack(padx=10, pady=5)
        
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add", command=self._on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        dialogs_logger.debug("AddGameDialog initialized.")


    def _on_add(self):
        game_name = self.name_entry.get().strip()
        if game_name:
            self.result = game_name
            dialogs_logger.info(f"Adding new game: '{game_name}'")
            self.destroy()
        else:
            messagebox.showwarning("Input Error", "Game name cannot be empty.", parent=self)
            dialogs_logger.warning("Add game failed due to empty name.")
