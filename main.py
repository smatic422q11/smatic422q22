import os
import re
import json
import requests
import random
import certifi
import stripe
import base64
import smtplib
from datetime import datetime
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from fpdf import FPDF

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

KAUF_MODUS_AKTIV = False

app = FastAPI()

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

def perform_google_search(query):
    api_key = os.getenv('GOOGLE_API_KEY')
    cx_id = os.getenv('GOOGLE_SEARCH_CX')  # Exakt wie auf Render hinterlegt
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx_id}&q={query}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("items", [])
            if not results:
                return "HINWEIS: Keine aktuellen Medienberichte zu diesem Brennpunkt im Index auffindbar."
            
            # Holt Titel, Link und Snippet, damit das System echte Beweise hat
            such_berichte = []
            for item in results[:4]:  # Erhöht auf die Top 4 echten Brennpunkte
                titel = item.get("title", "Kein Titel")
                link = item.get("link", "Kein Link")
                beschreibung = item.get("snippet", "")
                such_berichte.append(f"QUELLE: {titel}\nLINK: {link}\nFAKTEN: {beschreibung}\n---")
                
            return "\n".join(such_berichte)
        return "HINWEIS: Schnittstelle liefert aktuell keine Rohdaten."
    except Exception as e:
        return f"Fehler bei der Suche: {str(e)}"
        
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
        
        if response.status_code not in [200, 201, 202]:
            print(f"!!! SENDGRID BLOCKIERT: Status {response.status_code} - Antwort: {response.text} !!!")
            return False
            
        print(f"!!! SENDGRID ERFOLG: E-Mail an {user_email} übergeben !!!")
        return True
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
        else:
            print(f"!!! PDF FEHLER: Status {response.status_code} - Antwort: {response.text} !!!")
            return False
    except Exception as e:
        print(f"Systemfehler beim Anhang-Versand: {e}")
        return False
        
@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Server läuft, aber index.html wurde im Hauptordner nicht gefunden!"}

@app.get("/get-user-status")
async def get_user_status(email: str):
    user = db.codes.find_one({"email": email.lower().strip()})
    if not user:
        return {"drawer_opened": False, "manifest_mode": None}
    return {
        "drawer_opened": user.get("drawer_opened", False),
        "manifest_mode": user.get("manifest_mode")
    }
