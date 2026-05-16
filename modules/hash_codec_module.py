import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import logging
import threading
import hashlib
import base64
import urllib.parse
import binascii
import codecs # For ROT13
import html # For HTML entities
import json # For code snippets storage
import time # For Discord RPC timestamps

# Import your theme colors and APP_NAME for consistency
from modules.zyphria_nexus.styles import bg_dark, fg_white, text_highlight_color, hologram_glow
import settings_manager # For APP_NAME and user config directory

hash_codec_logger = logging.getLogger(__name__)

class HashCodecModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        # Hash Tab specific
        self.current_file_path = None
        self.selected_hash_algorithm = tk.StringVar(value="sha256") # Default hash algorithm
        self.calculation_thread = None
        self.calculated_hash_result = None
        self.calculated_hash_error = None

        # Text Manipulation specific attributes
        # No specific Tkinter Vars needed here as text is read directly from Text widgets
        self.text_manip_status_var = tk.StringVar(value="Characters: 0, Words: 0") # Initial status

        # Code Snippet specific attributes
        self.snippet_name_var = tk.StringVar()
        self.snippet_language_var = tk.StringVar(value="Plain Text")
        self.snippets = [] # List of dictionaries for snippets

        self.create_widgets()
        hash_codec_logger.debug("HashCodecModule initialized.")

        # Load snippets at initialization
        self._load_snippets()
        self._update_snippet_list_ui() # Ensure listbox is populated after loading

        self.main_app_instance.update_status_message("Hash & Codecs module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update

    def create_widgets(self):
        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change) # Bind tab change for RPC updates

        # Hashing Tab
        self.hash_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.hash_tab, text="Hashing")
        self._create_hashing_widgets(self.hash_tab)

        # Text Manipulation Tab
        self.text_manip_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.text_manip_tab, text="Text Manipulation")
        self._create_text_manipulation_widgets(self.text_manip_tab)

        # Code Snippets Tab
        self.code_snippets_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.code_snippets_tab, text="Code Snippets")
        self._create_code_snippets_widgets(self.code_snippets_tab)


    # --- Hashing Tab Widgets and Logic ---
    def _create_hashing_widgets(self, parent_frame):
        # Input Section
        input_label = ttk.Label(parent_frame, text="Input (Text or File):", font=("Arial", 12, "bold"))
        input_label.pack(pady=(0, 5), anchor=tk.W)

        self.hash_text_input = tk.Text(parent_frame, wrap=tk.WORD, height=8, bg=bg_dark, fg=fg_white, insertbackground=hologram_glow, selectbackground=text_highlight_color)
        self.hash_text_input.pack(fill=tk.X, pady=(0, 10))
        self.hash_text_input.bind("<KeyRelease>", self._clear_hash_file_path)

        # File Input Section
        file_frame = ttk.Frame(parent_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(file_frame, text="Selected File:", width=15).pack(side=tk.LEFT)
        self.hash_file_path_entry = ttk.Entry(file_frame, state="readonly")
        self.hash_file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.browse_hash_file_button = ttk.Button(file_frame, text="Browse File", command=self._browse_hash_file)
        self.browse_hash_file_button.pack(side=tk.LEFT)

        # Algorithm Selection
        algo_frame = ttk.Frame(parent_frame)
        algo_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(algo_frame, text="Algorithm:", width=15).pack(side=tk.LEFT)
        self.hash_algo_combobox = ttk.Combobox(algo_frame, textvariable=self.selected_hash_algorithm,
                                          values=["md5", "sha1", "sha224", "sha256", "sha512"], state="readonly")
        self.hash_algo_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.hash_algo_combobox.set("sha256")

        # Calculate Button
        self.calculate_hash_button = ttk.Button(parent_frame, text="Calculate Hash", command=self._start_hash_calculation)
        self.calculate_hash_button.pack(fill=tk.X, pady=(0, 15))

        # Output Section
        output_label = ttk.Label(parent_frame, text="Calculated Hash:", font=("Arial", 12, "bold"))
        output_label.pack(pady=(0, 5), anchor=tk.W)

        self.hash_output = tk.Text(parent_frame, wrap=tk.WORD, height=3, state="disabled", bg=bg_dark, fg=fg_white) # Styled
        self.hash_output.pack(fill=tk.X, pady=(0, 10))

        # Comparison Section
        compare_label = ttk.Label(parent_frame, text="Expected Hash for Comparison:", font=("Arial", 12, "bold"))
        compare_label.pack(pady=(0, 5), anchor=tk.W)

        self.expected_hash_entry = ttk.Entry(parent_frame)
        self.expected_hash_entry.pack(fill=tk.X, pady=(0, 10))
        self.expected_hash_entry.bind("<KeyRelease>", self._clear_hash_compare_status)

        self.compare_hash_button = ttk.Button(parent_frame, text="Compare Hashes", command=self._compare_hashes)
        self.compare_hash_button.pack(fill=tk.X, pady=(0, 10))

        self.hash_compare_status_label = ttk.Label(parent_frame, text="", font=("Arial", 11, "bold"))
        self.hash_compare_status_label.pack(pady=(0, 5), anchor=tk.W)

    def _browse_hash_file(self):
        self._disable_hash_buttons()
        file_path = filedialog.askopenfilename(parent=self)
        if file_path:
            self.current_file_path = file_path
            self.hash_file_path_entry.config(state="normal")
            self.hash_file_path_entry.delete(0, tk.END)
            self.hash_file_path_entry.insert(0, file_path)
            self.hash_file_path_entry.config(state="readonly")
            self.hash_text_input.delete(1.0, tk.END)
            hash_codec_logger.info(f"Selected file for hashing: {file_path}")
            self.main_app_instance.update_status_message(f"File selected: {os.path.basename(file_path)}", level="info")
            self.calculated_hash_result = None
            self.calculated_hash_error = None
            self._clear_hash_compare_status()
            self._clear_hash_output()
        else:
            hash_codec_logger.info("File browsing cancelled for hashing.")
        self._enable_hash_buttons()

    def _clear_hash_file_path(self, event=None):
        if self.current_file_path:
            self.current_file_path = None
            self.hash_file_path_entry.config(state="normal")
            self.hash_file_path_entry.delete(0, tk.END)
            self.hash_file_path_entry.config(state="readonly") # Keep it readonly but empty
            hash_codec_logger.debug("Hash file path cleared due to text input.")
            self.main_app_instance.update_status_message("Using text input for hashing.", level="info")
            self.calculated_hash_result = None
            self.calculated_hash_error = None
            self._clear_hash_output()
        self._clear_hash_compare_status()

    def _clear_hash_output(self):
        self.hash_output.config(state="normal")
        self.hash_output.delete(1.0, tk.END)
        self.hash_output.config(state="disabled")

    def _clear_hash_compare_status(self, event=None):
        """
        Clears the hash comparison status label.
        Called whenever:
        - expected hash changes
        - input text changes
        - new hash calculations begin
        """
        # Ensure the widget exists before trying to configure it
        if hasattr(self, "hash_compare_status_label") and self.hash_compare_status_label.winfo_exists():
            self.hash_compare_status_label.config(
                text="",
                foreground=fg_white
            )
        hash_codec_logger.debug("Hash comparison status cleared.")

    def _start_hash_calculation(self):
        if self.calculation_thread and self.calculation_thread.is_alive():
            self.main_app_instance.update_status_message("Hash calculation already in progress.", level="warning")
            return

        self.calculated_hash_result = None
        self.calculated_hash_error = None
        self._clear_hash_output()
        self._clear_hash_compare_status()
        self._disable_hash_buttons()

        algorithm = self.selected_hash_algorithm.get()
        file_to_hash = self.current_file_path
        text_to_hash = self.hash_text_input.get(1.0, tk.END).strip()

        if not file_to_hash and not text_to_hash:
            self.main_app_instance.update_status_message("Please enter text or select a file for hashing.", level="warning")
            self._enable_hash_buttons()
            return

        self.main_app_instance.update_status_message("Calculating hash... Please wait.", level="info")
        self.calculation_thread = threading.Thread(
            target=self._perform_hash_calculation,
            args=(file_to_hash, text_to_hash, algorithm)
        )
        self.calculation_thread.daemon = True
        self.calculation_thread.start()
        self.after(100, self._check_hash_calculation_status)

    def _perform_hash_calculation(self, file_path, text_content, algorithm):
        try:
            hasher = hashlib.new(algorithm)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                hash_codec_logger.info(f"Calculated {algorithm} for file: {file_path}")
            else:
                hasher.update(text_content.encode('utf-8'))
                hash_codec_logger.info(f"Calculated {algorithm} for text input.")
            self.calculated_hash_result = hasher.hexdigest()
        except FileNotFoundError:
            self.calculated_hash_error = f"File not found: {file_path}"
            hash_codec_logger.error(self.calculated_hash_error)
        except Exception as e:
            self.calculated_hash_error = f"Error calculating hash: {e}"
            hash_codec_logger.error(f"Error during hash calculation: {e}")

    def _check_hash_calculation_status(self):
        if self.calculation_thread.is_alive():
            self.after(100, self._check_hash_calculation_status)
        else:
            self._clear_hash_output()
            if self.calculated_hash_error:
                messagebox.showerror("Error", self.calculated_hash_error, parent=self)
                self.main_app_instance.update_status_message(f"Error: {self.calculated_hash_error}", level="error")
            elif self.calculated_hash_result:
                self.hash_output.config(state="normal")
                self.hash_output.insert(1.0, self.calculated_hash_result)
                self.hash_output.config(state="disabled")
                self.main_app_instance.update_status_message(f"Hash calculation complete.", level="info")
            self._enable_hash_buttons()

    def _disable_hash_buttons(self):
        self.calculate_hash_button.config(state="disabled")
        self.browse_hash_file_button.config(state="disabled")
        self.compare_hash_button.config(state="disabled")
        self.hash_text_input.config(state="disabled")
        self.hash_algo_combobox.config(state="disabled")
        self.expected_hash_entry.config(state="disabled")

    def _enable_hash_buttons(self):
        self.calculate_hash_button.config(state="normal")
        self.browse_hash_file_button.config(state="normal")
        self.compare_hash_button.config(state="normal")
        self.hash_text_input.config(state="normal")
        self.hash_algo_combobox.config(state="readonly")
        self.expected_hash_entry.config(state="normal")
        self.main_app_instance.update_status_message("Ready.", level="info")


    def _compare_hashes(self):
        if not self.calculated_hash_result:
            self.hash_compare_status_label.config(text="Calculate a hash first!", foreground="red")
            self.main_app_instance.update_status_message("Cannot compare: No hash calculated.", level="warning")
            hash_codec_logger.warning("Attempted to compare without a calculated hash.")
            return

        calculated_hash = self.calculated_hash_result
        expected_hash = self.expected_hash_entry.get().strip()

        self._clear_hash_compare_status()

        if not expected_hash:
            self.hash_compare_status_label.config(text="Enter an expected hash!", foreground="red")
            self.main_app_instance.update_status_message("Cannot compare: No expected hash provided.", level="warning")
            hash_codec_logger.warning("No expected hash provided for comparison.")
            return

        if calculated_hash.lower() == expected_hash.lower():
            self.hash_compare_status_label.config(text="Hashes MATCH!", foreground="green")
            self.main_app_instance.update_status_message("Hashes MATCH!", level="info")
            hash_codec_logger.info("Hashes match.")
        else:
            self.hash_compare_status_label.config(text="Hashes DO NOT MATCH!", foreground="red")
            self.main_app_instance.update_status_message("Hashes DO NOT MATCH!", level="error")
            hash_codec_logger.warning("Hashes do not match.")


    # --- Text Manipulation Widgets and Logic ---
    def _create_text_manipulation_widgets(self, parent_frame):
        # Input/Output text areas, buttons for transformations
        ttk.Label(parent_frame, text="Input Text:").pack(anchor="w", pady=(5,0))
        # Apply styles to tk.Text widget
        self.input_text_manip = tk.Text(parent_frame, height=10, wrap="word", bg=bg_dark, fg=fg_white, insertbackground=hologram_glow, selectbackground=text_highlight_color)
        self.input_text_manip.pack(fill="x", pady=(0,5))
        self.input_text_manip.bind("<KeyRelease>", self._auto_count_chars_words) # Bind for auto-counting

        # --- Button Frames ---
        # First row of buttons
        button_frame_row1 = ttk.Frame(parent_frame)
        button_frame_row1.pack(fill="x", pady=5)
        ttk.Button(button_frame_row1, text="To Uppercase", command=self._to_uppercase).pack(side="left", padx=2)
        ttk.Button(button_frame_row1, text="To Lowercase", command=self._to_lowercase).pack(side="left", padx=2)
        ttk.Button(button_frame_row1, text="Trim Whitespace", command=self._trim_whitespace).pack(side="left", padx=2)
        ttk.Button(button_frame_row1, text="Reverse Text", command=self._reverse_text).pack(side="left", padx=2)

        # Second row of buttons
        button_frame_row2 = ttk.Frame(parent_frame)
        button_frame_row2.pack(fill="x", pady=5)
        ttk.Button(button_frame_row2, text="Remove All Whitespace", command=self._remove_all_whitespace).pack(side="left", padx=2)
        ttk.Button(button_frame_row2, text="Remove Duplicate Lines", command=self._remove_duplicate_lines).pack(side="left", padx=2)


        ttk.Label(parent_frame, text="Output Text:").pack(anchor="w", pady=(5,0))
        # Apply styles to tk.Text widget
        self.output_text_manip = tk.Text(parent_frame, height=10, wrap="word", state="disabled", bg=bg_dark, fg=fg_white) # No insertbackground for disabled
        self.output_text_manip.pack(fill="both", expand=True, pady=(0,5))
        
        # Output actions and status
        output_action_frame = ttk.Frame(parent_frame)
        output_action_frame.pack(fill="x", pady=5)
        
        # Display auto-updated character/word count
        ttk.Label(output_action_frame, textvariable=self.text_manip_status_var, font=("Arial", 10), foreground=fg_white).pack(side="left", padx=2)
        ttk.Button(output_action_frame, text="Copy Output", command=lambda: self._copy_text_manip_output()).pack(side="right", padx=2)
        
        # Initial count when the tab is first displayed
        self._auto_count_chars_words()


    # --- Text Manipulation Methods ---
    def _to_uppercase(self):
        content = self.input_text_manip.get("1.0", tk.END).strip()
        self._set_text_manip_output(content.upper())
        self.main_app_instance.update_status_message("Text converted to uppercase.", level="info")

    def _to_lowercase(self):
        content = self.input_text_manip.get("1.0", tk.END).strip()
        self._set_text_manip_output(content.lower())
        self.main_app_instance.update_status_message("Text converted to lowercase.", level="info")

    def _remove_all_whitespace(self):
        content = self.input_text_manip.get("1.0", tk.END).strip()
        self._set_text_manip_output("".join(content.split())) # Removes all whitespace
        self.main_app_instance.update_status_message("All whitespace removed.", level="info")

    def _trim_whitespace(self):
        content = self.input_text_manip.get("1.0", tk.END).strip()
        lines = content.splitlines()
        trimmed_lines = [line.strip() for line in lines]
        self._set_text_manip_output("\n".join(trimmed_lines))
        self.main_app_instance.update_status_message("Leading/trailing whitespace trimmed from lines.", level="info")

    def _reverse_text(self):
        content = self.input_text_manip.get("1.0", tk.END).strip()
        reversed_content = content[::-1]
        self._set_text_manip_output(reversed_content)
        self.main_app_instance.update_status_message("Text reversed.", level="info")

    def _remove_duplicate_lines(self):
        content = self.input_text_manip.get("1.0", tk.END).strip()
        lines = content.splitlines()
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                unique_lines.append(line)
                seen.add(line)
        self._set_text_manip_output("\n".join(unique_lines))
        self.main_app_instance.update_status_message("Duplicate lines removed.", level="info")

    # NEW: Automatic character/word count method
    def _auto_count_chars_words(self, event=None): # event=None for manual calls
        content = self.input_text_manip.get("1.0", tk.END).strip()
        char_count = len(content)
        # Use re.findall to correctly count words, handling various separators
        words = [word for word in content.split() if word] # Filter out empty strings from split
        word_count = len(words)
        
        status_message = f"Characters: {char_count}, Words: {word_count}"
        self.text_manip_status_var.set(status_message)


    def _set_text_manip_output(self, text):
        self.output_text_manip.config(state="normal")
        self.output_text_manip.delete("1.0", tk.END)
        self.output_text_manip.insert("1.0", text)
        self.output_text_manip.config(state="disabled")

    def _copy_text_manip_output(self):
        content = self.output_text_manip.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.main_app_instance.update_status_message("Output copied to clipboard.", level="info")
        else:
            self.main_app_instance.update_status_message("No text to copy.", level="warning")

    # --- Code Snippets Widgets and Logic ---
    def _create_code_snippets_widgets(self, parent_frame):
        # Listbox for snippets, entry for new, text area for content
        ttk.Label(parent_frame, text="Snippets:").pack(anchor="w", pady=(5,0))
        # Apply styles to tk.Listbox widget
        self.snippet_listbox = tk.Listbox(parent_frame, height=10, bg=bg_dark, fg=fg_white, selectbackground=text_highlight_color, selectforeground="black", activestyle="none")
        self.snippet_listbox.pack(fill="x", pady=(0,5))
        self.snippet_listbox.bind("<<ListboxSelect>>", self._on_snippet_select)

        self.snippet_name_entry = ttk.Entry(parent_frame, textvariable=self.snippet_name_var)
        self.snippet_name_entry.pack(fill="x", pady=2)
        # Use a more generic grey for placeholder as style.fg_white might override
        self._setup_placeholder(self.snippet_name_entry, self.snippet_name_var, "Snippet Name", default_color='grey', active_color=fg_white)
        
        self.snippet_language_var = tk.StringVar(value="Plain Text")
        ttk.Combobox(parent_frame, textvariable=self.snippet_language_var, values=["Python", "JavaScript", "HTML", "CSS", "SQL", "Bash", "JSON", "Plain Text"], state="readonly").pack(fill="x", pady=2)

        # Apply styles to tk.Text widget
        self.snippet_code_text = tk.Text(parent_frame, height=10, wrap="word", bg=bg_dark, fg=fg_white, insertbackground=hologram_glow, selectbackground=text_highlight_color)
        self.snippet_code_text.pack(fill="both", expand=True, pady=2)

        snippet_button_frame = ttk.Frame(parent_frame)
        snippet_button_frame.pack(fill="x", pady=5)
        ttk.Button(snippet_button_frame, text="Add/Update Snippet", command=self._add_update_snippet).pack(side="left", padx=2)
        ttk.Button(snippet_button_frame, text="Delete Snippet", command=self._delete_snippet).pack(side="left", padx=2)
        ttk.Button(snippet_button_frame, text="Copy Snippet Code", command=self._copy_snippet_code).pack(side="right", padx=2)

    # --- Manual Placeholder Implementation for Snippet Name ---
    def _setup_placeholder(self, entry_widget, string_var, placeholder_text, default_color, active_color):
        def on_focus_in(event):
            if string_var.get() == placeholder_text:
                string_var.set("")
                entry_widget.config(foreground=active_color) 
        
        def on_focus_out(event):
            if not string_var.get():
                string_var.set(placeholder_text)
                entry_widget.config(foreground=default_color)
            else:
                entry_widget.config(foreground=active_color)

        string_var.set(placeholder_text)
        entry_widget.config(foreground=default_color)
        entry_widget.bind("<FocusIn>", on_focus_in)
        entry_widget.bind("<FocusOut>", on_focus_out)

    # --- Code Snippet Methods ---
    def _load_snippets(self):
        # Store snippets in the user's config directory, same as settings.json
        snippets_file = os.path.join(settings_manager.get_user_config_dir(), "snippets.json")

        if os.path.exists(snippets_file):
            try:
                with open(snippets_file, "r", encoding="utf-8") as f:
                    self.snippets = json.load(f)
                hash_codec_logger.info(f"Loaded snippets from {snippets_file}")
            except Exception as e:
                hash_codec_logger.error(f"Error loading snippets from {snippets_file}: {e}")
                self.snippets = []
        else:
            self.snippets = []

    def _save_snippets(self):
        snippets_file = os.path.join(settings_manager.get_user_config_dir(), "snippets.json")
        try:
            # Ensure the directory exists before saving
            os.makedirs(os.path.dirname(snippets_file), exist_ok=True)
            with open(snippets_file, "w", encoding="utf-8") as f:
                json.dump(self.snippets, f, indent=4)
            hash_codec_logger.info(f"Saved snippets to {snippets_file}")
        except Exception as e:
            hash_codec_logger.error(f"Error saving snippets to {snippets_file}: {e}")

    def _update_snippet_list_ui(self):
        # Only update if the snippet_listbox has been created
        if hasattr(self, 'snippet_listbox') and self.snippet_listbox.winfo_exists():
            self.snippet_listbox.delete(0, tk.END)
            for snippet in self.snippets:
                self.snippet_listbox.insert(tk.END, snippet.get("name", "Unnamed Snippet"))

    def _on_snippet_select(self, event):
        selection = self.snippet_listbox.curselection()
        if selection:
            index = selection[0]
            snippet = self.snippets[index]
            
            # Clear placeholder if present before setting new text
            if self.snippet_name_var.get() == "Snippet Name" and self.snippet_name_entry['foreground'] == 'grey':
                self.snippet_name_var.set("")
                self.snippet_name_entry.config(foreground=fg_white) # Set to normal text color

            self.snippet_name_var.set(snippet.get("name", ""))
            self.snippet_language_var.set(snippet.get("language", "Plain Text"))
            self.snippet_code_text.delete("1.0", tk.END)
            self.snippet_code_text.insert("1.0", snippet.get("code", ""))
        else:
            # If nothing selected, reset inputs and restore placeholder
            self.snippet_name_var.set("Snippet Name")
            self.snippet_name_entry.config(foreground='grey') # Set to placeholder color
            self.snippet_language_var.set("Plain Text")
            self.snippet_code_text.delete("1.0", tk.END)


    def _add_update_snippet(self):
        name = self.snippet_name_var.get().strip()
        # If placeholder is still there, treat as empty
        if name == "Snippet Name":
            name = ""

        language = self.snippet_language_var.get()
        code = self.snippet_code_text.get("1.0", tk.END).strip()

        if not name or not code:
            messagebox.showwarning("Warning", "Snippet Name and Code cannot be empty.", parent=self)
            return

        # Check if updating an existing snippet by name (if selected, or if name matches existing)
        found_index = -1
        for i, snippet in enumerate(self.snippets):
            if snippet["name"] == name:
                found_index = i
                break

        if found_index != -1:
            # Update existing snippet
            self.snippets[found_index] = {"name": name, "language": language, "code": code}
            self.main_app_instance.update_status_message(f"Snippet '{name}' updated.", level="info")
        else:
            # Add new snippet
            self.snippets.append({"name": name, "language": language, "code": code})
            self.main_app_instance.update_status_message(f"Snippet '{name}' added.", level="info")
        
        self._save_snippets()
        self._update_snippet_list_ui()
        # Reselect the item in the listbox if it was an update or highlight new item
        for i, snippet in enumerate(self.snippets):
            if snippet["name"] == name:
                self.snippet_listbox.selection_clear(0, tk.END)
                self.snippet_listbox.selection_set(i)
                self.snippet_listbox.see(i)
                break

    def _delete_snippet(self):
        selection = self.snippet_listbox.curselection()
        if selection:
            index = selection[0]
            name = self.snippets[index]["name"]
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete snippet '{name}'?", parent=self):
                del self.snippets[index]
                self.main_app_instance.update_status_message(f"Snippet '{name}' deleted.", level="info")
                self._save_snippets()
                self._update_snippet_list_ui()
                self.snippet_name_var.set("Snippet Name") # Reset to placeholder
                self.snippet_name_entry.config(foreground='grey') # Set to placeholder color
                self.snippet_language_var.set("Plain Text")
                self.snippet_code_text.delete("1.0", tk.END)
        else:
            messagebox.showwarning("Warning", "No snippet selected to delete.", parent=self)

    def _copy_snippet_code(self):
        selection = self.snippet_listbox.curselection()
        if selection:
            index = selection[0]
            code = self.snippets[index].get("code", "")
            if code:
                self.clipboard_clear()
                self.clipboard_append(code)
                self.main_app_instance.update_status_message("Snippet code copied to clipboard.", level="info")
            else:
                self.main_app_instance.update_status_message("Selected snippet has no code to copy.", level="warning")
        else:
            messagebox.showwarning("Warning", "No snippet selected to copy.", parent=self)

    # --- Module Lifecycle & RPC ---
    def _on_tab_change(self, event):
        selected_tab_id = self.notebook.select()
        selected_tab_text = self.notebook.tab(selected_tab_id, "text")

        if selected_tab_text == "Code Snippets":
            self._update_snippet_list_ui() 
        elif selected_tab_text == "Text Manipulation": # Clear status and re-evaluate on tab change
            self.text_manip_status_var.set("") # Clear previous manual status messages
            self._auto_count_chars_words() # Perform initial count for the currently loaded text
        
        # Update RPC based on the current active tab within this module
        self._update_discord_rpc()

    def refresh_settings_ui(self):
        # This is called when the entire HashCodecModule is brought to front
        self._load_snippets()
        self._update_snippet_list_ui() 
        hash_codec_logger.debug("HashCodecModule UI refreshed.")
        self._update_discord_rpc() # Update RPC after refresh

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
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="hash_codec") 
        
        selected_tab_id = self.notebook.select()
        selected_tab_text = self.notebook.tab(selected_tab_id, "text")

        details_text = "Using Hash & Codecs Module" 
        state_text = ""
        large_image_asset = default_rpc.get("large_image", "hash_codec_icon") # Use the module's primary icon

        if selected_tab_text == "Hashing":
            state_text = "Generating cryptographic hashes"
        elif selected_tab_text == "Text Manipulation":
            state_text = "Performing text transformations"
        elif selected_tab_text == "Code Snippets":
            state_text = "Managing code snippets"
        
        return {
            "details": details_text,
            "state": state_text,
            "large_image": large_image_asset,
            "large_text": "Hash & Codecs", # Always show the combined module name here
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": self.main_app_instance.base_title, # Use main_app's base_title for consistency
        }
    
    def get_menubar_commands(self):
        # Combine help commands from all functionalities
        help_commands = [
            ("About Hash & Codecs Module", self._show_about_dialog), # Overall about
            ("Hashing Help", self._show_hash_codec_help),
            ("Text Manipulation Help", self._show_text_manip_help), 
            ("Code Snippets Help", self._show_snippets_help), 
        ]
        return {
            "help_commands": help_commands
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About Hash & Codecs Module", # Overall module about
            f"This module provides tools for cryptographic hashing, general text manipulation, and code snippet management for {settings_manager.APP_NAME}.\n" # ADDED APP_NAME
            "Developed by Z.",
            parent=self.winfo_toplevel()
        )
        hash_codec_logger.info("About dialog shown for Hash & Codecs Module.")

    def _show_hash_codec_help(self):
        messagebox.showinfo(
            "Hashing Help",
            "Hashing Tab:\n1. Enter text OR browse for a file.\n2. Select a hashing algorithm.\n3. Click 'Calculate Hash'.\n4. (Optional) Enter an expected hash and click 'Compare Hashes'.",
            parent=self.winfo_toplevel()
        )
        hash_codec_logger.info("Help dialog shown for Hashing.")
        
    def _show_text_manip_help(self):
        messagebox.showinfo(
            "Text Manipulation Help",
            "Use this tab to perform various transformations on text.\n\n"
            "**Automatic Counts**: Character and word counts are displayed automatically as you type in the 'Input Text' box.\n\n"
            "**Available Actions**:\n"
            "- **To Uppercase**: Converts all text to capital letters.\n"
            "- **To Lowercase**: Converts all text to small letters.\n"
            "- **Trim Whitespace**: Removes leading and trailing spaces from each line.\n"
            "- **Reverse Text**: Reverses the order of characters in the entire text.\n"
            "- **Remove All Whitespace**: Removes all spaces, tabs, and newlines, joining words together.\n"
            "- **Remove Duplicate Lines**: Keeps only the first occurrence of each unique line.\n",
            parent=self.winfo_toplevel()
        )
        hash_codec_logger.info("Help dialog shown for Text Manipulation.")

    def _show_snippets_help(self):
        messagebox.showinfo(
            "Code Snippets Help",
            "Use this tab to store and organize frequently used code snippets or text templates.\n\n"
            "1. Enter a 'Snippet Name', select a 'Language', and paste your 'Code'.\n"
            "2. Click 'Add/Update Snippet' to save it.\n"
            "3. Select a snippet from the list to view/edit it, or click 'Delete Snippet' to remove it.\n"
            "4. 'Copy Snippet Code' will put the code into your clipboard.",
            parent=self.winfo_toplevel()
        )
        hash_codec_logger.info("Help dialog shown for Code Snippets.")

    def before_hide(self, closing_app=False):
        if self.calculation_thread and self.calculation_thread.is_alive():
            hash_codec_logger.warning("Hash calculation still in progress when module was hidden.")
            self.main_app_instance.update_status_message("Hash calculation might continue in background.", level="warning")
        
        self._save_snippets()
        hash_codec_logger.info("HashCodecModule before_hide executed. Snippets saved.")
        return True