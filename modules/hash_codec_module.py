# modules/hash_codec_module.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import hashlib
import os
import logging
import threading
import base64
import urllib.parse
import binascii
import codecs # For ROT13
import html # For HTML entities

hash_codec_logger = logging.getLogger(__name__)

class HashCodecModule(ttk.Frame):
    MORSE_CODE_DICT = {
        'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
        'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
        'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
        'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
        'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
        'Z': '--..',
        '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
        '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
        '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.', '!': '-.-.--',
        '/': '-..-.', '(': '-.--.', ')': '-.--.-', '&': '.-...', ':': '---...',
        ';': '-.-.-.', '=': '-...-', '+': '.-.-.', '-': '-....-', '_': '..--.-',
        '"': '.-..-.', '$': '...-..-', '@': '.--.-.', ' ': ' / ' # Space separator for words
    }

    # Reverse dictionary for Morse to Text conversion
    _MORSE_TO_TEXT_TEMP = {value: key for key, value in MORSE_CODE_DICT.items() if key != ' '}
    MORSE_TO_TEXT_DICT = {**_MORSE_TO_TEXT_TEMP, **{'': ' '}} # Add space for ' / ' delimiter


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

        # Encoding Tab specific
        self.selected_encoding_type = tk.StringVar(value="Base64") # Default encoding type

        # Morse Code Tab specific (None for now)

        self.create_widgets()
        hash_codec_logger.debug("HashCodecModule initialized.")

    def create_widgets(self):
        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # Hashing Tab
        self.hash_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.hash_tab, text="Hashing")
        self._create_hashing_widgets(self.hash_tab)

        # Encoding/Decoding Tab
        self.encoding_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.encoding_tab, text="Encoding/Decoding")
        self._create_encoding_widgets(self.encoding_tab)

        # Morse Code Tab (NEW)
        self.morse_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.morse_tab, text="Morse Code")
        self._create_morse_widgets(self.morse_tab) # NEW WIDGET CREATION

    # --- Hashing Tab Widgets and Logic ---
    def _create_hashing_widgets(self, parent_frame):
        # Input Section
        input_label = ttk.Label(parent_frame, text="Input (Text or File):", font=("Arial", 12, "bold"))
        input_label.pack(pady=(0, 5), anchor=tk.W)

        self.hash_text_input = tk.Text(parent_frame, wrap=tk.WORD, height=8, bg="#2A2A2A", fg="#FFFFFF", insertbackground="#00FFFF", selectbackground="#3D4D4D")
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
                                          values=["md5", "sha1", "sha256", "sha512"], state="readonly")
        self.hash_algo_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.hash_algo_combobox.set("sha256")

        # Calculate Button
        self.calculate_hash_button = ttk.Button(parent_frame, text="Calculate Hash", command=self._start_hash_calculation)
        self.calculate_hash_button.pack(fill=tk.X, pady=(0, 15))

        # Output Section
        output_label = ttk.Label(parent_frame, text="Calculated Hash:", font=("Arial", 12, "bold"))
        output_label.pack(pady=(0, 5), anchor=tk.W)

        self.hash_output = tk.Text(parent_frame, wrap=tk.WORD, height=3, state="disabled", bg="#2A2A2A", fg="#00FFFF")
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
            self.hash_file_path_entry.insert(0, tk.END)
            self.hash_file_path_entry.config(state="readonly")
            hash_codec_logger.debug("Hash file path cleared due to text input.")
            self.main_app_instance.update_status_message("Using text input for hashing.", level="info")
            self.calculated_hash_result = None
            self.calculated_hash_error = None
            self._clear_hash_output()
        self._clear_hash_compare_status()

    def _clear_hash_compare_status(self, event=None):
        self.hash_compare_status_label.config(text="")
        hash_codec_logger.debug("Hash comparison status cleared.")

    def _clear_hash_output(self):
        self.hash_output.config(state="normal")
        self.hash_output.delete(1.0, tk.END)
        self.hash_output.config(state="disabled")

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

    # --- Encoding/Decoding Tab Widgets and Logic ---
    def _create_encoding_widgets(self, parent_frame):
        # Input Section
        ttk.Label(parent_frame, text="Input Text:", font=("Arial", 12, "bold")).pack(pady=(0, 5), anchor=tk.W)
        self.encode_input_text = tk.Text(parent_frame, wrap=tk.WORD, height=8, bg="#2A2A2A", fg="#FFFFFF", insertbackground="#00FFFF", selectbackground="#3D4D4D")
        self.encode_input_text.pack(fill=tk.X, pady=(0, 10))

        # Encoding Type Selection
        encoding_type_frame = ttk.Frame(parent_frame)
        encoding_type_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(encoding_type_frame, text="Encoding Type:", width=15).pack(side=tk.LEFT)
        self.encoding_type_combobox = ttk.Combobox(encoding_type_frame, textvariable=self.selected_encoding_type,
                                                   values=["Base64", "Base85", "URL", "Hex", "Binary", "ROT13", "HTML Entities"], state="readonly")
        self.encoding_type_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.encoding_type_combobox.set("Base64")

        # Encode/Decode Buttons
        buttons_frame = ttk.Frame(parent_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(buttons_frame, text="Encode", command=self._perform_encoding).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(buttons_frame, text="Decode", command=self._perform_decoding).pack(side=tk.LEFT, expand=True, padx=5)

        # Output Section
        ttk.Label(parent_frame, text="Output Text:", font=("Arial", 12, "bold")).pack(pady=(0, 5), anchor=tk.W)
        self.encode_output_text = tk.Text(parent_frame, wrap=tk.WORD, height=8, state="disabled", bg="#2A2A2A", fg="#00FFFF")
        self.encode_output_text.pack(fill=tk.X, pady=(0, 10))

        self.encoding_status_label = ttk.Label(parent_frame, text="", font=("Arial", 11))
        self.encoding_status_label.pack(pady=(0, 5), anchor=tk.W)

    def _perform_encoding(self):
        self.encode_output_text.config(state="normal")
        self.encode_output_text.delete(1.0, tk.END)
        self.encoding_status_label.config(text="")

        input_text = self.encode_input_text.get(1.0, tk.END).strip()
        if not input_text:
            self.encoding_status_label.config(text="Enter text to encode!", foreground="red")
            self.main_app_instance.update_status_message("No input for encoding.", level="warning")
            self.encode_output_text.config(state="disabled")
            return

        encoding_type = self.selected_encoding_type.get()
        encoded_text = ""
        try:
            if encoding_type == "Base64":
                encoded_text = base64.b64encode(input_text.encode('utf-8')).decode('utf-8')
            elif encoding_type == "Base85":
                encoded_text = base64.b85encode(input_text.encode('utf-8')).decode('ascii')
            elif encoding_type == "URL":
                encoded_text = urllib.parse.quote_plus(input_text)
            elif encoding_type == "Hex":
                encoded_text = binascii.hexlify(input_text.encode('utf-8')).decode('utf-8')
            elif encoding_type == "Binary":
                encoded_text = ' '.join(format(ord(char), '08b') for char in input_text)
            elif encoding_type == "ROT13":
                encoded_text = codecs.encode(input_text, 'rot13')
            elif encoding_type == "HTML Entities":
                encoded_text = html.escape(input_text)
            else:
                raise ValueError(f"Unknown encoding type: {encoding_type}")
            
            self.encode_output_text.insert(1.0, encoded_text)
            self.encoding_status_label.config(text=f"Encoded successfully using {encoding_type}.", foreground="green")
            self.main_app_instance.update_status_message(f"Encoded using {encoding_type}.", level="info")
            hash_codec_logger.info(f"Encoded text using {encoding_type}.")

        except Exception as e:
            self.encoding_status_label.config(text=f"Encoding Error: {e}", foreground="red")
            self.main_app_instance.update_status_message(f"Encoding Error: {e}", level="error")
            hash_codec_logger.error(f"Encoding error for {encoding_type}: {e}")
        finally:
            self.encode_output_text.config(state="disabled")

    def _perform_decoding(self):
        self.encode_output_text.config(state="normal")
        self.encode_output_text.delete(1.0, tk.END)
        self.encoding_status_label.config(text="")

        input_text = self.encode_input_text.get(1.0, tk.END).strip()
        if not input_text:
            self.encoding_status_label.config(text="Enter text to decode!", foreground="red")
            self.main_app_instance.update_status_message("No input for decoding.", level="warning")
            self.encode_output_text.config(state="disabled")
            return

        encoding_type = self.selected_encoding_type.get()
        decoded_text = ""
        try:
            if encoding_type == "Base64":
                decoded_text = base64.b64decode(input_text.encode('utf-8')).decode('utf-8')
            elif encoding_type == "Base85":
                decoded_text = base64.b85decode(input_text.encode('ascii')).decode('utf-8')
            elif encoding_type == "URL":
                decoded_text = urllib.parse.unquote_plus(input_text)
            elif encoding_type == "Hex":
                decoded_text = binascii.unhexlify(input_text.encode('utf-8')).decode('utf-8')
            elif encoding_type == "Binary":
                # Remove spaces, then convert binary chunks to characters
                binary_string = input_text.replace(' ', '')
                if not all(c in '01' for c in binary_string) or len(binary_string) % 8 != 0:
                    raise ValueError("Invalid binary string format.")
                decoded_text = ''.join(chr(int(binary_string[i:i+8], 2)) for i in range(0, len(binary_string), 8))
            elif encoding_type == "ROT13":
                decoded_text = codecs.decode(input_text, 'rot13')
            elif encoding_type == "HTML Entities":
                decoded_text = html.unescape(input_text)
            else:
                raise ValueError(f"Unknown encoding type: {encoding_type}")

            self.encode_output_text.insert(1.0, decoded_text)
            self.encoding_status_label.config(text=f"Decoded successfully using {encoding_type}.", foreground="green")
            self.main_app_instance.update_status_message(f"Decoded using {encoding_type}.", level="info")
            hash_codec_logger.info(f"Decoded text using {encoding_type}.")

        except (binascii.Error, UnicodeDecodeError, ValueError, TypeError) as e:
            self.encoding_status_label.config(text=f"Decoding Error: Invalid {encoding_type} format. {e}", foreground="red")
            self.main_app_instance.update_status_message(f"Decoding Error: Invalid {encoding_type} format. {e}", level="error")
            hash_codec_logger.error(f"Decoding error for {encoding_type}: {e}")
        except Exception as e:
            self.encoding_status_label.config(text=f"Decoding Error: {e}", foreground="red")
            self.main_app_instance.update_status_message(f"Decoding Error: {e}", level="error")
            hash_codec_logger.error(f"Decoding error for {encoding_type}: {e}")
        finally:
            self.encode_output_text.config(state="disabled")

    # --- NEW: Morse Code Tab Widgets and Logic ---
    def _create_morse_widgets(self, parent_frame):
        # Main title
        ttk.Label(parent_frame, text=".--. .-.. .- -. -- --- .-. ... .", font=("Arial", 18, "bold")).pack(pady=10) # PLAN MORSE
        ttk.Label(parent_frame, text="Morse Code Translator", font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Text to Morse Section
        text_frame = ttk.LabelFrame(parent_frame, text=" Text Input ")
        text_frame.pack(fill=tk.X, padx=10, pady=5)

        self.morse_text_input = tk.Text(text_frame, wrap=tk.WORD, height=6, bg="#2A2A2A", fg="#FFFFFF", insertbackground="#00FFFF", selectbackground="#3D4D4D")
        self.morse_text_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.morse_text_input.bind("<KeyRelease>", self._auto_text_to_morse)

        ttk.Button(text_frame, text="Translate to Morse", command=self._text_to_morse_from_tab).pack(pady=5)

        # Morse to Text Section
        morse_frame = ttk.LabelFrame(parent_frame, text=" Morse Code Input ")
        morse_frame.pack(fill=tk.X, padx=10, pady=5)

        self.morse_morse_input = tk.Text(morse_frame, wrap=tk.WORD, height=6, bg="#2A2A2A", fg="#00FFFF", insertbackground="#00FFFF", selectbackground="#3D4D4D")
        self.morse_morse_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.morse_morse_input.bind("<KeyRelease>", self._auto_morse_to_text)

        ttk.Button(morse_frame, text="Translate to Text", command=self._morse_to_text_from_tab).pack(pady=5)

        # Status/Result Label for Morse tab
        self.morse_status_label = ttk.Label(parent_frame, text="Ready for translation.", font=("Arial", 11))
        self.morse_status_label.pack(fill=tk.X, padx=10, pady=10)

    def _auto_text_to_morse(self, event=None):
        """Automatically translates text to Morse as user types in the Text Input box."""
        self._text_to_morse_from_tab()

    def _auto_morse_to_text(self, event=None):
        """Automatically translates Morse to text as user types in the Morse Code Input box."""
        self._morse_to_text_from_tab()

    def _text_to_morse_from_tab(self):
        self.morse_status_label.config(text="")
        text = self.morse_text_input.get(1.0, tk.END).strip().upper() # Convert to uppercase for dictionary lookup
        if not text:
            self.morse_morse_input.delete(1.0, tk.END)
            self.morse_status_label.config(text="Enter text to translate.", foreground="orange")
            return

        morse_code_list = []
        words = text.split(' ')
        for i, word in enumerate(words):
            word_morse_parts = []
            for char in word:
                if char in self.MORSE_CODE_DICT:
                    word_morse_parts.append(self.MORSE_CODE_DICT[char])
                # else: ignore unknown characters

            if word_morse_parts: # Only add if word had translatable characters
                morse_code_list.append(' '.join(word_morse_parts))
            
            # Add word separator if it's not the last word and there was a space
            if i < len(words) - 1:
                morse_code_list.append('/')

        result = ' '.join(morse_code_list).strip()
        result = result.replace(' / / ', ' / ').replace('  ', ' ') # Clean up multiple slashes/spaces if any

        self.morse_morse_input.delete(1.0, tk.END)
        self.morse_morse_input.insert(1.0, result)
        self.morse_status_label.config(text="Text translated to Morse.", foreground="green")
        self.main_app_instance.update_status_message("Text translated to Morse code.", level="info")
        hash_codec_logger.info(f"Translated text to Morse: {text[:50]}...")

    def _morse_to_text_from_tab(self):
        self.morse_status_label.config(text="")
        morse_text = self.morse_morse_input.get(1.0, tk.END).strip()
        if not morse_text:
            self.morse_text_input.delete(1.0, tk.END)
            self.morse_status_label.config(text="Enter Morse code to translate.", foreground="orange")
            return

        word_delimiter_token = "__WORD_SPACE__"
        morse_text_processed = morse_text.replace(' / ', word_delimiter_token)
        morse_chars = morse_text_processed.split(' ')

        decoded_text_list = []
        for morse_char in morse_chars:
            if morse_char == word_delimiter_token:
                decoded_text_list.append(' ')
            elif morse_char in self.MORSE_TO_TEXT_DICT:
                decoded_text_list.append(self.MORSE_TO_TEXT_DICT[morse_char])
            # else: ignore unknown Morse sequences

        result = ''.join(decoded_text_list)
        self.morse_text_input.delete(1.0, tk.END)
        self.morse_text_input.insert(1.0, result)
        self.morse_status_label.config(text="Morse code translated to text.", foreground="green")
        self.main_app_instance.update_status_message("Morse code translated to text.", level="info")
        hash_codec_logger.info(f"Translated Morse code to text: {morse_text[:50]}...")

    # --- Menu Bar Commands for the Module ---
    def get_menubar_commands(self):
        return {
            "help_commands": [
                ("About Hashing & Encoding", lambda: messagebox.showinfo("About Hashing & Encoding",
                                                                  "Provides utilities for cryptographic hashing (MD5, SHA1, SHA256, SHA512) and various text encoding/decoding schemes (Base64, Base85, URL, Hex, Binary, ROT13, HTML Entities).\n\nUseful for data integrity verification and various text transformations.",
                                                                  parent=self)),
                ("Hashing Help", lambda: messagebox.showinfo("Hashing Help",
                                                                "Hashing Tab:\n1. Enter text OR browse for a file.\n2. Select a hashing algorithm.\n3. Click 'Calculate Hash'.\n4. (Optional) Enter an expected hash and click 'Compare Hashes'.",
                                                                parent=self)),
                ("Encoding/Decoding Help", lambda: messagebox.showinfo("Encoding/Decoding Help",
                                                                "Encoding/Decoding Tab:\n1. Enter text to encode/decode.\n2. Select an encoding type (Base64, Base85, URL, Hex, Binary, ROT13, HTML Entities).\n3. Click 'Encode' or 'Decode'.\n\nNote: Decoding requires valid input for the selected type.",
                                                                parent=self)),
                # NEW: Morse Code Help commands
                ("About Morse Code", self._show_morse_about_dialog),
                ("Morse Code Help", self._show_morse_help_dialog),
            ]
        }
    
    # NEW: Morse Code specific dialogs
    def _show_morse_about_dialog(self):
        messagebox.showinfo(
            "About Morse Code Translator",
            "This module allows you to translate plain text to Morse code and vice-versa.\n\n"
            "Morse code uses '.' (dot) and '-' (dash) to represent letters, numbers, and punctuation.\n"
            "Letters are separated by a space, and words are separated by ' / ' (space, slash, space).\n\n"
            "Developed by Z.",
            parent=self.winfo_toplevel()
        )
        hash_codec_logger.info("About dialog shown for Morse Code.")

    def _show_morse_help_dialog(self):
        help_text = (
            "Morse Code Translator Help Guide:\n\n"
            "1. To translate text to Morse code:\n"
            "   - Type your message into the 'Text Input' box.\n"
            "   - The Morse code equivalent will appear in the 'Morse Code Input' box automatically.\n"
            "   - Click 'Translate to Morse' to manually trigger if auto-translation is off or to confirm.\n\n"
            "2. To translate Morse code to text:\n"
            "   - Type or paste Morse code into the 'Morse Code Input' box.\n"
            "   - Use a single space to separate Morse characters (e.g., `.- -...`) and ' / ' to separate words (e.g., `.... . .-.. .-.. --- / .-- --- .-. .-.. -..`).\n"
            "   - The plain text will appear in the 'Text Input' box automatically.\n"
            "   - Click 'Translate to Text' to manually trigger if auto-translation is off or to confirm.\n\n"
            "Note: Only recognized characters/Morse sequences will be translated. Unknown inputs are ignored."
        )
        messagebox.showinfo(
            "Morse Code Help",
            help_text,
            parent=self.winfo_toplevel()
        )
        hash_codec_logger.info("Help dialog shown for Morse Code.")


    def before_hide(self, closing_app=False):
        # Check if hash calculation is in progress
        if self.calculation_thread and self.calculation_thread.is_alive():
            hash_codec_logger.warning("Hash calculation still in progress when module was hidden.")
            self.main_app_instance.update_status_message("Hash calculation might continue in background.", level="warning")
        return True