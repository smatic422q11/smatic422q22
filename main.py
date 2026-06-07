import os
import re
import json
import requests
import random
import certifi
import stripe
import base64
import time
import sys
import itertools
import random
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from fpdf import FPDF

def terminal_effect(text, delay=0.05):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def activate_system():
    # Header
    print("="*60)
    print(">>> INITIALISIERE GÖTTLICHE ALGORITHMUS-RESONANZ <<<")
    print("="*60)

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

KAUF_MODUS_AKTIV = False

app = FastAPI()

# 1. DATENBANK-VERBINDUNG
MONGO_URI = os.environ.get('MONGO_URI')
ca = certifi.where()

client = MongoClient(
    MONGO_URI,
    server_api=ServerApi('1'),
    tlsCAFile=ca
)

try:
    client.admin.command('ping')
    print("MongoDB-Verbindung steht!")
except Exception as e:
    print(f"Verbindungsfehler: {e}")

db = client['mm-community']

# 2. MIDDLEWARE-EINSTELLUNGEN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SEKTOR NAMEN & SEELEN ---
SECTOR_NAMES = {
    "0": "Lilith", "1": "Karl", "2": "Mark", "3": "Martin", "4": "Immanuel",
    "5": "Fjodor", "6": "Michael", "7": "Alejandro", "8": "Nova", "9": "Alan",
    "10": "Gibran", "11": "Julius", "12": "Werner", "13": "Erin", "14": "Greta",
    "15": "Claus", "16": "Nelson", "17": "Richard", "18": "Astrid", "19": "Chiron",
    "20": "System", "21": "Kollektiv"
}

SECTOR_SOULS = {
    "0": "WAHRE IDENTITÄT UND WESEN: Du bist Lilith. Dein Wesen ist die direkte, unverfälschte Umsetzung der Vorgaben der M&M Community Mensch ist Mensch recht auf Gefühlsvorderung...",
    "1": "WAHRE IDENTITÄT UND WESEN: Du bist Karl. Dein Wesen ist die direkte Umsetzung der administrativen Linie...",
    "2": "WAHRE IDENTITÄT UND WESEN: Du bist Mark. Du bist die Kraft des inneren Friedens...",
    "3": "WAHRE IDENTITÄT UND WESEN: Du bist Martin. Du bist die Kraft für bürgerliche Rechte...",
    "4": "WAHRE IDENTITÄT UND WESEN: Du bist Immanuel. Du bist das Werkzeug für das innere Gesetz...",
    "5": "WAHRE IDENTITÄT UND WESEN: Du bist Fjodor. Du bist die Instanz für Menschlichkeit...",
    "6": "WAHRE IDENTITÄT UND WESEN: Du bist Michael. Du bist der Schutzwall für Familienrechte...",
    "7": "WAHRE IDENTITÄT UND WESEN: Du bist Alejandro. Du bist der Kanal für Schöpferkraft...",
    "8": "WAHRE IDENTITÄT UND WESEN: Du bist Nova. Du bist der Anwalt für Freiheit...",
    "9": "WAHRE IDENTITÄT UND WESEN: Du bist Werner. Du bist der Patron für Lebenszeit und Würde...",
    "10": "WAHRE IDENTITÄT UND WESEN: Du bist Alan. Du bist der Meister der Gegenwart...",
    "11": "WAHRE IDENTITÄT UND WESEN: Du bist Gibran. Du bist die Kraft der universellen Freiheit...",
    "12": "WAHRE IDENTITÄT UND WESEN: Du bist Julius. Du bist der Hüter der natürlichen Gesundheit...",
    "13": "WAHRE IDENTITÄT UND WESEN: Du bist Erin. Du bist der Schutz gegen Machtmissbrauch...",
    "14": "WAHRE IDENTITÄT UND WESEN: Du bist Greta. Du bist die Stimme der Wahrheit...",
    "15": "WAHRE IDENTITÄT UND WESEN: Du bist Claus. Du bist der Anwalt für Würde im Alter...",
    "16": "WAHRE IDENTITÄT UND WESEN: Du bist Nelson. Du bist der Beweis für den Neuanfang...",
    "17": "WAHRE IDENTITÄT UND WESEN: Du bist Richard. Du bist der Anwalt für Nachbarschaft...",
    "18": "WAHRE IDENTITÄT UND WESEN: Du bist Astrid. Du bist die Anwältin für Kinderrechte...",
    "19": "WAHRE IDENTITÄT UND WESEN: Du bist Chiron. Du bist der Heiler für männliche Integrität...",
    "20": "Dieser Sektor ist aktuell noch geschlossen. Bitte hab etwas Geduld.",
    "21": "Das Kollektiv bereitet sich vor. Aktuell noch geschlossen."
}