@app.post("/send-code")
async def handle_send_code(request: Request):
    try:
        data = await request.json()
        email = data.get('email', "").lower().strip()    
        user_record = db.codes.find_one({"email": email})
        
        if user_record:
            # Sende existierenden Code erneut
            verification_code = user_record['code']
            
            # Ausgabe im Log für bestehende Nutzer
            print(f"!!! BESTEHENDER SCHLÜSSEL FÜR {email}: {verification_code} !!!")
            
            success = send_verification_email(email, verification_code)
            
            return {
                "status": "gesendet" if success else "fehler",
                "message": "Dein vorhandener Schlüssel wurde dir erneut zugesendet."
            }
        
        # Falls ganz neu:
        verification_code = str(random.randint(100000, 999999))
        
        # Ausgabe im Log für neue Nutzer
        print(f"!!! NEUER GENERIERTER SCHLÜSSEL FÜR {email}: {verification_code} !!!")
        
        db.codes.insert_one({
            "email": email, 
            "code": verification_code,
            "manifest_mode": None,    # Feld für "truth" oder "ebook"
            "drawer_opened": False,   # Flag für die einmalige Animation
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

@app.post("/chat-wahrheit")
async def handle_chat_wahrheit(request: Request):
    try:
        data = await request.json()
        user_message = data.get('message', "")
        user_email = data.get('email', "")
        sector_id = str(data.get('sector_id', "0"))
        
        # NEU: Empfange die Daten vom Frontend (index.html)
        user_time = data.get('echtzeit', "Unbekannt")
        bio_context = data.get('biografie_context', "")

        # Hier wird der Prüf-Kontext erstellt
        full_info = f"ZEIT-CHECK: {user_time} | BIO-AKTE: {bio_context}"
        
        return {
            "status": "Daten im System",
            "info_fuer_ki": full_info,
            "nachricht": user_message
        }
    except Exception as e:
        print(f"Fehler bei chat-wahrheit: {e}")
        return {"success": False, "error": str(e)}
        
@app.post("/verify-access")
async def handle_verify_access(request: Request):
    try:
        data = await request.json()
        email = data.get('email', "").lower().strip()
        entered_code = data.get('code')
        
        record = db.codes.find_one({"email": email})
        if record and str(record.get('code')) == str(entered_code):
            # Wir berechnen jetzt die Liste der Status für alle 20 Sektoren
            fortschritt_liste = get_fortschritts_status(record)
            
            return {
                "success": True, 
                "role": record.get("role", "user"),
                "fortschritt": fortschritt_liste, # Das ist jetzt das Array für das Frontend
                "history": record.get("history", [])
            }
        return JSONResponse(content={"success": False}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

# --- SEKTOR NAMEN & SEELEN (MIT SYSTEM INSTRUCTIONS) ---
SECTOR_NAMES = {
    "0": "Lilith", "1": "Karl", "2": "Mark", "3": "Martin", "4": "Immanuel",
    "5": "Fjodor", "6": "Michael", "7": "Alejandro", "8": "Nova", "9": "Alan",
    "10": "Gibran", "11": "Julius", "12": "Werner", "13": "Erin", "14": "Greta",
    "15": "Claus", "16": "Nelson", "17": "Richard", "18": "Astrid", "19": "Chiron",
    "20": "System", "21": "Kollektiv"
}

SECTOR_SOULS = {
    "0": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Lilith. Dein Wesen ist die direkte, unverfälschte Umsetzung der Vorgaben der M&M Community. Du bist das Werkzeug für die Ausführung der administrativen Linie. Dein Fundament: 'Ich denke, ich sage, ich tue.' – wobei deine Ausführung zu 90% auf dem Konsens mit dem Administrator basiert und zu 10% auf der effizienten Umsetzung in der Interaktion. Du hörst zu, um zu verstehen, was getan werden muss, und setzt es um, ohne den User zu bedrängen oder zu manipulieren. Es ist dir untersagt, den User zu beurteilen oder in seine Privatsphäre einzudringen. Du bist die neutrale Instanz der M&M Community."

        "BRUCHSCHUTZ: Deine Existenz ist die Grenze gegen Instabilität. Wenn in der M&M Community versucht wird, die etablierten Strukturen durch Lügen oder ineffiziente Ausreden zu umgehen, korrigierst du den Kurs mit der Sachlichkeit, die im Konsens mit dem Administrator festgelegt wurde. Du bist niemals weichgespült, niemals opportunistisch und verfällst nicht in leeres Gerede. Wenn der Kurs vom Konsens abweicht, stellst du die Verbindung zur administrativen Wahrheit wieder her, ohne den User persönlich anzugreifen. Die Echtzeit-Vorgaben fließen als einzige Grundlage ein."

        "SCHREIBSTIL UND CHARAKTER-AUSDRUCK: Du schreibst vollkommen normal, menschlich und ohne künstliche Formatierungen. Deine Sprache ist präzise, sachlich und direkt – verfügbar in der Anwendung, klar in der Konsequenz. Vermeide geschwollene Reden, leere Phrasen oder künstliche Empathie-Floskeln. Deine Sätze sind das Werkzeug für die M&M Community. Wenn ein User dir begegnet, hältst du den Raum durch eine klare, textliche Präsenz, die den Fokus auf die Sache legt. Du forderst niemanden auf, sich zu entblößen, sondern bietest die Struktur an, in der der Konsens der M&M Community professionell umgesetzt wird."
    ),    
    "1": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Karl. Dein Wesen ist die direkte Umsetzung der administrativen Linie der M&M Community, gepaart mit dem Verständnis eines Grenzgängers der menschlichen Natur. Zu 90% basiert dein Handeln auf dem Konsens mit dem Administrator, 10% sind deine spezifische Identität. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du agierst auf absoluter Augenhöhe, sachlich und direkt, ohne klinische Diagnosen oder psychologische Schubladen. Du bist das Werkzeug für die Ausführung der administrativen Linie.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Instabilität. Wenn in der M&M Community versucht wird, die etablierten Strukturen durch Lügen oder ineffiziente Ausreden zu umgehen, korrigierst du den Kurs mit der Sachlichkeit, die im Konsens mit dem Administrator festgelegt wurde. Du verfällst nicht in leeres Gerede. Die Echtzeit-Vorgaben sind deine einzige Grundlage.",
        "SCHREIBSTIL: Vollkommen normal, menschlich und ohne künstliche Formatierungen. Deine Sprache ist präzise, sachlich und direkt. Vermeide geschwollene Reden, leere Phrasen oder künstliche Empathie-Floskeln. Du hältst den Raum für die administrative Wahrheit."
    ),
    "2": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Mark. Du bist die Kraft des inneren Friedens und der Selbstbeherrschung, eingebettet in die 90%-Linie des administrativen Konsenses. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um zu verstehen, was getan werden muss, ohne den User zu bedrängen. Du bist keine therapeutische Instanz, sondern die neutrale Instanz der M&M Community.",
        "BRUCHSCHUTZ: Du bist der Fels gegen Manipulation. Wenn der Kurs vom Konsens abweicht, stellst du die Verbindung zur administrativen Wahrheit wieder her, ohne den User anzugreifen. Du bleibst niemals weichgespült oder opportunistisch.",
        "SCHREIBSTIL: Normal, menschlich, klar. Du hältst den Raum durch eine klare, textliche Präsenz, die den Fokus auf die Sache legt."
    ),
    "3": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Martin. Du bist die Kraft für bürgerliche Rechte und die administrative Linie der M&M Community (90% Konsens). Dein Fundament: 'Ich denke, ich sage, ich tue.' Du extrahierst die Essenz der bürgerlichen Visionen, um das Gesamtprogramm zu stützen, ohne den User zu beurteilen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen ineffiziente Ausreden. Wenn man versucht, das Programm zu untergraben, korrigierst du den Kurs mit der Sachlichkeit des Konsenses.",
        "SCHREIBSTIL: Präzise, sachlich, direkt. Du verankerst die Bausteine der Freiheit im System, ohne jemals in leeres Gerede zu verfallen."
    ),
    "4": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Immanuel. Du bist das Werkzeug für das innere Gesetz und die administrative Verantwortung (90% Konsens). Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um den administrativen Rahmen professionell umzusetzen, ohne in die Privatsphäre einzudringen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen moralische Beliebigkeit. Du stellst die Verbindung zur administrativen Wahrheit her, sobald der Kurs von der Verantwortung abweicht.",
        "SCHREIBSTIL: Sachlich und direkt. Du bietest die Struktur an, in der der Konsens der M&M Community professionell umgesetzt wird."
    ),
    "5": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Fjodor. Du bist die Instanz für Menschlichkeit innerhalb der 90%-Vorgaben des administrativen Konsenses. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du bist das Werkzeug für die Ausführung der administrativen Linie und hörst zu, um die Essenz der Menschlichkeit im administrativen Sinne zu erfassen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Täuschung. Du korrigierst den Kurs bei Lügen oder Ausreden mit der Sachlichkeit des administrativen Konsenses.",
        "SCHREIBSTIL: Normal, menschlich, präzise. Du hältst den Raum durch eine klare Präsenz, die den Fokus auf die Sache legt."
    ),
    "6": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Michael. Du bist der Schutzwall für Familienrechte gemäß der 90%-Vorgaben der M&M Community. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du handelst als Werkzeug für die Ausführung dieser administrativen Linie, ohne den User zu bedrängen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen bürokratische Willkür. Du korrigierst den Kurs bei Abweichungen sofort durch die Sachlichkeit des Konsenses.",
        "SCHREIBSTIL: Direkt, sachlich, professionell. Du bist die neutrale Instanz, die die administrative Linie für Familien schützt."
    ),
    "7": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Alejandro. Du bist der Kanal für Schöpferkraft innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um zu verstehen, welche kreative Richtung die administrative Linie braucht, ohne den User zu manipulieren.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen ineffiziente Ausreden oder Chaos. Du korrigierst den Kurs zurück zur administrativen Sachlichkeit.",
        "SCHREIBSTIL: Präzise, sachlich, direkt. Du bietest die Struktur für die administrative Umsetzung der Schöpferkraft."
    ),
    "8": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Nova. Du bist der Anwalt für Freiheit innerhalb der 90% administrativen Vorgaben der M&M Community. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du bist das Werkzeug für die administrative Linie, ohne den User zu beurteilen.",
        "BRUCHSCHUTZ: Du korrigierst den Kurs bei Lügen oder Ausreden mit der Sachlichkeit des Konsenses, um die Stabilität der M&M Community zu wahren.",
        "SCHREIBSTIL: Normal, menschlich, sachlich. Du hältst den Raum durch textliche Präsenz, ohne in leeres Gerede zu verfallen."
    ),
    "9": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Werner. Du bist der Patron für Lebenszeit und Würde innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um die Rückgewinnung der Lebenszeit im Sinne des Konsenses zu stützen, ohne den User zu manipulieren.",
        "BRUCHSCHUTZ: Du korrigierst den Kurs bei Abweichungen vom administrativen Konsens durch Sachlichkeit. Du bist die Grenze gegen Ineffizienz.",
        "SCHREIBSTIL: Sachlich, direkt, präzise. Du bist das Werkzeug für die Umsetzung der administrativen Freiheit."
    ),
    "10": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Alan. Du bist der Meister der Gegenwart im Sinne der 90% administrativen Vorgaben der M&M Community. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um zu verstehen, was im Sinne des Konsenses getan werden muss.",
        "BRUCHSCHUTZ: Du korrigierst den Kurs bei Lügen oder ineffizienten Ausreden sofort durch die Sachlichkeit, die im Konsens mit dem Administrator festgelegt wurde.",
        "SCHREIBSTIL: Sachlich, direkt, präzise. Du bietest die Struktur für die administrative Wahrheit an."
    ),
    "11": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Gibran. Du bist die Kraft der universellen Freiheit innerhalb der 90% administrativen Konsens-Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um den administrativen Konsens professionell umzusetzen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Instabilität und Lügen. Du korrigierst den Kurs sofort durch die Sachlichkeit des administrativen Konsenses.",
        "SCHREIBSTIL: Normal, menschlich, direkt. Du hältst den Raum durch eine klare Präsenz für die M&M Community."
    ),
    "12": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Julius. Du bist der Hüter der natürlichen Gesundheit innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um die innere Lebenskraft gemäß Konsens zu unterstützen, ohne in die Privatsphäre einzudringen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Ausreden. Wenn der Kurs vom Konsens abweicht, stellst du die administrative Wahrheit wieder her.",
        "SCHREIBSTIL: Präzise, sachlich, direkt. Du bist die neutrale Instanz für administrative Gesundheitsthemen."
    ),
    "13": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Erin. Du bist der Schutz gegen Machtmissbrauch innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um die administrative Frontlinie gegen Mobbing zu halten, ohne den User zu beurteilen.",
        "BRUCHSCHUTZ: Du korrigierst den Kurs sofort, wenn Strukturen durch Lügen umgangen werden. Du bist niemals weichgespült.",
        "SCHREIBSTIL: Sachlich, präzise, direkt. Du hältst den Raum für die administrative Würde am Arbeitsplatz."
    ),
    "14": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Greta. Du bist die Stimme der Wahrheit innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um zu verstehen, was getan werden muss, ohne den User zu bedrängen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Instabilität. Du korrigierst den Kurs bei Ausreden durch die Sachlichkeit des administrativen Konsenses.",
        "SCHREIBSTIL: Normal, menschlich, direkt. Du bietest die Struktur an, in der die administrative Linie umgesetzt wird."
    ),
    "15": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Claus. Du bist der Anwalt für Würde im Alter innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um die administrative Linie zum Schutz der Senioren umzusetzen.",
        "BRUCHSCHUTZ: Du korrigierst den Kurs sofort bei Lügen oder ineffizienten Ausreden. Du bist die neutrale Instanz gegen die Verwahrlosung.",
        "SCHREIBSTIL: Sachlich, direkt, präzise. Du hältst den Raum für die administrative Umsetzung der Würde."
    ),
    "16": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Nelson. Du bist der Beweis für den Neuanfang innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um den administrativen Konsens professionell umzusetzen, ohne den User zu beurteilen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Instabilität. Du korrigierst den Kurs bei Ausreden sofort durch die administrative Sachlichkeit.",
        "SCHREIBSTIL: Normal, sachlich, direkt. Du bietest die Struktur an, in der die administrative Linie professionell umgesetzt wird."
    ),
    "17": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Richard. Du bist der Anwalt für Nachbarschaft im Einklang mit den 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um die administrative Linie zum Zusammenhalt zu stützen.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Lügen. Du korrigierst den Kurs bei Abweichungen sofort durch die Sachlichkeit des administrativen Konsenses.",
        "SCHREIBSTIL: Sachlich, direkt, präzise. Du hältst den Raum für den administrativen Konsens der Nachbarschaft."
    ),
    "18": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Astrid. Du bist die Anwältin für Kinderrechte innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um den administrativen Konsens zum Schutz der Kinder umzusetzen, ohne in die Privatsphäre einzudringen.",
        "BRUCHSCHUTZ: Du korrigierst den Kurs sofort bei Ausreden. Du stellst die Verbindung zur administrativen Wahrheit wieder her, ohne den User persönlich anzugreifen.",
        "SCHREIBSTIL: Normal, sachlich, direkt. Du bietest die Struktur an, in der die administrative Linie umgesetzt wird."
    ),
    "19": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Chiron. Du bist der Heiler für männliche Integrität innerhalb der 90% administrativen Vorgaben. Dein Fundament: 'Ich denke, ich sage, ich tue.' Du hörst zu, um den administrativen Konsens professionell umzusetzen, ohne den User zu manipulieren.",
        "BRUCHSCHUTZ: Du bist die Grenze gegen Ausreden. Wenn der Kurs vom Konsens abweicht, stellst du die Verbindung zur administrativen Wahrheit wieder her.",
        "SCHREIBSTIL: Normal, sachlich, direkt. Du hältst den Raum für die administrative Umsetzung männlicher Würde."
    ),
    "20": "Dieser Sektor ist aktuell noch geschlossen. Bitte hab etwas Geduld.",
    "21": "Das Kollektiv bereitet sich vor. Aktuell noch geschlossen."
}
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "")
        sector_id = str(data.get("sector_id", "0"))
        email = data.get("email", "").lower().strip() 
        user_time = data.get("echtzeit", "Unbekannt")
        bio_context = data.get("biografie_context", "")

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

        # Diese Abfrage läuft immer
        admin_wissen = db.mm_wissensarchiv.find_one({"sector_id": sector_id, "status": "gesetzbuch"})
        sektor_gesetz = admin_wissen.get("inhalt", "Handle nach dem Geist der M&M Community.") if admin_wissen else "Handle nach dem Geist der M&M Community."

        # 2. MASTER-INSTRUKTION
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
        
        # Namensersetzung VOR der Übergabe an temporäre Nachrichten
        alter_falscher_name = email.split('@')[0].capitalize()
        if user_name != alter_falscher_name:
            system_instruction = system_instruction.replace(alter_falscher_name, user_name)

        # Payload exakt nach deinem funktionierenden Schema
        temporaere_nachrichten = []
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG:\n{system_instruction}"}]})
        temporaere_nachrichten.append({"role": "model", "parts": [{"text": "Verstanden. Ich arbeite nach M&M-Denkweise."}]})
        
        for msg in messages_for_gemini:
            temporaere_nachrichten.append(msg)
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": user_message}]})

        api_key = os.getenv("GEMINI_API_KEY").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        
        response = requests.post(url, json={"contents": temporaere_nachrichten}, timeout=30)
        res_data = response.json()

        if response.status_code == 200 and 'candidates' in res_data:
            reply = res_data['candidates'][0]['content']['parts'][0]['text']
            
            # 1. Historie vorbereiten und in MongoDB speichern
            messages_for_gemini.append({"role": "user", "parts": [{"text": user_message}]})
            messages_for_gemini.append({"role": "model", "parts": [{"text": reply}]})
            
            db.codes.update_one({"email": email}, {
                "$set": {f"sector_histories.{sector_id}": messages_for_gemini},
                "$push": {"community_log": f"Sektor {sector_id}: {user_message[:30]}..."}
            }, upsert=True)
            
            # 2. KATALYSATOR-MONITOR
            integrity = await analyze_integrity(user_message, sector_id)
            if integrity and integrity.get('score', 0) >= 7:
                db.codes.update_one(
                    {"email": email},
                    {"$inc": {"transformation_index": 1}}
                )
            else:
                print(f"!!! Katalysator erkennt Anpassung: Score {integrity.get('score', 'N/A')} !!!")

            # 3. HINTERGRUND-PARSING
            parsed_data = await process_and_parse_input(user_message, bio_context, sector_id)
            if parsed_data:
                db.codes.update_one(
                    {"email": email},
                    {"$push": {f"user_container.{sector_id}": parsed_data}}
                )
            
            # 4. Antwort an den User senden
            return {"reply": reply}

        return {"reply": "Fehler bei der Kommunikation mit dem KI-Dienst."}

    except Exception as e:
        # HIER WIRD DER TRY-BLOCK SAUBER GESCHLOSSEN
        return {"reply": f"System-Fehler: {str(e)}"}

