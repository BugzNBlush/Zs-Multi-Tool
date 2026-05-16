import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import logging
import tkinter.font as tkfont
import settings_manager # For APP_NAME and default settings
import time # For Discord RPC timestamps

# Import your theme colors
from modules.zyphria_nexus.styles import bg_dark, fg_white, text_highlight_color, hologram_glow, bg_medium

notes_logger = logging.getLogger(__name__)

class NotesModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        self.current_file_path = None
        self.text_changed = False # Flag to track unsaved changes

        # Load notes settings from app_settings with defaults
        notes_sub_settings = self.app_settings.get("notes_module", settings_manager.DEFAULT_SETTINGS["notes_module"])
        self.font_family = "Segoe UI" # Assuming a default font family
        self.font_size = notes_sub_settings.get("default_font_size", settings_manager.DEFAULT_SETTINGS["notes_module"]["default_font_size"])
        self.current_fg_color = "#FFFFFF" # Default text color (white) - used for color picker start and button

        self._setup_fonts()
        self._setup_button_styles()

        self.create_widgets()
        self._configure_text_tags() # Will include color tag
        
        self.update_window_title_status()
        self._update_counts() # Initial call for word/char count

        notes_logger.info("NotesModule initialized.")
        self.main_app_instance.update_status_message("Notes module loaded.", level="info")
        self.main_app_instance.after(100, self._update_discord_rpc) # Initial RPC update after widget creation is complete


    def _setup_fonts(self):
        # Update self.base_text_font with the loaded font size
        self.base_text_font = tkfont.Font(family=self.font_family, size=self.font_size)

        base_family = self.base_text_font.actual("family")
        base_size = self.base_text_font.actual("size")

        self.bold_font = tkfont.Font(family=base_family, size=base_size, weight="bold")
        self.italic_font = tkfont.Font(family=base_family, size=base_size, slant="italic")
        self.underline_font = tkfont.Font(family=base_family, size=base_size, underline=True)

        notes_logger.debug("Notes module fonts initialized.")

    def _setup_button_styles(self):
        s = ttk.Style()
        # Ensure these styles exist or are compatible with your theme
        s.configure('Toggled.TButton', background=text_highlight_color, foreground='black') # Brighter for "on" state
        s.configure('Untoggled.TButton', background=bg_medium, foreground=fg_white) # Default button state
        
        self.btn_bold = None
        self.btn_italic = None
        self.btn_underline = None
        self.btn_color = None # Reference for the color button
        notes_logger.debug("Notes module button styles initialized.")


    def _configure_text_tags(self):
        self.text_widget.configure(font=self.base_text_font)

        self.text_widget.tag_configure("bold", font=self.bold_font)
        self.text_widget.tag_configure("italic", font=self.italic_font)
        self.text_widget.tag_configure("underline", font=self.underline_font)

        # Base color tag, which can be dynamically configured
        self.text_widget.tag_configure("fg_color", foreground=self.current_fg_color)
        notes_logger.debug("Notes module text tags configured.")


    def create_widgets(self):
        # Toolbar Frame
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)

        # File Operations Buttons
        ttk.Button(toolbar_frame, text="New", command=self.new_file).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2, pady=2)

        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        # Formatting Buttons (Bold, Italic, Underline)
        self.btn_bold = ttk.Button(toolbar_frame, text="B", command=lambda: self._toggle_tag_for_selection("bold"), style='Untoggled.TButton')
        self.btn_bold.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_italic = ttk.Button(toolbar_frame, text="I", command=lambda: self._toggle_tag_for_selection("italic"), style='Untoggled.TButton')
        self.btn_italic.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_underline = ttk.Button(toolbar_frame, text="U", command=lambda: self._toggle_tag_for_selection("underline"), style='Untoggled.TButton')
        self.btn_underline.pack(side=tk.LEFT, padx=2, pady=2)
        
        # NEW: Color Button - changed to tk.Button (ttk.Button doesn't support direct background/foreground changes easily)
        self.btn_color = tk.Button(toolbar_frame, text="Color", command=self._choose_text_color,
                                    background=self.current_fg_color, 
                                    foreground="#000000" if sum(int(self.current_fg_color[i:i+2], 16) for i in (1, 3, 5)) / 3 > 128 else "#FFFFFF",
                                    relief="raised") # Use raised relief for tk.Button to look more like ttk
        self.btn_color.pack(side=tk.LEFT, padx=2, pady=2)

        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        # Undo/Redo Buttons
        ttk.Button(toolbar_frame, text="Undo", command=self.do_undo).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar_frame, text="Redo", command=self.do_redo).pack(side=tk.LEFT, padx=2, pady=2)

        # NEW: Remove Formatting Button
        ttk.Button(toolbar_frame, text="Clear Format", command=self.remove_formatting).pack(side=tk.LEFT, padx=2, pady=2)


        # Text Area with Scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind events for word/char count
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, undo=True, bg=bg_dark, fg=fg_white, insertbackground=hologram_glow, selectbackground=text_highlight_color)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_scroll = ttk.Scrollbar(text_frame, command=self.text_widget.yview)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.config(yscrollcommand=text_scroll.set)

        self.text_widget.bind("<<Modified>>", self.on_text_modify)
        # Bind to KeyRelease to update counts and button states
        self.text_widget.bind("<KeyRelease>", self._on_key_release_and_modify) 
        # Bind to mouse clicks for selection changes for button state updates
        self.text_widget.bind("<ButtonRelease-1>", self.update_formatting_buttons)
        # Handle <<Selection>> for when selection changes via keyboard (Shift + arrow)
        self.text_widget.bind("<<Selection>>", self.update_formatting_buttons) 

        # Status Bar for Notes module specific status (not global app status)
        bottom_frame = ttk.Frame(self) # NEW: Frame for status and counts
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        self.notes_status_label = ttk.Label(bottom_frame, text="Ready", anchor=tk.W)
        self.notes_status_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # NEW: Word/Character Count Label
        self.count_label = ttk.Label(bottom_frame, text="Words: 0, Chars: 0", anchor=tk.E)
        self.count_label.pack(side=tk.RIGHT)

        # Initial update of formatting buttons based on default state
        self.update_formatting_buttons()


    # NEW: Unified handler for KeyRelease and Modified events
    def _on_key_release_and_modify(self, event=None):
        self.on_text_modify(event) # Handle modified flag
        self._update_counts()      # Update word/char counts
        self.update_formatting_buttons() # Update button states
        self._update_discord_rpc() # Update RPC on text modification


    # No need for a load_settings directly in NotesModule as it happens in refresh_settings_ui
    # The font size is loaded in __init__ from app_settings
    def save_settings(self):
        # Save font size (and potentially other notes settings) to app_settings
        if "notes_module" not in self.app_settings: self.app_settings["notes_module"] = {}
        self.app_settings["notes_module"]["default_font_size"] = self.font_size
        # No need to call settings_manager.save_settings here as it's typically called by main_app or settings_module.
        notes_logger.debug("Notes settings updated in app_settings.")

    def update_window_title_status(self):
        """Updates the main application window title and this module's status label."""
        file_name = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
        dirty_indicator = "*" if self.text_changed else ""

        # Use main_app_instance.base_title for overall consistency
        self.main_app_instance.set_window_title(f"{self.main_app_instance.base_title} - Notes: {file_name}{dirty_indicator}")
        self.notes_status_label.config(text=f"{file_name}{dirty_indicator} - {('Unsaved Changes' if self.text_changed else 'Saved')}")
        notes_logger.debug(f"Updated notes title/status: {file_name}{dirty_indicator}")
        self._update_discord_rpc() # Update RPC on title/status change

    def on_text_modify(self, event=None):
        if self.text_widget.edit_modified():
            self.text_changed = True
            self.update_window_title_status()
        self.text_widget.edit_modified(False)

    # NEW: Method to update word and character counts
    def _update_counts(self):
        text_content = self.text_widget.get(1.0, tk.END).strip() # Remove trailing newline
        char_count = len(text_content)
        word_count = len(text_content.split())
        self.count_label.config(text=f"Words: {word_count}, Chars: {char_count}")

    # Helper to toggle any tag (bold, italic, underline)
    def _toggle_tag_for_selection(self, tag_name):
        try:
            current_selection = self.text_widget.tag_ranges(tk.SEL)
            if current_selection:
                start = current_selection[0]
                end = current_selection[1]

                # If any part of the selection has the tag, remove it. Otherwise, add it.
                if self.text_widget.tag_nextrange(tag_name, start, end):
                    self.text_widget.tag_remove(tag_name, start, end)
                    notes_logger.info(f"Removed {tag_name} tag from selection.")
                else:
                    self.text_widget.tag_add(tag_name, start, end)
                    notes_logger.info(f"Added {tag_name} tag to selection.")
                self.text_changed = True
                self.update_window_title_status()
            else:
                self.main_app_instance.update_status_message(f"Select text to toggle {tag_name}.", level="warning")
                notes_logger.warning(f"Attempted to toggle {tag_name} without selection.")
        except tk.TclError as e:
            notes_logger.error(f"Error toggling {tag_name}: {e}")
            self.main_app_instance.update_status_message(f"Error toggling {tag_name}: {e}", level="error")
        self.update_formatting_buttons()

    # NEW: Method to choose and apply text color
    def _choose_text_color(self):
        color_code = colorchooser.askcolor(title="Choose Text Color", parent=self)
        if color_code and color_code[1]: # color_code[1] is the hex string
            hex_color = color_code[1]
            try:
                current_selection = self.text_widget.tag_ranges(tk.SEL)
                if current_selection:
                    start = current_selection[0]
                    end = current_selection[1]

                    # Find and remove any existing fg_color_ tags from the selection
                    # Iterate over a copy of tag names to avoid issues if tags are removed during iteration
                    for tag in list(self.text_widget.tag_names(start)): # tags at start of selection
                        if tag.startswith("fg_color_"):
                            self.text_widget.tag_remove(tag, start, end)
                            notes_logger.debug(f"Removed existing color tag: {tag}")


                    # Create a specific tag for this color if it doesn't exist
                    color_tag = f"fg_color_{hex_color.replace('#', '')}"
                    if color_tag not in self.text_widget.tag_names():
                        self.text_widget.tag_configure(color_tag, foreground=hex_color)
                        notes_logger.debug(f"Configured new color tag: {color_tag}")
                    
                    # Apply the new color tag
                    self.text_widget.tag_add(color_tag, start, end)
                    self.current_fg_color = hex_color # Update current color for button feedback
                    notes_logger.info(f"Applied color {hex_color} to selection.")
                    self.text_changed = True
                    self.update_window_title_status()
                else:
                    self.main_app_instance.update_status_message("Select text to change color.", level="warning")
                    notes_logger.warning("Attempted to change color without selection.")
            except tk.TclError as e:
                notes_logger.error(f"Error changing text color: {e}")
                self.main_app_instance.update_status_message(f"Error changing text color: {e}", level="error")
            self.update_formatting_buttons() # Update button feedback
        notes_logger.debug(f"Color chooser returned: {color_code}")

    def do_undo(self):
        try:
            self.text_widget.edit_undo()
            self.text_changed = self.text_widget.edit_modified()
            self.update_window_title_status()
            self._update_counts() # Update counts after undo/redo
            self.main_app_instance.update_status_message("Undo executed.", level="info")
            notes_logger.info("Undo executed.")
        except tk.TclError:
            self.main_app_instance.update_status_message("Nothing to undo.", level="warning")
            notes_logger.debug("Nothing to undo.")
        self.update_formatting_buttons() # Update button states

    def do_redo(self):
        try:
            self.text_widget.edit_redo()
            self.text_changed = self.text_widget.edit_modified()
            self.update_window_title_status()
            self._update_counts() # Update counts after undo/redo
            self.main_app_instance.update_status_message("Redo executed.", level="info")
            notes_logger.info("Redo executed.")
        except tk.TclError:
            self.main_app_instance.update_status_message("Nothing to redo.", level="warning")
            notes_logger.debug("Nothing to redo.")
        self.update_formatting_buttons() # Update button states


    def remove_formatting(self):
        try:
            current_selection = self.text_widget.tag_ranges(tk.SEL)
            if current_selection:
                start = current_selection[0]
                end = current_selection[1]
                for tag in ["bold", "italic", "underline"]: # Remove specific formatting tags
                    self.text_widget.tag_remove(tag, start, end)
                
                # Also remove all fg_color tags
                for tag in list(self.text_widget.tag_names(start)): # Iterate over a copy of tag names
                    if tag.startswith("fg_color_"):
                        self.text_widget.tag_remove(tag, start, end)

                notes_logger.info("Removed all formatting from selection.")
                self.text_changed = True
                self.update_window_title_status()
            else:
                self.main_app_instance.update_status_message("Select text to remove formatting.", level="warning")
                notes_logger.warning("Attempted to remove formatting without selection.")
        except tk.TclError as e:
            notes_logger.error(f"Error removing formatting: {e}")
            self.main_app_instance.update_status_message(f"Error removing formatting: {e}", level="error")
        self.update_formatting_buttons()

    def update_formatting_buttons(self, event=None):
        # Determine the index to check tags at (cursor or start of selection)
        index_to_check = self.text_widget.index(tk.INSERT)
        if self.text_widget.tag_ranges(tk.SEL):
            index_to_check = self.text_widget.index(tk.SEL_FIRST)

        def is_tag_active(tag_name, idx):
            # Check if any character within the selected range (or at insert point) has the tag
            if self.text_widget.tag_ranges(tk.SEL):
                start_sel, end_sel = self.text_widget.tag_ranges(tk.SEL)
                return bool(self.text_widget.tag_nextrange(tag_name, start_sel, end_sel))
            else:
                return tag_name in self.text_widget.tag_names(idx)
        
        # Update Bold, Italic, Underline buttons based on ttk styles
        if self.btn_bold:
            self.btn_bold.config(style='Toggled.TButton' if is_tag_active("bold", index_to_check) else 'Untoggled.TButton')
        if self.btn_italic:
            self.btn_italic.config(style='Toggled.TButton' if is_tag_active("italic", index_to_check) else 'Untoggled.TButton')
        if self.btn_underline:
            self.btn_underline.config(style='Toggled.TButton' if is_tag_active("underline", index_to_check) else 'Untoggled.TButton')
        
        # Update the color button's appearance (now using tk.Button)
        if self.btn_color:
            current_fg_color_for_button = fg_white # Default to theme's foreground color
            
            # Check for specific color tags at the index
            for tag in self.text_widget.tag_names(index_to_check):
                if tag.startswith("fg_color_"):
                    current_fg_color_for_button = "#" + tag.replace("fg_color_", "")
                    break
            
            # Update the tk.Button's background and foreground directly
            self.btn_color.config(background=current_fg_color_for_button,
                                  foreground="#000000" if sum(int(current_fg_color_for_button[i:i+2], 16) for i in (1, 3, 5)) / 3 > 128 else "#FFFFFF")

    def new_file(self):
        if self.text_changed:
            response = messagebox.askyesnocancel("Unsaved Changes", "Do you want to save changes to the current file before creating a new one?", parent=self)
            if response is True:
                if not self.save_file():
                    return
            elif response is None:
                return

        self.text_widget.delete(1.0, tk.END)
        self.current_file_path = None
        self.text_changed = False
        self.update_window_title_status()
        self._update_counts() # Update counts for new file
        self.update_formatting_buttons() # Reset color button to default
        self.main_app_instance.update_status_message("New file created.", level="info")
        notes_logger.info("New notes file created.")

    def open_file(self):
        if self.text_changed:
            response = messagebox.askyesnocancel("Unsaved Changes", "Do you want to save changes to the current file before opening a new one?", parent=self)
            if response is True:
                if not self.save_file():
                    return
            elif response is None:
                return

        file_path = filedialog.askopenfilename(
            parent=self,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.insert(1.0, content)
                self.current_file_path = file_path
                self.text_changed = False
                self.update_window_title_status()
                self._update_counts() # Update counts for opened file
                self.update_formatting_buttons() # Update button states (including color)
                self.main_app_instance.update_status_message(f"Opened: {os.path.basename(file_path)}", level="info")
                notes_logger.info(f"Opened notes file: {file_path}")
            except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {file_path}", parent=self)
                self.main_app_instance.update_status_message(f"Error opening file: File not found.", level="error")
                notes_logger.error(f"File not found: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}", parent=self)
                self.main_app_instance.update_status_message(f"Error opening file: {e}", level="error")
                notes_logger.error(f"Error opening file '{file_path}': {e}")
        else:
            self.main_app_instance.update_status_message("Open file cancelled.", level="info")
            notes_logger.info("Open file operation cancelled.")

    def save_file(self):
        if self.current_file_path:
            try:
                with open(self.current_file_path, "w", encoding="utf-8") as file:
                    file.write(self.text_widget.get(1.0, tk.END))
                self.text_changed = False
                self.update_window_title_status()
                self.main_app_instance.update_status_message(f"Saved: {os.path.basename(self.current_file_path)}", level="info")
                notes_logger.info(f"Saved notes file: {self.current_file_path}")
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}", parent=self)
                self.main_app_instance.update_status_message(f"Error saving file: {e}", level="error")
                notes_logger.error(f"Error saving file '{self.current_file_path}': {e}")
                return False
        else:
            return self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="untitled.txt"
        )
        if file_path:
            self.current_file_path = file_path
            return self.save_file()
        else:
            self.main_app_instance.update_status_message("Save As cancelled.", level="info")
            notes_logger.info("Save As operation cancelled.")
            return False

    def before_hide(self, closing_app=False):
        if self.text_changed:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes in the Notes module. Do you want to save them?",
                parent=self
            )
            if response is True:
                return self.save_file()
            elif response is False:
                self.text_changed = False
                notes_logger.info("Notes changes discarded.")
                return True
            else:
                notes_logger.warning("User cancelled saving notes before hiding module.")
                return False
        self._update_discord_rpc() # Update RPC to reflect module is no longer active (or changed status)
        return True

    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self):
        """Helper method to update Discord RPC based on current module status."""
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
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="notes")
        
        details_text = "Using Notes Module"
        state_text = "Idle"

        file_name = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
        if file_name == "Untitled":
            state_text = "Editing a new note"
        else:
            state_text = f"Editing: {file_name}"
            if self.text_changed:
                state_text += " (Unsaved)"
        
        return {
            "details": details_text,
            "state": state_text,
            "large_image": default_rpc.get("large_image", "notes_icon"),
            "large_text": "Notes Module",
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": self.main_app_instance.base_title, # Use main_app's base_title for consistency
        }


    def get_menubar_commands(self):
        return {
            "file_commands": [
                ("New", self.new_file),
                ("Open...", self.open_file),
                ("Save", self.save_file),
                ("Save As...", self.save_file_as), # Added Save As to menu
            ],
            "edit_commands": [
                ("Undo", self.do_undo),
                ("Redo", self.do_redo),
                None, # Separator
                ("Bold", lambda: self._toggle_tag_for_selection("bold")),
                ("Italic", lambda: self._toggle_tag_for_selection("italic")),
                ("Underline", lambda: self._toggle_tag_for_selection("underline")),
                ("Text Color...", self._choose_text_color), # NEW: Text Color menu item
                ("Clear Formatting", self.remove_formatting), # Added clear formatting to menu
            ],
            "help_commands": [
                ("About Notes", lambda: messagebox.showinfo("About Notes Module", f"A simple text editor for quick notes in {settings_manager.APP_NAME}.\n\nNote: Basic formatting (bold, italic, underline, color) is visual only within the editor and is not saved to plain .txt files.", parent=self)),
                ("Notes Help", lambda: messagebox.showinfo("Notes Help", "Type text, use buttons to open/save. Select text to apply bolding, italics, underlining, or change color. Formatting is visual only within the editor and is not saved to plain .txt files.", parent=self))
            ]
        }

    def refresh_settings_ui(self):
        """Refreshes UI elements based on current app settings."""
        notes_sub_settings = self.app_settings.get("notes_module", settings_manager.DEFAULT_SETTINGS["notes_module"])
        new_font_size = notes_sub_settings.get("default_font_size", settings_manager.DEFAULT_SETTINGS["notes_module"]["default_font_size"])
        
        if new_font_size != self.font_size:
            self.font_size = new_font_size
            self._setup_fonts() # Re-create fonts with new size
            self._configure_text_tags() # Re-apply tags to update font size
            notes_logger.info(f"Notes module font size updated to: {self.font_size}")
            self.main_app_instance.update_status_message(f"Notes font size updated to {self.font_size}.", level="info")
        
        self._update_discord_rpc() # Update RPC after refresh