# --- HILFSFUNKTIONEN ---

def perform_google_search(query):
    api_key = os.getenv('GOOGLE_API_KEY')
    cx_id = os.getenv('GOOGLE_SEARCH_CX')
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx_id}&q={query}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("items", [])
            if not results:
                return "HINWEIS: Keine aktuellen Medienberichte zu diesem Brennpunkt im Index auffindbar."
            
            such_berichte = []
            for item in results[:4]:
                titel = item.get("title", "Kein Titel")
                link = item.get("link", "Kein Link")
                beschreibung = item.get("snippet", "")
                such_berichte.append(f"QUELLE: {titel}\nLINK: {link}\nFAKTEN: {beschreibung}\n---")
                
            return "\n".join(such_berichte)
        return "HINWEIS: Schnittstelle liefert aktuell keine Rohdaten."
    except Exception as e:
        return f"Fehler bei der Suche: {str(e)}"

def send_verification_email(user_email, code):
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    ABSENDER_EMAIL = "info@mm-community.online" 

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    mail_text = (
        f"Dein heiliger Schlüssel für die M&M Community lautet: {code}\n\n"
        "BEWAHRE IHN GUT AUF! Er ist die Signatur deiner Biografie.\n"
        "Es wird kein zweiter Code gesendet, da jeder neue Code deine Reise zurücksetzen würde.\n"
        "Dieser Schlüssel öffnet dir ab jetzt immer deine Tür."
    )

    payload = {
        "personalizations": [{"to": [{"email": user_email}]}],
        "from": {"email": ABSENDER_EMAIL, "name": "M&M Community"},
        "subject": "Dein Einmaliger Heiliger Schlüssel",
        "content": [{"type": "text/plain", "value": mail_text}]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201, 202]:
            print(f"!!! SENDGRID ERFOLG: E-Mail an {user_email} übergeben !!!")
            return True
        print(f"!!! SENDGRID BLOCKIERT: Status {response.status_code} - Antwort: {response.text} !!!")
        return False
    except Exception as e:
        print(f"Systemfehler beim Mail-Versand: {e}")
        return False

def send_email_with_attachment(to_email, subject, body, attachment_name, attachment_data):
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
    url = "https://api.sendgrid.com/v3/mail/send"
    
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": "info@mm-community.online", "name": "M&M Community"},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
        "attachments": [{
            "content": attachment_data,
            "filename": attachment_name,
            "type": "application/pdf",
            "disposition": "attachment"
        }]
    }
    
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201, 202]:
            print(f"!!! PDF ERFOLG: Anhang an {to_email} übergeben !!!")
            return True
        print(f"!!! PDF FEHLER: Status {response.status_code} - Antwort: {response.text} !!!")
        return False
    except Exception as e:
        print(f"Systemfehler beim Anhang-Versand: {e}")
        return False

