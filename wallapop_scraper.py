import requests
import json
import os
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
    session = requests.Session()

    # Primero visitamos la home para obtener cookies reales
    session.get(
        "https://es.wallapop.com/",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        timeout=15,
    )

    url = "https://api.wallapop.com/api/v3/general/search"
    params = {
        "keywords": query,
        "filters_source": "search_box",
        "order_by": "newest",
        "start": 0,
        "step": 20,
        "language": "es_ES",
        "country_code": "ES",
    }
    if max_price:
        params["max_sale_price"] = max_price

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://es.wallapop.com/",
        "Origin": "https://es.wallapop.com",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "X-DeviceOS": "0",
    }

    response = session.get(url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    items = []
    for item in data.get("search_objects", []):
        items.append({
            "id":    item["id"],
            "title": item["title"],
            "price": item["price"],
            "url":   f"https://es.wallapop.com/item/{item['web_slug']}",
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
