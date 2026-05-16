import json
import os
import sys # Import sys for platform detection
import logging

settings_logger = logging.getLogger(__name__)

# --- NEW: Define app name and settings file name ---
APP_NAME = "Z's Multi Tool" # Define your application name for the config directory
SETTINGS_FILE_NAME = "settings.json"

# Default settings - your comprehensive list!
DEFAULT_SETTINGS = {
    "music_player_default_volume": 0.7,
    "app_theme": "Hologram",
    # "music_player_playlist": [],  # REMOVED: Moved into music_player sub-dict
    "music_downloader": {
        "output_directory": os.path.join(os.path.expanduser("~"), "Downloads"),
        "download_format": "mp3",
        "download_type": "video", # or "playlist"
        "cookie_file_path": "" # Path to cookies.txt for YouTube-DL
    },
    "music_player": {
        "last_played_directory": "",
        "shuffle_enabled": False,  # NEW: Default for shuffle
        "repeat_mode": "none",     # NEW: Default for repeat
        "playlist": []             # ADDED: Default empty playlist
    },
    "notes_module": { # Default settings for the Notes Module
        "auto_save_interval": 60, # seconds
        "default_font_size": 12
    },
    "idle_management": {
        "enabled": False,        # Whether to enable idle detection and return to music player
        "timeout_seconds": 60    # Default to 60 seconds (1 minute)
    },
    # --- NEW: File Shredder Module Settings ---
    "file_shredder_module": {
        "num_passes": 3 # Default number of passes for secure deletion
    }
}

# --- NEW: Functions to determine user config directory ---
def get_user_config_dir():
    """
    Determines the appropriate user-specific, writable configuration directory
    based on the operating system.
    """
    if sys.platform.startswith('win'):
        # On Windows, use AppData\Roaming
        app_data_path = os.environ.get('APPDATA')
        if app_data_path:
            config_dir = os.path.join(app_data_path, APP_NAME)
        else:
            # Fallback if APPDATA env var is not set (unlikely)
            config_dir = os.path.join(os.path.expanduser("~"), f".{APP_NAME.replace(' ', '_')}_config") # Sanitize app name for fallback
    elif sys.platform.startswith('darwin'):
        # On macOS, use ~/Library/Application Support
        config_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
    else: # Linux and other Unix-like systems
        # On Linux, use ~/.config
        config_dir = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)

    os.makedirs(config_dir, exist_ok=True) # Ensure the directory exists
    return config_dir

def get_settings_file_path():
    """Returns the full path to the settings file in the user's config directory."""
    return os.path.join(get_user_config_dir(), SETTINGS_FILE_NAME)


def load_settings():
    # Start with a deep copy of default settings to avoid modifying the original DEFAULT_SETTINGS
    # Use json.loads(json.dumps()) for a robust deep copy, especially for nested dicts/lists
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    settings_path = get_settings_file_path() # Get the user-specific path

    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                user_settings = json.load(f)
                
                # Merge user settings with defaults, handling nested dictionaries
                # This ensures new default settings are added, and old user settings are preserved
                def deep_merge(d1, d2):
                    for k, v in d2.items():
                        if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                            d1[k] = deep_merge(d1[k], v)
                        else:
                            d1[k] = v
                    return d1
                
                settings = deep_merge(settings, user_settings)
            settings_logger.info(f"Loaded settings from {settings_path}.")
        except json.JSONDecodeError as e:
            settings_logger.error(f"Error decoding settings JSON from {settings_path}: {e}. Using default settings.")
            # Optionally, back up the corrupted file before overwriting it
            # os.rename(settings_path, settings_path + ".corrupted_backup")
        except Exception as e:
            settings_logger.error(f"An unexpected error occurred loading settings from {settings_path}: {e}. Using default settings.")
    else:
        settings_logger.info(f"Settings file not found at {settings_path}. Using default settings.")
        
    return settings

def save_settings(settings):
    settings_path = get_settings_file_path() # Get the user-specific path
    try:
        # Ensure the directory exists before attempting to write the file
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        settings_logger.info(f"Settings saved to {settings_path}.")
    except IOError as e:
        settings_logger.error(f"Error: Could not save settings to {settings_path}. {e}")
    except Exception as e:
        settings_logger.error(f"An unexpected error occurred saving settings to {settings_path}: {e}")

# Example usage (for testing, if you run settings_manager.py directly)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test getting path and creating directory
    test_path = get_settings_file_path()
    print(f"Settings will be stored at: {test_path}")

    # Test loading and saving
    current_settings = load_settings()
    print(f"Loaded settings: {current_settings}")

    # Make a change
    current_settings["music_downloader"]["output_directory"] = os.path.join(os.path.expanduser("~"), "NewDownloadsFolder")
    current_settings["notes_module"]["default_font_size"] = 14
    current_settings["idle_management"]["enabled"] = True
    current_settings["music_player_default_volume"] = 0.5
    current_settings["music_player"]["shuffle_enabled"] = True # Test new setting
    current_settings["file_shredder_module"]["num_passes"] = 7 # Test new setting
    save_settings(current_settings)
    print(f"Settings saved. Check {test_path}")

    # Verify reload
    reloaded_settings = load_settings()
    print(f"Reloaded settings: {reloaded_settings}")
    
    # Clean up test file
    # os.remove(test_path)
    # print(f"Cleaned up test settings file: {test_path}")