import discord
import requests
import os
import io # Necessario per creare il file .txt al volo
from flask import Flask
from threading import Thread

# --- 1. MINI WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "The Notion bot is awake and operational!"

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

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # --- COMANDO !library (restituisce un file .txt) ---
    if message.content.lower() == '!library':
        await message.channel.send("📄 Generating the full library list, please wait...")
        
        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            risposta = requests.post(query_url, headers=notion_headers)
            
            if risposta.status_code == 200:
                libri = risposta.json().get('results', [])
                
                if not libri:
                    await message.channel.send("📭 The library is empty.")
                    return

                # Creazione del contenuto del file testo
                file_content = "SOTR LIBRARY - FULL CATALOG\n"
                file_content += "="*30 + "\n\n"
                
                for libro in libri:
                    try:
                        titolo = libro['properties']['Name']['title'][0]['text']['content']
                        link = libro['properties']['Discord Link']['url']
                        file_content += f"BOOK: {titolo}\nLINK: {link}\n"
                        file_content += "-"*20 + "\n"
                    except:
                        continue

                # Trasformiamo il testo in un file binario per Discord
                buffer = io.BytesIO(file_content.encode('utf-8'))
                await message.channel.send(
                    content="✅ Here is the complete list of books:",
                    file=discord.File(buffer, filename="sotr_library_list.txt")
                )
            else:
                await message.channel.send("❌ Error connecting to Notion.")
        except Exception as e:
            await message.channel.send(f"❌ Error: {str(e)}")
        return

    # --- COMANDO !search <string> ---
    if message.content.lower().startswith('!search '):
        search_query = message.content[8:].strip() # Prende tutto dopo "!search "
        
        if not search_query:
            await message.channel.send("❓ Please provide a search term. Example: `!search alchemy`.")
            return

        await message.channel.send(f"🔍 Searching for '{search_query}' in the library...")

        try:
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            
            # Filtro per cercare nel titolo
            payload = {
                "filter": {
                    "property": "Name",
                    "title": {
                        "contains": search_query
                    }
                }
            }
            
            risposta = requests.post(query_url, headers=notion_headers, json=payload)
            
            if risposta.status_code == 200:
                results = risposta.json().get('results', [])
                
                if not results:
                    await message.channel.send(f"❌ No books found matching '{search_query}'.")
                    return

                testo_risposta = f"✅ Found **{len(results)}** match(es):\n\n"
                for libro in results:
                    titolo = libro['properties']['Name']['title'][0]['text']['content']
                    link = libro['properties']['Discord Link']['url']
                    testo_risposta += f"🔹 **{titolo}**\n🔗 {link}\n\n"
                
                if len(testo_risposta) > 2000:
                    testo_risposta = testo_risposta[:1900] + "\n...[Too many results, please be more specific!]"
                
                await message.channel.send(testo_risposta)
            else:
                await message.channel.send("❌ Error performing the search.")
        except Exception as e:
            await message.channel.send(f"❌ Search error: {str(e)}")
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
                except:
                    await message.channel.send("❌ Failed to add to Notion.")

keep_alive()
client.run(DISCORD_TOKEN)
