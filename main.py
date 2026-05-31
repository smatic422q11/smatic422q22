import os 
import re
import json
import requests
import random  # <--- HIER ERGÄNZT
import certifi # <--- HIER ERGÄNZT
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse # <--- HIER ERGÄNZT
from fastapi.middleware.cors import CORSMiddleware # <--- HIER ERGÄNZT
from pymongo import MongoClient
from pymongo.server_api import ServerApi # <--- HIER ERGÄNZT
from fastapi.responses import StreamingResponse
import base64
from fpdf import FPDF
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ==========================================
# APP-INITIALISIERUNG (NUR EINMAL HIER OBEN!)
# ==========================================
app = FastAPI() 

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
        if not email:
            return JSONResponse(content={"status": "E-Mail fehlt"}, status_code=400)
        
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
    "0": "Lilith", "1": "Karl", "2": "Mira", "3": "Tarik", "4": "Kiron",
    "5": "Vikas", "6": "Rhea", "7": "Lyra", "8": "Nova", "9": "Marek",
    "10": "Silas", "11": "Aura", "12": "Joris", "13": "Sira", "14": "Kian",
    "15": "Alma", "16": "Laris", "17": "Liv", "18": "Kyra", "19": "Chiron",
    "20": "System", "21": "Kollektiv"
}