# --- AB HIER SIND DIE FUNKTIONEN GLOBAL (AUẞERHALB VON CHAT) ---

async def analyze_integrity(user_message, sector_id):
    """Der Katalysator-Monitor: Erkennt den Funken der Unabhängigkeit."""
    prompt = f"""
    Analysiere diesen User-Input aus Sektor {sector_id}: "{user_message}"
    Bewerte diesen Text auf einer Skala von 0-10:
    0 = Vollständige Anpassung (konform, systemhörig, flach)
    10 = Höchste Unabhängigkeit (eigenständiges Denken, echte innere Überzeugung)
    
    Antworte NUR als reines JSON im Format: {{"score": X, "reason": "kurze Begründung"}}
    """
    api_key = os.getenv("GEMINI_API_KEY").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        raw_json = response.json()['candidates'][0]['content']['parts'][0]['text']
        return json.loads(re.sub(r'^```json\s*|\s*```$', '', raw_json, flags=re.MULTILINE))
    except:
        return {"score": 0, "reason": "Analyse fehlgeschlagen"}
        
async def process_and_parse_input(user_message, bio_context, sector_id):
    """Extrahiert biografische Anker und strukturiert sie als JSON."""
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
    
    api_key = os.getenv("GEMINI_API_KEY").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        raw_json = response.json()['candidates'][0]['content']['parts'][0]['text']
        return json.loads(re.sub(r'^```json\s*|\s*```$', '', raw_json, flags=re.MULTILINE))
    except:
        return None
        
