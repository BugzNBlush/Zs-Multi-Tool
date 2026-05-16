import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import logging
import base64
import time # For Discord RPC timestamps

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

import settings_manager # For APP_NAME consistency in dialogs and RPC
from modules.zyphria_nexus.styles import text_highlight_color, bg_dark, fg_white, hologram_glow # Import styles

# Configure logging for this module
encryptor_logger = logging.getLogger(__name__)

class FileEncryptorDecryptorModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        # Variables for Encrypt section
        self.encrypt_source_file_var = tk.StringVar()
        self.encrypt_dest_dir_var = tk.StringVar()
        self.encrypt_dest_dir_var.trace_add("write", self._save_module_settings) # Save on change
        self.encrypt_password_var = tk.StringVar()
        self.encrypt_show_password_var = tk.BooleanVar(value=False)

        # Variables for Decrypt section
        self.decrypt_source_file_var = tk.StringVar()
        self.decrypt_dest_dir_var = tk.StringVar()
        self.decrypt_dest_dir_var.trace_add("write", self._save_module_settings) # Save on change
        self.decrypt_password_var = tk.StringVar()
        self.decrypt_show_password_var = tk.BooleanVar(value=False)

        self._load_module_settings()
        self.create_widgets()
        encryptor_logger.info("FileEncryptorDecryptorModule initialized.")
        self.main_app_instance.update_status_message("File Encryptor/Decryptor module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update

    def _load_module_settings(self, *args): # Added *args to be compatible with trace_add
        """Loads module-specific settings, like last used directories."""
        module_settings = self.app_settings.get("file_encryptor_decryptor", {})
        self.encrypt_dest_dir_var.set(module_settings.get("last_encrypt_dest_dir", ""))
        self.decrypt_dest_dir_var.set(module_settings.get("last_decrypt_dest_dir", ""))

    def _save_module_settings(self, *args): # Added *args to be compatible with trace_add
        """Saves module-specific settings."""
        if "file_encryptor_decryptor" not in self.app_settings:
            self.app_settings["file_encryptor_decryptor"] = {}
        # Ensure the directories are valid before saving
        if os.path.isdir(self.encrypt_dest_dir_var.get()):
            self.app_settings["file_encryptor_decryptor"]["last_encrypt_dest_dir"] = self.encrypt_dest_dir_var.get()
        if os.path.isdir(self.decrypt_dest_dir_var.get()):
            self.app_settings["file_encryptor_decryptor"]["last_decrypt_dest_dir"] = self.decrypt_dest_dir_var.get()
        settings_manager.save_settings(self.app_settings)
        encryptor_logger.debug("Encryptor/Decryptor module settings saved.")

    def create_widgets(self):
        ttk.Label(self, text="🔒 File Encryptor/Decryptor 🔓", font=("Arial", 18, "bold")).pack(pady=20)

        # --- Encrypt Section ---
        encrypt_frame = ttk.LabelFrame(self, text=" Encrypt File ")
        encrypt_frame.pack(fill=tk.X, padx=10, pady=5)

        # Source File
        ttk.Label(encrypt_frame, text="Source File:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(encrypt_frame, textvariable=self.encrypt_source_file_var, state="readonly").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(encrypt_frame, text="Browse", command=self._browse_encrypt_source).grid(row=0, column=2, padx=5, pady=2)

        # Destination Directory
        ttk.Label(encrypt_frame, text="Destination Dir:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(encrypt_frame, textvariable=self.encrypt_dest_dir_var, state="readonly").grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(encrypt_frame, text="Browse", command=self._browse_encrypt_dest).grid(row=1, column=2, padx=5, pady=2)

        # Password
        ttk.Label(encrypt_frame, text="Password:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.encrypt_password_entry = ttk.Entry(encrypt_frame, textvariable=self.encrypt_password_var, show="*")
        self.encrypt_password_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ttk.Checkbutton(encrypt_frame, text="Show", variable=self.encrypt_show_password_var, command=self._toggle_encrypt_password_visibility).grid(row=2, column=2, padx=5, pady=2)

        # Encrypt Button
        ttk.Button(encrypt_frame, text="Encrypt File", command=self._encrypt_file).grid(row=3, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        encrypt_frame.grid_columnconfigure(1, weight=1)

        # --- Decrypt Section ---
        decrypt_frame = ttk.LabelFrame(self, text=" Decrypt File ")
        decrypt_frame.pack(fill=tk.X, padx=10, pady=5)

        # Source File (encrypted)
        ttk.Label(decrypt_frame, text="Encrypted File:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(decrypt_frame, textvariable=self.decrypt_source_file_var, state="readonly").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(decrypt_frame, text="Browse", command=self._browse_decrypt_source).grid(row=0, column=2, padx=5, pady=2)

        # Destination Directory
        ttk.Label(decrypt_frame, text="Destination Dir:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(decrypt_frame, textvariable=self.decrypt_dest_dir_var, state="readonly").grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(decrypt_frame, text="Browse", command=self._browse_decrypt_dest).grid(row=1, column=2, padx=5, pady=2)

        # Password
        ttk.Label(decrypt_frame, text="Password:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.decrypt_password_entry = ttk.Entry(decrypt_frame, textvariable=self.decrypt_password_var, show="*")
        self.decrypt_password_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ttk.Checkbutton(decrypt_frame, text="Show", variable=self.decrypt_show_password_var, command=self._toggle_decrypt_password_visibility).grid(row=2, column=2, padx=5, pady=2)

        # Decrypt Button
        ttk.Button(decrypt_frame, text="Decrypt File", command=self._decrypt_file).grid(row=3, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        decrypt_frame.grid_columnconfigure(1, weight=1)

    # --- Helper Methods for UI ---

    def _browse_encrypt_source(self):
        file_path = filedialog.askopenfilename(parent=self)
        if file_path:
            self.encrypt_source_file_var.set(file_path)
            encryptor_logger.debug(f"Encrypt source file selected: {file_path}")

    def _browse_encrypt_dest(self):
        dir_path = filedialog.askdirectory(parent=self)
        if dir_path:
            self.encrypt_dest_dir_var.set(dir_path)
            self._save_module_settings() # Save last used dir
            encryptor_logger.debug(f"Encrypt destination directory selected: {dir_path}")

    def _toggle_encrypt_password_visibility(self):
        if self.encrypt_show_password_var.get():
            self.encrypt_password_entry.config(show="")
        else:
            self.encrypt_password_entry.config(show="*")

    def _browse_decrypt_source(self):
        file_path = filedialog.askopenfilename(parent=self)
        if file_path:
            self.decrypt_source_file_var.set(file_path)
            encryptor_logger.debug(f"Decrypt source file selected: {file_path}")

    def _browse_decrypt_dest(self):
        dir_path = filedialog.askdirectory(parent=self)
        if dir_path:
            self.decrypt_dest_dir_var.set(dir_path)
            self._save_module_settings() # Save last used dir
            encryptor_logger.debug(f"Decrypt destination directory selected: {dir_path}")

    def _toggle_decrypt_password_visibility(self):
        if self.decrypt_show_password_var.get():
            self.decrypt_password_entry.config(show="")
        else:
            self.decrypt_password_entry.config(show="*")

    # --- Encryption/Decryption Logic ---

    # NOTE: Using a fixed salt for simplicity. For higher security, a unique salt should be generated
    # per file and stored alongside the encrypted data (e.g., as part of the header).
    # For a "simple" encryptor, this approach is acceptable, but be aware of the trade-offs.
    FIXED_SALT = b'zyphria_nexus_salt_for_encryption_tool_v1'

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derives a Fernet key from a password and salt using PBKDF2HMAC."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, # Fernet requires a 32-byte key
            salt=salt,
            iterations=480000, # Recommended iteration count for PBKDF2HMAC
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _encrypt_file(self):
        source_file = self.encrypt_source_file_var.get()
        dest_dir = self.encrypt_dest_dir_var.get()
        password = self.encrypt_password_var.get()

        if not all([source_file, dest_dir, password]):
            messagebox.showwarning("Missing Input", "Please provide a source file, destination directory, and password for encryption.", parent=self)
            return
        if not os.path.exists(source_file):
            messagebox.showerror("File Not Found", f"Source file not found: {source_file}", parent=self)
            return
        if not os.path.isdir(dest_dir):
            messagebox.showerror("Invalid Directory", f"Destination directory does not exist: {dest_dir}", parent=self)
            return
        if len(password) < 8:
            messagebox.showwarning("Weak Password", "Please use a password of at least 8 characters for better security.", parent=self)
            return

        try:
            self.main_app_instance.update_status_message(f"Encrypting '{os.path.basename(source_file)}'...", level="info")
            encryptor_logger.info(f"Starting encryption for '{source_file}'")

            key = self._derive_key(password, self.FIXED_SALT)
            fernet = Fernet(key)

            with open(source_file, 'rb') as f:
                original_data = f.read()

            encrypted_data = fernet.encrypt(original_data)

            output_filename = os.path.basename(source_file) + ".enc"
            output_path = os.path.join(dest_dir, output_filename)

            with open(output_path, 'wb') as f:
                f.write(encrypted_data)

            messagebox.showinfo("Encryption Successful", f"File successfully encrypted to:\n{output_path}", parent=self)
            self.main_app_instance.update_status_message(f"Successfully encrypted '{os.path.basename(source_file)}' to '{output_filename}'.", level="success")
            encryptor_logger.info(f"Encryption successful: '{output_path}'")
            
            # NEW FEATURE: Prompt to delete original unencrypted file
            delete_original = messagebox.askyesno(
                "Delete Original File?",
                f"Encryption successful! Do you want to delete the original unencrypted file:\n'{source_file}'?",
                parent=self
            )
            if delete_original:
                try:
                    os.remove(source_file)
                    messagebox.showinfo("Original File Deleted", f"Original file '{os.path.basename(source_file)}' deleted.", parent=self)
                    self.main_app_instance.update_status_message(f"Original file '{os.path.basename(source_file)}' deleted.", level="info")
                    encryptor_logger.info(f"Original unencrypted file '{source_file}' deleted.")
                    self.encrypt_source_file_var.set("") # Clear the source file entry
                except Exception as e:
                    messagebox.showwarning("Deletion Failed", f"Could not delete original file:\n{e}", parent=self)
                    self.main_app_instance.update_status_message(f"Failed to delete original file: {e}", level="warning")
                    encryptor_logger.warning(f"Failed to delete original unencrypted file '{source_file}': {e}")


            self._update_discord_rpc()

        except Exception as e:
            messagebox.showerror("Encryption Failed", f"An error occurred during encryption: {e}", parent=self)
            self.main_app_instance.update_status_message(f"Encryption failed for '{os.path.basename(source_file)}': {e}", level="error")
            encryptor_logger.error(f"Encryption failed for '{source_file}': {e}")

    def _decrypt_file(self):
        source_file = self.decrypt_source_file_var.get()
        dest_dir = self.decrypt_dest_dir_var.get()
        password = self.decrypt_password_var.get()

        if not all([source_file, dest_dir, password]):
            messagebox.showwarning("Missing Input", "Please provide an encrypted file, destination directory, and password for decryption.", parent=self)
            return
        if not os.path.exists(source_file):
            messagebox.showerror("File Not Found", f"Encrypted file not found: {source_file}", parent=self)
            return
        if not source_file.lower().endswith(".enc"):
            messagebox.showwarning("Invalid File", "The selected file does not appear to be an encrypted file (missing .enc extension).", parent=self)
            return
        if not os.path.isdir(dest_dir):
            messagebox.showerror("Invalid Directory", f"Destination directory does not exist: {dest_dir}", parent=self)
            return

        try:
            self.main_app_instance.update_status_message(f"Decrypting '{os.path.basename(source_file)}'...", level="info")
            encryptor_logger.info(f"Starting decryption for '{source_file}'")

            key = self._derive_key(password, self.FIXED_SALT)
            fernet = Fernet(key)

            with open(source_file, 'rb') as f:
                encrypted_data = f.read()

            # This is where the InvalidToken error will occur if the password is wrong
            decrypted_data = fernet.decrypt(encrypted_data)

            # Remove the ".enc" extension for the output filename
            output_filename = os.path.basename(source_file)[:-4] if source_file.lower().endswith(".enc") else os.path.basename(source_file)
            output_path = os.path.join(dest_dir, output_filename)

            # Check if the output file already exists and prompt for overwrite
            if os.path.exists(output_path):
                confirm = messagebox.askyesno(
                    "File Exists",
                    f"The decrypted file '{output_filename}' already exists in the destination directory.\n"
                    "Do you want to overwrite it?",
                    parent=self
                )
                if not confirm:
                    self.main_app_instance.update_status_message("Decryption cancelled: file already exists.", level="warning")
                    encryptor_logger.info("Decryption cancelled by user to avoid overwriting existing file.")
                    return

            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

            messagebox.showinfo("Decryption Successful", f"File successfully decrypted to:\n{output_path}", parent=self)
            self.main_app_instance.update_status_message(f"Successfully decrypted '{os.path.basename(source_file)}' to '{output_filename}'.", level="success")
            encryptor_logger.info(f"Decryption successful: '{output_path}'")

            # Prompt to delete original .enc file
            delete_original = messagebox.askyesno(
                "Delete Encrypted File?",
                f"Decryption successful! Do you want to delete the original encrypted file:\n'{source_file}'?",
                parent=self
            )
            if delete_original:
                try:
                    os.remove(source_file)
                    messagebox.showinfo("File Deleted", f"Encrypted file '{os.path.basename(source_file)}' deleted.", parent=self)
                    self.main_app_instance.update_status_message(f"Encrypted file '{os.path.basename(source_file)}' deleted.", level="info")
                    encryptor_logger.info(f"Original encrypted file '{source_file}' deleted.")
                    self.decrypt_source_file_var.set("") # Clear the source file entry
                except Exception as e:
                    messagebox.showwarning("Deletion Failed", f"Could not delete encrypted file:\n{e}", parent=self)
                    self.main_app_instance.update_status_message(f"Failed to delete encrypted file: {e}", level="warning")
                    encryptor_logger.warning(f"Failed to delete original encrypted file '{source_file}': {e}")

            self._update_discord_rpc()

        except InvalidToken:
            messagebox.showerror("Decryption Failed", "Invalid password or corrupted file. Ensure the correct password was entered.", parent=self)
            self.main_app_instance.update_status_message(f"Decryption failed for '{os.path.basename(source_file)}': Invalid password or corrupted file.", level="error")
            encryptor_logger.warning(f"Decryption failed for '{source_file}': Invalid password or corrupted file.")
        except Exception as e:
            messagebox.showerror("Decryption Failed", f"An error occurred during decryption: {e}", parent=self)
            self.main_app_instance.update_status_message(f"Decryption failed for '{os.path.basename(source_file)}': {e}", level="error")
            encryptor_logger.error(f"Decryption failed for '{source_file}': {e}")

    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self):
        if self.main_app_instance.discord_rpc_manager:
            rpc_data = self.get_discord_rpc_status()
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

    def get_discord_rpc_status(self):
        """
        Returns a dictionary with current details, state, and image assets for Discord Rich Presence.
        """
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="encryptor_decryptor")

        details_text = "Using File Encryptor/Decryptor"
        state_text = "Ready"

        if self.encrypt_source_file_var.get() and self.focus_get() in [self.encrypt_password_entry, self.encrypt_password_entry.winfo_parent()]:
            state_text = f"Encrypting {os.path.basename(self.encrypt_source_file_var.get())}"
        elif self.decrypt_source_file_var.get() and self.focus_get() in [self.decrypt_password_entry, self.decrypt_password_entry.winfo_parent()]:
            state_text = f"Decrypting {os.path.basename(self.decrypt_source_file_var.get())}"
        else: # Idle state
            state_text = "Idle"

        return {
            "details": details_text,
            "state": state_text,
            "large_image": default_rpc.get("large_image", "encryption_icon"), # Assuming an 'encryption_icon' asset
            "large_text": "File Encryptor/Decryptor",
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": self.main_app_instance.base_title,
        }

    def get_menubar_commands(self):
        return {
            "help_commands": [
                ("About Encryptor/Decryptor", self._show_about_dialog),
                ("Encryptor/Decryptor Help", self._show_help_dialog),
            ]
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About File Encryptor/Decryptor",
            f"{settings_manager.APP_NAME} File Encryptor/Decryptor v1.0\n"
            "Provides symmetric encryption and decryption for files using a password.\n"
            "Utilizes strong cryptographic primitives from the 'cryptography' library.\n"
            "Developed by Z.\n\n"
            "Always remember your password! There is no recovery if it's lost.",
            parent=self.winfo_toplevel()
        )
        encryptor_logger.info("About dialog shown for File Encryptor/Decryptor.")

    def _show_help_dialog(self):
        help_text = (
            "File Encryptor/Decryptor Help Guide:\n\n"
            "1. Encryption:\n"
            "   - Browse for the 'Source File' you want to encrypt.\n"
            "   - Browse for the 'Destination Dir' where the encrypted file will be saved.\n"
            "   - Enter a strong 'Password' (at least 8 characters recommended).\n"
            "   - Click 'Encrypt File'. An encrypted file with a '.enc' extension will be created.\n"
            "   - After successful encryption, you will be asked if you wish to delete the original unencrypted file.\n\n" # Updated help text
            "2. Decryption:\n"
            "   - Browse for the 'Encrypted File' (usually with a '.enc' extension).\n"
            "   - Browse for the 'Destination Dir' where the decrypted file will be saved.\n"
            "   - Enter the EXACT 'Password' used for encryption.\n"
            "   - Click 'Decrypt File'. The original file will be restored. You will be prompted if the file already exists.\n\n"
            "   - After successful decryption, you will be asked if you wish to delete the original '.enc' file.\n\n"
            "IMPORTANT: If you lose your password, your file cannot be recovered!"
        )
        messagebox.showinfo(
            "File Encryptor/Decryptor Help",
            help_text,
            parent=self.winfo_toplevel()
        )
        encryptor_logger.info("Help dialog shown for File Encryptor/Decryptor.")

    def before_hide(self, closing_app=False):
        self._save_module_settings()
        self._update_discord_rpc()
        return True

    def refresh_settings_ui(self):
        # This module primarily uses self.app_settings directly, but we can ensure
        # UI reflects any external changes to last used directories.
        self._load_module_settings()
        encryptor_logger.debug("Encryptor/Decryptor Module UI refreshed.")
        self._update_discord_rpc()