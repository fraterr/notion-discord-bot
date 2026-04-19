import discord
import requests
import os
import io
import random # Necessario per il comando !oracle
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

# Funzione di supporto per estrarre facilmente titolo e link da una riga di Notion
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
    # Ignora i messaggi del bot stesso
    if message.author == client.user:
        return

    testo_messaggio = message.content.lower()

    # --- COMANDO: !help ---
    if testo_messaggio == '!help':
        help_text = (
            "📜 **SOTR LIBRARIAN COMMANDS:**\n\n"
            "🔹 `!library` - Download the complete catalog as a text file.\n"
            "🔹 `!search <word>` - Find specific books (e.g., `!search alchemy`).\n"
            "🔹 `!latest` - View the 5 newest additions to the library.\n"
            "🔹 `!oracle` - Receive a random reading suggestion.\n"
            "🔹 `!stats` - See how many texts we currently safeguard.\n\n"
            "**How to upload:** Drop a PDF in the files channel named `Title,Author.pdf`."
        )
        await message.channel.send(help_text)
        return

    # --- COMANDO: !stats ---
    if testo_messaggio == '!stats':
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            # Chiediamo a Notion solo gli ID per risparmiare tempo e contare più in fretta
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
            else:
                await message.channel.send("❌ The Oracle's vision is clouded right now.")
        except Exception as e:
            print(f"Oracle Error: {e}")
        return

    # --- COMANDO: !latest ---
    if testo_messaggio == '!latest' or testo_messaggio == '!new':
        await message.channel.send("🆕 Checking the newest arrivals...")
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            # Ordiniamo per data di creazione, dal più recente al più vecchio, e ne prendiamo solo 5
            payload = {
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
                "page_size": 5
            }
            risposta = requests.post(query_url, headers=notion_headers, json=payload)
            
            if risposta.status_code == 200:
                libri = risposta.json().get('results', [])
                if not libri:
                    await message.channel.send("📭 No books have been added yet.")
                    return

                msg = "**🆕 HERE ARE THE 5 NEWEST ADDITIONS:**\n\n"
                for libro in libri:
                    titolo, link = get_book_info(libro)
                    msg += f"🔹 **{titolo}**\n🔗 {link}\n\n"
                
                await message.channel.send(msg)
            else:
                await message.channel.send("❌ Error fetching new arrivals.")
        except Exception as e:
            print(f"Latest Error: {e}")
        return

    # --- COMANDO: !library ---
    if testo_messaggio == '!library':
        await message.channel.send("📄 Generating the full library list, please wait...")
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            risposta = requests.post(query_url, headers=notion_headers)
            
            if risposta.status_code == 200:
                libri = risposta.json().get('results', [])
                if not libri:
                    await message.channel.send("📭 The library is empty.")
                    return

                file_content = "SOTR LIBRARY - FULL CATALOG\n"
                file_content += "="*30 + "\n\n"
                
                for libro in libri:
                    titolo, link = get_book_info(libro)
                    file_content += f"BOOK: {titolo}\nLINK: {link}\n"
                    file_content += "-"*20 + "\n"

                buffer = io.BytesIO(file_content.encode('utf-8'))
                await message.channel.send(
                    content="✅ Here is the complete list of books:",
                    file=discord.File(buffer, filename="sotr_library_list.txt")
                )
            else:
                await message.channel.send("❌ Error connecting to Notion.")
        except Exception as e:
            print(f"Library Error: {e}")
        return

    # --- COMANDO: !search <string> ---
    if testo_messaggio.startswith('!search '):
        search_query = testo_messaggio[8:].strip()
        if not search_query:
            await message.channel.send("❓ Please provide a search term. Example: `!search alchemy`.")
            return

        await message.channel.send(f"🔍 Searching for '{search_query}' in the library...")
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            payload = {
                "filter": {
                    "property": "Name",
                    "title": {"contains": search_query}
                }
            }
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
                
                if len(msg) > 2000:
                    msg = msg[:1900] + "\n...[Too many results, please be more specific!]"
                await message.channel.send(msg)
            else:
                await message.channel.send("❌ Error performing the search.")
        except Exception as e:
            print(f"Search Error: {e}")
        return

    # --- FUNZIONE ORIGINALE: CARICAMENTO PDF ---
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
                except Exception as e:
                    print(f"Upload Error: {e}")
                    await message.channel.send("❌ Failed to add to Notion.")

# --- 3. STARTUP ---
keep_alive()
client.run(DISCORD_TOKEN)