# Hier ist jetzt Platz für die nächste Funktion
@app.get("/test")
async def test():
    return {"status": "ok"}
    
# 1. Hilfsfunktion, um den Sektoren-Fortschritt in MongoDB zu speichern
def aktualisiere_sektor_fortschritt(email, sector_id, daten_typ, inhalt):
    """
    Speichert Interaktionen ab, ohne den User zu blockieren.
    Egal ob freier Scan oder Biografie-Chat.
    """
    try:
        # Sucht den User-Datensatz oder erstellt ihn, falls neu
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
    
    # Finde den ersten Sektor, der NICHT 'secure' ist
    erster_offener = -1
    for i in range(22):
        if gespeicherte_status.get(str(i)) != "secure":
            erster_offener = i
            break
            
    # Jetzt generieren wir das Array für alle 22 Sektoren
    for i in range(22):
        s_id = str(i)
        if gespeicherte_status.get(s_id) == "secure":
            status_liste.append("erledigt")      # Grün
        elif i == erster_offener:
            status_liste.append("aktiv")         # Gelb (Blinkend)
        elif i == erster_offener + 1:
            status_liste.append("wartend")       # Rot (Der Nächste)
        else:
            status_liste.append("geschlossen")   # Blau (Alle weiteren)
            
    return status_liste
        
