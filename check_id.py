import requests

# Bot B token and the admin chat ID where you want to send the message
BOT_B_TOKEN = '8097226904:AAHOiYiisuW45W6xu4PIiF_zEH_rPadParI'
BOT_B_CHAT_ID = '1278018722'  # can be group ID or individual

def send_to_admin_bot(user_id, message):
    url = f"https://api.telegram.org/bot{BOT_B_TOKEN}/sendMessage"
    payload = {
        "chat_id": BOT_B_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)
