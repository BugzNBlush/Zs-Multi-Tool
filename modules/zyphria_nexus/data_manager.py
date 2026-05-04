# modules/zyphria_nexus/data_manager.py

import json
import os
import sys
import logging

dm_logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self):
        self.profiles = []
        self.config_file = "config.json"
        self._load_profiles()

    def _get_resource_path(self, relative_path):
        """
        Get absolute path to resource, works for dev and for PyInstaller.
        """
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(os.path.dirname(sys.argv[0])) # Path to the executable/script
        return os.path.join(base_path, relative_path)

    def get_config_path(self):
        """
        Returns the correct path to the config.json file.
        Uses AppData/Local for PyInstaller --onefile exe, else current dir.
        """
        if getattr(sys, 'frozen', False):
            app_data_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'ZyphriaNexus')
            os.makedirs(app_data_dir, exist_ok=True)
            dm_logger.debug(f"Running as frozen app. Config path: {os.path.join(app_data_dir, self.config_file)}")
            return os.path.join(app_data_dir, self.config_file)
        else:
            # During development, save next to the script
            # Ensure it saves in the modules/zyphria_nexus folder
            module_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(module_dir, self.config_file)


    def _load_profiles(self):
        config_full_path = self.get_config_path()
        if os.path.exists(config_full_path):
            try:
                with open(config_full_path, 'r') as f:
                    self.profiles = json.load(f)
                dm_logger.info(f"Loaded profiles from {config_full_path}.")
            except json.JSONDecodeError:
                dm_logger.error(f"Could not decode JSON from {config_full_path}. Initializing empty profiles.")
                self.profiles = []
            except Exception as e:
                dm_logger.error(f"Error reading config file {config_full_path}: {e}. Initializing empty profiles.")
                self.profiles = []
        else:
            dm_logger.info(f"Config file not found at {config_full_path}. Initializing empty profiles.")
            self.profiles = []

    def _save_profiles(self):
        save_path = self.get_config_path()
        try:
            with open(save_path, 'w') as f:
                json.dump(self.profiles, f, indent=4)
            dm_logger.info(f"Saved profiles to {save_path}.")
        except Exception as e:
            dm_logger.error(f"Error saving profiles to {save_path}: {e}")

    def reload_profiles(self):
        self._load_profiles()
        dm_logger.info("Profiles reloaded from disk.")


    def add_game(self, name):
        if any(p['name'].lower() == name.lower() for p in self.profiles): # Case-insensitive check
            dm_logger.warning(f"Attempted to add game '{name}', but it already exists.")
            return False

        self.profiles.append({
            'name': name, 
            'saves_path': '', 
            'editors': [],
            'default_backup_path': ''
        })
        self._save_profiles()
        dm_logger.info(f"Added new game profile: '{name}'.")
        return True

    def delete_game(self, name):
        initial_len = len(self.profiles)
        self.profiles = [p for p in self.profiles if p['name'].lower() != name.lower()] # Case-insensitive delete
        if len(self.profiles) < initial_len:
            self._save_profiles()
            dm_logger.info(f"Deleted game profile: '{name}'.")
            return True
        dm_logger.warning(f"Attempted to delete game '{name}', but it was not found.")
        return False

    def get_profile(self, name):
        for p in self.profiles:
            if p['name'].lower() == name.lower(): # Case-insensitive lookup
                return p
        dm_logger.debug(f"Profile for '{name}' not found.")
        return None
    
    def get_profiles(self) -> list:
        """Returns the current list of profiles."""
        return self.profiles

    def update_paths(self, game_name, new_saves_path):
        for p in self.profiles:
            if p['name'].lower() == game_name.lower(): # Case-insensitive lookup
                p['saves_path'] = new_saves_path
                self._save_profiles()
                dm_logger.info(f"Updated saves path for '{game_name}' to '{new_saves_path}'.")
                return True
        dm_logger.warning(f"Failed to update saves path for '{game_name}': game not found.")
        return False

    def update_default_backup_path(self, game_name, new_backup_path):
        for p in self.profiles:
            if p['name'].lower() == game_name.lower(): # Case-insensitive lookup
                p['default_backup_path'] = new_backup_path
                self._save_profiles()
                dm_logger.info(f"Updated default backup path for '{game_name}' to '{new_backup_path}'.")
                return True
        dm_logger.warning(f"Failed to update default backup path for '{game_name}': game not found.")
        return False

    def add_editor(self, game_name, editor_name, editor_path):
        for p in self.profiles:
            if p['name'].lower() == game_name.lower(): # Case-insensitive lookup
                if not any(e['name'].lower() == editor_name.lower() for e in p['editors']): # Case-insensitive check
                    p['editors'].append({'name': editor_name, 'path': editor_path})
                    self._save_profiles()
                    dm_logger.info(f"Added editor '{editor_name}' to game '{game_name}'.")
                    return True
                dm_logger.warning(f"Failed to add editor '{editor_name}' to game '{game_name}': editor already exists.")
        dm_logger.warning(f"Failed to add editor '{editor_name}' to game '{game_name}': game not found.")
        return False

    def delete_editor(self, game_name, editor_name):
        for p in self.profiles:
            if p['name'].lower() == game_name.lower(): # Case-insensitive lookup
                initial_len = len(p['editors'])
                p['editors'] = [ed for ed in p['editors'] if ed['name'].lower() != editor_name.lower()] # Case-insensitive delete
                if len(p['editors']) < initial_len:
                    self._save_profiles()
                    dm_logger.info(f"Deleted editor '{editor_name}' from game '{game_name}'.")
                    return True
                dm_logger.warning(f"Failed to delete editor '{editor_name}' from game '{game_name}': editor not found.")
        dm_logger.warning(f"Failed to delete editor '{editor_name}' from game '{game_name}': game not found.")
        return False

    def move_profile_up(self, index: int) -> bool:
        """Moves a game profile up in the list."""
        if 0 < index < len(self.profiles):
            self.profiles[index], self.profiles[index - 1] = self.profiles[index - 1], self.profiles[index]
            self._save_profiles()
            dm_logger.info(f"Moved profile '{self.profiles[index-1]['name']}' up.")
            return True
        dm_logger.debug(f"Cannot move profile at index {index} up.")
        return False

    def move_profile_down(self, index: int) -> bool:
        """Moves a game profile down in the list."""
        if 0 <= index < len(self.profiles) - 1:
            self.profiles[index], self.profiles[index + 1] = self.profiles[index + 1], self.profiles[index]
            self._save_profiles()
            dm_logger.info(f"Moved profile '{self.profiles[index+1]['name']}' down.")
            return True
        dm_logger.debug(f"Cannot move profile at index {index} down.")
        return False