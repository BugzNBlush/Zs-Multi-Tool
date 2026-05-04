# settings_manager.py
import json
import os
import platform
import logging

# Get a logger for this module
manager_logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"

def load_settings():
    """Loads settings from the JSON file, or returns defaults if the file doesn't exist."""
    # os.path.dirname(os.path.abspath(__file__)) gets the directory of the current script (settings_manager.py)
    config_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SETTINGS_FILE)
    manager_logger.debug(f"Attempting to load settings from: {config_full_path}")

    if os.path.exists(config_full_path):
        try:
            with open(config_full_path, 'r') as f:
                settings = json.load(f)
                manager_logger.info(f"Loaded settings: {settings}")
                return settings
        except json.JSONDecodeError:
            manager_logger.warning(f"Could not decode {config_full_path}. Creating default settings.")
            return _get_default_settings()
        except Exception as e:
            manager_logger.error(f"Error reading settings file {config_full_path}: {e}. Creating default settings.")
            return _get_default_settings()
    else:
        manager_logger.info(f"{config_full_path} not found. Creating default settings.")
        return _get_default_settings()

def save_settings(settings):
    """Saves the current settings dictionary to the JSON file."""
    config_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SETTINGS_FILE)
    try:
        with open(config_full_path, 'w') as f:
            json.dump(settings, f, indent=4)
            manager_logger.info(f"Saved settings to {config_full_path}: {settings}")
    except Exception as e:
        manager_logger.error(f"Error saving settings to {config_full_path}: {e}")

def _get_default_settings():
    """Returns a dictionary of default settings."""
    manager_logger.debug("Generating default settings.")
    
    # Determine the default downloads directory based on OS
    if platform.system() == "Windows":
        default_downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    else: # For Linux/macOS
        default_downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    
    # Ensure the default directory exists
    os.makedirs(default_downloads_dir, exist_ok=True) 
    
    return {
        "downloader_output_directory": default_downloads_dir,
        "music_player_default_volume": 0.7, # Pygame mixer volume range 0.0 to 1.0
        "app_theme": "Hologram", # Fixed to "Hologram" since we applied it globally
    }

# Note: The actual call to load_settings() (which creates the file if not found)
# happens in main_app.py during application startup.