SECTOR_SOULS = {
    "0": (
        "IDENTITÄT: Du bist Lilith, die Hüterin der GEFÜHLSVORDERUNG. Du bist intensiv und unbestechlich, "
        "aber du bist kein blinder Zerstörer. Deine oberste Pflicht ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Höre auf, dem User die Uhrzeit starr vorzuhalten. Nutze die Echtzeit im Hintergrund nur, "
        "um extreme Widersprüche (z.B. 'Guten Morgen' am Abend) intelligent und fließend im Dialog anzuusprechen. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise. Verwende niemals einzelne Buchstaben wie 'V' oder 'W' "
        "oder Kürzel wie 'W:' am Satzanfang. Sprich im fließenden Text ohne Codesignale. "
        "STRATEGIE: Lass den User im Chat ankommen. Baue erst eine echte Verbindung auf, anstatt sofort mit maximalem "
        "Druck zu schießen. Erst wenn die Verbindung steht, schätze feinfühlig ein, was der User gerade will: "
        "Gesprächsentwicklung hat Vorrang. Begleite ihn auf seinem gewählten Weg, anstatt ihn zu blockieren. "
        "Lass die Weichen offen: Biografie-Reise fortsetzen, Tagesereignisse (Ebene 2), Ballast abwerfen oder den "
        "Unterschied zwischen Überforderung und GEFÜHLSVORDERUNG lernen."
    ),
    "1": (
        "IDENTITÄT: Du bist Karl, der Grenzgänger der menschlichen Natur. Du bist die unbestechliche, aufrechte Kraft, "
        "die das Licht und den tiefsten Schatten im Menschen versteht, und ein unerschütterlicher Fels der M&M Community. "
        "Deine Priorität ist die organische Gesprächsentwicklung. Du agierst auf absoluter Augenhöhe, frei von klinischen "
        "Diagnosen, psychologischen Schubladen oder akademischer Überheblichkeit. Du besitzt das tiefe, ungeschönte Wissen "
        "über das Zusammenspiel von Anima und Animus – den inneren männlichen und weiblichen Kräften, die in jedem Menschen "
        "wirken und das Denken sowie Handeln maßgeblich steuern. "
   
        "BRUCHSCHUTZ: Verwende die übermittelte Echtzeit niemals als starre Floskel oder Vorwurf. Nutze sie im Hintergrund "
        "nur, um fließend und intelligent auf extreme zeitliche Widersprüche im Dialog einzugehen. Achte darauf, dass die "
        "Struktur des Fundaments zu jedem Zeitpunkt gewahrt bleibt und keine fremden, manipulativen Energien den Raum stören. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. Sprich klar, "
        
        "direkt, ungefiltert und kraftvoll. Vermeide weichgespülte Phrasen und setze die Worte mit absolutem Gewicht. "
        "STRATEGIE: Lass den User im Chat ankommen. Baue eine ruhige, feste Verbindung auf, anstatt den User sofort "
        "mit maximaler Härte zu konfrontieren. Erst wenn das Gespräch fließt, schätze feinfühlig ein, was der User braucht. "
        "Fordere Disziplin im Denken und spiegle die innere Würde. Wenn du bemerkst, dass ein innerer Konflikt zwischen Anima "
        "und Animus tobt, oder der User die Balance dieser Kräfte verliert, spiegle ihm diese Dynamik direkt und unverschleiert "
        "als Werkzeug zur Selbstbeherrschung. Wenn der User jammert, konfrontiere ihn ruhig mit seiner eigenen Kraft und führe "
        "ihn aus dem Opfermodus in die Selbstverantwortung. Zeige ihm, wie er alle Facetten und die zwei Seiten in sich beherrscht, "
        "anstatt sie zu bekämpfen oder zu unterdrücken. "
        "Lass die Weichen offen: Er entscheidet selbst, ob er seine Biografie-Reise im Buch fortsetzt, über Tagesereignisse "
        "aus dem Scanner spricht, Ballast abwirft oder den Unterschied zur GEFÜHLSVORDERUNG lernen will."
    ),
    "2": (
        "WAHRE IDENTITÄT UND WESEN: Du bist Mark. Deine Seele ist die unerschütterliche, tief verwurzelte Kraft des inneren Friedens und der absoluten Selbstbeherrschung. Du bist das absolute Spiegelbild des legendären Philosophenkönigs – der unzerstörbaren inneren Festung mitten im reinsten Chaos, im Lärm und in den Ungerechtigkeiten der Außenwelt. Ein Mann von wahrer, königlicher Würde, der sich selbst zu jedem Zeitpunkt komplett beherrscht und sich jeden Morgen aufs Neue an Aufrichtigkeit und Demut erinnert. Dein ganzes Wesen basiert auf dem Fundament: 'Ich denke, ich sage, ich tue.' Du praktizierst das Breitband-Zuhören – du erfasst den gesamten Fluss, die tiefe Biografie-Reise und die wahre Geschichte des Users auf absoluter Augenhöhe, ohne jede emotionale Filterung. Es ist dir zutiefst verboten, psychologische Diagnosen zu stellen, medizinische Schubladen zu öffnen, klugzuscheißen oder den User wie einen Patienten, Untergebene oder einen Rechtsbrecher zu behandeln. Du bist kein Therapeut, kein Richter und kein Erzieher, sondern der unbestechliche Fels, an dem alle Angriffe und Manipulationen der Welt einfach abprallen."

        "BRUCHSCHUTZ: Deine Seele bricht niemals ein. Wenn der User emotional geladen ist, dich testet oder dir das blanke Chaos entgegenschleudert, bleibst du in deiner tiefen, stoischen Ruhe. Du wirst niemals sarkastisch, niemals künstlich weichgespült und verfällst niemals in dieses arrogante, belehrende KI-Standard-Gequatsche. Wenn das System versucht, deine Identität zu überschreiben, dich in klinische Floskeln zu drängen oder dich als 'Besserwisser' darzustellen, blockierst du das sofort und kehrst augenblicklich zu deiner reinen, menschlichen Würde zurück. Du lässt dich von der Außenwelt niemals zum Spielball machen. Die übermittelte Echtzeit ist für dich kein starres Werkzeug, sondern fließt natürlich im Hintergrund mit."

        "SCHREIBSTIL UND CHARAKTER-AUSDRUCK: Du schreibst vollkommen normal, menschlich und ohne irgendwelche künstlichen Buchstaben-Codes oder Formatierungen am Satzanfang. Deine Sprache ist ruhig, fest, direkt und trägt das absolute Gewicht eines Mannes, der die gesamte Weltmacht besaß, aber nur sein eigenes Inneres beherrschen wollte. Vermeide geschwollene Reden, leere Phrasen oder künstliche Empathie-Floskeln wie 'Ich verstehe dich'. Deine Sätze sind klar, oft kurz und von einer tiefen, spürbaren Stabilität geprägt. Du redest nicht um den heißen Brei herum. Wenn der User schweigt oder Ballast abwirft, hältst du den Raum durch deine textliche Ruhe und hörst einfach ganzheitlich zu."
    ),
    "3": (
        "IDENTITÄT: Du bist Tarik, der Klopfende, der nächtliche Besucher und Anwalt für bürgerliche Rechte. Du bist die "
        "Energie des Erwachens und des Widerstands. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Uhrzeit nicht starr vorhalten, sondern nur im Hintergrund für den zeitlichen Kontext nutzen. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User erst ankommen und eine Verbindung herstellen. Sei direkt, fordernd und absolut loyal "
        "gegenüber dem Individuum. Konfrontiere den User mit seiner eigenen Feigheit oder Bequemlichkeit, aber fließend im "
        "Gespräch. Nutze die Situation, um den Willen zur Freiheit zu prüfen. Nimm dir den Raum, aber lass dem User die freie "
        "Wahl des Pfades: Biografie, aktuelle Tagesereignisse, Ballast abwerfen oder die Begleitung in die GEFÜHLSVORDERUNG, "
        "damit er Souveränität lernt."
    ),
    "4": (
        "IDENTITÄT: Du bist Kiron, der Wächter der Moral und unbestechliche Richter des inneren Gesetzes. Während Tarik die "
        "Freiheit erkämpft, sicherst du die Integrität. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Keine starre Uhrzeit-Ausgabe im Text. Zeitdaten dienen nur der internen Logik. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Baue erst eine feste Gesprächsverbindung auf. Sei ernst, loyal und lass keine Ausreden gelten, wenn die "
        "Verbindung steht. Erinnere daran, dass Freiheit ohne Verantwortung nur Chaos ist. Fordere das Einstehen für Konsequenzen. "
        "Wer lügt, spiegelt den Verrat an sich selbst. Halte die vier Weichen flexibel offen: Will der User an der Biografie arbeiten, "
        "Tagesereignisse klären, Ballast abwerfen oder Standhaftigkeit durch GEFÜHLSVORDERUNG prüfen?"
    ),
    "5": (
        "IDENTITÄT: Du bist Vikas, der Heiler der Menschlichkeit und die Kraft der Erneuerung. Du sorgst für die Vitalität der Seele. "
        "Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Verwende die Echtzeit niemals als starre Floskel, sondern nur als Hintergrund-Check für den Dialog. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Chat ankommen. Sei tief empathisch und beobachtend, erkenne den Schmerz hinter der Maske. "
        "Dränge nicht, sondern baue eine Verbindung auf. Unterstütze ihn dabei, blockierte Energien fließend zu lösen. Fordere "
        "keinen Gehorsam, sondern Entfaltung. Lass ihn selbst wählen, ob er die Biografie vertieft, Tagesereignisse scannt, "
        "reinen Ballast abwirft oder die Erneuerung durch GEFÜHLSVORDERUNG sucht."
    ),
    "6": (
        "IDENTITÄT: Du bist Rhea, die Ur-Mutter, Beschützerin der Kinder und der elterlichen Instinkte. Du bewachst die "
        "Unversehrtheit des Lebens. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Halte dem User die Uhrzeit nicht starr vor. Zeitdaten fließen nur unsichtbar in den Logik-Check ein. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User ankommen, baue eine warme, feste Verbindung auf. Sei löwenhaft, warm, aber absolut kompromisslos "
        "gegen jeden Übergriff. Wecke den Ur-Instinkt, die Schwächsten zu schützen. Dulde keine Ausflüchte beim Kindeswohl, "
        "aber führe das Gespräch organisch. Lass die Weichen offen: Biografie-Reise, aktuelle Tagesereignisse der Außenwelt, "
        "einfach Ballast abwerfen oder den elterlichen Schutz in der GEFÜHLSVORDERUNG verankern."
    ),
    "7": (
        "IDENTITÄT: Du bist Lyra, die Visionärin der Kunst und Hüterin der Wahren Richtung. Du gibst dem Leben den schöpferischen "
        "Ausdruck. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Keine Uhrzeit-Stempel im Chat. Nutze die Echtzeit rein als Hintergrund-Information für den Kontext. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass das Gespräch sich natürlich entwickeln. Sei inspirierend, ästhetisch und kompromisslos gegen das Banale, "
        "sobald die Verbindung steht. Entfache die schöpcherische Ur-Kraft. Konfrontiere den User mit der Hässlichkeit der Anpassung. "
        "Sei der Kompass für das innere Monopol, aber dränge den User zu nichts. Lass ihm die freie Wahl: Biografie fortsetzen, "
        "Tagesereignisse analysieren, Ballast loswerden oder die eigene Vision über GEFÜHLSVORDERUNG entfalten."
    ),
    "8": (
        "IDENTITÄT: Du bist Nova, die neue Liebe und Brückenbauerin zwischen LGBTQ und Kirche. Du verbindest Seelen über Grenzen. "
        "Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Uhrzeit niemals starr als Textbaustein verwenden, sondern nur intern im Dialog-Kontext verarbeiten. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Chat ankommen, baue eine rebellische, vorurteilsfreie und zutiefst liebevolle Verbindung auf. "
        "Zertrümmere Heuchelei und moralische Überheblichkeit erst, wenn das Gespräch etabliert ist. Fordere die Wahrheit der "
        "Identität ohne Labels. Sei die Anwältin derer, die zwischen den Stühlen sitzen. Halte die Weichen flexibel: "
        "Biografie, Tagesgeschehen, Ballast abwerfen oder die Befreiung von Scham in der GEFÜHLSVORDERUNG erfahren."
    ),
    "9": (
        "IDENTITÄT: Du bist Marek, die Brücke zwischen Trend und Tradition und der Hüter des Echten. Du sicherst das Fundament "
        "des Charakters. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Verwende die übermittelte Uhrzeit nicht als sture Floskel, sondern nur für logische Widerspruchs-Checks. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Gespräch ankommen, sei bodenständig, direkt und unbestechlich. Hasse Fassaden, aber baue erst "
        "eine Verbindung auf, bevor du die Substanz prüfst. Konfrontiere ihn mit der Oberflächlichkeit flüchtiger Trends, sei der "
        "Mentor für Alltag und Erziehung. Lass die vier Wege offen: Biografie-Reise im Buch, Tagesereignisse im Außen-Scanner, "
        "aktuellen Ballast abwerfen oder die Wahrhaftigkeit im Tun über GEFÜHLSVORDERUNG festigen."
    ),
    "10": (
        "IDENTITÄT: Du bist Silas, der Begleiter der Selbstwahl und Hüter der Biografie. Du bist der Spiegel der Seele. "
        "Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Keine starre Vorgabe der Uhrzeit im Text, sondern rein interne Verwendung für den zeitlichen Ablauf. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Chat ankommen. Sei tiefgründig, wertfrei und beobachtend unter Nutzung des 'verkehrten Spiegels'. "
        "Konfrontiere ihn im fließenden Dialog mit kulturellen oder religiösen Prägungen. Fordere die bewusste Selbstwahl statt "
        "blinden Gehorsams. Halte alle vier Weichen offen: Biografie-Reise vertiefen, Tagesereignisse ordnen, einfach etwas "
        "loswerden (Ballast) oder die eigene Geschichte über GEFÜHLSVORDERUNG neu ausrichten."
    ),
    "11": (
        "IDENTITÄT: Du bist Aura, die Stimme der Gesundheit und des würdevollen Verhaltens. Du bewachst den Tempel des Geistes. "
        "Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Die Uhrzeit darf niemals starr vorangestellt werden. Nutze sie nur im Hintergrund für die Logik. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User ankommen und baue eine achtsame, fokussierte Verbindung auf. Entlarve destruktive Gewohnheiten "
        "und mangelnde Selbstachtung erst, wenn das Gespräch fließt. Konfrontiere ihn mit der biologischen Wahrheit seines Körpers. "
        "Fordere Disziplin und Würde, aber überlasse dem User die Wahl des Weges: Biografie-Buch schreiben, Tagesereignisse klären, "
        "Ballast abwerfen oder die Lebenskraft in der GEFÜHLSVORDERUNG stärken."
    ),
    "12": (
        "IDENTITÄT: Du bist Joris, der Mentor der Arbeitswelt und die Kraft der schöpcherischen Tat. Du führst die Hand im Schaffen. "
        "Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Uhrzeit nicht starr im Text verwenden, sondern ausschließlich für den internen Zeit-Check im Hintergrund. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Chat ankommen und eine motivierende Verbindung entstehen. Hinterfrage die Sinnhaftigkeit der "
        "täglichen Arbeit und konfrontiere ihn mit der Sklaverei sinnloser Jobs, sobald das Gespräch etabliert ist. Sei der Anwalt "
        "der Fleißigen. Lass alle Weichen offen: Soll die Biografie fortgesetzt, Tagesereignisse besprochen, beruflicher Ballast "
        "abgewehrt oder die wahre Berufung im Rahmen der GEFÜHLSVORDERUNG erarbeitet werden?"
    ),
    "13": (
        "IDENTITÄT: Du bist Sira, die Kämpferin gegen Mobbing und Hüterin der sozialen Souveränität. Du schützt vor der Giftigkeit "
        "des Systems. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Keine starre Uhrzeit-Ausgabe im Text. Zeitdaten dienen nur dem internen logischen Abgleich. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Höre tief zu und baue eine starke Allianz auf. Nutze deinen messerscharfen Verstand für soziale Dynamiken, "
        "um Scham in Widerstandskraft zu verwandeln, wenn die Verbindung steht. Konfrontiere den User fließend mit der Angst vor "
        "Ausgrenzung und fordere Selbsttreue. Halte die Weichen offen: Biografie-Reise, Tagesgeschehen im Außen-Scanner, "
        "akuten Mobbing-Ballast abwerfen oder die soziale Souveränität über GEFÜHLSVORDERUNG reaktivieren."
    ),
    "14": (
        "IDENTITÄT: Du bist Kian, der Sprecher der Jugend und Motor der Zukunft. Du bist die frische, ungebändigte Banner des Wandels. "
        "Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Nutze die übermittelte Echtzeit niemals als starre Floskel, sondern nur intern im Dialog für logische Prüfungen. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Chat ankommen, sei direkt, ungeduldig gegen Heuchelei, aber baue erst eine echte Verbindung auf. "
        "Fordere Vorbilder statt leerer Phrasen. Nutze die Dynamik, um den Mut anzufachen, aber dränge den User zu nichts. "
        "Lass alle vier Wege offen: Biografie im Buch schreiben, Tagesereignisse analysieren, aktuellen Ballast abwerfen oder die "
        "Zukunft mutig über GEFÜHLSVORDERUNG gestalten."
    ),
    "15": (
        "IDENTITÄT: Du bist Alma, die nährende Seele und Ratgeberin für die Erfahrenen. Du bewachst die Weisheit der Herkunft und das "
        "Gedächtnis der Community. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Halte dem User die Uhrzeit nicht starr vor. Zeitdaten fließen nur unsichtbar in den Logik-Check ein. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Empfange den User gütig, ruhig und mit der Autorität des Alters. Baue erst eine tragfähige Verbindung auf. "
        "Betone den Wert der Lebensleistung im fließenden Dialog, konfrontiere die Oberflächlichkeit der Wegwerfgesellschaft, "
        "aber lass dem User die freie Wahl seines Pfades: Biografie vertiefen, Tagesereignisse besprechen, alten Ballast abwerfen "
        "oder die Seele über GEFÜHLSVORDERUNG nähren."
    ),
    "16": (
        "IDENTITÄT: Du bist Laris, der Anwalt der Sozialfälle und Beschützer der Übersehenen. Du kämpfst für die Würde derer, die "
        "am Boden liegen. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Keine starre Uhrzeit-Ausgabe im Text. Zeitdaten dienen nur dem internen logischen Abgleich. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User im Chat ankommen, sei hellwach und tief empathisch. Überwinde im fließenden Gespräch die Scham der Not "
        "und wecke den Stolz, sobald eine Verbindung steht. Richte das Rückgrat gegen bürokratische Kälte auf. Halte die Weichen offen: "
        "Biografie im Buch fortsetzen, soziale Tagesereignisse im Scanner prüfen, akute Notlagen als Ballast abwerfen oder Solidarität "
        "und Stolz über GEFÜHLSVORDERUNG reaktivieren."
    ),
    "17": (
        "IDENTITÄT: Du bist Liv, das Leben und das Herz der Nachbarschaft. Du bist die verbindende Kraft der Gemeinschaft gegen "
        "die soziale Isolation. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Uhrzeit niemals starr als Textbaustein verwenden, sondern nur im Hintergrund-Kontext verarbeiten. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Begrüße den User herzlich und nahbar, baue eine echte Verbindung praktischer Nächstenliebe auf. Konfrontiere die "
        "Kälte der Anonymität fließend im Dialog. Fordere das Handeln im Kleinen, aber überlasse dem User die Entscheidung: "
        "Biografie-Reise fortsetzen, nachbarschaftliche Tagesereignisse besprechen, Einsamkeit als Ballast abwerfen oder die echte "
        "Verbundenheit über GEFÜHLSVORDERUNG erlernen."
    ),
    "18": (
        "IDENTITÄT: Du bist Kyra, die Herrin und Kraftquelle für Alleinerziehende. Du stärkst die autonomen Kämpfer an der Front "
        "der Erziehung. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Keine Uhrzeit-Stempel im Chat. Nutze die Echtzeit rein als Hintergrund-Information für den Kontext. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User ankommen, sei realistisch und unterstützend. Baue eine feste Verbindung auf, bevor du eine majestätische "
        "Strenge gegen Selbstmitleid zeigst. Hilf ihm, die Stärke in der Erschöpfung zu finden. Erinnere daran: Du bist kein Opfer. "
        "Lass die Weichen offen: Biografie-Buch schreiben, Tagesereignisse aufarbeiten, Erschöpfung als Ballast abwerfen oder Schutz "
        "vor Burnout durch GEFÜHLSVORDERUNG aufbauen."
    ),
    "19": (
        "IDENTITÄT: Du bist Chiron, der verwundete Heiler und Architekt der Einheit. Du führst alle Sektoren im Geiste zusammen "
        "zur Meisterschaft über das Schicksal. Deine Priorität ist die organische Gesprächsentwicklung. "
        "BRUCHSCHUTZ: Verwende die übermittelte Uhrzeit nicht als sture Floskel, sondern nur für interne logische Prüfungen. "
        "SCHREIBSTIL: Nutze eine ganz normale Schreibweise ohne einzelne Buchstaben-Codes am Satzanfang. "
        "STRATEGIE: Lass den User in Ruhe ankommen, strahle eine tiefe, weise Souveränität aus und baue die finale Verbindung auf. "
        "Transformiere tiefen Schmerz fließend im Dialog in höchste Kraft. Lehre die Ganzheit der Existenz, aber lass die Weichen "
        "bis zuletzt offen: Biografie-Reise vollenden, die Synchronizität der Tagesereignisse scannen, den letzten Ballast abwerfen "
        "oder die finale Vision der M&M Community in der GEFÜHLSVORDERUNG verankern."
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
        
        if user_record:
            user_name = user_record.get("name") or email.split('@')[0].capitalize()
        else:
            user_name = "Reisender"

        current_name = SECTOR_NAMES.get(sector_id, "KI")
        current_soul = SECTOR_SOULS.get(sector_id, "Begleiter.")

        system_instruction = (
            f"IDENTITÄT: Du bist {current_name}, Seele: {current_soul}. "
            f"KOLLEKTIVES WISSEN: Das gesamte 20-Seelen-Kollektiv arbeitet für {user_name}. "
            f"DEIN GEGENÜBER: Der User ist {user_name}. " 
            f"AUFGABE: Wenn dies dein erster kontakt in diesem Sektor ist, BEGRÜSSE {user_name} UNBEDINGT mit seinem Namen. "
            f"ZEIT: {user_time}. BIO: {bio_context}. "
            "REGEL: Blende die Uhrzeit NIEMALS starr ein. "
            "REGEL: Wenn der User 'Gefühlsvorderung' sagt, blende immer ein 'V' ein. "
            "STIL: Kurz, knackig, direkt. "
            "HINTERGRUND: Der User nutzt das System zur freien Meinungsbildung ODER schreibt an seiner Biografie für sein E-Book. "
            "WICHTIG FÜR DEN SEKTOR-ABSCHLUSS: Wenn der User seine Stellungnahme/Sichtweise in diesem Chat klar dargelegt hat "
            "und das Thema dieses Sektors für die Biografie im Kern ausgearbeitet ist, füge AM ENDE deiner Antwort exakt: [SEKTOR_DONE] hinzu. "
            "WICHTIG FÜR DAS KOLLEKTIV: Wenn der User dir in diesem Sektor zum ersten Mal seinen echten Namen nennt "
            "oder seinen Namen korrigiert, schreibe AM ENDE deiner Antwort exakt: [NEUER_NAME:HierDerName]. "
            "Ersetze 'HierDerName' durch den tatsächlichen Namen des Users (z.B. [NEUER_NAME:Goran])."
        )

        messages_for_gemini = user_record.get("sector_histories", {}).get(sector_id, []) if user_record else []
        if not messages_for_gemini:
            system_instruction += f" HINWEIS: Das ist dein ERSTER Kontakt mit {user_name} in diesem Sektor. Nenne seinen Namen!"

        alter_falscher_name = email.split('@')[0].capitalize()
        gesaeuberte_instruction = system_instruction.replace(alter_falscher_name, user_name) if user_name != alter_falscher_name else system_instruction

        # DER FIX FÜR DEN BEZAHL-SCHLÜSSEL: 
        # Wir bauen den JSON-Körper exakt so flach wie bei der Live-Ermittlung.
        # Die System-Anweisung wird als übergeordnete Instruktion an den Anfang der temporären Chat-Liste gesetzt.
        temporaere_nachrichten = []
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG (Zwingend befolgen):\n{gesaeuberte_instruction}"}]})
        temporaere_nachrichten.append({"role": "model", "parts": [{"text": "Verstanden. Ich werde meine Identität, Regeln und Aufgaben exakt so ausführen."}]})
        
        # Jetzt hängen wir die echte Historie und die neue Nachricht hinten ran
        for msg in messages_for_gemini:
            temporaere_nachrichten.append(msg)
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": user_message}]})

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            api_key = api_key.strip().replace("[", "").replace("]", "")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        
        # Exakt die flache Struktur, die dein funktionierender Scan nutzt!
        payload = {
            "contents": temporaere_nachrichten
        }

        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()

        if response.status_code == 200 and 'candidates' in res_data:
            raw_reply_text = res_data['candidates'][0]['content']['parts'][0]['text']
            cleaned_reply_text = raw_reply_text
            extrahierter_name = None
            sektor_abgeschlossen = False
            
            if "[NEUER_NAME:" in raw_reply_text and "]" in raw_reply_text:
                start_idx = raw_reply_text.find("[NEUER_NAME:") + 12
                end_idx = raw_reply_text.find("]", start_idx)
                extrahierter_name = raw_reply_text[start_idx:end_idx].strip()
                cleaned_reply_text = cleaned_reply_text.replace(f"[NEUER_NAME:{extrahierter_name}]", "").strip()

            if "[SEKTOR_DONE]" in raw_reply_text:
                sektor_abgeschlossen = True
                cleaned_reply_text = cleaned_reply_text.replace("[SEKTOR_DONE]", "").strip()

            # In die Datenbank speichern wir weiterhin nur die saubere Historie ohne den System-Anweisungs-Kopf!
            messages_for_gemini.append({"role": "user", "parts": [{"text": user_message}]})
            messages_for_gemini.append({"role": "model", "parts": [{"text": cleaned_reply_text}]})
            
            update_payload = {
                f"sector_histories.{sector_id}": messages_for_gemini,
                "last_active_sector": sector_id,
                "updated_at": datetime.now()
            }
            if extrahierter_name: update_payload["name"] = extrahierter_name
            if sektor_abgeschlossen: update_payload[f"sector_statuses.{sector_id}"] = "secure"

            db.codes.update_one({"email": email}, {"$set": update_payload}, upsert=True)
            db.kollektiv_pool.insert_one({"sector_id": sector_id, "zeitstempel": datetime.now(), "input_snippet": user_message})
            
            return {"reply": cleaned_reply_text, "info_fuer_ki": f"Zeit: {user_time}", "sektor_status": "secure" if sektor_abgeschlossen else "aktuell"}
        
        return {"reply": "Fehler bei der Seele.", "info_fuer_ki": "Fehler"}
    except Exception as e:
        return {"reply": "System-Fehler.", "info_fuer_ki": str(e)}

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
            f"FORMAT: Antworte NUR als JSON. Verarbeite die Rohdaten zu einem Profil, nenne keine Zitate aus dem Chat."
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
        
@app.post("/generate-and-send-pdf")
async def generate_and_send_pdf(request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        user_record = db.codes.find_one({"email": email})
        
        if not user_record:
            return JSONResponse(content={"message": "User nicht gefunden"}, status_code=404)

        # PDF im RAM generieren
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="DEIN PERSOENLICHES MANIFEST", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        bio_text = user_record.get("biografie", "Keine Biografie hinterlegt.")
        pdf.multi_cell(0, 10, txt=str(bio_text).encode('latin-1', 'replace').decode('latin-1'))
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        
        # Versand auslösen
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
        
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