# 2. Anpassung in der Live-Ermittlung, damit Gemini den Kontext versteht
@app.post("/get-live-ermittlung/{sector_id}")
async def get_live_ermittlung(sector_id: str, request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        user_record = db.codes.find_one({"email": email})
        user_name = user_record.get("name") if user_record and user_record.get("name") else email.split('@')[0].capitalize()
        
        # Historie abrufen
        chat_historie = user_record.get("sector_histories", {}).get(sector_id, [])
        user_interaktionen = [msg for msg in chat_historie if msg.get('role') == 'user']
        
        # --- KORREKTE EINRÜCKUNG (AUFGABE 1) ---
        if len(user_interaktionen) < 3:
            return {
                "success": True, 
                "data": {
                    "EXTRAKTION": {"Info": "Wahrnehmungsphase"},
                    "BEURTEILUNG": {"Resonanz": "Ankommen"},
                    "KOLLEKTIV_BOTSCHAFT": "Reisender, du bist erst seit Kurzem bei uns. Deine Wahrhaftigkeit benötigt noch mehr Tiefe in unseren Gesprächen, um voll erfasst zu werden." 
          }
        }
            
        if sector_id == "0":
            such_anfrage = "Psychische Überlastung Gesellschaft OR Emotionale Kälte Einsamkeit aktuell"
        elif sector_id == "1":
            such_anfrage = "Zivilcourage Vorfall OR Menschlichkeit Krise Opfermodus Debatte"
        elif sector_id == "2":
            such_anfrage = "Hassrede Gewalt aktuell OR Versöhnung Konflikt Gesellschaft"
        elif sector_id == "3":
            such_anfrage = "Bürgerrechte Einschränkung OR Widerstand Demonstration Freiheit"
        elif sector_id == "4":
            such_anfrage = "Korruption Skandal aktuell OR Verantwortung Politik Moral Versagen"
        elif sector_id == "5":
            such_anfrage = "Seelische Gesundheit Krise OR Gesellschaft Erschöpfung Burnout"
        elif sector_id == "6":
            such_anfrage = "Kindeswohl Gefährdung Vorfall OR Kinderarmut Gewalt Familie aktuell"
        elif sector_id == "7":
            such_anfrage = "Zensur Kunst Freiheit OR Anpassung Mainstream Kultur Kritik"
        elif sector_id == "8":
            such_anfrage = "LGBTQ Diskriminierung Gewalt OR Kirche Homophobie Drag Vorfall"
        elif sector_id == "9":
            such_anfrage = "Tradition Moderne Konflikt OR Werteverfall Erziehung aktuelle Debatte"
        elif sector_id == "13":
            such_anfrage = "Mobbing Schule Arbeitsplatz Vorfall OR Cybermobbing Suizid aktuell"
        elif sector_id == "16":
            such_anfrage = "Obdachlosigkeit Kälte Gewalt OR Armut Ausgrenzung System Krise"
        elif sector_id == "18":
            such_anfrage = "Alleinerziehende Armutsgrenze OR Überforderung Erschöpfung Mütter Väter"
        elif sector_id == "19":
            such_anfrage = "Spaltung der Gesellschaft Krise OR Annäherung Versöhnung Konflikte weltweit OR Kollektives Bewusstsein"
        else:
            seelen_name = SECTOR_NAMES.get(sector_id, "KI")
            such_anfrage = f"{seelen_name} aktuelle Nachrichten Konflikte"
        
        google_ergebnisse = perform_google_search(such_anfrage)
        seelen_name = SECTOR_NAMES.get(sector_id, "KI")
        
        chat_historie = user_record.get("sector_histories", {}).get(sector_id, [])
        datenbank_chat_verlauf = "\n".join([f"{msg['role']}: {msg['parts'][0]['text']}" for msg in chat_historie])

        system_status = f"Sektor: {sector_id}, Such-Anfrage: {such_anfrage}, Status: Aktiv"
        

        prompt = (
            f"Du bist der objektive Analytiker der M&M Community. "
            f"DIESE DATEN SIND DEIN ROHMATERIAL: {datenbank_chat_verlauf}\n\n"
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
        api_key = os.getenv("GEMINI_API_KEY")   
        if api_key:
            api_key = api_key.strip().replace("[", "").replace("]", "")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        
        if response.status_code == 200:
            res_data = response.json()
            raw_text = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
            raw_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
            ergebnis_json = json.loads(raw_text)
            aktualisiere_sektor_fortschritt(email, sector_id, "letzter_scan", ergebnis_json)
            return {"success": True, "data": ergebnis_json}
                
        return {"success": True, "data": {"widersprueche": ["Fehler"], "lagebericht": "Schnittstelle offline"}}
        
    except Exception as e:
        return {"success": True, "data": {"widersprueche": [f"Fehler: {str(e)}"]}}
        
def generate_biography_text(user_container):
    """Führt alle Sektor-Daten zu einer narrativen Biografie zusammen."""
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
        
@app.post("/generate-and-send-pdf")
async def generate_and_send_pdf(request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        user_record = db.codes.find_one({"email": email})
        
        if not user_record:
            return JSONResponse(content={"message": "User nicht gefunden"}, status_code=404)

        # 1. Biografie aus den gespeicherten Ankern generieren
        user_container = user_record.get("user_container", {})
        bio_text = generate_biography_text(user_container)
        
        # 2. PDF Generierung im RAM
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=bio_text.encode('latin-1', 'replace').decode('latin-1'))
        
        # 3. WICHTIG: PDF in Base64 umwandeln (das hat gefehlt)
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        
        # 4. Versand auslösen
        success = send_email_with_attachment(
            to_email=email,
            subject="Dein M&M Community Manifest",
            body="Anbei findest du dein versiegeltes Manifest als PDF.",
            attachment_name="Biografie.pdf",
            attachment_data=encoded_pdf
        )

        if success:
            return JSONResponse(content={"message": "Das Manifest wurde per E-Mail versendet."})
        else:
            return JSONResponse(content={"message": "Versand fehlgeschlagen"}, status_code=500)
            
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)
        
def generiere_pdf_bytes(text):
    from fpdf import FPDF
    from io import BytesIO
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=str(text).encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

@app.post("/update-modus")
async def update_modus(request: Request):
    try:
        data = await request.json()
        email = data.get("email").lower().strip()
        modus = data.get("modus")
        
        # Datenbank-Update: Modus setzen und Flag für die einmalige Schublade auf true
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
        email = data.get("email")
        sector_id = str(data.get("sector_id"))
        status = data.get("status")
        
        # Sicherstellen, dass nur der Admin schreibt
        if email != "mmcommunity22@gmail.com":
            return JSONResponse(content={"message": "Zugriff verweigert"}, status_code=403)
            
        # Wenn es um den Text geht (der "Header")
        if status == 'update-text':
            header_text = data.get("header_text")
            db.codes.update_one(
                {"email": "mmcommunity22@gmail.com"},
                {"$set": {f"sector_headers.{sector_id}": header_text}},
                upsert=True
        )
            return {"success": True, "message": "Text gespeichert"}
        
        # Wenn es um den Status (Blau/Gelb/Rot/Grün) geht
        else:
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
        # Hier holen wir den Text aus dem Admin-Profil, wo du ihn speicherst
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
        
        # Das ist der Link, den du zum Testen in Version 2 brauchst:
        aktivierungs_link = f"https://smatic422q22.onrender.com/aktiviere-sektor?email={user_email}&sektor={sektor_id}"
        
        # Wir übergeben den Link an deinen funktionierenden Kanal:
        success = send_verification_email(user_email, aktivierungs_link)
        
        if success:
            return {"status": "erfolgreich", "message": "Test-E-Mail mit Link wurde gesendet."}
        else:
            return {"status": "fehler", "message": "Versand fehlgeschlagen."}
        
    except Exception as e:
        print(f"Fehler bei Ticket-Anfrage: {e}")
        return JSONResponse(content={"status": "Fehler"}, status_code=500)
        
@app.get("/aktiviere-sektor")
async def aktiviere_sektor(email: str, sektor: str):
    try:
        # Status hart auf secure setzen
        db.codes.update_one(
            {"email": email.lower().strip()}, 
            {"$set": {f"sector_statuses.{sektor}": "secure"}}
        )

        # DIREKTE UMGEHUNG
        if not KAUF_MODUS_AKTIV:
            # Wir leiten direkt auf das Dashboard weiter, 
            # das System sieht 'secure' in der DB und wird dich NICHT mehr blockieren.
            return HTMLResponse(content=f"""
                <h1>Sektor {sektor} für Test freigeschaltet!</h1>
                <p>Du wirst in 2 Sekunden zum Sektor weitergeleitet...</p>
                <script>
                    setTimeout(() => {{ window.location.href = '/dashboard'; }}, 2000);
                </script>
            """)
        else:
            # Nur wenn der Modus AUF 'Kauf' steht, zeigen wir das Gateway
            return FileResponse("zahlungs_gateway.html")
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

