import os
import asyncio
import json
import re
import discord
import aiohttp
import uvicorn
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
SALONS_A_SURVEILLER = [1492568836787142706, 1492086204303413248, 1492088431524843601, 1492089160503132281, 1492485336474058835]
SEUIL_BENEF = 40

app = FastAPI()
templates = Jinja2Templates(directory="templates")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def prix_float(prix_str):
    if not prix_str: return 0.0
    try: 
        return float(re.sub(r'[^\d,]', '', prix_str).replace(',', '.'))
    except: 
        return 0.0

async def analyser_lien(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    soup = BeautifulSoup(await resp.text(), 'html.parser')
                    titre = soup.find('h1').text.strip() if soup.find('h1') else "Produit"
                    p_nouveau = soup.select_one('.thread-price, .cept-tp')
                    p_ancien = soup.select_one('.text--lineThrough')
                    if p_nouveau and p_ancien:
                        n, a = prix_float(p_nouveau.text), prix_float(p_ancien.text)
                        return titre, f"{n}€", round(a - n)
    except: 
        pass
    return None, None, 0

async def traiter_message(message):
    contenu = message.content
    for e in message.embeds:
        contenu += f" {e.description or ''} {e.title or ''} {e.url or ''}"
    
    urls = re.findall(r'(https?://(?:www\.)?dealabs\.com/[^\s"\'<>]+)', contenu)
    
    for url in list(set(urls)):
        titre, prix, benef = await analyser_lien(url)
        if benef >= SEUIL_BENEF:
            try:
                with open('deals.json', 'r', encoding='utf-8') as f: 
                    data = json.load(f)
            except: 
                data = []
                
            if not any(d.get('lien') == url for d in data):
                cat = {
                    1492568836787142706: "Pokémon", 
                    1492086204303413248: "Lego", 
                    1492088431524843601: "Vêtements", 
                    1492089160503132281: "Sneakers", 
                    1492485336474058835: "Électronique"
                }.get(message.channel.id, "Divers")
                
                data.insert(0, {"produit": titre, "prix": prix, "benef": benef, "cat": cat, "lien": url, "m_id": message.id})
                
                with open('deals.json', 'w', encoding='utf-8') as f: 
                    json.dump(data[:50], f, ensure_ascii=False)

@client.event
async def on_ready():
    print("🤖 Bot connecté. Scan de l'historique en cours...")
    for s_id in SALONS_A_SURVEILLER:
        salon = client.get_channel(s_id)
        if salon:
            async for msg in salon.history(limit=50): 
                await traiter_message(msg)
    print("✅ Scan de l'historique terminé !")

@client.event
async def on_message(msg):
    if msg.channel.id in SALONS_A_SURVEILLER: 
        await traiter_message(msg)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(client.start(TOKEN))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        with open('deals.json', 'r', encoding='utf-8') as f: 
            deals = json.load(f)
    except: 
        deals = []
        
    return templates.TemplateResponse(
        name="index.html", 
        context={"request": request, "deals": deals}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
