import hashlib
import sqlite3
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from functools import wraps
from check_id import send_to_admin_bot
import re
from database import init_db, is_authorized, add_user, list_users, remove_user, create_order_br, create_order_ph, create_admin, list_admin_users, list_admin_id
from db_connect import get_connection
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio
import html
import logging
from typing import Final
from telegram import InlineKeyboardButton, InlineKeyboardMarkup




def restricted_to_admin(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE username = %s", (user.username,))
        is_admin = cursor.fetchone()
        conn.close()

        if not is_admin:
            await update.message.reply_text("⛔ You are not authorized to perform this admin action.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@restricted_to_admin
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addadmin <username> <id>")
        return

    new_admin = context.args[0]
    new_adminid = str(context.args[1])
    if adminid == '1278018722' or adminid == '1978808516':
        try:
            add_user(new_admin, adminid)
        except Exception as e:
            await update.message.reply_text(f"Error adding Admin . Talk to Developer")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admins (username, admin_id, br_coin, ph_coin) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", (new_admin, new_adminid, 0, 0))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ @{new_admin} added as admin.")
    else:
        await update.message.reply_text(f"❌ You are not authorized!")

@restricted_to_admin
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    try:
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /removeadmin <username>")
            return
        admin_to_remove = context.args[0]
        if adminid == '1278018722' or adminid == '1978808516':
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE username = %s", (admin_to_remove,))
            conn.commit()
            if cursor.rowcount > 0:
                await update.message.reply_text(f"✅ @{admin_to_remove} removed from admins.")
            else:
                await update.message.reply_text(f"❌ No admin Found")

        else:
           await update.message.reply_text(f"❌ You cannot remove this admin : @{admin_to_remove}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error.Contact to Developer")
    finally:
        if conn:
            conn.close()


# --- Configuration ---
config = {
    #"TOKEN": "7995213634:AAHV7_AnmcVLRgZOL7AcG4yB1pjkgg2zr28", #mk
    #"TOKEN": "7471922595:AAH_qMW0b1PTNVK4fzxteL4ENru704aDtsk", #shine
    #"TOKEN": "8457013411:AAEgmqenIS3rGou58tRayumTzDn5L0j_VL0", # madeinmyanmarBot
    #"TOKEN": "8336856493:AAHxGvE83jMQdPGwruGq47xhfFfcXxmzwEs", #renzy bot
    "TOKEN": "8237614023:AAFDETzY5tqXdFXmVO26fuOxHtVme2XxKto", #kyawbot
    #"TOKEN": "8382899337:AAHEOI6vK66CRfEUIggku5GE_GlbKCMQjEs", #Test Bot
    
    #"API_KEY": "22d687785ac420062a47842f83005d43",
    "API_KEY":  "5ac7dae900ad537222746493c15d7bb1",
    "UID": "2469659",
    "EMAIL": "mr.youngburmese@gmail.com",
    "PRODUCT": "mobilelegends",
    "setting_in_progress": False,
    "user_inputs": {}
}


def extract_total_diamonds_br(spu):
    """
    Extracts and sums the main + bonus diamonds from a string like:
    'mobilelegends BR 625&81 Diamond' → 706
    'mobilelegends BR 165 Diamond' → 165
    'mobilelegends BR Passagem do crepúsculo' → None
    """
    match = re.search(r'(\d+)(?:&(\d+))? Diamond', spu)
    if match:
        main = int(match.group(1))
        bonus = int(match.group(2)) if match.group(2) else 0
        return main + bonus
    return spu

def extract_total_diamonds_ph(spu):
    """
    Extracts diamond count from strings like:
    'Mobile Legends PH-diamond_11' → 11
    'Mobile Legends PH-diamond_570' → 570
    Returns int if matched, else returns original string.
    """
    try:
        if not spu:
            return spu

        spu = str(spu)
        match = re.search(r'diamond_(\d+)', spu, re.IGNORECASE)
        if match:
            return int(match.group(1))  # Return as integer

        # Try other patterns
        match = re.search(r'(\d+)\s*Diamonds?', spu, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Try to extract any number
        match = re.search(r'(\d+)', spu)
        if match:
            return int(match.group(1))

        return spu
    except (ValueError, TypeError, AttributeError):
        return spu


# --- Restrict Access ---
def restricted_to_pro_users(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        username = update.effective_user.username
        if not is_authorized(username) and not list_admin_id(username):
            print(list_admin_id(username))
            if update.message:
                await update.message.reply_text(" 🚫 Contact to owner of your group Thank you very much for your interest")
            elif update.callback_query:
                await update.callback_query.answer("🚫 Access denied.", show_alert=True)
            return
        return await func(update, context)
    return wrapper


# --- Generate Sign ---
def generate_sign(params, m_key):
    sorted_params = '&'.join(f'{key}={value}' for key, value in sorted(params.items())) + '&' + m_key
    return hashlib.md5(hashlib.md5(sorted_params.encode()).hexdigest().encode()).hexdigest()


def generate_signature_ph(data: dict, key: str) -> str:
    sorted_items = sorted(data.items())  # sort by keys
    base_str = '&'.join([f"{k}={v}" for k, v in sorted_items])
    full_str = base_str + key
    return hashlib.md5(hashlib.md5(full_str.encode()).hexdigest().encode()).hexdigest()




import aiohttp
import time

def get_points_br():
    url = "https://www.smile.one/customer/order"
    cookies = {
        "PHPSESSID": "mmres80rfmjpkg9k2pbk7pcjcm"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, cookies=cookies, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the balance container
    balance_div = soup.find("div", class_="balance-coins")
    print(balance_div)
    balance_value = balance_div.find_all("p")[1].get_text(strip=True)
    return balance_value


def get_points_ph():
    url = "https://www.smile.one/ph/customer/order"
    cookies = {
        "PHPSESSID": "mmres80rfmjpkg9k2pbk7pcjcm"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, cookies=cookies, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the balance container
    balance_div = soup.find("div", class_="balance-coins")
    balance_value = balance_div.find_all("p")[1].get_text(strip=True)
    return balance_value


def get_product_list_br():
    current_time = int(time.time())
    params = {
        'uid': config["UID"],
        'email': config["EMAIL"],
        'product': config["PRODUCT"],
        'time': current_time
    }
    sign = generate_sign(params, config["API_KEY"])
    params['sign'] = sign
    url = "https://www.smile.one/br/smilecoin/api/productlist"
    response = requests.post(url, data=params)
    return response.json()

def get_product_list_ph():
    uid = config["UID"]
    email = config["EMAIL"]
    product = "mobilelegends"
    m_key = config["API_KEY"]
    timestamp = int(time.time())

    data = {
        "uid": uid,
        "email": email,
        "product": product,
        "time": timestamp
    }

    data["sign"] = generate_sign(data, m_key)

    url = "https://www.smile.one/ph/smilecoin/api/productlist"
    response = requests.post(url, data=data)

    try:
        return response.json()
    except Exception as e:
        print("Error:", e)
        print("Response:", response.text)
        return None


@restricted_to_pro_users
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM authorized_users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.execute("UPDATE authorized_users SET telegram_id = %s WHERE username = %s", (telegram_id, username))
    else:
        pass
    conn.commit()
    conn.close()

    await update.message.reply_text("Welcome! Use /help to configure this session.")


@restricted_to_admin
async def check_points_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) == '1278018722' or str(user_id) == '1978808516':
        try:
            response = get_points_br()
            if response:
                await update.message.reply_text(f"💰 Smile Points: {response}")
            else:
                await update.message.reply_text("❌ Failed to get points.")
        except Exception as e:
            print(e)
            await update.message.reply_text("❌  authorize first.")
    else:
        await update.message.reply_text("❌  You cannnot access.")

@restricted_to_admin
async def check_points_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) == '1278018722' or str(user_id) == '1978808516':
        try:
            response = get_points_ph()
            if response:
                await update.message.reply_text(f"💰 Smile Points: {response}")
            else:
                await update.message.reply_text("❌ Failed to get points.")
        except Exception:
            await update.message.reply_text("❌  authorize first.")
    else:
        await update.message.reply_text("❌  You cannnot access.")


translations = {
    'Passagem do crepúsculo': 'Twilight Pass',
    'Passe Semanal de Diamante': 'Weekly Diamond Pass',
}

def translate_name(name):
    name = name.replace(" BR ", " ")  # Remove BR
    for pt, en in translations.items():
        name = name.replace(pt, en)
    return name


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your Telegram ID is: {user_id}")

@restricted_to_pro_users
async def show_products_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = get_product_list_br()
    if response.get('status') == 200:
        products = response.get('data', {}).get('product', [])

        diamond_prices = {}
        special_packs = {}

        for product in products:
            name = translate_name(product.get('spu', 'Unnamed'))
            try:
                price = float(product.get('price', '0.00'))
            except ValueError:
                price = 0.0

            try:
                discount = float(product.get('discount') or 0)
            except ValueError:
                discount = 0.0

            final_price = (price - discount) * 10

            if product.get('id') == '25':
                final_price = (price - 0.92) * 10

            dia = extract_total_diamonds_br(name)
            if isinstance(dia, int):
                if dia not in diamond_prices or final_price < diamond_prices[dia]:
                    diamond_prices[dia] = final_price
            else:
                special_packs[name] = final_price

        def get_diamond_price(n):
            if n in diamond_prices:
                return diamond_prices[n]
            if n in DIAMOND_SPLITS:
                total = 0
                for part in DIAMOND_SPLITS[n]:
                    if part in diamond_prices:
                        total += diamond_prices[part]
                    else:
                        return None
                return total
            return None

        message_lines = []
        message_lines.append("💎 *Available Products for Recharge - Brazil* 💎\n")

        # Limited-Time Value Pack
        for name, price in special_packs.items():
            if "Limited" in name and "Value" in name:
                message_lines.append(f" 💎 {name} -(🪙{price:.2f})\n")
            if "Super" in name and "Value" in name:
                message_lines.append(f" 💎 {name} -(🪙{price:.2f})\n")

        message_lines.append(" First Recharge")
        first_recharge = [55, 165, 275, 565]
        for d in first_recharge:
            p = get_diamond_price(d)
            if p is not None:
                message_lines.append(f"  💎 {d} -(🪙{p:.2f})")
        message_lines.append("")

        normal_diamonds = [86, 172, 257, 343, 429, 514, 600, 706, 878, 963, 1049, 1135, 1220, 1412, 2195, 2901, 3158, 3688, 4394, 5100, 5532, 9288]
        for d in normal_diamonds:
            p = get_diamond_price(d)
            if p is not None:
                message_lines.append(f"  💎 {d}  -(🪙{p:.2f})")
        message_lines.append("")

        # Check for Twilight Pass with translated or original name
        tp_price = special_packs.get('Twilight Pass') or special_packs.get('mobilelegends Twilight Pass')
        if tp_price:
             message_lines.append(f"  💎 mobilelegends Twilight Pass -(🪙{tp_price:.2f})\n")

        # Check for Weekly Diamond Pass with translated or original name
        wp_price = special_packs.get('Weekly Diamond Pass') or special_packs.get('mobilelegends Weekly Diamond Pass')
        
        # If not found, try to find partial match
        if not wp_price:
             for k, v in special_packs.items():
                 if 'Weekly Diamond Pass' in k:
                     wp_price = v
                     break
        
        # Check for Super Value Pack if not found above
        svp_price = None
        for k, v in special_packs.items():
             if "Super" in k and "Value" in k:
                 svp_price = v
                 break
        if svp_price:
             message_lines.append(f" 💎 Super Value Pack -(🪙{svp_price:.2f})\n")

        if wp_price:
            for i in range(1, 6):
                name = "wp" if i == 1 else f"wp {i}"
                message_lines.append(f" 💎 {name} -(🪙{(wp_price * i):.2f})")
                if i < 5:
                    message_lines.append("")  # Add extra newline between items

        full_msg = "\n".join(message_lines)

        if len(full_msg) > 4000:
            for i in range(0, len(full_msg), 4000):
                await update.message.reply_text(full_msg[i:i+4000], parse_mode='Markdown')
        else:
            await update.message.reply_text(full_msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Failed to fetch products. Please try again later.")


def show_diamond_br():
    main_dia = []
    response = get_product_list_br()
    if response.get('status') == 200:
        for key, value in response.items():
            if key == 'data':
                for product in value['product']:
                    name = translate_name(product.get('spu', 'Unnamed'))
                    dia = extract_total_diamonds_br(name)
                    if (type(dia) == int):
                        main_dia.append(dia)
    return main_dia


def show_diamond_ph():
    main_dia = []
    response = get_product_list_ph()
    if response.get('status') == 200:
        for key, value in response.items():
            if key == 'data':
                for product in value['product']:
                    name = translate_name(product.get('spu', 'Unnamed'))
                    dia = extract_total_diamonds_ph(name)
                    if (type(dia) == int):
                        main_dia.append(dia)
    return main_dia


@restricted_to_pro_users
async def show_products_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #query = update.callback_query
    response = get_product_list_ph()
    if response.get('status') == 200:
        product_list_message = "💎 *Available Products for Recharge - Philippines* 💎\n\n"
        message_chunks = []

        for key, value in response.items():
            if key == 'data':
                for product in value['product']:
                    name = translate_name(product.get('spu', 'Unnamed'))
                    main_dia = extract_total_diamonds_ph(name)
                    #print("Main Diamond : ", main_dia)
                    cost_price = float(product.get('cost_price', '0.00'))
                    product_id = product.get('id', 'N/A')

                    # Safe discount conversion
                    try:
                        discount = float(product.get('discount') or 0)
                    except ValueError:
                        discount = 0.0

                    line = f"\n 💎 {main_dia} -(🪙{cost_price - discount})\n"

                    if len(product_list_message + line) > 4000:
                        message_chunks.append(product_list_message)
                        product_list_message = ""
                    product_list_message += line

        message_chunks.append(product_list_message)  # Add the last chunk

        for chunk in message_chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Failed to fetch products. Please try again later.")


def gamename(user_id, zone_id):
    url = f"https://api.isan.eu.org/nickname/ml?id={user_id}&zone={zone_id}"
    response = requests.get(url)

    # Show response
    try:
        data = response.json()
        if data['success'] == False:
            return (data['message'])
        else:
            return (data['name'])
    except ValueError:
        print("Invalid response from server:", response.text)



from itertools import combinations

# AVAILABLE_DIAMONDS = [55, 86, 165, 172, 257, 275, 565, 706, 2195, 3688, 5532, 9288]
AVAILABLE_DIAMONDS = [55, 86, 165, 172, 257, 275, 565, 706, 2195, 3688, 5532, 9288]
AVAILABLE_DIAMONDS_PH = [11, 22, 56, 112, 223, 336, 570, 1163, 2398, 6042]


DIAMOND_SPLITS = {
    343: [86, 257],
    429: [257, 172],
    514: [257, 257],
    600: [257, 257, 86],
    706: [706],
    878: [706, 172],
    963: [706, 257],
    1049: [706, 257, 86],
    1135: [706, 257, 172],
    1220: [706, 257, 257],
    1412: [706, 706],
    2901: [2195, 706],
    3158: [2195, 706, 257],
    4394: [2195, 2195],
    5100: [2195, 2195, 706],

    55: [55],
    86: [86],
    165: [165],
    172: [172],
    257: [257],
    275: [275],
    565: [565],
    2195: [2195],
    3688: [3688],
    5532: [5532],
    9288: [9288]
}

def exact_split_diamonds(target):
    return DIAMOND_SPLITS.get(target, [])


def exact_split_diamonds_ph(target):
    if target in AVAILABLE_DIAMONDS_PH:
        return [target]

    best_combo = None
    for r in range(2, len(AVAILABLE_DIAMONDS_PH) + 1):
        for combo in combinations(AVAILABLE_DIAMONDS_PH, r):
            if sum(combo) == target:
                if best_combo is None or len(combo) < len(best_combo):
                    best_combo = combo
        if best_combo:
            break

    return sorted(best_combo) if best_combo else []



from telegram.helpers import escape_markdown

def clean_text(s):
    """Remove NUL bytes and convert None to empty string."""
    if s is None:
        return ""
    return str(s).replace("\x00", "")


def recharge_user_br(userid, zoneid, product_id):
    current_time = int(time.time())
    params = {
        'uid': config["UID"],
        'email': config["EMAIL"],
        'userid': userid,
        'zoneid': zoneid,
        'product': config["PRODUCT"],
        'productid': product_id,
        'time': current_time
    }
    sign = generate_sign(params, config["API_KEY"])
    params['sign'] = sign
    url = "https://www.smile.one/br/smilecoin/api/createorder"
    return requests.post(url, data=params).json()

def recharge_user_ph(userid, zoneid, product_id):
    current_time = int(time.time())
    params = {
        'uid': config["UID"],
        'email': config["EMAIL"],
        'userid': userid,
        'zoneid': zoneid,
        'product': config["PRODUCT"],
        'productid': product_id,
        'time': current_time
    }
    sign = generate_sign(params, config["API_KEY"])
    params['sign'] = sign
    url = "https://www.smile.one/ph/smilecoin/api/createorder"
    return requests.post(url, data=params).json()

# from br_recharge import recharge_order_br
# from ph_recharge import recharge_order_ph
# # ========================= RECHARGE BR ==========================
# from fast_recharge_br import fast_recharge_order_br_async
# from fast_recharge_ph import fast_recharge_order_ph_async

from datetime import datetime
import random
import string
def generate_sn():
    """Generate order SN"""
    now = datetime.now()
    date_part = now.strftime("%y%m%d")
    time_part = now.strftime("%H%M%S")
    rand_digits = str(random.randint(100, 999))
    rand_letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    return f"S{date_part}{time_part}{rand_digits}{rand_letters}"

from smileorder import SmileOneOrder
#from smilebr import SmileOneOrderBr
#from smileph import SmileOneOrderPh
@restricted_to_pro_users
async def recharge_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = clean_text(update.effective_user.username)
    full_name = clean_text(update.effective_user.full_name)
    user_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    is_admin = bool(list_admin_id(username))

    try:
        # Get balance
        if not is_admin:
            cursor.execute("SELECT smilecoin_balance_br FROM authorized_users WHERE username = %s", (username,))
        else:
            cursor.execute("SELECT br_coin FROM admins WHERE username = %s", (username,))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text(f"❌ User @{username} not found in database.")
            return

        current_balance = row[0] or 0
        args = context.args
        args = [arg.replace("(", "").replace(")", "").strip() for arg in args]

        i = 0

        if len(args) < 3:
            await update.message.reply_text(
                "❌ Invalid format. Usage: /mk <userid> <zoneid> <diamonds/wp/tp> [count] ..."
            )
            return

        if len(args) > 20:
            await update.message.reply_text(
                "❌ Invalid format. Please adjust your order limit"
            )
            return

        response = get_product_list_br()
        if response.get('status') != 200:
            await update.message.reply_text("❌ Failed to retrieve product list.")
            return

        # Send immediate processing message
        processing_msg = await update.message.reply_text("⚡ Processing your order...")
        success_orders = []
        failed_orders = []
        sum_price = 0
        # Process arguments in chunks
        while i + 2 < len(args):
            userid = clean_text(args[i])
            zoneid = clean_text(args[i + 1])
            diamond_input = clean_text(args[i + 2])
            i += 3

            # Optional count only for WP/TP/Limit/SVP
            count = 1
            if diamond_input.lower() in ['wp', 'tp', 'limit', 'svp'] and i < len(args) and args[i].isdigit():
                count = int(args[i])
                i += 1

            if count > 5:
                await processing_msg.edit_text("❌ Max 5 items per order")
                continue

            # Determine diamond packages
            if diamond_input.lower() == 'wp':
                diamond_packages = [1] * count
                is_pass = True
            elif diamond_input.lower() == 'tp':
                diamond_packages = [2] * count
                is_pass = True
            elif diamond_input.lower() == 'limit':
                diamond_packages = [3] * count
                is_pass = True
            elif diamond_input.lower() == 'svp':
                diamond_packages = [4] * count
                is_pass = True
            else:
                is_pass = False
                try:
                    diamond_count = int(diamond_input)
                except ValueError:
                    await processing_msg.edit_text(f"❌ Invalid diamond value: {diamond_input}")
                    continue

                if count != 1:
                    await processing_msg.edit_text("❌ Count is only allowed for WP or TP")
                    continue

                diamond_packages = exact_split_diamonds(diamond_count)
                if not diamond_packages:
                    await processing_msg.edit_text(
                        f"❌ Invalid diamond value "
                    )
                    continue

            # Get game name
            try:
                game_name_val = clean_text(gamename(userid, zoneid))
                if(game_name_val == "Not found"):
                    await processing_msg.edit_text(f"❌ User not found.")
                    continue
            except Exception:
                await processing_msg.edit_text(f"❌ API Error for user {userid} zone {zoneid}")
                continue



            # Process each package
            for package in diamond_packages:
                matched_product = None
                for product in response['data']['product']:
                    if is_pass:
                        if (package == 1 and product['id'] == '16642') or (package == 2 and product['id'] == '33'):
                            matched_product = product
                            break
                        # Support for Limited-Time Value Pack (Assuming 'limit' maps to this)
                        # We need to find the product ID for "Limited-Time Value Pack"
                        # Since we don't know the ID for sure, we can match by name for 'limit'
                        if package == 3:
                            name = translate_name(product.get('spu', 'Unnamed'))
                            if "Limited" in name and "Value" in name:
                                matched_product = product
                                break
                        if package == 4:
                            name = translate_name(product.get('spu', 'Unnamed'))
                            if "Super" in name and "Value" in name:
                                matched_product = product
                                break
                    else:
                        if extract_total_diamonds_br(product['spu']) == package:
                            matched_product = product
                            break

                if not matched_product:
                    failed_orders.append(f"No product found for {package} diamonds")
                    continue

                try:
                    price_val = float(matched_product.get('cost_price') or '0.00')
                except ValueError:
                    price_val = 0.0

                try:
                    discount_val = float(matched_product.get('discount') or 0)
                except ValueError:
                    discount_val = 0.0

                price_per_unit = (price_val - discount_val) * 10.0
                if matched_product['id'] == '25':
                    price_per_unit = (price_val - 0.92) * 10.0

                if current_balance < price_per_unit:
                    failed_orders.append(f"Insufficient balance for {package} diamonds")
                    continue

                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                product_name = "Wp" if package == 1 else "Twilight Pass" if package == 2 else "Limited Value Pack" if package == 3 else f"{package}"

                # Make the recharge order
                try:
                    order = SmileOneOrder(region="BR")
                    order_response = order.execute_order_flow(user_id=str(userid), zone_id=str(zoneid), product_id=str(matched_product['id']))
                    if order_response:
                        if order_response.get("success"):
                            success = True
                        else:
                            success = False
                    if success:
                        current_balance -= price_per_unit
                        success_orders.append({
                            'order_id': generate_sn(),
                            'package': product_name,
                            'price': price_per_unit
                        })
                    else:
                        error_detail = order_response.get('message') if isinstance(order_response, dict) else str(order_response)
                        failed_orders.append(f"Order failed for {package} diamonds: {error_detail}")

                except asyncio.TimeoutError:
                    failed_orders.append(f"Order timeout for {package} diamonds")
                except Exception as e:
                    faileders:
                # Update balance from server for accuracy
                try:
                    real_balance_str = get_points_br()
                    if r_al_balance_sto:
                         current_balance = float(real_balance_rtr)
                except Exception as e:
                    print(f"Failed to fetch real balanced {e}")
ers.append(f"Order error for {package} diamonds: {str(e)}")

                sum_price += price_per_unit

            # Success summary - FIXED MARKDOWN FORMATTING
            if success_orders:
                summary = "==== Transaction Report! ====\n\n"
                summary += f"UID       :   {userid} ({zoneid})\n"
                summary += f"Name      :   {game_name_val}\n"
                summary += f"SN        :\n"
                for oid in success_orders:
                    summary += f"{oid['order_id']} ({oid['package']})\n"
                summary += f"Ordered   :   {sum(diamond_packages)} package\n"
                summary += f"Time      :   {timestamp}\n"
                summary += f"==== {username} ====\n"
                summary += f"Amount    :   {sum_price:.2f} 🪙\n"
                summary += f"Assets    :   {current_balance:.2f} 🪙\n"

                await update.message.reply_text(summary)


                send_to_admin_bot(user_id, summary)

                # Save to database
                cursor.execute('''
                    INSERT INTO br_order_history (
                        username, tele_name, user_id, zone_id, diamond_count, total_cost, order_ids, time, current_balance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    game_name_val,
                    username,
                    userid,
                    zoneid,
                    ", ".join([o['package'] for o in success_orders]),
                    sum(o['price'] for o in success_orders),
                    ", ".join([o['order_id'] for o in success_orders]),
                    timestamp,
                    current_balance
                ))

            # Failed summary
            if failed_orders:
                print(failed_orders)
                fail_text = "❌ Recharge failed:\n"
                error_msg = "Weekly Pass limit reached"
                for error in failed_orders:
                    if "Insufficient" in error:
                        error_msg = "❌ Insufficient Balance"
                        break
                await processing_msg.edit_text(error_msg)
                send_to_admin_bot(user_id, f"❌ Recharge failed:\n{fail_text}")
        if success_orders:
            await processing_msg.edit_text("✅ Order completed.")

    except Exception as e:
        print("Error:", e)
        await update.message.reply_text("❌ Check Your Command (eg. userid, zoneid, diamond).")
    finally:
        if conn:
            if not is_admin:
                cursor.execute("UPDATE authorized_users SET smilecoin_balance_br = %s WHERE username = %s", (current_balance, username))
            else:
                cursor.execute("UPDATE admins SET br_coin = %s WHERE username = %s", (current_balance, username))
            conn.commit()
            conn.close()

# Update your PH product mapping based on actual product list
def get_ph_product_mapping():
    """
    Get actual PH product IDs from the product list - FIXED VERSION
    """
    response = get_product_list_ph()
    if response and response.get('status') == 200:
        products = response['data']['product']
        mapping = {}

        for product in products:
            product_id = str(product['id'])  # Ensure string
            product_name = product.get('spu', '')
            diamond_count = extract_total_diamonds_ph(product_name)

            # Only add if we got a valid integer diamond count
            if isinstance(diamond_count, int) and diamond_count > 0:
                mapping[str(diamond_count)] = product_id
                print(f"📦 PH Product: {diamond_count} diamonds -> ID: {product_id}")

            # Check for passes
            product_name_lower = product_name.lower()
            if 'weekly' in product_name_lower or 'semanal' in product_name_lower:
                mapping['wp'] = product_id
                print(f"📦 PH Product: Wp -> ID: {product_id}")
            elif 'starlight' in product_name_lower or 'mensal' in product_name_lower or 'privilege' in product_name_lower:
                mapping['gp'] = product_id
                print(f"📦 PH Product: Starlight Pass -> ID: {product_id}")

        print(f"✅ PH Product Mapping: {mapping}")
        return mapping
    else:
        print("❌ Failed to get PH product list")
        return {}



# Update the Telegram bot to use dynamic product mapping
@restricted_to_pro_users
async def recharge_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = clean_text(update.effective_user.username)
    full_name = clean_text(update.effective_user.full_name)
    user_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    is_admin = bool(list_admin_id(username))

    try:
        # Get balance - ensure float
        if not is_admin:
            cursor.execute("SELECT smilecoin_balance_ph FROM authorized_users WHERE username = %s", (username,))
        else:
            cursor.execute("SELECT ph_coin FROM admins WHERE username = %s", (username,))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text(f"❌ User @{username} not found in database.")
            return

        current_balance = float(row[0] or 0.0)
        args = context.args
        args = [arg.replace("(", "").replace(")", "").strip() for arg in args]

        if len(args) < 3:
            await update.message.reply_text("❌ Invalid format. Usage: /mkp <userid> <zoneid> <diamonds/wp/gp> [count] ...")
            return

        processing_msg = await update.message.reply_text("⚡ Searching For your product...")

        # Get product list and mapping
        response = get_product_list_ph()
        if not response or response.get('status') != 200:
            await processing_msg.edit_text("❌ Failed to retrieve product list.")
            return

        # Get actual product mapping
        ph_mapping = get_ph_product_mapping()
        if not ph_mapping:
            await processing_msg.edit_text("❌ Could not load product mapping.")
            return

        

        i = 0
        success_orders = []
        failed_orders = []
        sum_price = 0.0
        while i + 2 < len(args):
            userid = clean_text(args[i])
            zoneid = clean_text(args[i + 1])
            diamond_input = clean_text(args[i + 2])
            i += 3

            count = 1
            if diamond_input.lower() in ['wp', 'gp', 'svp'] and i < len(args) and args[i].isdigit():
                count = int(args[i])
                i += 1

            if count > 5:
                await processing_msg.edit_text("❌ Max 5 items per order")
                continue

            # Determine packages and get product IDs
            diamond_packages = []
            product_key = ""
            is_pass = False

            if diamond_input.lower() == 'wp':
                diamond_packages = [1] * count
                is_pass = True
                product_key = 'wp'
            elif diamond_input.lower() == 'gp':
                diamond_packages = [2] * count
                is_pass = True
                product_key = 'gp'
            elif diamond_input.lower() == 'svp':
                diamond_packages = [3] * count
                is_pass = True
                product_key = 'svp'
            else:
                is_pass = False
                try:
                    diamond_count = int(diamond_input)  # Convert to integer
                    diamond_packages = exact_split_diamonds_ph(diamond_count)
                    if not diamond_packages:
                        await processing_msg.edit_text(f"❌ Invalid diamond value: {diamond_input}")
                        continue
                    # Use the actual diamond amount for product lookup
                    product_key = str(diamond_packages[0])
                except ValueError:
                    await processing_msg.edit_text(f"❌ Invalid diamond value:")
                    continue

            # Get actual product ID from mapping
            actual_product_id = ph_mapping.get(product_key)
            if not actual_product_id and product_key != 'svp': # svp might not be in mapping yet, will search dynamically
                await processing_msg.edit_text(f"❌ No product found for {diamond_input} (key: {product_key})")
                continue

            # Get game name
            try:
                game_name_val = clean_text(gamename(userid, zoneid))
                if(game_name_val == "Not found"):
                    await processing_msg.edit_text(f"❌ User not found.")
                    continue
            except Exception:
                await processing_msg.edit_text(f"❌ API Error for user {userid} zone {zoneid}")
                continue



            # Process each package
            for package in diamond_packages:
                # Find the product for this package
                matched_product = None
                for product in response['data']['product']:
                    if is_pass:
                        if (package == 1 and product_key == 'wp') or (package == 2 and product_key == 'gp'):
                            if product['id'] == actual_product_id:
                                matched_product = product
                                break
                    else:
                        # Convert both to same type for comparison
                        product_diamonds = extract_total_diamonds_ph(product['spu'])
                        if isinstance(product_diamonds, int) and product_diamonds == package:
                            matched_product = product
                            break

                if not matched_product:
                    failed_orders.append(f"No product found for {package} diamonds")
                    continue

                # Ensure price is float
                try:
                    price_per_unit = float(matched_product.get('price', 0))
                except (ValueError, TypeError):
                    price_per_unit = 0.0

                if current_balance < price_per_unit:
                    failed_orders.append(f"Insufficient balance for {package} diamonds (need {price_per_unit}, have {current_balance})")
                    continue

                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                product_name = "Wp" if package == 1 else "Starlight Pass" if package == 2 else f"{package}"

                # Make the recharge order
                try:
                    order = SmileOneOrder(region="PH")
                    order_response = order.execute_order_flow(userid, zoneid, actual_product_id)
                    if order_response:
                        if order_response.get("success"):
                            success = True
                        else:
                            success = False
                    if success:
                        current_balance -= price_per_unit
                        success_orders.append({
                            'order_id': generate_sn(),
                            'package': product_name,
                            'price': price_per_unit
                        })
                        print(f"✅ PH Order successful: {order_response.get('SN')}")
                    else:
                        error_detail = order_response.get('message', 'Unknown error')
                        failed_orders.append(f"Order failed: {error_detail}")
                        print(f"❌ PH Order failed: {error_detail}")

                except asyncio.TimeoutError:
                    failed_orders.append(f"Order timeout for {package} diamonds")
                    print(f"⏰ PH Order timeout")
                except Exception as e:
                    failed_orders.append(f"Order error: {str(e)}")
                    print(f"❌ PH Order error: {e}")

                sum_price += price_per_unit

            # Success summary
            if success_orders:
                summary = "==== Transaction Report! ====\n\n"
                summary += f"UID       :   {userid} ({zoneid})\n"
                summary += f"Name      :   {game_name_val}\n"
                summary += f"SN        :\n"
                for oid in success_orders:
                    summary += f"{oid['order_id']} ({oid['package']})\n"
                summary += f"Ordered   :   {sum(diamond_packages)} package\n"
                summary += f"Time      :   {timestamp}\n"
                summary += f"==== {username} ====\n"
                summary += f"Amount    :   {sum_price:.2f} 🪙\n"
                summary += f"Assets    :   {current_balance:.2f} 🪙\n"


                
                await update.message.reply_text(summary)


                send_to_admin_bot(user_id, summary)

                # Save to database
                cursor.execute('''
                    INSERT INTO ph_order_history (username, tele_name, user_id, zone_id, diamond_count, total_cost, order_ids, time, current_balance)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    game_name_val, username, userid, zoneid,
                    ", ".join([o['package'] for o in success_orders]),
                    float(sum_price),
                    ", ".join([o['order_id'] for o in success_orders]),
                    timestamp, float(current_balance)
                ))

            # Failed summary
            if failed_orders:
                fail_text = "❌ Recharge failed:\n"
                error_msg = "Weekly Pass limit reached"
                for error in failed_orders:
                    if "Insufficient" in error:
                        error_msg = "❌ Insufficient Balance"
                        break
                await processing_msg.edit_text(error_msg)
                send_to_admin_bot(user_id, f"❌ Recharge failed:\n{fail_text}")
        if success_orders:
            await processing_msg.edit_text("✅ Order completed.")

    except Exception as e:
        print(f"❌ Error in recharge_ph: {e}")
        await update.message.reply_text("❌ System error, please try again.")
    finally:
        if conn:
            try:
                if not is_admin:
                    cursor.execute("UPDATE authorized_users SET smilecoin_balance_ph = %s WHERE username = %s", (float(current_balance), username))
                else:
                    cursor.execute("UPDATE admins SET ph_coin = %s WHERE username = %s", (float(current_balance), username))
                conn.commit()
            except Exception as e:
                print(f"❌ Error updating balance: {e}")
            finally:
                conn.close()




@restricted_to_admin
async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adminid = update.effective_user.id
    if str(adminid) == '1278018722' or str(adminid) == '1978808516':
        text = (
            "🆘 *Help Menu*\n\n"
            "/adduser - Start bot\n"
            "/removeuser  - Remove User \n"
            "/listusers   - Show User Lists \n"
            # "/listadminusers   - Show Admin Lists \n"
            "/addcoinbr   - Recharge Coin (BR) \n"
            "/addcoinph   - Recharge Coin (PH) \n"
            "/addcoinphtoadmin   - Recharge Coin To Admin (PH) \n"
            "/addcoinbrtoadmin   - Recharge Coin To Admin (BR) \n"
            # "/addadmin    - Add Admin \n"
            # "/removeadmin - Remove Admin\n"
            "/ubalance    - Check User Balance\n"
            "/ucheckbr    - Check User Orders (BR)\n"
            "/ucheckph    - Check User Orders (PH)\n"
            "/brpoints    - Check My Coins (BR)\n"
            "/phpoints    - Check My Coins (PH)"
        )
    else:
        text = (
            "🆘 *Help Menu*\n\n"
            "/adduser - Start bot\n"
            "/removeuser  - Remove User \n"
            "/listusers   - Show User Lists \n"
            "/addcoinbr   - Recharge Coin (BR) \n"
            "/addcoinph   - Recharge Coin (PH) \n"
            "/ubalance    - Check User Balance\n"
            "/ucheckbr    - Check User Orders (BR)\n"
            "/ucheckph    - Check User Orders (PH)\n"

        )
    await update.message.reply_text(text, parse_mode="Markdown")

@restricted_to_admin
async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if not context.args:
        await update.message.reply_text("Usage: /adduser <username>")
        return
    username = context.args[0]
    if add_user(username, adminid):
        await update.message.reply_text(f"✅ {username} added to authorized users.")
    else:
        await update.message.reply_text(f"⚠️ {username} already exists or error occurred.")

@restricted_to_admin
async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if not context.args:
        await update.message.reply_text("Usage: /removeuser <username>")
        return
    username = context.args[0]
    result = remove_user(username, adminid)
    if result:
        await update.message.reply_text(f"🗑️ {username} removed from authorized users.")
    else:
        await update.message.reply_text(f"⚠️ {username} cannot be removed from authorized users.")


@restricted_to_admin
async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    conn = None
    total_br = 0.0
    total_ph = 0.0
    reply_text = "🧑 Your Authorized Users:—  🇧🇷BR / 🇵🇭PH\n\n"

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get current admin's ID from the admins table
        #adminid = update.effective_user.id

        users = list_users(adminid)  # list of usernames from somewhere else
        if not users:
            await update.message.reply_text("❌ No authorized users found.")
            return

        # Get all authorized_users with balances + owner_id
        cursor.execute("""
            SELECT telegram_id, username, smilecoin_balance_br, smilecoin_balance_ph
            FROM authorized_users
        """)
        db_data = cursor.fetchall()
        for username in users:
            cursor.execute("SELECT owner_id FROM authorized_users WHERE username = %s", (username,))
            # Find user where username matches AND owner_id equals admin_id
            userid = cursor.fetchone()
            matched = [row for row in db_data if row[1] == username]

            if matched:
                telegram_id, db_username, br_balance, ph_balance = matched[0]
                br_balance = br_balance or 0
                ph_balance = ph_balance or 0
                cursor.execute("SELECT username FROM admins WHERE admin_id = %s", (userid[0],))
                uname = cursor.fetchone()
                if uname is not None:
                    if telegram_id is None or db_username is None:
                        reply_text += f"👤 User : {username} (❌)\n(BR : {br_balance:.2f} / PH : {ph_balance:.2f})\n Owned by @{uname[0]}\n\n"
                    else:
                        if userid[0] == str(adminid):
                            reply_text += f"👤 User : {username} ✅\n(BR : {br_balance:.2f} / PH : {ph_balance:.2f}) \n\n"
                        else:
                            reply_text += f"👤 User : {username} \n(BR : {br_balance:.2f} / PH : {ph_balance:.2f}) \n Owned by @{uname[0]}\n\n"

                total_br += br_balance
                total_ph += ph_balance

        reply_text += (
            f"📊 <b>TOTAL</b>\n"
            f"🟦 <b>BR:</b> <code>{total_br:.2f}</code>\n"
            f"🟥 <b>PH:</b> <code>{total_ph:.2f}</code>\n"
        )

        await update.message.reply_text(reply_text, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"❌ No user found : {e}")

    finally:
        if conn:
            conn.close()


@restricted_to_admin
async def listadminusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = None
    reply_text = "🧑 Your Admin Users:—  🇧🇷BR / 🇵🇭PH\n\n"

    try:
        adminid = update.effective_user.id
        if str(adminid) == '1278018722' or str(adminid) == '1978808516':
            conn = get_connection()
            cursor = conn.cursor()

            users = list_admin_users()  # list of usernames from somewhere else
            if not users:
                await update.message.reply_text("❌ No authorized users found.")
                return

            for username,br_coin,ph_coin in users:
                reply_text += f"👤 Admin : {username} \nBR : {br_coin} \nPH : {ph_coin}\n\n"

            await update.message.reply_text(reply_text)
        else:
            await update.message.reply_text("❌ You are not authorized!")

    except Exception as e:
        await update.message.reply_text(f"❌ No user found : {e}")

    finally:
        if conn:
            conn.close()



async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #query = update.callback_query
    username = update.effective_user.username
    adid = update.effective_user.id
    adminid = str(adid)
    conn = get_connection()
    cursor = conn.cursor()
    admin = None

    try:
        cursor.execute("SELECT username, br_coin, ph_coin FROM admins WHERE admin_id =%s",(adminid,))
        admincoin = cursor.fetchone()
        admin, brcoin, phcoin = admincoin
    except Exception as e:
        print("This is form check balance : ", e)

    if (admin == username):
        conn.close()
        await update.message.reply_text(f"💰 Your Smile Coin balance:\n\n BR : {brcoin:.2f}\nPH : {phcoin:.2f}")
    else:
        cursor.execute("SELECT smilecoin_balance_br,smilecoin_balance_ph FROM authorized_users WHERE username = %s", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text("You are not registered.")
            return
        br_balance = row[0] or 0
        ph_balance = row[1] or 0
        await update.message.reply_text(f"💰 Your Smile Coin balance:\n\n BR : {br_balance:.2f}\nPH : {ph_balance:.2f}")

@restricted_to_admin
async def admin_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adminid = update.effective_user.id
    try:
        username = context.args[0]
        users = list_users(adminid)
        if username in users:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT smilecoin_balance_br,smilecoin_balance_ph FROM authorized_users WHERE username = %s", (username,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                await update.message.reply_text("You are not registered.")
                return
            br_balance = row[0] or 0
            ph_balance = row[1] or 0
            await update.message.reply_text(f"💰 {username}'s Smile Coin balance:\n\n BR : {br_balance:.2f}\nPH : {ph_balance:.2f}")
        else:
            await update.message.reply_text(f"❌ This user @{username} not found")
    except Exception as e:
        await update.message.reply_text(f"Usage : /ubalance username")

@restricted_to_admin
async def add_smilecoin_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if adminid in ('1278018722', '1978808516'):
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /addcoinbr <username> <amount>")
            return

        username = context.args[0].lstrip('@')
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT smilecoin_balance_br, telegram_id FROM authorized_users WHERE username = %s", (username,))
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"User @{username} not found in database.")
            conn.close()
            return

        current_balance, telegram_id = row
        new_balance = current_balance + amount
        cursor.execute("UPDATE authorized_users SET smilecoin_balance_br = %s WHERE username = %s", (new_balance, username))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Added {amount} Smile Coin to @{username}. New balance: {new_balance}")

        # Send notification to user if telegram_id exists
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"💰 You received {amount} Smile Coin from admin!\nYour BR balance: {new_balance}"
                )
            except Exception as e:
                await update.message.reply_text(f"⚠️ Could not notify @{username}: {e}")
    else:
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /addcoinbr <username> <amount>")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT br_coin  FROM admins WHERE admin_id = %s", (adminid,))
        brcoin = cursor.fetchone()
        username = context.args[0].lstrip('@')
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number.")
            return

        if(brcoin[0] > amount) :
            cursor.execute("SELECT smilecoin_balance_br, telegram_id FROM authorized_users WHERE username = %s", (username,))
            row = cursor.fetchone()

            if not row:
                await update.message.reply_text(f"User @{username} not found in database.")
                conn.close()
                return
            try:
                current_balance, telegram_id = row
                new_balance = current_balance + amount
                cursor.execute("UPDATE authorized_users SET smilecoin_balance_br = %s WHERE username = %s", (new_balance, username))
                conn.commit()

                await update.message.reply_text(f"✅ Added {amount} Smile Coin to @{username}. New balance: {new_balance}")

                upd_coin = brcoin[0] - amount
                cursor.execute("UPDATE admins SET br_coin = %s WHERE admin_id = %s", (upd_coin, adminid))
                conn.commit()
                # Send notification to user if telegram_id exists
                if telegram_id:
                    try:
                        await context.bot.send_message(
                            chat_id=telegram_id,
                            text=f"💰 You received {amount} Smile Coin from admin!\nYour BR balance: {new_balance}"
                        )
                    except Exception as e:
                        await update.message.reply_text(f"⚠️ Could not notify @{username}: {e}")

            except Exception as e:
                await update.message.reply_text(f"⚠️ Error! . Contact to Developer . {e}")
            finally:
                if conn:
                    conn.close()
        else:
            await update.message.reply_text(f"⚠️ You don't have enough coin . Please Redeem more ")


@restricted_to_admin
async def add_smilecoin_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if adminid in ('1278018722', '1978808516'):
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /addcoinph <username> <amount>")
            return

        username = context.args[0].lstrip('@')
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT smilecoin_balance_ph, telegram_id FROM authorized_users WHERE username = %s", (username,))
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"User @{username} not found in database.")
            conn.close()
            return

        current_balance, telegram_id = row
        new_balance = current_balance + amount
        cursor.execute("UPDATE authorized_users SET smilecoin_balance_ph = %s WHERE username = %s", (new_balance, username))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Added {amount} Smile Coin to @{username}. New balance: {new_balance}")

        # Send notification to user if telegram_id exists
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"💰 You received {amount} Smile Coin from admin!\nYour PH balance: {new_balance}"
                )
            except Exception as e:
                await update.message.reply_text(f"⚠️ Could not notify @{username}: {e}")
    else:
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /addcoinph <username> <amount>")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ph_coin  FROM admins WHERE admin_id = %s", (adminid,))
        phcoin = cursor.fetchone()
        username = context.args[0].lstrip('@')
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number.")
            return

        if(phcoin[0] > amount) :
            cursor.execute("SELECT smilecoin_balance_ph, telegram_id FROM authorized_users WHERE username = %s", (username,))
            row = cursor.fetchone()

            if not row:
                await update.message.reply_text(f"User @{username} not found in database.")
                conn.close()
                return
            try:
                current_balance, telegram_id = row
                new_balance = current_balance + amount
                cursor.execute("UPDATE authorized_users SET smilecoin_balance_ph = %s WHERE username = %s", (new_balance, username))
                conn.commit()

                await update.message.reply_text(f"✅ Added {amount} Smile Coin to @{username}. New balance: {new_balance}")

                upd_coin = phcoin[0] - amount
                cursor.execute("UPDATE admins SET ph_coin = %s WHERE admin_id = %s", (upd_coin, adminid))
                conn.commit()
                # Send notification to user if telegram_id exists
                if telegram_id:
                    try:
                        await context.bot.send_message(
                            chat_id=telegram_id,
                            text=f"💰 You received {amount} Smile Coin from admin!\nYour PH balance: {new_balance}"
                        )
                    except Exception as e:
                        await update.message.reply_text(f"⚠️ Could not notify @{username}: {e}")

            except Exception as e:
                await update.message.reply_text(f"⚠️ Error! . Contact to Developer . {e}")
            finally:
                if conn:
                    conn.close()
        else:
            await update.message.reply_text(f"⚠️ You don't have enough coin . Please Redeem more ")



