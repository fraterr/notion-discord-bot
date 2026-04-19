import discord
import requests
import os
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
# Assicurati che questo sia il VERO ID del database (quello da 32 caratteri)
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
TARGET_CHANNEL_ID = 1002297308756586597

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Header standard per le richieste a Notion
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

    # --- NUOVA FUNZIONE: COMANDO !library ---
    if message.content.lower() == '!library':
        await message.channel.send("🔍 Consulting the Notion archives, just a moment...")
        
        try:
            # Chiediamo a Notion la lista dei contenuti del database
            query_url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
            risposta = requests.post(query_url, headers=notion_headers)
            
            if risposta.status_code == 200:
                dati = risposta.json()
                libri = dati.get('results', [])
                
                if not libri:
                    await message.channel.send("📭 The library is currently empty.")
                    return
                
                # Creiamo il messaggio di risposta
                testo_risposta = "**📚 AVAILABLE TEXTS IN THE SOTR LIBRARY:**\n\n"
                
                for libro in libri:
                    proprieta = libro.get('properties', {})
                    
                    # Estraiamo il nome (ignoriamo la riga se non ha un titolo)
                    try:
                        titolo = proprieta['Name']['title'][0]['text']['content']
                    except (KeyError, IndexError):
                        titolo = "Untitled Document"
                        
                    # Estraiamo il link di Discord
                    try:
                        link = proprieta['Discord Link']['url']
                    except KeyError:
                        link = "No link available"
                        
                    testo_risposta += f"🔹 **{titolo}**\n🔗 {link}\n\n"
                
                # Discord ha un limite di 2000 caratteri per messaggio. 
                # Se la libreria è enorme, tagliamo il messaggio per evitare crash.
                if len(testo_risposta) > 2000:
                    testo_risposta = testo_risposta[:1900] + "\n...[List too long, visit Notion to see them all!]"
                    
                await message.channel.send(testo_risposta)
                
            else:
                await message.channel.send("❌ Unable to communicate with Notion at this moment.")
                print(f"Notion Query Error: {risposta.text}")
                
        except Exception as e:
            print(f"Error reading the library: {e}")
            await message.channel.send("❌ An error occurred while reading the library.")
        
        return # Ferma il codice qui, non controllare gli allegati se è un comando

    # --- FUNZIONE ORIGINALE: CARICAMENTO PDF ---
    if message.channel.id == TARGET_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith('.pdf'):
                await message.channel.send(f"⏳ I saw `{attachment.filename}`, creating the entry in the Notion library...")
                
                try:
                    page_url = 'https://api.notion.com/v1/pages'
                    discord_link = message.jump_url
                    
                    page_data = {
                        "parent": { "database_id": NOTION_DATABASE_ID },
                        "properties": {
                            "Name": {
                                "title": [{"text": {"content": attachment.filename}}]
                            },
                            "Discord Link": {
                                "url": discord_link
                            }
                        }
                    }
                    
                    page_res = requests.post(page_url, headers=notion_headers, json=page_data)
                    
                    if page_res.status_code == 200:
                        await message.channel.send("✅ Library updated! You can find the permanent link on Notion.")
                    else:
                        print(f"Notion Error: {page_res.json()}")
                        await message.channel.send("❌ Error creating the row in the Notion Database.")
                        
                except Exception as e:
                    print(f"Error: {e}")
                    await message.channel.send("❌ An unexpected error occurred.")

# --- 3. STARTUP ---
keep_alive()
client.run(DISCORD_TOKEN)
