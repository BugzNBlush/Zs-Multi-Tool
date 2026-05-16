import tkinter as tk
from tkinter import ttk, messagebox
import os
import platform
import psutil
import threading
import logging
import datetime
import socket 
import time # For Discord RPC timestamps

from modules.zyphria_nexus.styles import bg_medium 
import settings_manager # Re-added for APP_NAME consistency in dialogs and RPC

system_monitor_logger = logging.getLogger(__name__)

class SystemMonitorModule(ttk.Frame):
    def __init__(self, parent, app_settings, main_app_instance):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_app_instance = main_app_instance
        self.pack(fill=tk.BOTH, expand=True)

        self.update_id = None 
        self.refresh_interval_ms = 2000 

        # NEW: Always initialize as hidden (False)
        self.network_info_visible_var = tk.BooleanVar(value=False) 

        # Store a reference to the disk_frame and net_frame
        self.disk_frame = None
        self.net_frame = None

        self.create_widgets()
        system_monitor_logger.info("SystemMonitorModule initialized.")
        self.main_app_instance.update_status_message("System Monitor module loaded.", level="info")
        self._update_discord_rpc() # Initial RPC update

    def create_widgets(self):
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=bg_medium) 
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=self.canvas.winfo_width())
        self.scrollable_frame.bind("<Configure>", self._on_scrollable_frame_resize) 
        self.canvas.bind('<Motion>', self._bound_to_mousewheel) 

        row_idx = 0

        # --- OS Information ---
        os_frame = ttk.LabelFrame(self.scrollable_frame, text=" Operating System ")
        os_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        os_frame.grid_columnconfigure(1, weight=1)
        row_idx += 1

        ttk.Label(os_frame, text="System:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.os_system_label = ttk.Label(os_frame, text="N/A")
        self.os_system_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(os_frame, text="Release:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.os_release_label = ttk.Label(os_frame, text="N/A")
        self.os_release_label.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(os_frame, text="Version:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.os_version_label = ttk.Label(os_frame, text="N/A")
        self.os_version_label.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        
        ttk.Label(os_frame, text="Architecture:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.os_arch_label = ttk.Label(os_frame, text="N/A")
        self.os_arch_label.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(os_frame, text="Uptime:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.os_uptime_label = ttk.Label(os_frame, text="N/A")
        self.os_uptime_label.grid(row=4, column=1, padx=5, pady=2, sticky="w")


        # --- CPU Information ---
        cpu_frame = ttk.LabelFrame(self.scrollable_frame, text=" CPU Information ")
        cpu_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        cpu_frame.grid_columnconfigure(1, weight=1)
        row_idx += 1

        ttk.Label(cpu_frame, text="Processor:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.cpu_model_label = ttk.Label(cpu_frame, text="N/A")
        self.cpu_model_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(cpu_frame, text="Cores (Physical/Logical):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.cpu_cores_label = ttk.Label(cpu_frame, text="N/A")
        self.cpu_cores_label.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(cpu_frame, text="Current Usage:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.cpu_usage_label = ttk.Label(cpu_frame, text="N/A")
        self.cpu_usage_label.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        self.cpu_usage_progress = ttk.Progressbar(cpu_frame, orient=tk.HORIZONTAL, mode="determinate", length=200)
        self.cpu_usage_progress.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")

        # --- Memory Information ---
        mem_frame = ttk.LabelFrame(self.scrollable_frame, text=" Memory (RAM) ")
        mem_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        mem_frame.grid_columnconfigure(1, weight=1)
        row_idx += 1

        ttk.Label(mem_frame, text="Total:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.mem_total_label = ttk.Label(mem_frame, text="N/A")
        self.mem_total_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(mem_frame, text="Available:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.mem_available_label = ttk.Label(mem_frame, text="N/A")
        self.mem_available_label.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(mem_frame, text="Used:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.mem_used_label = ttk.Label(mem_frame, text="N/A")
        self.mem_used_label.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        self.mem_usage_progress = ttk.Progressbar(mem_frame, orient=tk.HORIZONTAL, mode="determinate", length=200)
        self.mem_usage_progress.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")

        # --- Disk Information ---
        self.disk_frame = ttk.LabelFrame(self.scrollable_frame, text=" Disk Drives ") 
        self.disk_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.disk_frame.grid_columnconfigure(0, weight=1)
        self.disk_frame.grid_columnconfigure(1, weight=1) 
        row_idx += 1
        
        self.disk_info_labels = {} 
        self._initialize_disk_widgets(self.disk_frame) 

        # --- Network Information ---
        self.net_frame = ttk.LabelFrame(self.scrollable_frame, text=" Network Adapters ") 
        self.net_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.net_frame.grid_columnconfigure(0, weight=1)
        row_idx += 1

        self.toggle_network_checkbutton = ttk.Checkbutton(
            self.net_frame, 
            text="Show Network Details (uncheck to hide)", 
            variable=self.network_info_visible_var, 
            command=self._on_network_visibility_toggle, 
            style="TCheckbutton"
        )
        self.toggle_network_checkbutton.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.network_details_frame = ttk.Frame(self.net_frame)
        self.network_details_frame.grid_columnconfigure(0, weight=1) 

        self.net_adapters_text = tk.StringVar(value="")
        self.net_adapters_label = ttk.Label(self.network_details_frame, textvariable=self.net_adapters_text, wraplength=400, justify=tk.LEFT)
        self.net_adapters_label.pack(fill=tk.BOTH, expand=True) 

        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Apply initial visibility state after widgets are created
        self._toggle_network_details_visibility(initial_load=True)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window_id, width=event.width)
        self.after(10, self._update_scroll_region) 

    def _on_scrollable_frame_resize(self, event=None):
        self.after(10, self._update_scroll_region) 

    def _update_scroll_region(self):
        yview_fraction = self.canvas.yview()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        if yview_fraction and self.canvas.bbox("all"):
            self.canvas.yview_moveto(yview_fraction[0])

    def _bound_to_mousewheel(self, event):
        if self.canvas.bbox("all") is None: 
            return
        if platform.system() == "Windows":
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif platform.system() == "Darwin": 
            self.canvas.yview_scroll(int(-1*event.delta), "units")
        elif event.num == 4:
            self.canvas.yview_scroll( -1, "units" )
        elif event.num == 5:
            self.canvas.yview_scroll( 1, "units" )

    def _initialize_disk_widgets(self, parent_frame):
        current_yview = self.canvas.yview() 
        
        # Destroy all existing disk widgets except the main disk_frame
        for widget in parent_frame.winfo_children():
            widget.destroy() 
        self.disk_info_labels.clear()

        ttk.Label(parent_frame, text="Drive", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Label(parent_frame, text="Usage", font=("Arial", 9, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        partitions = psutil.disk_partitions(all=False) 
        grid_row_offset = 1 
        for i, part in enumerate(partitions):
            row = grid_row_offset + (i * 2) 
            mountpoint = part.mountpoint
            
            ttk.Label(parent_frame, text=mountpoint).grid(row=row, column=0, padx=5, pady=2, sticky="w")
            
            usage_label = ttk.Label(parent_frame, text="Loading...")
            usage_label.grid(row=row, column=1, padx=5, pady=2, sticky="w")
            
            progress_bar = ttk.Progressbar(parent_frame, orient=tk.HORIZONTAL, mode="determinate", length=150)
            progress_bar.grid(row=row + 1, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
            
            self.disk_info_labels[mountpoint] = {
                "usage_label": usage_label,
                "progress_bar": progress_bar,
                "row_start": row 
            }
            parent_frame.grid_rowconfigure(row, weight=0) 
            parent_frame.grid_rowconfigure(row + 1, weight=1) 
        
        self.after(50, self._update_scroll_region) 
        self._update_discord_rpc() # Update RPC after disk widgets are initialized

    def _update_system_info(self):
        try:
            current_yview = self.canvas.yview() 

            # --- OS Info ---
            self.os_system_label.config(text=platform.system())
            self.os_release_label.config(text=platform.release())
            self.os_version_label.config(text=platform.version())
            self.os_arch_label.config(text=platform.architecture()[0])
            
            boot_time_timestamp = psutil.boot_time()
            boot_time_datetime = datetime.datetime.fromtimestamp(boot_time_timestamp)
            uptime_delta = datetime.datetime.now() - boot_time_datetime
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.os_uptime_label.config(text=f"{days}d {hours}h {minutes}m")

            # --- CPU Info ---
            cpu_percent = psutil.cpu_percent(interval=None) 
            self.cpu_model_label.config(text=platform.processor())
            self.cpu_cores_label.config(text=f"{psutil.cpu_count(logical=False)} / {psutil.cpu_count(logical=True)}")
            self.cpu_usage_label.config(text=f"{cpu_percent:.1f}%")
            self.cpu_usage_progress.config(value=cpu_percent)

            # --- Memory Info ---
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            available_gb = mem.available / (1024**3)
            used_gb = mem.used / (1024**3)
            self.mem_total_label.config(text=f"{total_gb:.2f} GB")
            self.mem_available_label.config(text=f"{available_gb:.2f} GB")
            self.mem_used_label.config(text=f"{used_gb:.2f} GB ({mem.percent:.1f}%)")
            self.mem_usage_progress.config(value=mem.percent)

            # --- Disk Info ---
            current_partitions = {p.mountpoint for p in psutil.disk_partitions(all=False)}
            known_partitions = set(self.disk_info_labels.keys())
            
            if current_partitions != known_partitions:
                system_monitor_logger.info("Disk partitions changed, re-initializing disk widgets.")
                self.after(0, lambda: self._initialize_disk_widgets(self.disk_frame)) 
            
            for mountpoint, widgets in self.disk_info_labels.items():
                try:
                    usage = psutil.disk_usage(mountpoint)
                    total_gb_disk = usage.total / (1024**3)
                    used_gb_disk = usage.used / (1024**3)
                    free_gb_disk = usage.free / (1024**3)
                    
                    widgets["usage_label"].config(text=f"Total: {total_gb_disk:.2f} GB, Used: {used_gb_disk:.2f} GB, Free: {free_gb_disk:.2f} GB ({usage.percent:.1f}%)")
                    widgets["progress_bar"].config(value=usage.percent)
                except Exception as e:
                    widgets["usage_label"].config(text=f"Error: {e}")
                    widgets["progress_bar"].config(value=0)
                    system_monitor_logger.warning(f"Error updating disk info for {mountpoint}: {e}")

            # --- Network Info (Conditional based on visibility) ---
            if self.network_info_visible_var.get():
                net_addrs = psutil.net_if_addrs()
                net_io = psutil.net_io_counters(pernic=True)
                net_info_str = ""
                for interface_name, addresses in net_addrs.items():
                    net_info_str += f"Adapter: {interface_name}\n"
                    for addr in addresses:
                        if addr.family == socket.AF_LINK: 
                            net_info_str += f"  MAC: {addr.address}\n"
                        elif addr.family == socket.AF_INET: 
                            net_info_str += f"  IPv4: {addr.address}\n"
                        elif addr.family == socket.AF_INET6: 
                            net_info_str += f"  IPv6: {addr.address}\n"
                    if interface_name in net_io:
                        bytes_sent_mb = net_io[interface_name].bytes_sent / (1024**2)
                        bytes_recv_mb = net_io[interface_name].bytes_recv / (1024**2)
                        net_info_str += f"  Sent: {bytes_sent_mb:.2f} MB, Recv: {bytes_recv_mb:.2f} MB\n"
                    net_info_str += "\n"
                
                self.net_adapters_text.set(net_info_str.strip())
            else:
                self.net_adapters_text.set("Network information hidden by user preference.")

        except Exception as e:
            system_monitor_logger.error(f"Error updating system info: {e}")
            self.main_app_instance.update_status_message(f"Error updating system info: {e}", level="error")
        finally:
            self.update_id = self.after(self.refresh_interval_ms, self._update_system_info)
            self.after(50, lambda: self._restore_scroll_position(current_yview))
            self._update_discord_rpc() # Update RPC with latest system stats

    def _restore_scroll_position(self, yview_fraction):
        if yview_fraction and self.canvas.bbox("all"):
            self.canvas.yview_moveto(yview_fraction[0])

    def _start_update_loop(self):
        if not self.update_id: 
            system_monitor_logger.info("Starting system monitor update loop.")
            self._update_system_info() 

    def _stop_update_loop(self):
        if self.update_id:
            system_monitor_logger.info("Stopping system monitor update loop.")
            self.after_cancel(self.update_id)
            self.update_id = None

    def _toggle_network_details_visibility(self, initial_load=False):
        current_yview = self.canvas.yview() 
        
        if self.network_info_visible_var.get():
            self.network_details_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
            if not initial_load:
                self.net_adapters_text.set("Loading network info...") 
        else:
            self.network_details_frame.grid_forget()
            self.net_adapters_text.set("Network information hidden by user preference.")

        self.after(50, lambda: self._restore_scroll_position(current_yview))
        self._update_discord_rpc() # Update RPC on network visibility change

    def _on_network_visibility_toggle(self):
        self._toggle_network_details_visibility() 
        
        # Log the change, but don't save persistently
        should_hide_in_settings = not self.network_info_visible_var.get()
        system_monitor_logger.info(f"Network info visibility set to: {'hidden' if should_hide_in_settings else 'visible'} (session-only)")
        self.main_app_instance.update_status_message(f"Network information visibility updated for this session.", level="info")
        
        if self.network_info_visible_var.get():
            self._update_system_info()

    # --- Discord Rich Presence Integration ---
    def _update_discord_rpc(self):
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
        default_rpc = self.main_app_instance.get_discord_rpc_status(module_name="system_monitor")
        
        details_text = "Monitoring System"
        state_text = ""

        cpu_percent = psutil.cpu_percent(interval=None) # Get current CPU % for state
        mem = psutil.virtual_memory()
        
        state_text = f"CPU: {cpu_percent:.1f}% | RAM: {mem.percent:.1f}%"

        if self.network_info_visible_var.get():
            details_text = "Monitoring System (Network Visible)"
        else:
            details_text = "Monitoring System (Network Hidden)"

        return {
            "details": details_text,
            "state": state_text,
            "large_image": default_rpc.get("large_image", "monitor_icon"),
            "large_text": "System Monitor",
            "small_image": default_rpc.get("small_image", "app_logo"),
            "small_text": self.main_app_instance.base_title, # Use main_app's base_title for consistency
        }


    def get_menubar_commands(self):
        return {
            "help_commands": [
                ("About System Monitor", self._show_about_dialog),
                ("System Monitor Help", self._show_help_dialog),
            ]
        }

    def _show_about_dialog(self):
        messagebox.showinfo(
            "About System Monitor",
            f"{settings_manager.APP_NAME} System Monitor v1.0\n" # Use APP_NAME
            "Displays real-time hardware and OS information.\n"
            "Developed by Z.\n\n"
            "Powered by psutil.",
            parent=self.winfo_toplevel()
        )
        system_monitor_logger.info("About dialog shown for System Monitor.")


    def _show_help_dialog(self):
        messagebox.showinfo(
            "System Monitor Help",
            "This module displays real-time information about your computer's operating system, CPU, memory, disk drives, and network adapters.\n\n"
            "Information is refreshed automatically every few seconds.\n\n"
            "You can toggle the visibility of the 'Network Adapters' section using the checkbox within that frame to hide sensitive network details if you are sharing your screen. This preference is reset when the application restarts.",
            parent=self.winfo_toplevel()
        )
        system_monitor_logger.info("System Monitor help dialog shown.")

    def before_hide(self, closing_app=False):
        self._stop_update_loop()
        self._update_discord_rpc() # Update RPC to reflect module is no longer active (or changed status)
        return True

    def refresh_settings_ui(self):
        # This module doesn't rely on app_settings for its runtime behavior (except app_name)
        # So, we just ensure the update loop is started and UI is consistent.
        self._start_update_loop()
        self._toggle_network_details_visibility(initial_load=True) 
        self.after(100, self._update_scroll_region) 
        self.after(150, lambda: self._restore_scroll_position(self.canvas.yview()))
        self._update_discord_rpc() # Update RPC after refresh