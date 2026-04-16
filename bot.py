import discord
import requests
import os
from flask import Flask
from threading import Thread

# --- 1. MINI SERVER WEB ---
app = Flask('')

@app.route('/')
def home():
    return "Il bot di Notion è sveglio e operativo!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURAZIONI DEL BOT ---
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
TARGET_CHANNEL_ID = 1002297308756586597

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot operativo come {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id == TARGET_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            
            if attachment.filename.lower().endswith('.pdf'):
                await message.channel.send(f"⏳ Ho visto `{attachment.filename}`, sto creando la scheda nella libreria Notion...")
                
                try:
                    page_url = 'https://api.notion.com/v1/pages'
                    page_headers = {
                        'Authorization': f'Bearer {NOTION_TOKEN}',
                        'Notion-Version': '2022-06-28',
                        'Content-Type': 'application/json'
                    }
                    
                    # Recuperiamo il link permanente al messaggio di Discord
                    discord_link = message.jump_url
                    
                    page_data = {
                        "parent": { "database_id": NOTION_DATABASE_ID },
                        "properties": {
                            # Titolo del PDF
                            "Nome": {
                                "title": [{"text": {"content": attachment.filename}}]
                            },
                            # Link per recuperare il file
                            "Link Discord": {
                                "url": discord_link
                            }
                        }
                    }
                    
                    page_res = requests.post(page_url, headers=page_headers, json=page_data)
                    
                    if page_res.status_code == 200:
                        await message.channel.send("✅ Libreria aggiornata! Trovi il link permanente su Notion.")
                    else:
                        print(f"Errore Notion: {page_res.json()}") # Questo ci aiuterà nei log se serve
                        await message.channel.send("❌ Errore durante la creazione della riga nel Database Notion.")
                        
                except Exception as e:
                    print(f"Errore: {e}")
                    await message.channel.send("❌ Si è verificato un errore imprevisto.")

keep_alive()
client.run(DISCORD_TOKEN)
