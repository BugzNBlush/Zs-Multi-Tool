# modules/zyphria_nexus_module.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging

from modules.zyphria_nexus.data_manager import DataManager
from modules.zyphria_nexus.gui import ZyphriaDashboard

nexus_module_logger = logging.getLogger(__name__)

class ZyphriaNexusModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance): # MODIFIED: Added main_app_instance
        super().__init__(parent)
        self.parent = parent
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance # NEW: Store reference to main app
        self.data_manager = DataManager()
        self.dashboard_gui = None # Initialize as None

        self.create_widgets()
        nexus_module_logger.info("ZyphriaNexusModule initialized.")
        self.main_app_instance.update_status_message("Save Manager module loaded.", level="info") # NEW

    def create_widgets(self):
        # The main ZyphriaDashboard (Save Manager) GUI
        # MODIFIED: Pass main_app_instance to ZyphriaDashboard
        self.dashboard_gui = ZyphriaDashboard(self, self.data_manager, self.main_app_instance) 
        self.dashboard_gui.pack(fill=tk.BOTH, expand=True)
        self.dashboard_gui.refresh_games() # Load initial games

    def refresh_settings_ui(self):
        """Called by main_app.py to refresh the UI when the module becomes active.
        This ensures the Save Manager GUI updates its content."""
        if self.dashboard_gui:
            self.dashboard_gui.refresh_games() # Refresh the game list and associated data
        nexus_module_logger.debug("ZyphriaNexusModule UI refreshed.")
        self.main_app_instance.update_status_message("Save Manager UI refreshed.", level="info") # NEW

    # --- Menu Bar Commands for this Module ---
    def export_profile_data(self):
        """Wrapper to call the dashboard's export function."""
        if self.dashboard_gui:
            self.dashboard_gui.export_profile_data()

    def import_profile_data(self):
        """Wrapper to call the dashboard's import function."""
        if self.dashboard_gui:
            self.dashboard_gui.import_profile_data()

    def show_about_dialog(self):
        """Wrapper to call the dashboard's about dialog."""
        if self.dashboard_gui:
            self.dashboard_gui.show_about_dialog()

    def show_help_dialog(self):
        """Wrapper to call the dashboard's help dialog."""
        if self.dashboard_gui:
            self.dashboard_gui.show_help_dialog()

    def get_menubar_commands(self):
        """
        Returns a dictionary of commands specific to this module for the menubar.
        """
        return {
            "file_commands": [
                ("Export Profile Data", self.export_profile_data),
                ("Import Profile Data", self.import_profile_data),
            ],
            "help_commands": [
                ("About Save Manager", self.show_about_dialog),
                ("Save Manager Help Content", self.show_help_dialog),
            ]
        }