@restricted_to_admin
async def add_admin_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if adminid in ('1278018722', '1978808516'):
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /addcoinphtoadmin <username> <amount>")
            return

        username = context.args[0].lstrip('@')
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ph_coin, admin_id FROM admins WHERE username = %s", (username,))
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"User @{username} not found in database.")
            conn.close()
            return

        current_balance, telegram_id = row
        new_balance = current_balance + amount
        cursor.execute("UPDATE admins SET ph_coin = %s WHERE username = %s", (new_balance, username))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Added {amount} Smile Coin to @{username}. New balance: {new_balance}")

        # Send notification to user if telegram_id exists
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"💰 You received {amount} Smile Coin from admin!\nYour PH balance: {new_balance}"
                )
            except Exception as e:
                await update.message.reply_text(f"⚠️ Could not notify @{username}: {e}")
    else:
        await update.message.reply_text(f"⚠️ You don't have permission .")



@restricted_to_admin
async def add_admin_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adid = update.effective_user.id
    adminid = str(adid)
    if adminid in ('1278018722', '1978808516'):
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /addcoinbrtoadmin <username> <amount>")
            return

        username = context.args[0].lstrip('@')
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Amount must be a number.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT br_coin, admin_id FROM admins WHERE username = %s", (username,))
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text(f"User @{username} not found in database.")
            conn.close()
            return

        current_balance, telegram_id = row
        new_balance = current_balance + amount
        cursor.execute("UPDATE admins SET br_coin = %s WHERE username = %s", (new_balance, username))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Added {amount} Smile Coin to @{username}. New balance: {new_balance}")

        # Send notification to user if telegram_id exists
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"💰 You received {amount} Smile Coin from admin!\nYour BR balance: {new_balance}"
                )
            except Exception as e:
                await update.message.reply_text(f"⚠️ Could not notify @{username}: {e}")
    else:
        await update.message.reply_text(f"⚠️ You don't have permission .")

