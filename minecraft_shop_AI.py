#!/usr/bin/env python3
"""
Minecraft Shop Application
A GUI application for managing Minecraft item purchases with Discord integration.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import csv
from io import StringIO
import os
import sys
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

try:
    from discord_webhook import DiscordWebhook
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("Warning: discord-webhook not installed. Discord integration disabled.")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. Icon functionality disabled.")


@dataclass
class Config:
    """Configuration class for the application."""
    discord_webhook_url: str = "https://discord.com/api/webhooks/1426471170437550162/rEwrlOkvyX38VSzOaWgBu3AM-tXsinIhf-kHfQc9K2VWTC0BWywR6V-MMNJRt633Ytm3"
    sheet_id: str = "1MxjocKFqa4Chv9HHiOeom3LlGLbdicZXaR_41arPEkk"
    log_file: str = "purchases.log"
    config_file: str = "config.json"
    icon_file: str = "mine.png"


class Logger:
    """Centralized logging class."""
    
    def __init__(self, log_file: str = "purchases.log"):
        self.log_file = Path(log_file)
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log_purchase(self, message: str):
        """Log a purchase with timestamp."""
        self.logger.info(f"PURCHASE: {message}")
    
    def log_error(self, message: str):
        """Log an error."""
        self.logger.error(message)
    
    def log_info(self, message: str):
        """Log general information."""
        self.logger.info(message)


class PriceManager:
    """Manages price fetching and caching."""
    
    def __init__(self, config: Config, logger: Logger, app_instance=None):
        self.config = config
        self.logger = logger
        self.app_instance = app_instance
        self.prices: Dict[str, int] = {}
        self.last_fetch: Optional[datetime] = None
        self.cache_duration = 300  # 5 minutes in seconds
    
    def fetch_prices_from_sheet(self) -> bool:
        """Fetch prices from Google Sheets with caching."""
        try:
            # Check if we have recent cached data
            if (self.last_fetch and 
                (datetime.now() - self.last_fetch).seconds < self.cache_duration and 
                self.prices):
                self.logger.log_info("Using cached prices")
                return True
            
            url = f"https://docs.google.com/spreadsheets/d/{self.config.sheet_id}/export?format=csv"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            f = StringIO(response.text)
            lines = f.readlines()
            
            # Skip first 1 row (row 1), start from row 2 (index 1)
            # This will include Diamond as the first item
            if len(lines) < 2:
                raise ValueError("Sheet doesn't have enough rows")
            
            # Read from row 2 onwards (includes Diamond)
            csv_content = ''.join(lines[1:])  # Skip first 1 row
            reader = csv.DictReader(StringIO(csv_content))
            
            # Debug: print available columns
            if reader.fieldnames:
                self.logger.log_info(f"Available columns: {reader.fieldnames}")
            
            new_prices = {}
            for i, row in enumerate(reader):
                # Debug: print each row
                self.logger.log_info(f"Row {i+3}: {row}")
                
                columns = list(row.keys())
                if len(columns) >= 3:
                    # Column A (first column): Item name
                    # Column C (third column): AdjustedPrice
                    item_name = row[columns[0]]  # First column (A) - item name
                    adjusted_price = row[columns[2]]  # Third column (C) - adjusted price
                    
                    # Skip empty item names
                    if item_name and item_name.strip():
                        try:
                            new_prices[item_name.strip()] = int(adjusted_price)
                            self.logger.log_info(f"Added price: {item_name.strip()} = {adjusted_price}")
                        except ValueError:
                            self.logger.log_error(f"Invalid price for {item_name}: {adjusted_price}")
                            continue
                else:
                    self.logger.log_error(f"Not enough columns in row: {row}")
            
            if new_prices:
                self.prices = new_prices
                self.last_fetch = datetime.now()
                self.logger.log_info(f"Prices fetched successfully: {len(self.prices)} items")
                return True
            else:
                raise ValueError("No valid prices found in sheet")
                
        except requests.exceptions.RequestException as e:
            self.logger.log_error(f"Error fetching sheet: {e}")
            if self.app_instance and hasattr(self.app_instance, '_show_error_window'):
                self.app_instance._show_error_window(f"Failed to fetch prices from Google Sheets:\n{e}")
            elif self.app_instance and hasattr(self.app_instance, 'root'):
                messagebox.showerror("Error", f"Failed to fetch prices from Google Sheets:\n{e}")
            return False
        except Exception as e:
            self.logger.log_error(f"Unexpected error fetching prices: {e}")
            if self.app_instance and hasattr(self.app_instance, '_show_error_window'):
                self.app_instance._show_error_window(f"Unexpected error fetching prices:\n{e}")
            elif self.app_instance and hasattr(self.app_instance, 'root'):
                messagebox.showerror("Error", f"Unexpected error fetching prices:\n{e}")
            return False
    
    def _show_error_window(self, error_message: str):
        """Show an error window when prices can't be fetched."""
        error_window = tk.Toplevel()
        error_window.title("Error - Cannot Load Prices")
        error_window.geometry("500x300")
        error_window.resizable(False, False)
        error_window.transient(self.root if hasattr(self, 'root') and self.root else None)
        error_window.grab_set()
        
        # Center the error window
        if hasattr(self, 'root') and self.root:
            self._center_window(error_window)
        
        error_frame = ttk.Frame(error_window, padding="20")
        error_frame.pack(expand=True, fill="both")
        
        ttk.Label(error_frame, text="❌ Error Loading Prices", 
                 font=("Arial", 16, "bold"), foreground="red").pack(pady=(0, 20))
        
        ttk.Label(error_frame, text=error_message, 
                 font=("Arial", 10), wraplength=450).pack(pady=(0, 20))
        
        ttk.Label(error_frame, text="Please check your internet connection and Google Sheet settings.", 
                 font=("Arial", 10), foreground="blue").pack(pady=(0, 20))
        
        button_frame = ttk.Frame(error_frame)
        button_frame.pack()
        
        ttk.Button(button_frame, text="Retry", 
                  command=lambda: [error_window.destroy(), self._retry_fetch_prices()]).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Exit", 
                  command=lambda: [error_window.destroy(), self.root.quit() if hasattr(self, 'root') and self.root else None]).pack(side="left")
    
    def _retry_fetch_prices(self):
        """Retry fetching prices."""
        if hasattr(self, 'root') and self.root:
            self.status_label.config(text="Retrying...", foreground="blue")
            self.root.update()
            success = self.price_manager.fetch_prices_from_sheet()
            if success:
                self.status_label.config(text="Prices loaded successfully!", foreground="green")
            else:
                self.status_label.config(text="Failed to load prices", foreground="red")
    
    def get_price(self, item: str) -> int:
        """Get price for an item."""
        return self.prices.get(item, 0)
    
    def get_all_prices(self) -> Dict[str, int]:
        """Get all prices."""
        return self.prices.copy()


