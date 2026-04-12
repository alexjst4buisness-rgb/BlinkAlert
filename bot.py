import discord
import aiohttp
from bs4 import BeautifulSoup
import json
import re
import asyncio

# --- CONFIGURATION ---
TOKEN = "MTQ5MjkxMTY3NTgxNTQ5MzkxNA.G_aK8H.rYwV8kloyPQMUhSWLYa1Pkc1BukmOfEpSXq2y8" # Ton Token
SALONS_A_SURVEILLER = [1492568836787142706, 1492086204303413248, 1492088431524843601, 1492089160503132281, 1492485336474058835]
SEUIL_BENEF = 40 # On passe à 40€ comme demandé

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

def prix_float(prix_str):
    if not prix_str: return 0.0
    try:
        return float(re.sub(r'[^\d,]', '', prix_str).replace(',', '.'))
    except: return 0.0

def mettre_a_jour_json(data):
    with open('deals.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def detecter_categorie(channel_id):
    mapping = {1492568836787142706: "Pokémon", 1492086204303413248: "Lego", 
               1492088431524843601: "Vêtements", 1492089160503132281: "Sneakers", 1492485336474058835: "Électronique"}
    return mapping.get(channel_id, "Divers")

async def analyser_lien(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    soup = BeautifulSoup(await resp.text(), 'html.parser')
                    titre = soup.find('h1').text.strip() if soup.find('h1') else "Produit sans titre"
                    p_nouveau = soup.select_one('.thread-price, .cept-tp')
                    p_ancien = soup.select_one('.text--lineThrough')
                    if p_nouveau and p_ancien:
                        n = prix_float(p_nouveau.text)
                        a = prix_float(p_ancien.text)
                        return titre, f"{n}€", round(a - n)
    except: pass
    return None, None, 0

async def traiter_message(message):
    # 1. On récupère TOUT le texte (message + embeds)
    contenu_complet = message.content
    for embed in message.embeds:
        if embed.description: contenu_complet += f" {embed.description}"
        if embed.title: contenu_complet += f" {embed.title}"
        if embed.url: contenu_complet += f" {embed.url}"
    
    # 2. On cherche les liens Dealabs
    urls = re.findall(r'(https?://(?:www\.)?dealabs\.com/[^\s"\'<>]+)', contenu_complet)
    
    for url in list(set(urls)): # set() pour éviter de scanner 2 fois le même lien
        titre, prix, benef = await analyser_lien(url)
        if benef >= SEUIL_BENEF:
            try:
                with open('deals.json', 'r', encoding='utf-8') as f: data = json.load(f)
            except: data = []
            
            if not any(d.get('lien') == url for d in data):
                cat = detecter_categorie(message.channel.id)
                data.insert(0, {"produit": titre, "prix": prix, "benef": benef, "cat": cat, "lien": url, "m_id": message.id})
                mettre_a_jour_json(data[:100])
                print(f"✅ Ajouté (+{benef}€) : {titre[:50]}...")

@client.event
async def on_ready():
    print(f"🚀 Scan profond lancé...")
    for s_id in SALONS_A_SURVEILLER:
        salon = client.get_channel(s_id)
        if salon:
            print(f"🔎 Analyse de #{salon.name} (200 derniers messages)...")
            async for msg in salon.history(limit=200): # On monte à 200 pour ne rien rater
                await traiter_message(msg)
    print("✨ Ton site est maintenant synchronisé !")

@client.event
async def on_message(message):
    if message.channel.id in SALONS_A_SURVEILLER:
        await traiter_message(message)

@client.event
async def on_raw_message_delete(payload):
    try:
        with open('deals.json', 'r', encoding='utf-8') as f: data = json.load(f)
        nouvelle_data = [d for d in data if d.get('m_id') != payload.message_id]
        if len(data) != len(nouvelle_data):
            mettre_a_jour_json(nouvelle_data)
    except: pass

client.run(TOKEN)