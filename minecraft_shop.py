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
SHEET_ID = "1MxjocKFqa4Chv9HHiOeom3LlGLbdicZXaR_41arPEkk"

prices = {}
selected_item = None
item_buttons = []
quantity_entry = None
total_label = None
money_supply = 0

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def fetch_prices_from_sheet():
    global prices, money_supply
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
        response = requests.get(url)
        response.raise_for_status()
        f = StringIO(response.text)
        lines = f.readlines()
        try:
            money_supply = int(lines[0].split()[-1])
        except Exception:
            money_supply = 0
        reader = csv.DictReader(lines[1:])
        prices = {row['Item']: int(row['AdjustedPrice']) for row in reader}
        print("Prices fetched:", prices)
    except requests.exceptions.RequestException as e:
        print("Error fetching sheet:", e)
        prices = {}
    except KeyError as e:
        print("KeyError while reading CSV:", e)
        print("Check your sheet headers: should be 'Item', 'BasePrice', 'AdjustedPrice'")
        prices = {}

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
    shop = tk.Tk()
    shop.title("Minecraft Shop")
    shop.geometry("350x550")

    notebook = ttk.Notebook(shop)
    shop_tab = ttk.Frame(notebook)
    empty_tab = ttk.Frame(notebook)
    notebook.add(shop_tab, text="Shop")
    notebook.add(empty_tab, text="Empty Tab")
    notebook.pack(expand=True, fill="both")

    header_text = f"Welcome {player_name.get()}!"
    if money_supply > 0:
        header_text += f" | Money: ${money_supply}"
    tk.Label(shop_tab, text=header_text, font=("Arial", 14)).pack(pady=5)
    tk.Label(shop_tab, text="Select an item:", font=("Arial", 12)).pack(pady=5)

    container = ttk.Frame(shop_tab)
    canvas = tk.Canvas(container)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    container.pack(fill="both", expand=True, pady=5)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(-1 * int(event.delta / 120), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    global item_buttons
    item_buttons = []

    row = 0
    col = 0
    for item, price in prices.items():
        frame = tk.Frame(scrollable_frame, relief="ridge", borderwidth=2, padx=5, pady=5)
        frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")

        btn = tk.Button(frame, text=f"{item} (${price})")
        btn.config(command=lambda i=item, b=btn: select_item(i, b))
        btn.pack(fill="x")
        item_buttons.append(btn)

        col += 1
        if col >= 2:
            col = 0
            row += 1

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
login_window.geometry("300x150")
player_name = tk.StringVar()

tk.Label(login_window, text="Enter your player name:", font=("Arial", 12)).pack(pady=10)
tk.Entry(login_window, textvariable=player_name).pack(pady=5)
tk.Button(login_window, text="Enter Shop", command=login).pack(pady=10)
login_window.mainloop()
