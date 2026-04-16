import discord
import requests
import io
import os

# --- CONFIGURAZIONI ---
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
TARGET_CHANNEL_ID = 1002297308756586597  # L'ID del tuo canale "files" su Discord

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot operativo come {client.user}')

@client.event
async def on_message(message):
    # Evita loop se il bot scrive messaggi
    if message.author == client.user:
        return

    # Controlla se siamo nel canale giusto e se ci sono allegati
    if message.channel.id == TARGET_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            
            # Filtra solo i file PDF
            if attachment.filename.lower().endswith('.pdf'):
                await message.channel.send(f"⏳ Ho visto `{attachment.filename}`, lo sto caricando nella libreria Notion...")
                
                try:
                    # 1. Scarica il file da Discord in memoria (RAM)
                    file_bytes = await attachment.read()
                    
                    # 2. Carica il file direttamente nei server di Notion (Limite: 20MB per file)
                    upload_url = 'https://api.notion.com/v1/file_uploads'
                    headers = {
                        'Authorization': f'Bearer {NOTION_TOKEN}',
                        'Notion-Version': '2022-06-28' # Versione stabile delle API
                    }
                    # Struttura il file per l'upload multipart
                    files = {'file': (attachment.filename, file_bytes, 'application/pdf')}
                    upload_res = requests.post(upload_url, headers=headers, files=files)
                    
                    if upload_res.status_code != 200:
                        await message.channel.send("❌ Errore durante l'upload sui server di Notion.")
                        continue
                        
                    # Ottieni l'ID del file appena ospitato su Notion
                    file_upload_id = upload_res.json().get('id')
                    
                    # 3. Crea la riga nel Database Notion e allegaci il file caricato
                    page_url = 'https://api.notion.com/v1/pages'
                    page_headers = {
                        'Authorization': f'Bearer {NOTION_TOKEN}',
                        'Notion-Version': '2022-06-28',
                        'Content-Type': 'application/json'
                    }
                    
                    page_data = {
                        "parent": { "database_id": NOTION_DATABASE_ID },
                        "properties": {
                            # "Nome" è la colonna principale (Titolo) nel tuo DB Notion
                            "Nome": {
                                "title": [{"text": {"content": attachment.filename}}]
                            },
                            # "Documento" è la colonna di tipo File
                            "Documento": {
                                "files": [
                                    {
                                        "name": attachment.filename,
                                        "type": "file_upload",
                                        "file_upload": {
                                            "id": file_upload_id
                                        }
                                    }
                                ]
                            }
                        }
                    }
                    
                    page_res = requests.post(page_url, headers=page_headers, json=page_data)
                    
                    if page_res.status_code == 200:
                        await message.channel.send("✅ Libreria aggiornata! PDF caricato con successo su Notion.")
                    else:
                        await message.channel.send("❌ Errore durante la creazione della riga nel Database.")
                        
                except Exception as e:
                    print(f"Errore: {e}")
                    await message.channel.send("❌ Si è verificato un errore imprevisto.")

client.run(DISCORD_TOKEN)
