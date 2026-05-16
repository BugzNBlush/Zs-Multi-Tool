import time
import logging
import threading
from pypresence import Presence # Import the client class

discord_rpc_logger = logging.getLogger(__name__)

class DiscordRPCManager:
    def __init__(self, client_id, main_app_instance):
        self.client_id = client_id
        self.main_app_instance = main_app_instance
        self.rpc = None
        self._connected = False
        self._thread = None
        self._running = False
        self.current_activity = {}

    def _connect_and_loop(self):
        while self._running:
            try:
                if not self._connected:
                    discord_rpc_logger.info("Attempting to connect to Discord RPC...")
                    self.rpc = Presence(self.client_id)  # Initialize the Presence client
                    self.rpc.connect()                   # Start the handshake loop
                    self._connected = True
                    discord_rpc_logger.info("Successfully connected to Discord RPC.")
                    # Set initial activity if available
                    if self.current_activity:
                        self._set_activity_internal(self.current_activity)
                
                # Keep the connection alive by sleeping
                time.sleep(15) # Discord recommends updating/keeping alive every 15-20 seconds
            except Exception as e:
                self._connected = False
                discord_rpc_logger.warning(f"Discord RPC connection error: {e}. Retrying in 30 seconds...")
                self.rpc = None # Reset RPC object
                time.sleep(30) # Wait before retrying

    def start_rpc(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._connect_and_loop, daemon=True)
            self._thread.start()
            discord_rpc_logger.info("Discord RPC background thread started.")
        
        # Set a default "initial" activity when the app starts
        self.update_activity(details="Starting Up", state="Idle", 
                             large_image="app_logo", large_text=self.main_app_instance.base_title, # Use base_title
                             start=int(time.time()))

    def stop_rpc(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5) # Give the thread a moment to shut down
        
        if self._connected and self.rpc:
            try:
                discord_rpc_logger.info("Clearing Discord Rich Presence and disconnecting.")
                self.rpc.clear()
                self.rpc.close()
            except Exception as e:
                discord_rpc_logger.error(f"Error during Discord RPC disconnection: {e}")
        self._connected = False
        self.rpc = None
        discord_rpc_logger.info("Discord RPC background thread stopped.")

    def _set_activity_internal(self, activity_data):
        if self._connected and self.rpc:
            try:
                self.rpc.update(**activity_data)
                discord_rpc_logger.debug(f"Discord RPC activity updated: {activity_data.get('details')}")
            except Exception as e:
                discord_rpc_logger.warning(f"Failed to update Discord RPC activity (connection might have dropped): {e}")
                self._connected = False # Mark as disconnected to trigger a reconnect
        else:
            discord_rpc_logger.debug("Not connected to Discord RPC, activity not set.")

    def update_activity(self, details=None, state=None, large_image=None, large_text=None, 
                        small_image=None, small_text=None, start=None, end=None, 
                        party_size=None, party_max=None, buttons=None):
        
        new_activity = {k: v for k, v in locals().items() if k not in ['self', 'new_activity'] and v is not None}
        self.current_activity = {**self.current_activity, **new_activity} # Merge with existing, overriding if new values provided

        # If we have a start time, keep it updated unless a new one is provided
        if "start" not in self.current_activity and self._connected:
            self.current_activity["start"] = int(time.time())

        # Discord requires `details` for Rich Presence to show up properly
        if "details" not in self.current_activity or not self.current_activity["details"]:
            self.current_activity["details"] = f"Using {self.main_app_instance.base_title}" # Use base_title

        # Ensure large_image and large_text are always present for the app itself
        if "large_image" not in self.current_activity:
            self.current_activity["large_image"] = "app_logo" # Default app logo asset name
        if "large_text" not in self.current_activity:
            self.current_activity["large_text"] = self.main_app_instance.base_title # Use base_title

        self._set_activity_internal(self.current_activity)

    def clear_activity(self):
        if self._connected and self.rpc:
            try:
                self.rpc.clear()
                self.current_activity = {}
                discord_rpc_logger.info("Discord RPC activity cleared.")
            except Exception as e:
                discord_rpc_logger.error(f"Error clearing Discord RPC activity: {e}")