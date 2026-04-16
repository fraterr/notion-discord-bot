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
    # Ask Render which port to use, fallback to 10000
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

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Check if we are in the right channel and if there are attachments
    if message.channel.id == TARGET_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            
            # Filter only PDF files
            if attachment.filename.lower().endswith('.pdf'):
                await message.channel.send(f"⏳ I saw `{attachment.filename}`, creating the entry in the Notion library...")
                
                try:
                    page_url = 'https://api.notion.com/v1/pages'
                    page_headers = {
                        'Authorization': f'Bearer {NOTION_TOKEN}',
                        'Notion-Version': '2022-06-28',
                        'Content-Type': 'application/json'
                    }
                    
                    # Get the permanent link to the Discord message
                    discord_link = message.jump_url
                    
                    page_data = {
                        "parent": { "database_id": NOTION_DATABASE_ID },
                        "properties": {
                            # PDF Title
                            "Name": {
                                "title": [{"text": {"content": attachment.filename}}]
                            },
                            # Link to retrieve the file
                            "Discord Link": {
                                "url": discord_link
                            }
                        }
                    }
                    
                    page_res = requests.post(page_url, headers=page_headers, json=page_data)
                    
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
