# modules/unit_converter_module.py
import tkinter as tk
from tkinter import ttk, messagebox
import logging

unit_converter_logger = logging.getLogger(__name__)

class UnitConverterModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        # Initialize StringVars here to ensure they exist before widgets use them
        self.category_var = tk.StringVar()
        self.input_value_var = tk.StringVar() # MOVED: Initialized here
        self.from_unit_var = tk.StringVar()
        self.to_unit_var = tk.StringVar()
        self.output_result_var = tk.StringVar()

        self._initialize_conversion_data() # Setup conversion factors
        self.create_widgets()
        self._set_initial_state() # Set default selections
        
        unit_converter_logger.info("UnitConverterModule initialized.")
        self.main_app_instance.update_status_message("Unit Converter module loaded.", level="info")

    def _initialize_conversion_data(self):
        # Conversion factors. All units convert to a base unit (e.g., meter, gram, celsius_base)
        # and then from that base unit to the target unit.
        self.conversion_data = {
            "Length": {
                "base_unit": "meter",
                "units": {
                    "meter": 1.0,
                    "kilometer": 1000.0,
                    "centimeter": 0.01,
                    "millimeter": 0.001,
                    "micrometer": 1e-6,
                    "nanometer": 1e-9,
                    "mile": 1609.34,
                    "yard": 0.9144,
                    "foot": 0.3048,
                    "inch": 0.0254
                }
            },
            "Mass": {
                "base_unit": "gram",
                "units": {
                    "gram": 1.0,
                    "kilogram": 1000.0,
                    "milligram": 0.001,
                    "pound": 453.592,
                    "ounce": 28.3495,
                    "tonne": 1_000_000.0
                }
            },
            "Temperature": {
                "base_unit": "celsius_base", # Fictional base to handle non-linear conversion
                "units": {
                    "Celsius": lambda val, to_base: val if to_base else val,
                    "Fahrenheit": lambda val, to_base: (val - 32) * 5/9 if to_base else (val * 9/5) + 32,
                    "Kelvin": lambda val, to_base: val - 273.15 if to_base else val + 273.15,
                }
            },
            "Volume": {
                "base_unit": "liter",
                "units": {
                    "liter": 1.0,
                    "milliliter": 0.001,
                    "cubic meter": 1000.0,
                    "cubic centimeter": 0.001,
                    "gallon (US)": 3.78541,
                    "quart (US)": 0.946353,
                    "pint (US)": 0.473176,
                    "fluid ounce (US)": 0.0295735
                }
            },
            "Time": {
                "base_unit": "second",
                "units": {
                    "second": 1.0,
                    "millisecond": 0.001,
                    "minute": 60.0,
                    "hour": 3600.0,
                    "day": 86400.0,
                    "week": 604800.0,
                    "year": 31536000.0 # Approximate solar year
                }
            }
        }
        self.categories = list(self.conversion_data.keys())

    def create_widgets(self):
        # Main title
        ttk.Label(self, text="📊 Unit Converter 📏", font=("Arial", 18, "bold")).pack(pady=20)

        # Frame for controls
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        control_frame.grid_columnconfigure(1, weight=1) # Allow comboboxes to expand

        # Category selection
        ttk.Label(control_frame, text="Category:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.category_combobox = ttk.Combobox(control_frame, textvariable=self.category_var,
                                              values=self.categories, state="readonly")
        self.category_combobox.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        self.category_combobox.bind("<<ComboboxSelected>>", self._on_category_selected)

        # Value to convert
        ttk.Label(control_frame, text="Value:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.input_value_entry = ttk.Entry(control_frame, textvariable=self.input_value_var)
        self.input_value_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # From Unit
        ttk.Label(control_frame, text="From:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.from_unit_combobox = ttk.Combobox(control_frame, textvariable=self.from_unit_var, state="readonly")
        self.from_unit_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.from_unit_combobox.bind("<<ComboboxSelected>>", self._do_conversion_if_possible)

        # To Unit
        ttk.Label(control_frame, text="To:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.to_unit_combobox = ttk.Combobox(control_frame, textvariable=self.to_unit_var, state="readonly")
        self.to_unit_combobox.grid(row=2, column=3, padx=5, pady=5, sticky="ew")
        self.to_unit_combobox.bind("<<ComboboxSelected>>", self._do_conversion_if_possible)

        # Convert Button
        ttk.Button(control_frame, text="Convert", command=self._do_conversion).grid(row=3, column=0, columnspan=4, padx=5, pady=10, sticky="ew")

        # Output Section
        output_frame = ttk.LabelFrame(self, text=" Result ")
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        output_frame.grid_columnconfigure(0, weight=1)

        ttk.Entry(output_frame, textvariable=self.output_result_var, state="readonly", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.status_label = ttk.Label(output_frame, text="", font=("Arial", 11))
        self.status_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        
        # This needs to be after self.input_value_var is defined
        self.input_value_var.trace_add("write", lambda *args: self._do_conversion_if_possible())


    def _set_initial_state(self):
        if self.categories:
            self.category_var.set(self.categories[0])
            self._update_unit_comboboxes(self.categories[0])
            # Set default units if available
            current_category = self.conversion_data[self.categories[0]]
            units_list = list(current_category["units"].keys())
            if len(units_list) >= 2:
                self.from_unit_var.set(units_list[0])
                self.to_unit_var.set(units_list[1])
            elif len(units_list) == 1:
                self.from_unit_var.set(units_list[0])
                self.to_unit_var.set(units_list[0]) # Fallback if only one unit
        self.input_value_var.set("1.0") # Default input value
        self._do_conversion() # Perform initial conversion

    def _on_category_selected(self, event=None):
        selected_category = self.category_var.get()
        self._update_unit_comboboxes(selected_category)
        # Reset units to defaults for new category
        current_category_data = self.conversion_data.get(selected_category)
        if current_category_data:
            units_list = list(current_category_data["units"].keys())
            if len(units_list) >= 2:
                self.from_unit_var.set(units_list[0])
                self.to_unit_var.set(units_list[1])
            elif len(units_list) == 1:
                self.from_unit_var.set(units_list[0])
                self.to_unit_var.set(units_list[0])
            else: # No units in category, clear selections
                self.from_unit_var.set("")
                self.to_unit_var.set("")
        self._do_conversion() # Perform conversion with new units

    def _update_unit_comboboxes(self, category_name):
        units = self.conversion_data.get(category_name, {}).get("units", {}).keys()
        unit_list = sorted(list(units)) # Sort for consistent display
        self.from_unit_combobox["values"] = unit_list
        self.to_unit_combobox["values"] = unit_list

    def _do_conversion_if_possible(self, *args):
        # This function is called on key press in input and combobox selection.
        # It attempts conversion if all necessary inputs are present.
        try:
            float(self.input_value_var.get())
            if self.from_unit_var.get() and self.to_unit_var.get():
                self._do_conversion()
        except ValueError:
            self.output_result_var.set("Invalid Number")
            self.status_label.config(text="Please enter a valid number.", foreground="red")
            self.main_app_instance.update_status_message("Invalid input for conversion.", level="warning")
            unit_converter_logger.debug("Invalid number entered for conversion.")


    def _do_conversion(self):
        try:
            value = float(self.input_value_var.get())
            from_unit = self.from_unit_var.get()
            to_unit = self.to_unit_var.get()
            category = self.category_var.get()

            if not all([from_unit, to_unit, category]):
                self.output_result_var.set("")
                self.status_label.config(text="Select category and units.", foreground="orange")
                return

            category_data = self.conversion_data[category]
            
            # Special handling for Temperature (non-linear conversion)
            if category == "Temperature":
                # Convert from_unit to a common base (e.g., Celsius)
                if from_unit == "Celsius":
                    value_in_base = value
                elif from_unit == "Fahrenheit":
                    value_in_base = category_data["units"]["Fahrenheit"](value, True)
                elif from_unit == "Kelvin":
                    value_in_base = category_data["units"]["Kelvin"](value, True)
                else:
                    raise ValueError(f"Unknown temperature unit: {from_unit}")

                # Convert from base to to_unit
                if to_unit == "Celsius":
                    converted_value = value_in_base
                elif to_unit == "Fahrenheit":
                    converted_value = category_data["units"]["Fahrenheit"](value_in_base, False)
                elif to_unit == "Kelvin":
                    converted_value = category_data["units"]["Kelvin"](value_in_base, False)
                else:
                    raise ValueError(f"Unknown temperature unit: {to_unit}")

            # General linear conversion for other categories
            else:
                from_factor = category_data["units"][from_unit]
                to_factor = category_data["units"][to_unit]
                
                # Convert input value to the category's base unit
                value_in_base = value * from_factor
                
                # Convert from base unit to the target unit
                converted_value = value_in_base / to_factor

            self.output_result_var.set(f"{converted_value:.6f}") # Display with 6 decimal places
            self.status_label.config(text=f"Converted {value:.2f} {from_unit} to {to_unit}.", foreground="green")
            self.main_app_instance.update_status_message(f"Converted {value:.2f} {from_unit} to {converted_value:.2f} {to_unit}.", level="info")
            unit_converter_logger.debug(f"Conversion: {value} {from_unit} to {converted_value} {to_unit}")

        except ValueError as e:
            self.output_result_var.set("Error")
            self.status_label.config(text=f"Error: {e}", foreground="red")
            self.main_app_instance.update_status_message(f"Conversion error: {e}", level="error")
            unit_converter_logger.error(f"Conversion error: {e}")
        except Exception as e:
            self.output_result_var.set("Error")
            self.status_label.config(text=f"An unexpected error occurred: {e}", foreground="red")
            self.main_app_instance.update_status_message(f"Unexpected conversion error: {e}", level="error")
            unit_converter_logger.critical(f"Unexpected conversion error: {e}")

    def get_menubar_commands(self):
        return {
            "help_commands": [
                ("About Unit Converter", self.show_about_dialog),
                ("Unit Converter Help", self.show_help_dialog),
            ]
        }

    def show_about_dialog(self):
        messagebox.showinfo(
            "About Unit Converter",
            "This module allows you to convert values between various units across different categories like Length, Mass, Temperature, Volume, and Time.\n\n"
            "Developed by Z.\n\n"
            "Provides quick and accurate unit transformations for everyday use.",
            parent=self.winfo_toplevel()
        )
        unit_converter_logger.info("About dialog shown for Unit Converter.")

    def show_help_dialog(self):
        help_text = (
            "Unit Converter Help Guide:\n\n"
            "1. Select a 'Category' (e.g., Length, Temperature).\n"
            "2. Enter the 'Value' you wish to convert.\n"
            "3. Select the 'From' unit and the 'To' unit from the respective dropdowns.\n"
            "4. The converted result will appear automatically in the 'Result' field.\n\n"
            "Tip: Changing any selection or typing in the value field will automatically trigger a conversion."
        )
        messagebox.showinfo(
            "Unit Converter Help",
            help_text,
            parent=self.winfo_toplevel()
        )
        unit_converter_logger.info("Help dialog shown for Unit Converter.")

    def before_hide(self, closing_app=False):
        # This module has no unsaved changes or active processes that need interruption.
        return True