# modules/file_shredder_module.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import threading
import logging

file_shredder_logger = logging.getLogger(__name__)

class FileShredderModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        self.files_to_shred = [] # List of (path, is_dir) tuples
        self.shredding_active = False
        self.total_bytes_to_shred = 0
        self.bytes_shredded_current_session = 0
        
        # Tkinter variables
        self.num_passes_var = tk.IntVar(value=3) # Default to 3 passes (DoD 5220.22-M like)
        self.shredding_progress_var = tk.DoubleVar(value=0)
        self.shredding_status_var = tk.StringVar(value="Ready to shred files.")

        self.create_widgets()
        file_shredder_logger.info("FileShredderModule initialized.")
        self.main_app_instance.update_status_message("File Shredder module loaded.", level="info")

    def create_widgets(self):
        # Frame for file/folder selection
        selection_frame = ttk.LabelFrame(self, text=" Files/Folders to Shred ")
        selection_frame.pack(fill=tk.X, padx=10, pady=5)

        self.shred_listbox = tk.Listbox(selection_frame, height=10, selectmode=tk.EXTENDED, 
                                        bg="#2A2A2A", fg="#00FFFF", selectbackground="#007BFF", activestyle="none")
        self.shred_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        list_scroll = ttk.Scrollbar(selection_frame, command=self.shred_listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.shred_listbox.config(yscrollcommand=list_scroll.set)

        # Buttons for selection
        button_frame = ttk.Frame(selection_frame)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        ttk.Button(button_frame, text="Add File(s)", command=self._add_files).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Add Folder(s)", command=self._add_folders).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Remove Selected", command=self._remove_selected).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Clear All", command=self._clear_list).pack(fill=tk.X, pady=2)

        # Shredding options and controls
        options_frame = ttk.LabelFrame(self, text=" Shredding Options ")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(options_frame, text="Number of Passes:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Spinbox(options_frame, from_=1, to_=10, textvariable=self.num_passes_var, wrap=True).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        self.shred_button = ttk.Button(options_frame, text="SHRED SELECTED FILES/FOLDERS", command=self._confirm_shred, style="Danger.TButton")
        self.shred_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Progress and status
        progress_frame = ttk.LabelFrame(self, text=" Progress ")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(progress_frame, textvariable=self.shredding_status_var).pack(fill=tk.X, padx=5, pady=2)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode="determinate", variable=self.shredding_progress_var)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        # Styles for the Danger Button
        s = ttk.Style()
        s.configure('Danger.TButton', background='red', foreground='white', font=('Arial', 10, 'bold'))
        s.map('Danger.TButton',
              background=[('active', 'darkred'), ('!disabled', 'red')],
              foreground=[('active', 'white'), ('!disabled', 'white')])


    def _add_files(self):
        files = filedialog.askopenfilenames(parent=self, title="Select Files to Shred")
        if files:
            for f in files:
                if (f, False) not in self.files_to_shred:
                    self.files_to_shred.append((f, False)) # False indicates it's a file
                    self.shred_listbox.insert(tk.END, f"[FILE] {f}")
                    file_shredder_logger.info(f"Added file for shredding: {f}")
            self.main_app_instance.update_status_message(f"Added {len(files)} file(s) for shredding.", level="info")

    def _add_folders(self):
        folders = filedialog.askdirectory(parent=self, title="Select Folder(s) to Shred")
        if folders:
            # filedialog.askdirectory returns a single string, so make it iterable
            if isinstance(folders, str):
                folders = [folders]
            for folder in folders:
                if (folder, True) not in self.files_to_shred:
                    self.files_to_shred.append((folder, True)) # True indicates it's a directory
                    self.shred_listbox.insert(tk.END, f"[FOLDER] {folder}")
                    file_shredder_logger.info(f"Added folder for shredding: {folder}")
            self.main_app_instance.update_status_message(f"Added {len(folders)} folder(s) for shredding.", level="info")

    def _remove_selected(self):
        selected_indices = self.shred_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select items to remove from the list.", parent=self)
            return

        for index in reversed(selected_indices): # Delete from end to avoid index issues
            removed_item = self.files_to_shred.pop(index)
            self.shred_listbox.delete(index)
            file_shredder_logger.info(f"Removed item from shred list: {removed_item[0]}")
        self.main_app_instance.update_status_message(f"Removed {len(selected_indices)} item(s) from shred list.", level="info")

    def _clear_list(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the entire list of items to shred?", parent=self):
            self.files_to_shred.clear()
            self.shred_listbox.delete(0, tk.END)
            self.main_app_instance.update_status_message("Cleared all items from shred list.", level="info")
            file_shredder_logger.info("Cleared all items from shred list.")

    def _confirm_shred(self):
        if not self.files_to_shred:
            messagebox.showwarning("No Items", "Please add files or folders to shred first.", parent=self)
            return
        if self.shredding_active:
            messagebox.showwarning("Shredding in Progress", "Shredding is already active. Please wait.", parent=self)
            return

        response = messagebox.askyesno(
            "CONFIRM SECURE DELETION",
            "WARNING: Securely deleting files is IRREVERSIBLE!\n\n"
            "Are you absolutely sure you want to shred the selected files/folders?\n"
            "This action cannot be undone!",
            icon='warning',
            parent=self
        )
        if response:
            self._start_shredding()
        else:
            self.main_app_instance.update_status_message("File shredding cancelled by user.", level="info")

    def _start_shredding(self):
        self.shredding_active = True
        self.shred_button.config(state=tk.DISABLED)
        self.progress_bar.config(mode="indeterminate") # Use indeterminate for initial file enumeration
        self.shredding_status_var.set("Enumerating files to shred...")
        self.main_app_instance.update_status_message("Starting secure deletion process...", level="info")
        file_shredder_logger.info("Starting secure deletion process.")

        shred_thread = threading.Thread(target=self._perform_shredding_logic, daemon=True)
        shred_thread.start()

    def _perform_shredding_logic(self):
        num_passes = self.num_passes_var.get()
        all_files_to_shred = []
        
        # First, enumerate all individual files from selected items
        self.total_bytes_to_shred = 0
        current_enum_status = 0
        for item_path, is_dir in self.files_to_shred:
            if not os.path.exists(item_path):
                file_shredder_logger.warning(f"Item not found, skipping: {item_path}")
                self.after(0, lambda p=item_path: self.main_app_instance.update_status_message(f"Warning: Item not found, skipping: {p}", level="warning"))
                continue

            if is_dir:
                for root, _, files in os.walk(item_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        all_files_to_shred.append(full_path)
                        try:
                            self.total_bytes_to_shred += os.path.getsize(full_path)
                        except OSError as e:
                            file_shredder_logger.warning(f"Could not get size of '{full_path}': {e}")
                        current_enum_status += 1
                        if current_enum_status % 100 == 0:
                            self.after(0, lambda c=current_enum_status: self.shredding_status_var.set(f"Enumerating files: {c} files found..."))
            else:
                all_files_to_shred.append(item_path)
                try:
                    self.total_bytes_to_shred += os.path.getsize(item_path)
                except OSError as e:
                    file_shredder_logger.warning(f"Could not get size of '{item_path}': {e}")
        
        # Multiply total bytes by number of passes for accurate total progress
        self.total_bytes_to_shred *= num_passes
        
        self.after(0, lambda: self.progress_bar.config(mode="determinate", maximum=self.total_bytes_to_shred))
        self.bytes_shredded_current_session = 0
        
        files_shredded_count = 0
        failed_shreds = []

        for current_file_path in all_files_to_shred:
            try:
                self._shred_file(current_file_path, num_passes)
                files_shredded_count += 1
                self.after(0, lambda c=files_shredded_count, p=current_file_path: self.shredding_status_var.set(f"Shredding {c}/{len(all_files_to_shred)}: {os.path.basename(p)}"))
            except Exception as e:
                file_shredder_logger.error(f"Failed to shred '{current_file_path}': {e}")
                failed_shreds.append(current_file_path)
                self.after(0, lambda p=current_file_path: self.main_app_instance.update_status_message(f"Error shredding '{p}': {e}", level="error"))
        
        # After shredding individual files, remove the originally selected (now empty) folders
        for item_path, is_dir in self.files_to_shred:
            if is_dir and os.path.exists(item_path) and not os.listdir(item_path): # Check if folder is now empty
                try:
                    os.rmdir(item_path)
                    file_shredder_logger.info(f"Removed empty directory: {item_path}")
                except OSError as e:
                    file_shredder_logger.error(f"Could not remove empty directory '{item_path}': {e}")
                    failed_shreds.append(item_path)

        self._finish_shredding(files_shredded_count, failed_shreds)

    def _shred_file(self, filepath, num_passes):
        chunk_size = 4096 # Read/write in 4KB chunks
        
        try:
            file_size = os.path.getsize(filepath)
        except OSError as e:
            raise Exception(f"Could not access file size: {e}")

        if file_size == 0:
            os.remove(filepath)
            self.bytes_shredded_current_session += num_passes * file_size # Account for progress
            self.after(0, lambda: self.shredding_progress_var.set(self.bytes_shredded_current_session))
            file_shredder_logger.info(f"Removed empty file: {filepath}")
            return
            
        # Standard overwriting patterns (DoD 5220.22-M inspiration)
        patterns = [b'\x00', b'\xFF', os.urandom(chunk_size)] # Zeros, ones, then random
        
        for pass_num in range(num_passes):
            current_pattern_chunk = patterns[pass_num % len(patterns)] if pass_num < len(patterns) else os.urandom(chunk_size)

            try:
                with open(filepath, 'r+b') as f: # Open for read/write, binary
                    f.seek(0) # Go to beginning of file
                    bytes_written_this_pass = 0
                    while bytes_written_this_pass < file_size:
                        bytes_to_write = min(chunk_size, file_size - bytes_written_this_pass)
                        
                        if current_pattern_chunk is patterns[2]:
                            data_to_write = os.urandom(bytes_to_write)
                        else:
                            data_to_write = current_pattern_chunk * (bytes_to_write // len(current_pattern_chunk))
                            if bytes_to_write % len(current_pattern_chunk) != 0:
                                data_to_write += current_pattern_chunk[:bytes_to_write % len(current_pattern_chunk)]
                        
                        f.write(data_to_write)
                        f.flush()
                        os.fsync(f.fileno())
                        
                        bytes_written_this_pass += bytes_to_write
                        self.bytes_shredded_current_session += bytes_to_write
                        self.after(0, lambda: self.shredding_progress_var.set(self.bytes_shredded_current_session))
                file_shredder_logger.debug(f"Pass {pass_num + 1}/{num_passes} completed for '{filepath}'")
            except OSError as e:
                raise Exception(f"File operation failed during shredding pass {pass_num + 1}: {e}")
            except Exception as e:
                raise Exception(f"An unexpected error occurred during shredding pass {pass_num + 1}: {e}")

        # Final step: Rename file multiple times then delete
        dir_name, base_name = os.path.split(filepath)
        for _ in range(5):
            try:
                new_name = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for i in range(len(base_name)))
                os.rename(filepath, os.path.join(dir_name, new_name))
                filepath = os.path.join(dir_name, new_name)
            except OSError:
                break
        
        try:
            os.remove(filepath)
            file_shredder_logger.info(f"Successfully shredded and deleted: {filepath}")
        except OSError as e:
            raise Exception(f"Failed to delete file after shredding: {e}")

    def _finish_shredding(self, files_shredded_count, failed_shreds):
        self.shredding_active = False
        self.after(0, lambda: self.shred_button.config(state=tk.NORMAL))
        self.after(0, lambda: self.shred_listbox.delete(0, tk.END))
        self.files_to_shred.clear()
        self.after(0, lambda: self.shredding_progress_var.set(0))

        if not failed_shreds:
            final_message = f"Secure deletion complete! {files_shredded_count} file(s) shredded successfully."
            level = "success"
        else:
            final_message = f"Shredding completed with {len(failed_shreds)} error(s). {files_shredded_count} file(s) shredded. Check logs for details."
            level = "warning"
        
        self.after(0, lambda: self.shredding_status_var.set(final_message))
        self.after(0, lambda: self.main_app_instance.update_status_message(final_message, level=level))
        file_shredder_logger.info(final_message)
        if failed_shreds:
            file_shredder_logger.warning(f"Files that failed to shred: {failed_shreds}")

    def get_menubar_commands(self):
        return {
            "help_commands": [
                ("File Shredder Help", self._show_help_dialog),
            ]
        }

    def _show_help_dialog(self):
        messagebox.showinfo(
            "File Shredder Help",
            "This module allows you to securely delete files and folders, making their contents unrecoverable.\n\n"
            "How to use:\n"
            "1. Use 'Add File(s)' or 'Add Folder(s)' to select items you wish to shred.\n"
            "2. Select the 'Number of Passes' (more passes increase security but take longer).\n"
            "3. Click 'SHRED SELECTED FILES/FOLDERS'. You will be asked for confirmation.\n\n"
            "WARNING: This action is IRREVERSIBLE. Once files are shredded, they cannot be recovered by any means. Use with extreme caution.",
            parent=self.winfo_toplevel()
        )
        file_shredder_logger.info("File Shredder help dialog shown.")

    def before_hide(self, closing_app=False):
        return True

    def refresh_settings_ui(self):
        pass