# modules/app_updater.py
import os
import sys
import requests
import json
import subprocess
import time
import logging
from tkinter import messagebox, filedialog

app_updater_logger = logging.getLogger(__name__)

class AppUpdater:
    def __init__(self, main_app_instance):
        self.main_app_instance = main_app_instance
        self.current_version = self._get_current_version()
        # --- IMPORTANT: Configure these URLs ---
        # 1. URL to your latest_version.json (e.g., GitHub Gist raw URL or raw.githubusercontent.com link)
        #    Example: "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/latest_version.json"
        self.update_check_url = "https://raw.githubusercontent.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool/main/latest_version.json" 
        # 2. Base URL for your GitHub Releases.
        #    Example: "https://github.com/YOUR_USERNAME/YOUR_REPO/releases/download/"
        self.release_download_base_url = "https://github.com/BugzNBlush/Zyphria-Nexus-Multi-Use-Tool/releases/download/" 
        # --- END IMPORTANT CONFIG ---
        
        # Determine paths for the updater script and new executable
        if getattr(sys, 'frozen', False): # Running as PyInstaller executable
            self.app_executable_path = sys.executable
            # Store temp files in a directory next to the executable
            self.temp_dir = os.path.join(os.path.dirname(sys.executable), "temp_update")
            self.updater_script_name = "updater.exe" # This would be a pre-compiled updater.py
        else: # Running as Python script (during development)
            self.app_executable_path = os.path.abspath(sys.argv[0])
            # Store temp files in a directory next to the main_app.py
            self.temp_dir = os.path.join(os.path.dirname(self.app_executable_path), "temp_update")
            self.updater_script_name = "updater.py" # Python updater script
        
        os.makedirs(self.temp_dir, exist_ok=True)
        app_updater_logger.info(f"AppUpdater initialized. Current version: {self.current_version}")
        app_updater_logger.debug(f"App Executable Path: {self.app_executable_path}")
        app_updater_logger.debug(f"Temp Directory for updates: {self.temp_dir}")
        app_updater_logger.debug(f"Updater Script Name: {self.updater_script_name}")


    def _get_current_version(self):
        """Reads the current application version from resources/version.txt."""
        base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        version_file_path = os.path.join(base_path, "resources", "version.txt")
        version_file_path = os.path.normpath(version_file_path) # Normalize path for consistency

        try:
            with open(version_file_path, 'r') as f:
                version = f.read().strip()
            app_updater_logger.debug(f"Read local version: {version} from {version_file_path}")
            return version
        except FileNotFoundError:
            app_updater_logger.error(f"Version file not found at: {version_file_path}. Defaulting to 0.0.0")
            return "0.0.0" # Default if not found
        except Exception as e:
            app_updater_logger.error(f"Error reading version file '{version_file_path}': {e}. Defaulting to 0.0.0")
            return "0.0.0"

    def _fetch_latest_version_info(self):
        """Fetches latest version info from the update_check_url."""
        try:
            response = requests.get(self.update_check_url, timeout=10)
            response.raise_for_status() # Raise an exception for HTTP errors
            latest_info = json.loads(response.text)
            app_updater_logger.debug(f"Fetched latest version info: {latest_info}")
            return latest_info
        except requests.exceptions.RequestException as e:
            app_updater_logger.error(f"Failed to fetch latest version info: {e}")
            self.main_app_instance.update_status_message(f"Update check failed: {e}", level="error")
            return None
        except json.JSONDecodeError as e:
            app_updater_logger.error(f"Failed to parse latest version info JSON: {e}")
            self.main_app_instance.update_status_message(f"Update info corrupted: {e}", level="error")
            return None

    def check_for_updates(self, silent=True):
        """
        Checks for available updates.
        If silent is False, prompts the user regardless of update availability.
        """
        app_updater_logger.info("Checking for updates...")
        self.main_app_instance.update_status_message("Checking for updates...", level="info")

        latest_info = self._fetch_latest_version_info()
        if not latest_info:
            if not silent:
                messagebox.showerror("Update Check Failed", "Could not check for updates. Please check your internet connection or try again later.", parent=self.main_app_instance)
            return False

        latest_version_str = latest_info.get("version")
        download_filename = latest_info.get("filename")
        release_tag = latest_info.get("tag")

        if not all([latest_version_str, download_filename, release_tag]):
            app_updater_logger.error(f"Incomplete update info received: {latest_info}")
            if not silent:
                messagebox.showerror("Update Error", "Received incomplete update information from the server.", parent=self.main_app_instance)
            return False

        if self._is_new_version_available(latest_version_str):
            app_updater_logger.info(f"New version {latest_version_str} available.")
            self.main_app_instance.update_status_message(f"New version {latest_version_str} available!", level="warning")
            
            confirm = messagebox.askyesno(
                "Update Available",
                f"A new version ({latest_version_str}) of {self.main_app_instance.base_title} is available.\n"
                f"Your current version is {self.current_version}.\n\n"
                "Do you want to download and install the update now?\n"
                "(The application will close and restart after updating)",
                parent=self.main_app_instance
            )
            if confirm:
                self.download_and_prepare_update(release_tag, download_filename)
            return True
        else:
            app_updater_logger.info("No new updates found.")
            if not silent:
                messagebox.showinfo("No Updates", f"You are running the latest version ({self.current_version}) of {self.main_app_instance.base_title}.", parent=self.main_app_instance)
            return False

    def _is_new_version_available(self, latest_version_str):
        """Compares versions (simple string comparison for now, can be improved)."""
        # Basic semantic versioning comparison (major.minor.patch)
        current_parts = [int(p) for p in self.current_version.split('.')]
        latest_parts = [int(p) for p in latest_version_str.split('.')]

        for i in range(max(len(current_parts), len(latest_parts))):
            current_val = current_parts[i] if i < len(current_parts) else 0
            latest_val = latest_parts[i] if i < len(latest_parts) else 0

            if latest_val > current_val:
                return True
            if latest_val < current_val:
                return False
        return False # Versions are the same


    def download_and_prepare_update(self, release_tag, download_filename):
        """Downloads the new executable and launches the external updater."""
        download_url = f"{self.release_download_base_url}{release_tag}/{download_filename}"
        new_exe_path = os.path.join(self.temp_dir, download_filename)
        app_updater_logger.info(f"Downloading update from: {download_url} to {new_exe_path}")
        self.main_app_instance.update_status_message(f"Downloading update {download_filename}...", level="info")

        try:
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(new_exe_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            app_updater_logger.info("Update download complete.")
            self.main_app_instance.update_status_message("Update download complete. Preparing to install...", level="info")
            self._launch_external_updater(new_exe_path, self.app_executable_path)
            
        except requests.exceptions.RequestException as e:
            app_updater_logger.error(f"Failed to download update: {e}")
            messagebox.showerror("Download Failed", f"Could not download the update: {e}\nPlease check your internet connection.", parent=self.main_app_instance)
            self.main_app_instance.update_status_message(f"Update download failed: {e}", level="error")
        except Exception as e:
            app_updater_logger.error(f"Error during update preparation: {e}")
            messagebox.showerror("Update Error", f"An error occurred while preparing the update: {e}", parent=self.main_app_instance)
            self.main_app_instance.update_status_message(f"Update preparation failed: {e}", level="error")


    def _launch_external_updater(self, new_exe_path, old_exe_path):
        """
        Launches a separate script/executable to handle the file replacement
        and then exits the main application.
        """
        updater_path = os.path.join(self.temp_dir, self.updater_script_name)

        if getattr(sys, 'frozen', False):
            # If main app is frozen, the updater should ideally also be a frozen executable.
            # For simplicity in this example, we'll write a Python script and try to run it.
            # In a production setup, you would typically compile updater_script.py into updater.exe
            # and distribute it (either bundled or as a separate download if it's generic enough).
            # If updater.exe is expected, ensure it's copied to self.temp_dir before this call.
            # For this context, we will write the Python script and attempt to run it with the system's python,
            # which might not work reliably if the user doesn't have Python installed, or
            # if sys.executable within the frozen app doesn't point to a valid Python interpreter outside the bundle.
            # A more robust solution for frozen apps would be to pre-compile the updater.py into updater.exe
            # and include it in the main app's distribution, copying it to temp_dir before launching.
            
            # For now, we'll write the python updater script even for frozen, and use sys.executable
            # which points to the main app's executable. This is a compromise; ideally, updater.exe is pre-built.
            self._write_updater_script(updater_path)
            cmd = [sys.executable, updater_path, new_exe_path, old_exe_path, self.main_app_instance.base_title]
        else:
            # If running as script, run the Python updater script
            self._write_updater_script(updater_path)
            cmd = [sys.executable, updater_path, new_exe_path, old_exe_path, self.main_app_instance.base_title]
        
        app_updater_logger.info(f"Launching external updater: {' '.join(cmd)}")
        self.main_app_instance.update_status_message("Launching updater. Application will close to install...", level="warning")

        try:
            # Using Popen to launch without waiting, then exit main app
            subprocess.Popen(cmd, close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
            self.main_app_instance.quit_app() # Custom method to gracefully exit Tkinter app
        except Exception as e:
            app_updater_logger.critical(f"Failed to launch external updater: {e}")
            messagebox.showerror("Update Launch Error", f"Could not launch the update installer: {e}\nPlease try again.", parent=self.main_app_instance)
            self.main_app_instance.update_status_message(f"Update launch failed: {e}", level="error")

    def _write_updater_script(self, updater_path):
        """
        Writes the Python updater script content to a file.
        This script performs the actual file replacement and relaunch.
        """
        # Note: This script needs to be self-contained as it will run after the main app closes.
        # It should not rely on imports from the main application's environment.
        script_content = f'''
import os
import sys
import time
import shutil
import subprocess

# Args: [new_exe_path, old_exe_path, app_title]
if len(sys.argv) < 4:
    # In a real scenario, you might log this or handle it more robustly.
    # For now, we'll just print and exit.
    print("Updater: Insufficient arguments.")
    sys.exit(1)

new_exe_path = sys.argv[1]
old_exe_path = sys.argv[2]
app_title = sys.argv[3]
app_dir = os.path.dirname(old_exe_path)

print(f"Updater started: new={{new_exe_path}}, old={{old_exe_path}}, app_title={{app_title}}")

# Wait for the main application to close
for _ in range(30): # Wait up to 30 seconds
    try:
        # Try to rename the old executable to check if it's still in use.
        # If it succeeds, the app is closed. If it fails, it's still running.
        temp_old_exe = old_exe_path + ".old"
        if os.path.exists(old_exe_path):
            os.rename(old_exe_path, temp_old_exe)
            os.rename(temp_old_exe, old_exe_path) # Rename it back
        print("Updater: Main application process terminated.")
        break
    except OSError as e: # File still in use (WindowsError or similar)
        print(f"Updater: Main application still running ({{e}}), waiting...")
        time.sleep(1)
    except FileNotFoundError: # Old exe might already be gone (e.g., if debugging)
        print("Updater: Old executable not found, proceeding...")
        break
else:
    print("Updater: Main application did not close in time. Aborting update.")
    # In a production updater, you might show a small popup window here.
    sys.exit(1)

# Perform replacement
try:
    if os.path.exists(old_exe_path):
        os.remove(old_exe_path) # Remove the old executable
        print(f"Updater: Removed old executable: {{old_exe_path}}")
    else:
        print(f"Updater: Old executable not found at {{old_exe_path}}, performing clean copy.")

    shutil.copy2(new_exe_path, old_exe_path)
    print(f"Updater: Copied new executable from {{new_exe_path}} to {{old_exe_path}}")

    # Clean up temp files
    temp_dir = os.path.dirname(new_exe_path)
    if os.path.exists(temp_dir):
        # Only remove the downloaded new executable, not the whole temp_dir if it contains the updater.
        # If updater.exe is bundled, it will be in temp_dir. So just remove new_exe_path.
        os.remove(new_exe_path)
        print(f"Updater: Removed downloaded new executable from temp: {{new_exe_path}}")
        # You might want to try and remove the temp_dir itself if it's empty after this
        try:
            os.rmdir(temp_dir)
            print(f"Updater: Removed empty temporary directory: {{temp_dir}}")
        except OSError:
            pass # Directory might not be empty (e.g., updater.exe is still there)


    print("Updater: Update successful! Relaunching application...")
    # Relaunch the updated application
    subprocess.Popen([old_exe_path], close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
    sys.exit(0)

except Exception as e:
    print(f"Updater: Update failed: {{e}}")
    # In a production updater, you might show a small popup window here.
    sys.exit(1)
'''
        try:
            with open(updater_path, 'w') as f:
                f.write(script_content)
            app_updater_logger.debug(f"Updater script written to {updater_path}")
        except Exception as e:
            app_updater_logger.error(f"Failed to write updater script to {updater_path}: {e}")
            raise # Re-raise to indicate a critical failure


    def get_menubar_commands(self):
        return {
            "file_commands": [
                ("Check for Updates", lambda: self.check_for_updates(silent=False)),
            ],
            "help_commands": [
                ("About Updater", self._show_about_dialog),
            ]
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About App Updater",
            f"{self.main_app_instance.base_title} Updater v{self.current_version}\n"
            "Checks for new versions and helps keep your application up-to-date.\n"
            "Developed by Z.\n\n"
            "Always ensuring you have the latest features and fixes!",
            parent=self.main_app_instance
        )
        app_updater_logger.info("About Updater dialog shown.")

    def refresh_settings_ui(self):
        # No specific settings to refresh for the updater module, but it's good to have the method.
        pass
