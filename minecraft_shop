import tkinter as tk
from tkinter import ttk, messagebox
from discord_webhook import DiscordWebhook
import requests
import csv
from io import StringIO
import os
import sys
from PIL import Image, ImageTk

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1426471170437550162/rEwrlOkvyX38VSzOaWBu3AM-tXsinIhf-kHfQc9K2VWTC0BWywR6V-MMNJRt633Ytm3"

prices = {}
selected_item = None
item_buttons = []
quantity_entry = None
total_label = None
icon_img = None

SHEET_ID = "1MxjocKFqa4Chv9HHiOeom3LlGLbdicZXaR_41arPEkk"

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def fetch_prices_from_sheet():
    global prices
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
        response = requests.get(url)
        response.raise_for_status()
        f = StringIO(response.text)
        reader = csv.DictReader(f)
        prices = {row['Item']: int(row['Price']) for row in reader}
        print("Prices fetched:", prices)
    except requests.exceptions.RequestException as e:
        print("Error fetching sheet:", e)
        prices = {"Diamond": 50, "Iron": 20, "Dirt": 1, "Gold": 30}

def select_item(item, button):
    global selected_item
    for btn in item_buttons:
        btn.config(bg="SystemButtonFace")
    button.config(bg="lightgreen")
    selected_item = item
    update_total()

def clear_selection():
    global selected_item
    selected_item = None
    for btn in item_buttons:
        btn.config(bg="SystemButtonFace")
    if total_label:
        total_label.config(text="Total: $0")

def update_total(*args):
    if not selected_item or total_label is None:
        return
    qty = quantity_entry.get().strip()
    if qty.isdigit() and int(qty) > 0:
        total = prices[selected_item] * int(qty)
        total_label.config(text=f"Total: ${prices[selected_item]} × {qty} = ${total}")
    else:
        total_label.config(text=f"Total: ${prices[selected_item]} × 0 = $0")

def place_order():
    if not selected_item:
        messagebox.showerror("Error", "Please select an item first!")
        return
    quantity = quantity_entry.get().strip()
    if not quantity.isdigit() or int(quantity) <= 0:
        messagebox.showerror("Error", "Please enter a valid number for quantity!")
        return
    quantity = int(quantity)
    total_cost = prices[selected_item] * quantity
    message = f"Order from {player_name.get()}:\n- Item: {selected_item}\n- Amount: {quantity}\n- Total Cost: ${total_cost}"
    log_purchase(message)
    send_discord(message)
    messagebox.showinfo("Order Placed", "Your order has been sent to Discord!")

def log_purchase(msg):
    with open("purchases.log", "a") as f:
        f.write(msg + "\n")
    print(msg)

def send_discord(msg):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=msg)
    webhook.execute()

def refresh_buttons():
    for btn in item_buttons:
        item_name = btn.cget("text").split(" ($")[0]
        if item_name in prices:
            btn.config(text=f"{item_name} (${prices[item_name]})")
    update_total()

def login():
    if player_name.get().strip() == "":
        messagebox.showerror("Error", "Please enter your name")
        return
    login_window.destroy()
    fetch_prices_from_sheet()
    open_shop()

def open_shop():
    global icon_img
    shop = tk.Tk()
    shop.title("Minecraft Shop")
    icon_img = ImageTk.PhotoImage(Image.open(resource_path("mine.png")))
    shop.iconphoto(False, icon_img)
    shop.geometry("400x450")
    notebook = ttk.Notebook(shop)
    shop_tab = ttk.Frame(notebook)
    empty_tab = ttk.Frame(notebook)
    notebook.add(shop_tab, text="Shop")
    notebook.add(empty_tab, text="Empty Tab")
    notebook.pack(expand=True, fill="both")
    tk.Label(shop_tab, text=f"Welcome {player_name.get()}!", font=("Arial", 14)).pack(pady=5)
    tk.Label(shop_tab, text="Select an item:", font=("Arial", 12)).pack(pady=5)
    global item_buttons
    item_buttons = []
    for item, price in prices.items():
        btn = tk.Button(shop_tab, text=f"{item} (${price})")
        btn.config(command=lambda i=item, b=btn: select_item(i, b))
        btn.pack(pady=3)
        item_buttons.append(btn)
    tk.Button(shop_tab, text="Refresh Prices", command=lambda: [fetch_prices_from_sheet(), refresh_buttons()]).pack(pady=5)
    tk.Label(shop_tab, text="Enter Quantity:", font=("Arial", 12)).pack(pady=5)
    global quantity_entry
    quantity_entry = tk.Entry(shop_tab)
    quantity_entry.pack(pady=5)
    quantity_entry.bind("<KeyRelease>", update_total)
    global total_label
    total_label = tk.Label(shop_tab, text="Total: $0", font=("Arial", 12), fg="blue")
    total_label.pack(pady=5)
    tk.Button(shop_tab, text="Place Order", command=place_order).pack(pady=5)
    tk.Button(shop_tab, text="Clear Selection", command=clear_selection).pack(pady=5)
    tk.Label(empty_tab, text="Test", font=("Arial", 14)).pack(pady=20)
    shop.mainloop()

login_window = tk.Tk()
login_window.title("Login")
icon_img = ImageTk.PhotoImage(Image.open(resource_path("mine.png")))
login_window.iconphoto(False, icon_img)
login_window.geometry("300x150")
player_name = tk.StringVar()
tk.Label(login_window, text="Enter your player name:", font=("Arial", 12)).pack(pady=10)
tk.Entry(login_window, textvariable=player_name).pack(pady=5)
tk.Button(login_window, text="Enter Shop", command=login).pack(pady=10)
login_window.mainloop()