@restricted_to_pro_users
async def view_history_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ph_order_history WHERE tele_name = %s ORDER BY id DESC LIMIT 10",
        (username,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 No order history found.")
        conn.close()
        return

    for row in rows:
        summary = (
            f"*📜 Last Order:*\n\n"
            f"UID: `{escape_markdown(str(row[3]), version=1)} ({escape_markdown(str(row[4]), version=1)})`\n"
            f"Name: {escape_markdown(str(row[1]), version=1)}\n"
            f"SN: `{escape_markdown(str(row[8]), version=1)}`\n"
            f"Order: {escape_markdown(str(row[5]), version=1)}\n"
            f"Time: `{escape_markdown(str(row[9]), version=1)}`\n"
            f"Paid SmileCoins: `{float(row[6]):.2f}`\n"
            f"Current SmileCoins: `{float(row[10]):.2f}`"
        )
        await update.message.reply_text(summary, parse_mode="Markdown")

    conn.close()

@restricted_to_pro_users
async def view_history_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM br_order_history WHERE tele_name = %s ORDER BY id DESC LIMIT 10",
        (username,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 No order history found.")
        conn.close()
        return

    for row in rows:
        summary = (
            f"*📜 Last Order:*\n\n"
            f"UID: `{escape_markdown(str(row[3]), version=1)} ({escape_markdown(str(row[4]), version=1)})`\n"
            f"Name: {escape_markdown(str(row[1]), version=1)}\n"
            f"SN: `{escape_markdown(str(row[8]), version=1)}`\n"
            f"Order: {escape_markdown(str(row[5]), version=1)}\n"
            f"Time: `{escape_markdown(str(row[9]), version=1)}`\n"
            f"Paid SmileCoins: `{float(row[6]):.2f}`\n"
            f"Current SmileCoins: `{float(row[10]):.2f}`"
        )
        await update.message.reply_text(summary, parse_mode="Markdown")

    conn.close()



@restricted_to_admin
async def admin_view_history_br(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adminid = update.effective_user.id
    users = list_users(adminid)
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a username. Usage: /ucheckbr <username> [limit]")
        return

    username = context.args[0]

    if username in users:
        try:
            limit = int(context.args[1]) if len(context.args) > 1 else 10
            if limit <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Invalid limit. Use a number > 0. Example: /ucheckbr <username> 5")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM br_order_history WHERE tele_name = %s ORDER BY id DESC LIMIT %s",
            (username, limit)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("📭 No order history found.")
            return

        for row in rows:
            summary = (
                f"*📜 Last Order:*\n\n"
                f"UID: `{escape_markdown(str(row[3]), version=1)} ({escape_markdown(str(row[4]), version=1)})`\n"
                f"Name: {escape_markdown(str(row[1]), version=1)}\n"
                f"SN: `{escape_markdown(str(row[8]), version=1)}`\n"
                f"Order: {escape_markdown(str(row[5]), version=1)}\n"
                f"Time: `{escape_markdown(str(row[9]), version=1)}`\n"
                f"Paid SmileCoins: `{float(row[6]):.2f}`\n"
                f"Current SmileCoins: `{float(row[10]):.2f}`"
            )
            await update.message.reply_text(summary, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ This user @{username} not found")


@restricted_to_admin
async def admin_view_history_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    adminid = update.effective_user.id
    users = list_users(adminid)
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a username. Usage: /ucheckph <username> [limit]")
        return

    username = context.args[0]
    if username in users:
        try:
            limit = int(context.args[1]) if len(context.args) > 1 else 10
            if limit <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Invalid limit. Use a number > 0. Example: /ucheckph kaungset 5")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM ph_order_history WHERE tele_name = %s ORDER BY id DESC LIMIT %s",
            (username, limit)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("📭 No order history found.")
            return

        for row in rows:
            summary = (
                f"*📜 Last Order:*\n\n"
                f"UID: `{escape_markdown(str(row[3]), version=1)} ({escape_markdown(str(row[4]), version=1)})`\n"
                f"Name: {escape_markdown(str(row[1]), version=1)}\n"
                f"SN: `{escape_markdown(str(row[8]), version=1)}`\n"
                f"Order: {escape_markdown(str(row[5]), version=1)}\n"
                f"Time: `{escape_markdown(str(row[9]), version=1)}`\n"
                f"Paid SmileCoins: `{float(row[6]):.2f}`\n"
                f"Current SmileCoins: `{float(row[10]):.2f}`"
            )
            await update.message.reply_text(summary, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ This user @{username} not found!")

async def pizzashop_check_user_info(user_id: str, zone_id: str) -> str:
    cookies = {
        'ci_session': '10218da0c0ec02212ddf170dbecf3859266459b8',
        'cf_clearance': 'PmKZc6Bzs1dFH6poD11N97I0bsOLwf0WO9cagOmufNo-1750927802-1.2.1.1-sJxvRLvdjX3GuIDrgBbLZ89BlBbG2C7zeLGylIY89P3kBHaSFjKAAtdA43g8qGpZO4iYNKLOzxu3Symvw2oKo9BaD1NY1V5OK9.cyQLiVOt0360kuQ7ZmnULjWf.NsKy1z1Yt4HcPMok9vYnC_JAm9nzNWEW8zoFAZcws233bQTELuTJJh01BVzZP79aTtJh865iLU5sEQtWpXupwGrlqQHJvE.fX1asbCJaaN8KcNbZrxIRy2i6TfZA5fZRrEOBIZyrM355FADyPyrewV3yzMuWZKjvlsJS5Jmpo1JZ8cf92V2HHIZSMj6_kVty30Oww7mJg2f_lJf4pntQLYx9tBCJB3XYgeCOTCejI9P_qIo',
    }

    headers = {
        'authority': 'pizzoshop.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://pizzoshop.com',
        'referer': 'https://pizzoshop.com/mlchecker/check',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }

    data = {
        'user_id': user_id,
        'zone_id': zone_id,
    }

    async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
        try:
            async with session.post('https://pizzoshop.com/mlchecker/check', data=data) as response:
                response.raise_for_status()
                html_content = await response.text()

            soup = BeautifulSoup(html_content, 'html.parser')

            nick_name = "N/A (Not found)"
            region = "N/A (Not found)"

            account_info_div = soup.find('div', class_='mt-4 card card-custom shadow-sm')

            if account_info_div:
                table = account_info_div.find('table', class_='table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            if th.get_text(strip=True) == 'Nickname':
                                nick_name = td.get_text(strip=True).replace('+', ' ').replace("&#039;", "'")
                            elif th.get_text(strip=True) == 'Region ID':
                                region = td.get_text(strip=True)

            return (f"✅ User Info:\n\n"
                    f"🆔 User ID: <code>{html.escape(user_id)}</code>\n\n"
                    f"🌍 Server ID: <code>{html.escape(zone_id)}</code>\n\n"
                    f"🎮 Nickname: {html.escape(nick_name)}\n\n"
                    f"📍 Region: {html.escape(region)}")

        except aiohttp.ClientError as e:
            return f"❌ Error checking user info: {html.escape(str(e))}. Please try again later."
        except Exception as e:
            return f"❌ An unexpected error occurred: {html.escape(str(e))}"

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ Please use the format: `/checkID userId zoneId` or `/checkID userId(zoneId)`.", parse_mode='Markdown')
        return

    full_args_string = " ".join(context.args)
    match = re.match(r'(\d+)\s*\(?(\d+)\)?$', full_args_string)

    if not match:
        await update.message.reply_text("⚠️ Invalid ID format. Please use `userId zoneId` or `userId(zoneId)`.", parse_mode='Markdown')
        return

    user_id, zone_id = match.groups()

    loading_message = await update.message.reply_text("🗂️ Fetching user information...", parse_mode='HTML')

    message = await pizzashop_check_user_info(user_id, zone_id)

    await loading_message.edit_text(message, parse_mode='HTML')





async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    telegram_id = update.effective_user.id

    help_text = (
        "🆘 *Help Menu*\n\n"
        "Here are the available commands:\n"
        "/balance - 💰 Check current balance\n"
        "/showph - 📦 Show  products (PH)\n"
        "/showbr - 📦 Show  products (BR)\n"
        "/mkp - 💎 Recharge MLBB (PH)\n"
        "/mk  - 💎 Recharge MLBB (BR)\n"
        "/orph - 📜 View order history (PH)\n"
        "/orbr - 📜 View order history (BR)\n"
        "/checkID - 📜 Player\n"
        "/myid - 📜 Check Your Telegram ID\n"
        "/redeem  - 💎 Exchange Redeem Code to Coin\n"
    )
    # conn.commit()
    # conn.close()
    await update.message.reply_text(help_text, parse_mode="Markdown")



# --- Your Smile.One PHPSESSID (must be logged in already) ---
SESSION_COOKIE = "mmres80rfmjpkg9k2pbk7pcjcm"  # Change this to your session cookie

# ----------------------------
# SmileOne Activator Class
# ----------------------------
class SmileOneActivator:
    def __init__(self, session_cookie, activation_code):
        self.amount = None
        self.base_url = "https://www.smile.one"
        self.session = requests.Session()
        self.session.cookies.set("PHPSESSID", session_cookie, domain="www.smile.one")
        self.activation_code = activation_code
        self._setup_headers()

    def _setup_headers(self):
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Origin": self.base_url,
            "Referer": urljoin(self.base_url, "/customer/activationcode"),
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })

    def _get_csrf_token(self):
        csrf_cookie = self.session.cookies.get("_csrf", "")
        if csrf_cookie:
            try:
                parts = csrf_cookie.split("%22")
                if len(parts) >= 4:
                    return parts[3]
            except:
                pass
        return ""

    def validate_code(self):
        url = urljoin(self.base_url, "/smilecard/pay/checkcard")
        data = {"sec": self.activation_code}

        response = self.session.post(url, data=data)
        if response.status_code != 200:
            return False, f"HTTP Error: {response.status_code}"

        try:
            result = response.json()
            if result.get("code") == 200:
                return True, result
            return False, result.get("info", "Validation failed")
        except ValueError:
            return False, "Invalid JSON response"

    def confirm_activation(self, country):
        url = urljoin(self.base_url, "/smilecard/pay/payajax")
        data = {
            "sec": self.activation_code,
            "country": country,
            "_csrf": self._get_csrf_token(),
        }

        response = self.session.post(url, data=data)
        if response.status_code != 200:
            return False, f"HTTP Error: {response.status_code}"

        try:
            result = response.json()
            print(result)
            if result.get("code") == 200:
                return True, "Activation confirmed successfully"
            return False, result.get("info", "Confirmation failed")
        except ValueError:
            return False, "Invalid JSON response"

    def complete_activation(self):
        valid, result = self.validate_code()
        if not valid:
            return False, result
        self.amount = result.get("info")
        country = result.get("country", "Brasil（Brazil）")
        return self.confirm_activation(country)


async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uname = update.effective_user.username
    adid = update.effective_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id, smilecoin_balance_br FROM authorized_users WHERE username = %s", (uname,))
    owid = cursor.fetchone()
    #br_balance = owid[1] or 0

    try:

        if len(context.args) != 1:
            await update.message.reply_text("Usage: /redeem ACTIVATION_CODE")
            return

        activation_code = context.args[0]
        loading_message = await update.message.reply_text(f"Redeeming code: {activation_code} ...")

        activator = SmileOneActivator(SESSION_COOKIE, activation_code)
        success, message = activator.complete_activation()

        if success:
            await loading_message.edit_text(f"✅  {activator.amount} coins Redeem successfully.")
        else:
            await loading_message.edit_text(
                "❌ FAILED: Validation failed.\n\n🙏 I have deducted ten coins from you.\n🙏 To avoid losing your remaining\ncoins, do not use codes that have\nalready been redeemed."
            )


        # --- Check if user is admin or normal user ---
        admin = None
        try:
            cursor.execute("SELECT username FROM admins WHERE admin_id = %s", (str(adid),))
            admin = cursor.fetchone()
        except Exception:
            pass

        if admin:
            cursor.execute("SELECT br_coin, ph_coin FROM admins WHERE username = %s", (uname,))
            row = cursor.fetchone()
            if not row:
                await update.message.reply_text(f"User @{uname} not found in database.")
                return

            if activator.amount:
                before_balance = row[0]
                if activator.amount == 300:
                    amount = (activator.amount * 0.6) / 100
                else:
                    amount = (activator.amount * 0.2) / 100
                after_balance = before_balance + (activator.amount - amount)

                cursor.execute("UPDATE admins SET br_coin = %s WHERE username = %s", (after_balance, uname))
                conn.commit()

                # Notify user
                await update.message.reply_text(
                    f"✅ Redeem Success\nBefore: {before_balance} BR\nAfter: {after_balance} BR\n@{uname}"
                )

                # Notify admin
                await context.bot.send_message(
                    chat_id=1278018722,
                    text=(
                        f"@{uname} redeemed {activator.amount} coins ✅\n\n"
                        f"Before: {before_balance} BR\n"
                        f"After: {after_balance} BR"
                    )
                )

        else:
            cursor.execute("SELECT smilecoin_balance_br, telegram_id FROM authorized_users WHERE username = %s", (uname,))
            row = cursor.fetchone()

            if not row:
                await update.message.reply_text(f"User @{uname} not found in database.")
                return

            if activator.amount:
                before_balance = row[0]
                amount = (activator.amount * 0.2) / 100
                after_balance = before_balance + (activator.amount - amount)

                cursor.execute("UPDATE authorized_users SET smilecoin_balance_br = %s WHERE username = %s", (after_balance, uname))
                conn.commit()

                # Notify user
                await update.message.reply_text(
                    f"✅ Redeem Success\nBefore: {before_balance} BR\nAfter: {after_balance} BR\n@{uname}"
                )

                # Notify admin
                await context.bot.send_message(
                    chat_id=1278018722,
                    text=(
                        f"@{uname} redeemed {activator.amount} coins ✅\n\n"
                        f"Before: {before_balance} BR\n"
                        f"After: {after_balance} BR"
                    )
                )

        # --- Handle failed activation penalty ---
        if not activator.amount:
            if admin:
                cursor.execute("SELECT br_coin FROM admins WHERE username = %s", (uname,))
                row = cursor.fetchone()
                if not row:
                    return

                before_balance = row[0]
                after_balance = before_balance - 10

                cursor.execute("UPDATE admins SET br_coin = %s WHERE username = %s", (after_balance, uname))
                conn.commit()

                # Notify admin about penalty
                await context.bot.send_message(
                    chat_id=1278018722,
                    text=(
                        f"@{uname} was punished ❌\n10 coins deducted.\n\n"
                        f"Before: {before_balance} BR\n"
                        f"After: {after_balance} BR"
                    )
                )
            else:
                cursor.execute("SELECT smilecoin_balance_br FROM authorized_users WHERE username = %s", (uname,))
                row = cursor.fetchone()
                if not row:
                    return

                before_balance = row[0]
                after_balance = before_balance - 10

                cursor.execute("UPDATE authorized_users SET smilecoin_balance_br = %s WHERE username = %s", (after_balance, uname))
                conn.commit()

                # Notify admin about penalty
                await context.bot.send_message(
                    chat_id=1278018722,
                    text=(
                        f"@{uname} was punished ❌\n10 coins deducted.\n\n"
                        f"Before: {before_balance} BR\n"
                        f"After: {after_balance} BR"
                    )
                )

    except Exception as e:
        print("This is from redeem error:", e)

    finally:
        if conn:
            conn.close()


@restricted_to_admin
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    message_text = " ".join(context.args)  # The message after the /broadcast command

    if not message_text:
        await update.message.reply_text("Please provide a message to send.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT telegram_id FROM authorized_users WHERE telegram_id IS NOT NULL")
    users = cursor.fetchall()

    conn.close()

    sent_count = 0
    for (uid,) in users:
        if uid != sender_id:  # Don't send to the person who initiated
            try:
                await context.bot.send_message(chat_id=uid, text=message_text)
                sent_count += 1
                print("This is valid user : ", uid)
            except Exception as e:
                print(f"Failed to send to {uid}: {e}")

    await update.message.reply_text(f"Message sent to {sent_count} users.")

from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, CommandHandler

# === DB function to fetch admin IDs ===
def get_all_admin_ids():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT admin_id FROM admins")
        return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

def main():
    init_db()
    create_order_ph()
    create_order_br()
    create_admin()

    app = ApplicationBuilder().token(config["TOKEN"]).build()

    # === User Handlers ===
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("showph", show_products_ph))
    app.add_handler(CommandHandler("showbr", show_products_br))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("mk", recharge_br))
    app.add_handler(CommandHandler("mkp", recharge_ph))
    app.add_handler(CommandHandler("balance", check_balance))
    app.add_handler(CommandHandler("orph", view_history_ph))
    app.add_handler(CommandHandler("orbr", view_history_br))
    app.add_handler(CommandHandler("checkid", check_command))
    app.add_handler(CommandHandler("myid", get_id))
    app.add_handler(CommandHandler("redeem", redeem))

    # === Admin Handlers (restricted by @restricted_to_admin) ===
    app.add_handler(CommandHandler("brpoints", check_points_br))
    app.add_handler(CommandHandler("phpoints", check_points_ph))
    app.add_handler(CommandHandler("adminhelp", admin_help_command))
    app.add_handler(CommandHandler("addcoinphtoadmin", add_admin_ph))
    app.add_handler(CommandHandler("addcoinbrtoadmin", add_admin_br))
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("removeuser", removeuser))
    app.add_handler(CommandHandler("listusers", listusers))
    #app.add_handler(CommandHandler("listadminusers", listadminusers))
    app.add_handler(CommandHandler("addcoinbr", add_smilecoin_br))
    app.add_handler(CommandHandler("addcoinph", add_smilecoin_ph))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("ubalance", admin_check_balance))
    app.add_handler(CommandHandler("ucheckbr", admin_view_history_br))
    app.add_handler(CommandHandler("ucheckph", admin_view_history_ph))
    app.add_handler(CommandHandler("tell", broadcast))
    app.add_handler(CommandHandler("listadminusers", listadminusers))
    #app.add_handler(CommandHandler("addadmin", add_admin))
    #app.add_handler(CommandHandler("removeadmin", remove_admin))

    app.run_polling()

if __name__ == "__main__":
    main()
