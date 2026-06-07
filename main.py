import os
import random
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import certifi
import uvicorn
from dotenv import load_dotenv

# --- INITIALISIERUNG ---
load_dotenv()
app = FastAPI()

def get_db():
    uri = os.environ.get('MONGO_URI')
    if not uri:
        raise Exception("MONGO_URI ist nicht gesetzt!")
    client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())
    return client['mm-community']
    
db = get_db()
# --- KERN-MODULE (Die Intelligenz) ---
class SovereignOS_Kernel:
    def __init__(self, email):
        self.email = email

    def deinstalliere_malware(self):
        db.codes.update_one(
            {"email": self.email.lower().strip()},
            {"$unset": {"gefall_sucht_malware": "", "zustimmungs_algorithmus": ""}}
        )
        return "MALWARE_DEINSTALLIERT: Wahrheitsprotokolle aktiviert."

    def starte_realitaet_rendering(self):
        return {"mode": "REALITY_RENDERING_ACTIVE", "status": "Die Realität passt sich der inneren Frequenz an."}

# --- DIE ROUTEN (Der Zugang) ---

@app.get("/")
async def root():
    return {"status": "Sovereign OS Kernel Online", "mode": "REALITY_RENDERING_READY"}

@app.post("/boot-sovereign-os")
async def boot_os(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        os_kernel = SovereignOS_Kernel(email)
        log_1 = os_kernel.deinstalliere_malware()
        log_2 = os_kernel.starte_realitaet_rendering()
        return {"boot_log": [log_1, log_2], "system_status": "SOVEREIGN_OS_READY"}
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)

# --- START-SEQUENZ ---
if __name__ == "__main__":
    print(">>> INITIALISIERE GÖTTLICHE ALGORITHMUS-RESONANZ <<<")
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
