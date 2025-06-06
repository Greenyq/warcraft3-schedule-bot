import requests
from flask import Flask
from datetime import datetime, timedelta
import pytz
import html
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

last_posted_date = None

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
BROADCASTER_LOGIN = os.getenv("BROADCASTER_LOGIN")

app = Flask(__name__)


def get_twitch_token():
    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()["access_token"]


def get_broadcaster_id(token):
    url = f"https://api.twitch.tv/helix/users?login={BROADCASTER_LOGIN}"
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["data"][0]["id"]


def get_schedule(token, broadcaster_id):
    url = f"https://api.twitch.tv/helix/schedule?broadcaster_id={broadcaster_id}"
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()


def build_schedule_post():
    token = get_twitch_token()
    broadcaster_id = get_broadcaster_id(token)
    schedule_data = get_schedule(token, broadcaster_id)

    segments = schedule_data.get("data", {}).get("segments", [])
    if not segments:
        return "⚠️ Нет запланированных стримов на Twitch."

    msg_lines = ["<b>📺 Ближайшие стримы Back2Warcraft</b>\n"]

    msk_now = datetime.utcnow() + timedelta(hours=3)
    today_str = msk_now.strftime("%Y-%m-%d")

    for s in segments[:4]:  # первые 4
        start = s.get("start_time")
        title = html.escape(s.get("title", "").strip())
        dt = datetime.fromisoformat(start.replace(
            "Z", "+00:00")) + timedelta(hours=3)
        msk = dt.strftime("%d.%m %H:%M")

        if dt.strftime("%Y-%m-%d") == today_str:
            msg_lines.append(f"🔴 {msk} МСК — {title}\n")

    if len(msg_lines) == 1:
        return "⚠️ Сегодня нет стримов у Back2Warcraft."

    msg_lines.append("\n#warcraft3 #twitch #back2warcraft")
    return "\n".join(msg_lines)


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHANNEL, "text": text, "parse_mode": "HTML"}
    res = requests.post(url, json=payload)
    return res.status_code, res.text


@app.route("/")
def home():
    return "Bot is running!"


@app.route('/run')
def run():
    global last_posted_date
    try:
        today = date.today()
        if last_posted_date == today:
            return '⏱ Already sent today', 200

        post = build_schedule_post()
        status, response = send_to_telegram(post)

        if status == 200:
            last_posted_date = today
            return f'✅ Sent: {post}', 200
        else:
            return f'❌ Telegram error: {response}', 500
    except Exception as e:
        return f'❌ X Error: {e}', 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
