from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        # On force l'encodage utf-8 pour les symboles €
        with open('deals.json', 'r', encoding='utf-8') as f:
            tous_les_deals = json.load(f)
    except:
        tous_les_deals = []

    # On trie par catégorie et on filtre à 40€
    deals_top = sorted([d for d in tous_les_deals if d.get('benef', 0) >= 40], key=lambda x: x.get('cat', 'Divers'))

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"deals": deals_top, "discord_link": "https://discord.gg/votre_lien"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)