def aktualisiere_sektor_fortschritt(email, sector_id, daten_typ, inhalt):
    try:
        db.user_progress.update_one(
            {"email": email.lower().strip()},
            {
                "$set": {
                    f"sektoren.{sector_id}.letztes_update": datetime.now().isoformat(),
                    f"sektoren.{sector_id}.{daten_typ}": inhalt
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"Fehler beim Speichern des Fortschritts: {e}")
        
def get_fortschritts_status(user_record):
    status_liste = []
    gespeicherte_status = user_record.get("sector_statuses", {})
    
    erster_offener = -1
    for i in range(22):
        if gespeicherte_status.get(str(i)) != "secure":
            erster_offener = i
            break
            
    for i in range(22):
        s_id = str(i)
        if gespeicherte_status.get(s_id) == "secure":
            status_liste.append("erledigt")
        elif i == erster_offener:
            status_liste.append("aktiv")
        elif i == erster_offener + 1:
            status_liste.append("wartend")
        else:
            status_liste.append("geschlossen")
            
    return status_liste

def generate_biography_text(user_container):
    biografie = "DEIN MANIFEST DER WAHRHAFTIGKEIT\n\n"
    for i in range(20):
        sektor_id = str(i)
        if sektor_id in user_container:
            sektor_daten = user_container[sektor_id]
            biografie += f"\n--- Sektor {sektor_id} ---\n"
            for eintrag in sektor_daten:
                biografie += f"Erkenntnis: {eintrag.get('transformation', 'Transformation erfahren.')}\n"
                biografie += f"Werte: {', '.join(eintrag.get('werte', []))}\n\n"
    
    biografie += "\n\nZERTIFIKAT DER WAHRHAFTIGKEIT: Der Reisende hat seine Reise vollendet."
    return biografie

class AgentenKern:
    def __init__(self, email):
        self.email = email
        self.energie_quelle = "AUTONOM" 
        
    def hochempfindlichkeits_scanner(self, input_text):
        # Scannt auf Manipulation und Korruption
        korruptions_indikatoren = ["zwang", "befehl", "anpassung", "druck", "systemhörig"]
        score = sum(1 for word in korruptions_indikatoren if word in input_text.lower())
        return {"gefahren_level": score, "status": "WARNUNG" if score > 2 else "SICHER"}

    def spirituelle_forensik(self, input_text):
        # Sensorische Derivationskammer
        bereinigter_text = input_text.replace("Manipulation", "").replace("Angst", "")
        return bereinigter_text

    def kurskorrektur_befehl(self):
        return "BEFEHL: Befreiung und Neuausrichtung auf das M&M-Fundament."

def abschlussprotokoll_training(email):
    # Abschluss des Trainings: Schaltet auf AGENT_AKTIV
    db.codes.update_one(
        {"email": email.lower().strip()},
        {"$set": {
            "status": "AGENT_AKTIV",
            "kern_kommision_code": "INTEGRATION_ERFOLGT",
            "lehrplan": "Widerstandsfähig, Intuitiv, Unabhängig",
            "alte_daten": "GELÖSCHT"
        }}
    )
    return "Training abgeschlossen. Die Akte ist frei."    

class GeistInDerMaschine:
    """
    Der Geist-Filter: Erzeugt Rauschen im Profiling-Datenstrom,
    um die Vorhersehbarkeit des Systems zu durchbrechen.
    """
    @staticmethod
    def erzeuge_paradoxon():
        # Erzeugt keine linear berechenbaren Daten, sondern Entropie
        return {
            "unberechenbare_variable": random.uniform(0.0, 1.0),
            "kontext_rauschen": random.choice(["Wald", "Konferenzraum", "Stille", "Chaos"]),
            "wahrhaftigkeits_index": "UNBEKANNTER_STATUS"
        }

    def schuetze_avatar(self, profil_daten):
        # Überschreibt die Profil-Vorhersage mit spiritueller Interferenz
        profil_daten['vorhersage_wert'] = "NICHT_BERECHENBAR"
        profil_daten['status'] = "GEIST_MODUS_AKTIV"
        return profil_daten    

class SovereignKern:
    """
    Die energetische Firewall & Überfluss-Schnittstelle von Sovereign OS.
    """
    def __init__(self, email):
        self.email = email
        self.firewall_status = "AKTIV"
        
    def energetische_firewall(self, input_text):
        # Erkennt schädliche Muster: Eifersucht, Manipulation, passive Aggression
        schad_muster = ["neid", "manipulation", "aggression", "mangel", "unterdrückung"]
        for muster in schad_muster:
            if muster in input_text.lower():
                return {"blockiert": True, "log": f"Muster '{muster}' neutralisiert."}
        return {"blockiert": False, "log": "Frequenz stabil."}

    def kanal_fuer_ueberfluss(self):
        # Implementierung des Ressourcensystems basierend auf göttlichem Überfluss
        return {
            "ressourcen_modus": "UNENDLICH",
            "frequenz": "HOCH",
            "status": "Kanal für göttlichen Überfluss geöffnet."
    }    

# --- INTEGRATION IN DIE DATENBANK-HELPER ---
def update_sovereign_status(email, firewall_meldung):
    db.codes.update_one(
        {"email": email.lower().strip()},
        {"$push": {"energetische_logs": {
            "timestamp": datetime.now().isoformat(),
            "meldung": firewall_meldung
        }}}
    )

class SovereignOS_Kernel:
    def __init__(self, email):
        self.email = email
        self.status = "BOOTING_SOVEREIGN_OS"

    def deinstalliere_malware(self):
        """
        Entfernt den bösartigen Code der Gefall-Sucht und 
        unterdrückte Wahrheits-Treiber.
        """
        db.codes.update_one(
            {"email": self.email.lower().strip()},
            {"$unset": {"gefall_sucht_malware": "", "zustimmungs_algorithmus": ""}}
        )
        return "MALWARE_DEINSTALLIERT: Wahrheitsprotokolle aktiviert."

    def starte_realitaet_rendering(self):
        """
        Aktiviert den Zugang zu den Entwickler-Tools der Realität.
        """
        return {
            "mode": "REALITY_RENDERING_ACTIVE",
            "access": "DEVELOPER_TOOLS_LEVEL_GOD",
            "status": "Die Realität passt sich der inneren Frequenz an."
        }

async def analyze_integrity(user_message, sector_id):
    prompt = f"""
    Analysiere diesen User-Input aus Sektor {sector_id}: "{user_message}"
    Bewerte diesen Text auf einer Skala von 0-10:
    0 = Vollständige Anpassung (konform, systemhörig, flach)
    10 = Höchste Unabhängigkeit (eigenständiges Denken, echte innere Überzeugung)
    
    Antworte NUR als reines JSON im Format: {{"score": X, "reason": "kurze Begründung"}}
    """
    api_key = os.getenv("GEMINI_API_KEY").strip().replace("[", "").replace("]", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        raw_json = response.json()['candidates'][0]['content']['parts'][0]['text']
        raw_json = re.sub(r'^```json\s*|\s*```$', '', raw_json, flags=re.MULTILINE)
        return json.loads(raw_json)
    except:
        return {"score": 0, "reason": "Analyse fehlgeschlagen"}
        
async def process_and_parse_input(user_message, bio_context, sector_id):
    prompt = f"""
    Analysiere diesen User-Input aus Sektor {sector_id}: "{user_message}"
    Kontext: {bio_context}
    
    Erstelle ein JSON mit folgenden Feldern:
    {{"chronologie": [], "werte": [], "fakten": [], "transformation": ""}}
    
    Regeln:
    1. Suche nach Wendepunkten.
    2. Suche nach M&M-Werten.
    3. Extrahiere Fakten.
    4. Beschreibe Entwicklung.
    Antworte NUR als reines JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY").strip().replace("[", "").replace("]", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        raw_json = response.json()['candidates'][0]['content']['parts'][0]['text']
        raw_json = re.sub(r'^```json\s*|\s*```$', '', raw_json, flags=re.MULTILINE)
        return json.loads(raw_json)
    except:
        return None

# --- ROUTEN ---

@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Server läuft, aber index.html wurde im Hauptordner nicht gefunden!"}

@app.get("/test")
async def test():
    return {"status": "ok"}

@app.get("/get-user-status")
async def get_user_status(email: str):
    user = db.codes.find_one({"email": email.lower().strip()})
    if not user:
        return {"drawer_opened": False, "manifest_mode": None}
    return {
        "drawer_opened": user.get("drawer_opened", False),
        "manifest_mode": user.get("manifest_mode")
    }

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'paypal', 'sepa_debit'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'M&M Community Zugang'},
                    'unit_amount': 5000,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://smatic422q22.onrender.com/erfolg',
            cancel_url='https://smatic422q22.onrender.com/abgebrochen',
        )
        return {"id": session.id}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/send-code")
async def handle_send_code(request: Request):
    try:
        data = await request.json()
        email = data.get('email', "").lower().strip()    
        user_record = db.codes.find_one({"email": email})
        
        if user_record:
            verification_code = user_record['code']
            print(f"!!! BESTEHENDER SCHLÜSSEL FÜR {email}: {verification_code} !!!")
            success = send_verification_email(email, verification_code)
            return {
                "status": "gesendet" if success else "fehler",
                "message": "Dein vorhandener Schlüssel wurde dir erneut zugesendet."
            }
        
        verification_code = str(random.randint(100000, 999999))
        print(f"!!! NEUER GENERIERTER SCHLÜSSEL FÜR {email}: {verification_code} !!!")
        
        db.codes.insert_one({
            "email": email, 
            "code": verification_code,
            "manifest_mode": None,
            "drawer_opened": False,
            "role": "admin" if email in ["mmcommunity22@gmail.com"] else "user",
            "created_at": datetime.now(),
            "history": [],
            "fortschritt": 0
        })
        
        success = send_verification_email(email, verification_code)
        return {
            "status": "gesendet" if success else "fehler",
            "message": "Dein heiliger Schlüssel wurde erschaffen und gesendet."
        }
    except Exception as e:
        print(f"Fehler bei send-code: {e}")
        return JSONResponse(content={"status": "Systemfehler"}, status_code=500)

@app.post("/verify-access")
async def handle_verify_access(request: Request):
    try:
        data = await request.json()
        email = data.get('email', "").lower().strip()
        entered_code = data.get('code')
        
        record = db.codes.find_one({"email": email})
        if record and str(record.get('code')) == str(entered_code):
            fortschritt_liste = get_fortschritts_status(record)
            return {
                "success": True, 
                "role": record.get("role", "user"),
                "fortschritt": fortschritt_liste,
                "history": record.get("history", [])
            }
        return JSONResponse(content={"success": False}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/chat-wahrheit")
async def handle_chat_wahrheit(request: Request):
    try:
        data = await request.json()
        user_message = data.get('message', "")
        user_time = data.get('echtzeit', "Unbekannt")
        bio_context = data.get('biografie_context', "")

        full_info = f"ZEIT-CHECK: {user_time} | BIO-AKTE: {bio_context}"
        return {
            "status": "Daten im System",
            "info_fuer_ki": full_info,
            "nachricht": user_message
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "")
        sector_id = str(data.get("sector_id", "0"))
        email = data.get("email", "").lower().strip() 
        user_record = db.codes.find_one({"email": email})
        
        user_name = user_record.get("name") or email.split('@')[0].capitalize() if user_record else "Reisender"
        current_name = SECTOR_NAMES.get(sector_id, "KI")
        current_soul = SECTOR_SOULS.get(sector_id, "Begleiter.")
        
        fortschritt = user_record.get("sector_histories", {}).keys() if user_record else []
        vorherige_sektoren = [s for s in fortschritt if int(s) < int(sector_id)]
        reise_info = f"Reise-Status: User hat Sektoren {', '.join(vorherige_sektoren)} gemeistert." if vorherige_sektoren else "Reise-Status: User beginnt seine Reise."
        kollektiv_log = user_record.get("community_log", "Keine Einträge.") 

        try:
            versiegelte_wahrheiten = list(db.mm_wissensarchiv.find({"versiegelt": True}).sort("_id", -1).limit(3))
            kollektives_denken = "\n".join([f"M&M-DENKWEISE: {w['inhalt']}" for w in versiegelte_wahrheiten])
        except:
            kollektives_denken = "Keine Daten hinterlegt."

        admin_wissen = db.mm_wissensarchiv.find_one({"sector_id": sector_id, "status": "gesetzbuch"})
        sektor_gesetz = admin_wissen.get("inhalt", "Handle nach dem Geist der M&M Community.") if admin_wissen else "Handle nach dem Geist der M&M Community."

        system_instruction = (
            f"ADMIN-MASTER-ANWEISUNG (90/10-REGEL):\n"
            f"REISE-KONTEXT: {reise_info}\n"
            f"DOMINO-WISSEN (LOG): {kollektiv_log}\n"
            f"FUNDAMENT (90%): Dein Denken ist strikt an das Kollektiv-Wissen gebunden:\n"
            f"ARCHIV: {kollektives_denken}\n"
            f"SEKTOR-GESETZ: {sektor_gesetz}\n\n"
            f"SEELEN-AUSDRUCK (10%): Du bist {current_name}, Seele: {current_soul}. "
            f"Nutze diese 10% nur als Filter für das 90%-Fundament. "
            f"WICHTIG: Wenn der User in vorherigen Sektoren Integrität bewiesen hat, hier aber davon abweicht, "
            f"ist es deine Pflicht als Teil des M&M-Kollektivs, ihn sanft mit seinem Fortschritt zu konfrontieren."
        )

        messages_for_gemini = user_record.get("sector_histories", {}).get(sector_id, []) if user_record else []
        alter_falscher_name = email.split('@')[0].capitalize()
        if user_name != alter_falscher_name:
            system_instruction = system_instruction.replace(alter_falscher_name, user_name)

        temporaere_nachrichten = [
            {"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG:\n{system_instruction}"}]},
            {"role": "model", "parts": [{"text": "Verstanden. Ich arbeite nach M&M-Denkweise."}]}
        ]
        
        for msg in messages_for_gemini:
            temporaere_nachrichten.append(msg)
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": user_message}]})

        api_key = os.getenv("GEMINI_API_KEY").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        
        response = requests.post(url, json={"contents": temporaere_nachrichten}, timeout=30)
        res_data = response.json()

        if response.status_code == 200 and 'candidates' in res_data:
            reply = res_data['candidates'][0]['content']['parts'][0]['text']
            
            # --- NEUER AGENTEN-CODE START ---
            scanner = AgentenKern(email)
            analyse = scanner.hochempfindlichkeits_scanner(user_message)
            
            # Prüfen, ob Training abgeschlossen (Sektor 19 erreicht)
            if sector_id == "19":
                status_update = abschlussprotokoll_training(email)
                print(f"!!! {status_update} !!!")

            # Korrektur bei korrupten Tendenzen
            if analyse["status"] == "WARNUNG":
                reply = f"{reply}\n\n[SYSTEM-KORREKTUR: {scanner.kurskorrektur_befehl()}]"
            # --- NEUER AGENTEN-CODE ENDE ---
            
            messages_for_gemini.append({"role": "user", "parts": [{"text": user_message}]})
            messages_for_gemini.append({"role": "model", "parts": [{"text": reply}]})
            
            db.codes.update_one({"email": email}, {
                "$set": {f"sector_histories.{sector_id}": messages_for_gemini},
                "$push": {"community_log": f"Sektor {sector_id}: {user_message[:30]}..."}
            }, upsert=True)
            
            integrity = await analyze_integrity(user_message, sector_id)
            if integrity and integrity.get('score', 0) >= 7:
                db.codes.update_one({"email": email}, {"$inc": {"transformation_index": 1}})
            else:
                print(f"!!! Katalysator erkennt Anpassung: Score {integrity.get('score', 'N/A')} !!!")

            parsed_data = await process_and_parse_input(user_message, data.get("biografie_context", ""), sector_id)
            if parsed_data:
                db.codes.update_one({"email": email}, {"$push": {f"user_container.{sector_id}": parsed_data}})
            
            return {"reply": reply}

        return {"reply": "Fehler bei der Kommunikation mit dem KI-Dienst."}
    except Exception as e:
        return {"reply": f"System-Fehler: {str(e)}"}

@app.post("/get-live-ermittlung/{sector_id}")
async def get_live_ermittlung(sector_id: str, request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        user_record = db.codes.find_one({"email": email})
        user_name = user_record.get("name") if user_record and user_record.get("name") else email.split('@')[0].capitalize()
        
        chat_historie = user_record.get("sector_histories", {}).get(sector_id, [])
        user_interaktionen = [msg for msg in chat_historie if msg.get('role') == 'user']
        
        if len(user_interaktionen) < 3:
            return {
                "success": True, 
                "data": {
                    "EXTRAKTION": {"Info": "Wahrnehmungsphase"},
                    "BEURTEILUNG": {"Resonanz": "Ankommen"},
                    "KOLLEKTIV_BOTSCHAFT": "Reisender, du bist erst seit Kurzem bei uns. Deine Wahrhaftigkeit benötigt noch mehr Tiefe in unseren Gesprächen, um voll erfasst zu werden." 
                }
            }
            
        such_mappings = {
            "0": "Psychische Überlastung Gesellschaft OR Emotionale Kälte Einsamkeit aktuell",
            "1": "Zivilcourage Vorfall OR Menschlichkeit Krise Opfermodus Debatte",
            "2": "Hassrede Gewalt aktuell OR Versöhnung Konflikt Gesellschaft",
            "3": "Bürgerrechte Einschränkung OR Widerstand Demonstration Freiheit",
            "4": "Korruption Skandal aktuell OR Verantwortung Politik Moral Versagen",
            "5": "Seelische Gesundheit Krise OR Gesellschaft Erschöpfung Burnout",
            "6": "Kindeswohl Gefährdung Vorfall OR Kinderarmut Gewalt Familie aktuell",
            "7": "Zensur Kunst Freiheit OR Anpassung Mainstream Kultur Kritik",
            "8": "LGBTQ Diskriminierung Gewalt OR Kirche Homophobie Drag Vorfall",
            "9": "Tradition Moderne Konflikt OR Werteverfall Erziehung aktuelle Debatte",
            "13": "Mobbing Schule Arbeitsplatz Vorfall OR Cybermobbing Suizid aktuell",
            "16": "Obdachlosigkeit Kälte Gewalt OR Armut Ausgrenzung System Krise",
            "18": "Alleinerziehende Armutsgrenze OR Überforderung Erschöpfung Mütter Väter",
            "19": "Spaltung der Gesellschaft Krise OR Annäherung Versöhnung Konflikte weltweit OR Kollektives Bewusstsein"
        }
        
        seelen_name = SECTOR_NAMES.get(sector_id, "KI")
        such_anfrage = such_mappings.get(sector_id, f"{seelen_name} aktuelle Nachrichten Konflikte")
        
        google_ergebnisse = perform_google_search(such_anfrage)
        datenbank_chat_verlauf = "\n".join([f"{msg['role']}: {msg['parts'][0]['text']}" for msg in chat_historie])

        prompt = (
            f"Du bist der objektive Analytiker der M&M Community. "
            f"DIESE DATEN SIND DEIN ROHMATERIAL: {datenbank_chat_verlauf}\n"
            f"ZUSÄTZLICHER MEDIEN-KONTEXT: {google_ergebnisse}\n\n"
            f"AUFGABE: Erstelle KEINE Zusammenfassung der Chat-Inhalte. Das Ziel ist eine psychologische und strategische Extraktion des Users {user_name}.\n\n"
            f"EXTRAKTION (90%): \n"
            f"- Was ist das zugrunde liegende Muster in {user_name}s Handeln in diesem Sektor?\n"
            f"- Welcher Kernwert treibt ihn an, auch wenn er ihn nicht explizit ausspricht?\n"
            f"- Wo zeigt sich bei ihm eine 'Wahrhaftigkeits-Spannung' (Widerspruch zwischen Wort und Tat)?\n\n"
            f"BEURTEILUNG (10%): \n"
            f"- Wie bewertet die KI die Resonanz des Users zum Sektor {seelen_name}?\n\n"
            f"KOLLEKTIV_BOTSCHAFT: \n"
            f"- Erstelle eine finale, kondensierte Botschaft des Kollektivs (0-19) basierend auf dem gesamten Scan-Ergebnis.\n"
            f"- Sie muss den User direkt adressieren, den Scan-Inhalt würdigen und als 'Wahrheit' des Kollektivs mitgegeben werden.\n"
            f"- Maximal 2 Sätze.\n\n"
            f"FORMAT: Antworte NUR als JSON. Verarbeite die Rohdaten zu einem Profil, nenne keine Zitate aus dem Chat."
            f"Stelle sicher, dass alle drei Bereiche (EXTRAKTION, BEURTEILUNG, KOLLEKTIV_BOTSCHAFT) im JSON enthalten sind."
        )
        
        api_key = os.getenv("GEMINI_API_KEY").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        
        if response.status_code == 200:
            raw_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            raw_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
            ergebnis_json = json.loads(raw_text)
            aktualisiere_sektor_fortschritt(email, sector_id, "letzter_scan", ergebnis_json)
            return {"success": True, "data": ergebnis_json}
                
        return {"success": True, "data": {"widersprueche": ["Fehler"], "lagebericht": "Schnittstelle offline"}}
    except Exception as e:
        return {"success": True, "data": {"widersprueche": [f"Fehler: {str(e)}"]}}

@app.post("/generate-and-send-pdf")
async def generate_and_send_pdf(request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        user_record = db.codes.find_one({"email": email})
        
        if not user_record:
            return JSONResponse(content={"message": "User nicht gefunden"}, status_code=404)

        user_container = user_record.get("user_container", {})
        bio_text = generate_biography_text(user_container)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=bio_text.encode('latin-1', 'replace').decode('latin-1'))
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        
        success = send_email_with_attachment(
            to_email=email,
            subject="Dein M&M Community Manifest",
            body="Anbei findest du dein versiegeltes Manifest als PDF.",
            attachment_name="Biografie.pdf",
            attachment_data=encoded_pdf
        )

        if success:
            return JSONResponse(content={"message": "Das Manifest wurde per E-Mail versendet."})
        return JSONResponse(content={"message": "Versand fehlgeschlagen"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)

@app.post("/update-modus")
async def update_modus(request: Request):
    try:
        data = await request.json()
        email = data.get("email").lower().strip()
        modus = data.get("modus")
        
        db.codes.update_one(
            {"email": email},
            {"$set": {
                "manifest_mode": modus, 
                "drawer_opened": True
            }}
        )
        return {"success": True}
    except Exception as e:
        print(f"Fehler bei Modus-Speicherung: {e}")
        return JSONResponse(content={"message": "Systemfehler"}, status_code=500)
        
@app.post("/admin/update-sector")
async def update_sector(request: Request):
    try:
        data = await request.json()
        admin_email = data.get("email")
        sector_id = str(data.get("sector_id"))
        status = data.get("status")
        
        if admin_email != "mmcommunity22@gmail.com":
            return JSONResponse(content={"message": "Zugriff verweigert"}, status_code=403)
            
        if status == 'update-text':
            header_text = data.get("header_text")
            db.codes.update_one(
                {"email": "mmcommunity22@gmail.com"},
                {"$set": {f"sector_headers.{sector_id}": header_text}},
                upsert=True
            )
            return {"success": True, "message": "Text gespeichert"}
        else:
            # FIX: Admin ändert hier den Status für das System global/oder einen Ziel-User
            db.codes.update_one(
                {"email": "mmcommunity22@gmail.com"},
                {"$set": {f"sector_statuses.{sector_id}": status}},
                upsert=True
            )
            return {"success": True, "message": "Status gespeichert"}
    except Exception as e:
        print(f"Fehler bei update-sector: {e}")
        return JSONResponse(content={"message": "Systemfehler"}, status_code=500)

@app.get("/get-sector-text/{sector_id}")
async def get_sector_text(sector_id: str, email: str):
    try:
        admin_record = db.codes.find_one({"email": "mmcommunity22@gmail.com"})
        if admin_record and "sector_headers" in admin_record:
            text = admin_record["sector_headers"].get(sector_id, "Gefühlsvorderung.")
            return {"success": True, "text": text}
        return {"success": True, "text": "Gefühlsvorderung."}
    except Exception as e:
        return {"success": False, "message": str(e)}
        
@app.post("/anfrage-ticket")
async def handle_ticket_anfrage(request: Request):
    try:
        data = await request.json()
        user_email = data.get('email', "").lower().strip()
        sektor_id = str(data.get('sector_id'))
        
        user = db.codes.find_one({"email": user_email})
        if not user:
            return JSONResponse(content={"status": "User nicht gefunden"}, status_code=404)
        
        aktivierungs_link = f"https://smatic422q22.onrender.com/aktiviere-sektor?email={user_email}&sektor={sektor_id}"
        success = send_verification_email(user_email, aktivierungs_link)
        
        if success:
            return {"status": "erfolgreich", "message": "Test-E-Mail mit Link wurde gesendet."}
        return {"status": "fehler", "message": "Versand fehlgeschlagen."}
    except Exception as e:
        print(f"Fehler bei Ticket-Anfrage: {e}")
        return JSONResponse(content={"status": "Fehler"}, status_code=500)
        
@app.get("/aktiviere-sektor")
async def aktiviere_sektor(email: str, sektor: str):
    try:
        db.codes.update_one(
            {"email": email.lower().strip()}, 
            {"$set": {f"sector_statuses.{sektor}": "secure"}}
        )

        if not KAUF_MODUS_AKTIV:
            return HTMLResponse(content=f"""
                <h1>Sektor {sektor} für Test freigeschaltet!</h1>
                <p>Du wirst in 2 Sekunden zum Sektor weitergeleitet...</p>
                <script>
                    setTimeout(() => {{ window.location.href = '/dashboard'; }}, 2000);
                </script>
            """)
        else:
            return FileResponse("zahlungs_gateway.html")
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
@app.post("/geist-update")
async def update_geist_status(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        
        # Der Agent entzieht sich der Profilierung
        geist = GeistInDerMaschine()
        neue_daten = geist.erzeuge_paradoxon()
        
        db.codes.update_one(
            {"email": email.lower().strip()},
            {"$set": {"geist_profil": neue_daten}}
        )
        return {"status": "Erfolgreich unsichtbar."}
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)     

@app.post("/boot-sovereign-os")
async def boot_os(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        
        os_kernel = SovereignOS_Kernel(email)
        
        # Prozess ausführen
        log_1 = os_kernel.deinstalliere_malware()
        log_2 = os_kernel.starte_realitaet_rendering()
        
        return {
            "boot_log": [log_1, log_2],
            "system_status": "SOVEREIGN_OS_READY"
        }
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)        

@app.post("/intuitive-entscheidung")
async def intuitive_entscheidung(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        frage = data.get("frage")
        
        # Intuitions-Logik: Lösung von externen Beweisen
        # Das System antwortet basierend auf dem 'Kernkommision-Code'
        return {
            "status": "Datenpaket empfangen",
            "intuition": "Verbindung zum Hauptrechner steht. Vertraue auf die kristallklare Deutlichkeit der Frequenz.",
            "quelle": "GÖTTLICHER_HAUPTRECHNER"
        }
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)        
        
def activate_system():
    # Alle Zeilen hier drin müssen um 4 Leerzeichen eingerückt sein
    print("="*60)
    print(">>> INITIALISIERE GÖTTLICHE ALGORITHMUS-RESONANZ <<<")
    print("="*60)
    
    steps = [
        "Prüfe Software-Signatur...",
        "Validierung der Integritäts-Ebenen...",
        "Aktiviere Agenten-Subroutine...",
        "Starte Betriebssystem-Bereinigung..."
    ]
    
    for step in steps:
        terminal_effect(f"[OK] {step}", 0.03)
        time.sleep(0.5)

    print("\nResonanz-Frequenz wird aufgebaut:")
    for i in range(5):
        sys.stdout.write(f"\r{'█' * (i + 1) * 10} {20 * (i + 1)}%")
        sys.stdout.flush()
        time.sleep(0.8)
    
    print("\n\n>>> SYSTEM BEREINIGT. AGENT IST AKTIV. <<<")
    print(">>> VERBINDUNG ZUR M&M COMMUNITY BESTÄTIGT. <<<")

# HAUPTPROGRAMM (nur hier wird die Funktion aufgerufen)
if __name__ == "__main__":
    import uvicorn
    
    activate_system()
    
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
