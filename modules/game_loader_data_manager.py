# modules/game_loader_data_manager.py

import json
import os
import sys
import logging
import settings_manager # Import settings_manager for consistent config path

gl_dm_logger = logging.getLogger(__name__)

class GameLoaderDataManager:
    def __init__(self):
        self.games = []
        self.config_file = "game_loader_config.json"
        self._load_games()

    def _get_config_path(self):
        """
        Returns the correct path to the game_loader_config.json file.
        Uses the user-specific application data directory determined by settings_manager.
        """
        # Use the centralized user config directory
        user_app_config_dir = settings_manager.get_user_config_dir()
        path = os.path.join(user_app_config_dir, self.config_file)
        gl_dm_logger.debug(f"GameLoader config path determined: {path}")
        return path

    def _load_games(self):
        config_full_path = self._get_config_path()
        if os.path.exists(config_full_path):
            try:
                with open(config_full_path, 'r', encoding='utf-8') as f: # Added encoding
                    self.games = json.load(f)
                gl_dm_logger.info(f"Loaded game list from {config_full_path}.")
            except json.JSONDecodeError:
                gl_dm_logger.error(f"Could not decode JSON from {config_full_path}. Initializing empty game list.")
                self.games = []
            except Exception as e:
                gl_dm_logger.error(f"Error reading game config file {config_full_path}: {e}. Initializing empty game list.")
                self.games = []
        else:
            gl_dm_logger.info(f"Game config file not found at {config_full_path}. Initializing empty game list.")
            self.games = []

    def _save_games(self):
        save_path = self._get_config_path()
        try:
            # Ensure the directory exists before saving
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f: # Added encoding
                json.dump(self.games, f, indent=4)
            gl_dm_logger.info(f"Saved game list to {save_path}.")
        except Exception as e:
            gl_dm_logger.error(f"Error saving game list to {save_path}: {e}")

    # NEW: Public method to trigger a save from outside
    def save_all_games(self):
        """Public method to trigger a save of the current game list."""
        self._save_games()

    def add_game(self, name: str, path: str) -> bool:
        """Adds a new game to the list."""
        if any(g['name'].lower() == name.lower() for g in self.games):
            gl_dm_logger.warning(f"Attempted to add game '{name}', but it already exists.")
            return False
        
        self.games.append({'name': name, 'path': path})
        self._save_games() # Save immediately after change
        gl_dm_logger.info(f"Added new game: '{name}' at '{path}'.")
        return True

    def delete_game(self, name: str) -> bool:
        """Deletes a game from the list by name."""
        initial_len = len(self.games)
        self.games = [g for g in self.games if g['name'].lower() != name.lower()]
        if len(self.games) < initial_len:
            self._save_games() # Save immediately after change
            gl_dm_logger.info(f"Deleted game: '{name}'.")
            return True
        gl_dm_logger.warning(f"Attempted to delete game '{name}', but it was not found.")
        return False

    def get_game_path(self, name: str) -> str | None:
        """Returns the path for a given game name."""
        for game in self.games:
            if game['name'].lower() == name.lower():
                return game['path']
        gl_dm_logger.debug(f"Path for game '{name}' not found.")
        return None

    def get_games(self) -> list:
        """Returns the current list of games."""
        return self.games
    
    def update_game(self, old_name: str, new_name: str, new_path: str) -> bool:
        """Updates an existing game's name and/or path."""
        for game in self.games:
            if game['name'].lower() == old_name.lower():
                game['name'] = new_name
                game['path'] = new_path
                self._save_games() # Save immediately after change
                gl_dm_logger.info(f"Updated game: '{old_name}' to '{new_name}' with path '{new_path}'.")
                return True
        gl_dm_logger.warning(f"Attempted to update game '{old_name}', but it was not found.")
        return False

    def move_game_up(self, index: int) -> bool:
        """Moves a game up in the list."""
        if 0 < index < len(self.games):
            self.games[index], self.games[index - 1] = self.games[index - 1], self.games[index]
            self._save_games() # Save immediately after change
            gl_dm_logger.info(f"Moved game '{self.games[index-1]['name']}' up.")
            return True
        gl_dm_logger.debug(f"Cannot move game at index {index} up.")
        return False

    def move_game_down(self, index: int) -> bool:
        """Moves a game down in the list."""
        if 0 <= index < len(self.games) - 1:
            self.games[index], self.games[index + 1] = self.games[index + 1], self.games[index]
            self._save_games() # Save immediately after change
            gl_dm_logger.info(f"Moved game '{self.games[index+1]['name']}' down.")
            return True
        gl_dm_logger.debug(f"Cannot move game at index {index} down.")
        return False