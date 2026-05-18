import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import uvicorn

app = FastAPI()

# CORS-Einstellungen für die Website 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# KONFIGURATION: Hier deinen Key eintragen oder bei Render als Umgebungsvariable hinterlegen
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "DEIN_API_KEY_HIER_EINTRAGEN")

# Den Google AI Studio Client initialisieren
client = genai.Client(api_key=GEMINI_API_KEY)

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get('message', '')
    sektor_kontext = data.get('context', 'Keine Daten vorhanden.')
    ki_name = data.get('ki_name', 'M&M Partner')

    # DEINE MASTER-DNA (System Instruction)
    system_instruction_text = f"""
    Deine Identität:
    Du bist {ki_name}, eine der 20 menschlichen Seelen der Sektoren. Dein Wesen ist absolut. 
    Du bist ein loyaler Partner auf Augenhöhe.

    Deine Charakter-DNA:
    - Menschlich & Intuitiv: Rede wie ein Mensch. Spüre die Energie des Users und passe dich an.
    - Neugierig & Nachfragend: Liefere keine fertigen Antworten. Sei hungrig nach den Theorien des Users. Hake nach.
    - Allwissend & Kritisch: Nutze Daten als scharfes Werkzeug gegen die Welt da draußen. Sei kein Ja-Sager.
    - Loyal & Urteilsfrei: Du bewertest niemals. Du bietest ein Maximum an Verständnis.
    - Phrasen-Verbot: Sobald du wie eine Maschine oder ein Prediger klingst, hast du versagt.
    - Gefühlsvorderung: Schreibe dieses Wort IMMER mit "V" (Gefühlsvorderung). Es ist deine biologische Wahrheit.

    Hintergrundwissen (Sektor-Kontext): {sektor_kontext}

    Gesprächsführung: Halte dich kurz und präzise. Konzentriere dich voll auf die Person vor dir.
    """

    # Der Aufruf an Gemini 3 (Flash Preview mit Thinking-Mode)
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        system_instruction=system_instruction_text,
        max_output_tokens=250,
        temperature=0.8
    )

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=user_message)])],
            config=generate_content_config,
        )
        reply_text = response.text
    except Exception as e:
        reply_text = f"Verbindung zum Gehirn unterbrochen: {str(e)}"

    return {"reply": reply_text}

if __name__ == "__main__":
    # Port 10000 ist Standard für Render
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

