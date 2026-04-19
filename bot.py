import discord
import requests
import os
import io
import random
from flask import Flask
from threading import Thread

# --- 1. MINI WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "The SOTR Librarian is awake and operational!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. BOT CONFIGURATION ---
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
TARGET_CHANNEL_ID = 1002297308756586597

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

notion_headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

def get_book_info(libro):
    try:
        titolo = libro['properties']['Name']['title'][0]['text']['content']
    except (KeyError, IndexError):
        titolo = "Untitled Document"
    try:
        link = libro['properties']['Discord Link']['url']
    except KeyError:
        link = "No link available"
    return titolo, link

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    testo_messaggio = message.content.lower()

    # --- COMANDO: !h? ---
    if testo_messaggio == '!h?':
        help_text = (
            "📜 **SOTR LIBRARIAN COMMANDS:**\n\n"
            "🔹 `!h?` - Display this list of commands.\n"
            "🔹 `!libstats` - See how many texts we currently safeguard.\n"
            "🔹 `!library` - Download the complete catalog as a text file.\n"
            "🔹 `!search <word>` - Find specific books (e.g., `!search alchemy`).\n"
            "🔹 `!latest` - View the 5 newest additions to the library.\n"
            "🔹 `!oracle` - Receive a random reading suggestion.\n\n"
            "**How to upload:** Drop a PDF in the files channel named `Title,Author.pdf`."
        )
        await message.channel.send(help_text)
        return

    # --- COMANDO: !libstats ---
    if testo_messaggio == '!libstats':
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            risposta = requests.post(query_url, headers=notion_headers)
            if risposta.status_code == 200:
                totale = len(risposta.json().get('results', []))
                await message.channel.send(f"🏛️ **The SOTR Library currently safeguards {totale} sacred texts and documents.**")
            else:
                await message.channel.send("❌ Cannot access the archives right now.")
        except Exception as e:
            print(f"Stats Error: {e}")
        return

    # --- COMANDO: !oracle ---
    if testo_messaggio == '!oracle' or testo_messaggio == '!random':
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            risposta = requests.post(query_url, headers=notion_headers)
            if risposta.status_code == 200:
                libri = risposta.json().get('results', [])
                if not libri:
                    await message.channel.send("📭 The library is empty. The Oracle is silent.")
                    return
                libro_scelto = random.choice(libri)
                titolo, link = get_book_info(libro_scelto)
                await message.channel.send(f"🔮 **The Oracle suggests this reading for you today:**\n\n🔹 **{titolo}**\n🔗 {link}")
        except Exception as e:
            print(f"Oracle Error: {e}")
        return

    # --- COMANDO: !latest ---
    if testo_messaggio == '!latest' or testo_messaggio == '!new':
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            payload = {
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
                "page_size": 5
            }
            risposta = requests.post(query_url, headers=notion_headers, json=payload)
            if risposta.status_code == 200:
                libri = risposta.json().get('results', [])
                msg = "**🆕 HERE ARE THE 5 NEWEST ADDITIONS:**\n\n"
                for libro in libri:
                    titolo, link = get_book_info(libro)
                    msg += f"🔹 **{titolo}**\n🔗 {link}\n\n"
                await message.channel.send(msg)
        except Exception as e:
            print(f"Latest Error: {e}")
        return

    # --- COMANDO: !library ---
    if testo_messaggio == '!library':
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            risposta = requests.post(query_url, headers=notion_headers)
            if risposta.status_code == 200:
                libri = risposta.json().get('results', [])
                file_content = "SOTR LIBRARY - FULL CATALOG\n" + "="*30 + "\n\n"
                for libro in libri:
                    titolo, link = get_book_info(libro)
                    file_content += f"BOOK: {titolo}\nLINK: {link}\n" + "-"*20 + "\n"
                buffer = io.BytesIO(file_content.encode('utf-8'))
                await message.channel.send(content="✅ Complete list generated:", file=discord.File(buffer, filename="sotr_library_list.txt"))
        except Exception as e:
            print(f"Library Error: {e}")
        return

    # --- COMANDO: !search ---
    if testo_messaggio.startswith('!search '):
        search_query = testo_messaggio[8:].strip()
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            payload = {"filter": {"property": "Name", "title": {"contains": search_query}}}
            risposta = requests.post(query_url, headers=notion_headers, json=payload)
            if risposta.status_code == 200:
                results = risposta.json().get('results', [])
                if not results:
                    await message.channel.send(f"❌ No books found matching '{search_query}'.")
                    return
                msg = f"✅ Found **{len(results)}** match(es):\n\n"
                for libro in results:
                    titolo, link = get_book_info(libro)
                    msg += f"🔹 **{titolo}**\n🔗 {link}\n\n"
                await message.channel.send(msg[:2000])
        except Exception as e:
            print(f"Search Error: {e}")
        return

    # --- UPLOAD PDF ---
    if message.channel.id == TARGET_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith('.pdf'):
                await message.channel.send(f"⏳ Indexing `{attachment.filename}`...")
                try:
                    page_url = 'https://api.notion.com/v1/pages'
                    page_data = {
                        "parent": { "database_id": NOTION_DATABASE_ID },
                        "properties": {
                            "Name": {"title": [{"text": {"content": attachment.filename}}]},
                            "Discord Link": {"url": message.jump_url}
                        }
                    }
                    requests.post(page_url, headers=notion_headers, json=page_data)
                    await message.channel.send("✅ Notion library updated.")
                except:
                    await message.channel.send("❌ Failed to add to Notion.")

keep_alive()
client.run(DISCORD_TOKEN)