class DiscordNotifier:
    """Handles Discord notifications."""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.enabled = DISCORD_AVAILABLE and bool(config.discord_webhook_url)
    
    def send_message(self, message: str) -> bool:
        """Send a message to Discord."""
        if not self.enabled:
            self.logger.log_info("Discord integration disabled")
            return False
        
        try:
            webhook = DiscordWebhook(url=self.config.discord_webhook_url, content=message)
            webhook.execute()
            self.logger.log_info("Message sent to Discord successfully")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to send Discord message: {e}")
            return False


class MinecraftShopApp:
    """Main application class."""
    
    def __init__(self):
        self.config = Config()
        self.logger = Logger(self.config.log_file)
        self.price_manager = PriceManager(self.config, self.logger, self)
        self.discord_notifier = DiscordNotifier(self.config, self.logger)
        
        self.root = None
        self.shop_window = None
        self.player_name = None
        self.selected_item = None
        self.item_buttons: List[tk.Button] = []
        self.quantity_entry = None
        self.total_label = None
        self.status_label = None
        
        self._load_config()
        self._setup_ui()
    
    def _load_config(self):
        """Load configuration from file if it exists."""
        config_path = Path(self.config.config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    saved_config = json.load(f)
                    self.config.discord_webhook_url = saved_config.get('discord_webhook_url', self.config.discord_webhook_url)
                    self.config.sheet_id = saved_config.get('sheet_id', self.config.sheet_id)
                    self.logger.log_info("Configuration loaded from file")
            except Exception as e:
                self.logger.log_error(f"Error loading config: {e}")
    
    def _save_config(self):
        """Save current configuration to file."""
        try:
            config_data = {
                'discord_webhook_url': self.config.discord_webhook_url,
                'sheet_id': self.config.sheet_id
            }
            with open(self.config.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            self.logger.log_info("Configuration saved")
        except Exception as e:
            self.logger.log_error(f"Error saving config: {e}")
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.root = tk.Tk()
        self.root.title("Minecraft Shop - Login")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Create StringVar after root window is created
        self.player_name = tk.StringVar()
        
        # Set icon if available
        if PIL_AVAILABLE:
            try:
                icon_path = self._resource_path(self.config.icon_file)
                if os.path.exists(icon_path):
                    icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                    self.root.iconphoto(False, icon_img)
            except Exception as e:
                self.logger.log_error(f"Error loading icon: {e}")
        
        # Center the window
        self._center_window(self.root)
        
        # Login frame
        login_frame = ttk.Frame(self.root, padding="20")
        login_frame.pack(expand=True, fill="both")
        
        ttk.Label(login_frame, text="Minecraft Shop", font=("Arial", 16, "bold")).pack(pady=(0, 20))
        
        ttk.Label(login_frame, text="Enter your player name:", font=("Arial", 12)).pack(pady=(0, 10))
        
        name_entry = ttk.Entry(login_frame, textvariable=self.player_name, font=("Arial", 12), width=30)
        name_entry.pack(pady=(0, 20))
        name_entry.focus()
        
        # Bind Enter key to login
        name_entry.bind('<Return>', lambda e: self._login())
        
        button_frame = ttk.Frame(login_frame)
        button_frame.pack()
        
        self.login_button = ttk.Button(button_frame, text="Enter Shop", command=self._login)
        self.login_button.pack()
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(login_frame, mode='indeterminate')
        self.progress_bar.pack(pady=(10, 0), fill="x")
        self.progress_bar.pack_forget()  # Hide initially
        
        # Status label
        self.status_label = ttk.Label(login_frame, text="", foreground="blue")
        self.status_label.pack(pady=(10, 0))
    
    def _center_window(self, window):
        """Center a window on the screen."""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _resource_path(self, relative_path):
        """Get resource path for bundled applications."""
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)
    
    def _login(self):
        """Handle login process."""
        name = self.player_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter your player name")
            return
        
        if len(name) < 2:
            messagebox.showerror("Error", "Player name must be at least 2 characters long")
            return
        
        # Disable the login button and show loading message
        self.login_button.config(state="disabled", text="Loading...")
        self.status_label.config(text="Please wait a moment while we fetch the latest prices...", foreground="blue")
        self.progress_bar.pack(pady=(10, 0), fill="x")  # Show progress bar
        self.progress_bar.start(10)  # Start animation
        self.root.update()
        
        # Show step-by-step loading messages
        self.status_label.config(text="Connecting to Google Sheets...", foreground="blue")
        self.root.update()
        self.root.after(500, lambda: self._update_loading_status("Reading price data..."))
        
        # Fetch prices in background
        success = self.price_manager.fetch_prices_from_sheet()
        if success:
            self.status_label.config(text="Prices loaded successfully! Opening shop...", foreground="green")
        else:
            self.status_label.config(text="Failed to load prices. Please check your connection.", foreground="red")
        
        self.root.after(2000, self._open_shop)  # Delay to show status
    
    def _update_loading_status(self, message):
        """Update the loading status message."""
        self.status_label.config(text=message, foreground="blue")
        self.root.update()
    
    def _open_shop(self):
        """Open the shop window."""
        # Stop progress bar and hide it
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        self.root.withdraw()  # Hide login window
        
        self.shop_window = tk.Toplevel()
        self.shop_window.title(f"Minecraft Shop - {self.player_name.get()}")
        self.shop_window.geometry("375x785")
        self.shop_window.resizable(True, True)
        
        # Set icon
        if PIL_AVAILABLE:
            try:
                icon_path = self._resource_path(self.config.icon_file)
                if os.path.exists(icon_path):
                    icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                    self.shop_window.iconphoto(False, icon_img)
            except Exception as e:
                self.logger.log_error(f"Error loading icon: {e}")
        
        self._center_window(self.shop_window)
        
        # Handle window close
        self.shop_window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self._create_shop_ui()
    
    def _create_shop_ui(self):
        """Create the shop UI."""
        # Main frame
        main_frame = ttk.Frame(self.shop_window, padding="10")
        main_frame.pack(expand=True, fill="both")
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Left side - Welcome message
        ttk.Label(header_frame, text=f"Welcome {self.player_name.get()}!", 
                 font=("Arial", 16, "bold")).pack(side="left")
        
        # Right side - Action buttons
        right_frame = ttk.Frame(header_frame)
        right_frame.pack(side="right")
        
        ttk.Button(right_frame, text="Refresh Prices", 
                  command=self._refresh_prices).pack(side="right", padx=(5, 0))
        ttk.Button(right_frame, text="View Logs", 
                  command=self._view_orders).pack(side="right")
        
        # Items frame
        items_frame = ttk.LabelFrame(main_frame, text="Available Items", padding="15")
        items_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Create scrollable frame for items
        canvas = tk.Canvas(items_frame)
        scrollbar = ttk.Scrollbar(items_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Item buttons
        self.item_buttons = []
        prices = self.price_manager.get_all_prices()
        
        for i, (item, price) in enumerate(prices.items()):
            row = i // 2
            col = i % 2
            
            btn = tk.Button(
                scrollable_frame,
                text=f"{item}\n${price}",
                command=lambda i=item, b=None: self._select_item(i, b),
                width=15,
                height=3,
                font=("Arial", 10),
                relief="raised",
                bd=2,
                bg="lightgray",
                activebackground="lightblue"
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            self.item_buttons.append(btn)
        
        # Configure grid weights
        scrollable_frame.grid_columnconfigure(0, weight=1)
        scrollable_frame.grid_columnconfigure(1, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Order frame
        order_frame = ttk.LabelFrame(main_frame, text="Place Order", padding="15")
        order_frame.pack(fill="x", pady=(0, 15))
        
        # Quantity input
        quantity_frame = ttk.Frame(order_frame)
        quantity_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(quantity_frame, text="Quantity:", font=("Arial", 12)).pack(side="left")
        
        self.quantity_entry = ttk.Entry(quantity_frame, font=("Arial", 12), width=10)
        self.quantity_entry.pack(side="left", padx=(10, 0))
        self.quantity_entry.bind("<KeyRelease>", self._update_total)
        
        # Total display
        self.total_label = ttk.Label(quantity_frame, text="Total: $0", 
                                   font=("Arial", 12, "bold"), foreground="blue")
        self.total_label.pack(side="right")
        
        # Buttons
        button_frame = ttk.Frame(order_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Place Order", 
                  command=self._place_order).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Clear Selection", 
                  command=self._clear_selection).pack(side="left")
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="green")
        self.status_label.pack(side="left")
        
        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Shop Statistics", padding="15")
        stats_frame.pack(fill="x", pady=(10, 0))
        
        self._create_stats_tab(stats_frame)
    
    def _select_item(self, item: str, button: tk.Button):
        """Select an item for purchase."""
        # Reset all buttons
        for btn in self.item_buttons:
            btn.config(relief="raised")
            # Reset background by recreating the button style
            btn.config(bg="lightgray", activebackground="lightblue")
        
        # Highlight selected button
        for btn in self.item_buttons:
            if item in btn.cget("text"):
                btn.config(bg="lightgreen", relief="sunken")
                break
        
        self.selected_item = item
        self._update_total()
        self.status_label.config(text=f"Selected: {item}", foreground="blue")
    
    def _clear_selection(self):
        """Clear the current selection."""
        self.selected_item = None
        for btn in self.item_buttons:
            btn.config(relief="raised")
            # Reset background by recreating the button style
            btn.config(bg="lightgray", activebackground="lightblue")
        
        if self.quantity_entry:
            self.quantity_entry.delete(0, tk.END)
        
        if self.total_label:
            self.total_label.config(text="Total: $0")
        
        self.status_label.config(text="Selection cleared", foreground="green")
    
    def _update_total(self, *args):
        """Update the total price display."""
        if not self.selected_item or not self.total_label:
            return
        
        qty_text = self.quantity_entry.get().strip()
        if qty_text.isdigit() and int(qty_text) > 0:
            qty = int(qty_text)
            price = self.price_manager.get_price(self.selected_item)
            total = price * qty
            self.total_label.config(text=f"Total: ${total}")
        else:
            self.total_label.config(text="Total: $0")
    
    def _place_order(self):
        """Place an order."""
        if not self.selected_item:
            messagebox.showerror("Error", "Please select an item first!")
            return
        
        qty_text = self.quantity_entry.get().strip()
        if not qty_text.isdigit() or int(qty_text) <= 0:
            messagebox.showerror("Error", "Please enter a valid quantity!")
            return
        
        quantity = int(qty_text)
        price = self.price_manager.get_price(self.selected_item)
        total_cost = price * quantity
        
        # Create order message
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = (f"**New Order** - {order_time}\n"
                  f"Player: {self.player_name.get()}\n"
                  f"Item: {self.selected_item}\n"
                  f"Quantity: {quantity}\n"
                  f"Total Cost: ${total_cost}")
        
        # Log the purchase
        self.logger.log_purchase(f"Order: {self.player_name.get()} - {self.selected_item} x{quantity} = ${total_cost}")
        
        # Send to Discord
        discord_success = self.discord_notifier.send_message(message)
        
        # Update statistics
        self._update_stats()
        
        # Show confirmation
        if discord_success:
            messagebox.showinfo("Order Placed", "Your order has been sent to Discord!")
            self.status_label.config(text="Order placed successfully!", foreground="green")
        else:
            messagebox.showwarning("Order Logged", "Order logged locally but Discord notification failed.")
            self.status_label.config(text="Order logged (Discord failed)", foreground="orange")
        
        # Clear selection
        self._clear_selection()
    
    def _add_to_log_display(self, message: str):
        """Add a message to the log display."""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
    
    def _load_recent_orders(self):
        """Load recent orders from log file."""
        try:
            if os.path.exists(self.config.log_file):
                with open(self.config.log_file, 'r') as f:
                    lines = f.readlines()
                    # Show last 10 orders
                    recent_lines = lines[-10:] if len(lines) > 10 else lines
                    for line in recent_lines:
                        if line.strip():
                            self._add_to_log_display(line.strip())
        except Exception as e:
            self.logger.log_error(f"Error loading recent orders: {e}")
    
    def _create_stats_tab(self, parent):
        """Create the statistics section."""
        # Stats grid with better layout
        stats_grid = ttk.Frame(parent)
        stats_grid.pack(fill="x")
        
        # Left column
        left_col = ttk.Frame(stats_grid)
        left_col.pack(side="left", fill="x", expand=True)
        
        # Right column
        right_col = ttk.Frame(stats_grid)
        right_col.pack(side="right", fill="x", expand=True)
        
        # Left column stats
        ttk.Label(left_col, text="Items Available:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.items_count_label = ttk.Label(left_col, text=str(len(self.price_manager.get_all_prices())), 
                                         font=("Arial", 11), foreground="blue")
        self.items_count_label.pack(anchor="w", pady=(0, 10))
        
        ttk.Label(left_col, text="Orders Today:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.orders_today_label = ttk.Label(left_col, text="0", 
                                          font=("Arial", 11), foreground="green")
        self.orders_today_label.pack(anchor="w", pady=(0, 10))
        
        # Right column stats
        ttk.Label(right_col, text="Last Price Update:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.last_update_label = ttk.Label(right_col, text="Never", 
                                         font=("Arial", 11), foreground="orange")
        self.last_update_label.pack(anchor="w", pady=(0, 10))
        
        ttk.Label(right_col, text="Price Range:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.price_range_label = ttk.Label(right_col, text="$0 - $0", 
                                         font=("Arial", 11), foreground="purple")
        self.price_range_label.pack(anchor="w", pady=(0, 10))
        
        # Update stats
        self._update_stats()
    
    
    def _update_stats(self):
        """Update the statistics display."""
        try:
            # Update items count
            items_count = len(self.price_manager.get_all_prices())
            self.items_count_label.config(text=str(items_count))
            
            # Update orders today
            today_orders = self._count_orders_today()
            self.orders_today_label.config(text=str(today_orders))
            
            # Update last price update
            if self.price_manager.last_fetch:
                last_update = self.price_manager.last_fetch.strftime("%H:%M:%S")
                self.last_update_label.config(text=last_update)
            
            # Update price range
            prices = list(self.price_manager.get_all_prices().values())
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                self.price_range_label.config(text=f"${min_price} - ${max_price}")
            
        except Exception as e:
            self.logger.log_error(f"Error updating stats: {e}")
    
    def _count_orders_today(self):
        """Count orders placed today."""
        try:
            if not os.path.exists(self.config.log_file):
                return 0
            
            today = datetime.now().strftime("%Y-%m-%d")
            count = 0
            
            with open(self.config.log_file, 'r') as f:
                for line in f:
                    if today in line and "PURCHASE:" in line:
                        count += 1
            
            return count
        except Exception as e:
            self.logger.log_error(f"Error counting orders: {e}")
            return 0
    
    def _view_orders(self):
        """Open a detailed logs view window."""
        logs_window = tk.Toplevel(self.shop_window)
        logs_window.title("Purchase Logs")
        logs_window.geometry("700x500")
        logs_window.resizable(True, True)
        
        # Center the window
        self._center_window(logs_window)
        
        logs_frame = ttk.Frame(logs_window, padding="15")
        logs_frame.pack(fill="both", expand=True)
        
        # Header with title and refresh button
        header_frame = ttk.Frame(logs_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(header_frame, text="Purchase Logs", 
                 font=("Arial", 16, "bold")).pack(side="left")
        
        ttk.Button(header_frame, text="Refresh", 
                  command=lambda: self._refresh_logs(logs_text)).pack(side="right")
        
        # Logs text area with better styling
        logs_text = scrolledtext.ScrolledText(logs_frame, height=25, state="disabled", 
                                            font=("Consolas", 10), wrap=tk.WORD)
        logs_text.pack(fill="both", expand=True)
        
        # Load logs
        self._refresh_logs(logs_text)
    
    def _refresh_logs(self, logs_text):
        """Refresh the logs display."""
        try:
            logs_text.config(state="normal")
            logs_text.delete(1.0, tk.END)
            
            if os.path.exists(self.config.log_file):
                with open(self.config.log_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        logs_text.insert(tk.END, content)
                    else:
                        logs_text.insert(tk.END, "No logs found.")
            else:
                logs_text.insert(tk.END, "No log file found.")
            
            logs_text.config(state="disabled")
            logs_text.see(tk.END)  # Scroll to bottom
        except Exception as e:
            logs_text.config(state="normal")
            logs_text.insert(tk.END, f"Error loading logs: {e}")
            logs_text.config(state="disabled")
    
    def _refresh_prices(self):
        """Refresh prices from the sheet."""
        self.status_label.config(text="Refreshing prices...", foreground="blue")
        self.shop_window.update()
        
        success = self.price_manager.fetch_prices_from_sheet()
        
        if success:
            # Update button texts
            prices = self.price_manager.get_all_prices()
            for btn in self.item_buttons:
                # Extract item name from button text
                current_text = btn.cget("text")
                if "\n" in current_text:
                    item_name = current_text.split("\n")[0]
                    if item_name in prices:
                        btn.config(text=f"{item_name}\n${prices[item_name]}")
            
            self._update_total()
            self._update_stats()  # Update statistics
            self.status_label.config(text="Prices refreshed successfully!", foreground="green")
        else:
            self.status_label.config(text="Failed to refresh prices", foreground="red")
    
    def _open_settings(self):
        """Open settings window."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the settings window
        self._center_window(settings_window)
        
        settings_frame = ttk.Frame(settings_window, padding="20")
        settings_frame.pack(expand=True, fill="both")
        
        # Discord webhook URL
        ttk.Label(settings_frame, text="Discord Webhook URL:", font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        webhook_entry = ttk.Entry(settings_frame, width=50, font=("Arial", 10))
        webhook_entry.insert(0, self.config.discord_webhook_url)
        webhook_entry.pack(fill="x", pady=(0, 15))
        
        # Google Sheet ID
        ttk.Label(settings_frame, text="Google Sheet ID:", font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        sheet_entry = ttk.Entry(settings_frame, width=50, font=("Arial", 10))
        sheet_entry.insert(0, self.config.sheet_id)
        sheet_entry.pack(fill="x", pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(fill="x")
        
        def save_settings():
            self.config.discord_webhook_url = webhook_entry.get().strip()
            self.config.sheet_id = sheet_entry.get().strip()
            self._save_config()
            self.discord_notifier = DiscordNotifier(self.config, self.logger)
            messagebox.showinfo("Settings", "Settings saved successfully!")
            settings_window.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side="left")
    
    def _on_closing(self):
        """Handle application closing."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.shop_window.destroy()
            self.root.destroy()
    
    def run(self):
        """Run the application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.log_info("Application interrupted by user")
        except Exception as e:
            self.logger.log_error(f"Unexpected error: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


def main():
    """Main entry point."""
    try:
        app = MinecraftShopApp()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
