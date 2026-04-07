import requests
import json
import os
import xml.etree.ElementTree as ET
from twilio.rest import Client

# ── CONFIGURACIÓN ──────────────────────────────────────────────
SEARCH_QUERY = "cinta de correr myrun"
MAX_PRICE = None  # Pon un número si quieres filtrar por precio máximo, ej: 500

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN  = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM        = os.environ["TWILIO_WHATSAPP_FROM"]   # ej: "whatsapp:+14155238886"
TWILIO_TO          = os.environ["TWILIO_WHATSAPP_TO"]     # ej: "whatsapp:+34600000000"

SEEN_IDS_FILE = "seen_ids.json"
# ───────────────────────────────────────────────────────────────


def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_ids(ids):
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(list(ids), f)


def search_wallapop(query, max_price=None):
    # Usamos el feed RSS público de Wallapop (sin restricciones anti-bot)
    keyword = query.replace(" ", "+")
    url = f"https://es.wallapop.com/rss?keywords={keyword}&order_by=newest"
    if max_price:
        url += f"&max_sale_price={max_price}"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }

    response = requests.get(url, headers=headers, timeout=15)
    print("STATUS:", response.status_code)
    print("HEADERS:", response.headers)
    print("BODY:", response.text[:500])
    response.raise_for_status()

    root = ET.fromstring(response.content)
    channel = root.find("channel")

    items = []
    for entry in channel.findall("item"):
        title = entry.findtext("title", "").strip()
        link  = entry.findtext("link", "").strip()
        desc  = entry.findtext("description", "").strip()

        # Extraer precio de la descripción (formato: "X €" o "X€")
        price = "?"
        import re
        match = re.search(r"([\d.,]+)\s*€", desc)
        if match:
            price = match.group(1)

        # Usar el link como ID único
        item_id = link

        items.append({
            "id":    item_id,
            "title": title,
            "price": price,
            "url":   link,
        })
    return items


def send_whatsapp(message):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_=TWILIO_FROM,
        to=TWILIO_TO,
        body=message,
    )
    print("✅ WhatsApp enviado")


def main():
    print(f"🔍 Buscando: {SEARCH_QUERY}")
    seen_ids = load_seen_ids()

    items = search_wallapop(SEARCH_QUERY, MAX_PRICE)
    new_items = [i for i in items if i["id"] not in seen_ids]

    if new_items:
        print(f"🆕 {len(new_items)} anuncio(s) nuevo(s) encontrado(s)")
        for item in new_items:
            msg = (
                f"🏃 *Wallapop Alert* - {SEARCH_QUERY}\n\n"
                f"📌 {item['title']}\n"
                f"💶 {item['price']}€\n"
                f"🔗 {item['url']}"
            )
            send_whatsapp(msg)
            seen_ids.add(item["id"])
    else:
        print("😴 Sin novedades hoy")

    save_seen_ids(seen_ids)


if __name__ == "__main__":
    main()
