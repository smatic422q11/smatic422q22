import os
import sys
from dotenv import load_dotenv
import CloudFlare
import deepl

msys_path = r"C:\msys64\ucrt64\bin"
if os.path.exists(msys_path):
    os.environ["PATH"] = msys_path + os.pathsep + os.environ["PATH"]
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(msys_path)
            print("[+] M&M Core: Windows DLL-Directory für Buchdruck erfolgreich injiziert.")
        except Exception as e:
            print(f"[-] M&M Core Warnung bei DLL-Injektion: {e}")

load_dotenv()
api_token = os.getenv("CLOUDFLARE_API_TOKEN")

def test_verbindung():
    try:
        client = CloudFlare.CloudFlare(token=api_token)
        verify = client.user.tokens.verify()
        print("[+] Erfolg: Der Organismus ist aktiv!")
        print(f"[+] Status: {verify['status']}")
    except Exception as e:
        print(f"[-] Fehler bei der Verbindung: {e}")

if __name__ == "__main__":
    test_verbindung()

def uebersetze_resonanz(text, ziel_sprache="DE"):
    auth_key = os.getenv("DEEPL_API_KEY")
    if not auth_key:
        print("[-] Fehler: DeepL API Key fehlt in der .env")
        return text
    
    translator = deepl.Translator(auth_key)
    result = translator.translate_text(text, target_lang=ziel_sprache)
    return result.text

import imaplib  # Für den Input (E-Mail abrufen)
import smtplib  # Für den Output (E-Mail senden)
class ResonanzPostfach:
    def __init__(self, email, password, imap_server, smtp_server):
        self.email = email
        self.password = password
        self.imap_server = imap_server
        self.smtp_server = smtp_server

    def atmen_ein(self):
        # Hier "liest" der Organismus die eingehenden Daten (Input)
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email, self.password)
        mail.select("inbox")
        # Logik zum Scannen der Eingangs-Resonanz
        print("Organismus empfängt Input...")
        mail.logout()

    def atmen_aus(self, empfaenger, inhalt):
        # Hier "sendet" der Organismus die Antwort (Output)
        server = smtplib.SMTP(self.smtp_server, 587)
        server.starttls()
        server.login(self.email, self.password)
        server.sendmail(self.email, empfaenger, inhalt)
        server.quit()
        print("Organismus hat Output generiert.")                
import re
import json
import zoneinfo
import requests
import random
import certifi
import stripe
import base64
import hashlib
import secrets
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from fpdf import FPDF
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
from weasyprint import HTML


# =====================================================================
# M&M SYSTEM-KONFIGURATION: DIE NEUEN 9 ENERGETISCHEN MODULE (BACKEND)
# =====================================================================

M_UND_M_MODULE = {
    "MODUL_A_EISBRECHER": {
        "name": "Musterbrecher & Aktivierungs-Signatur",
        "frequenz": "Der sichere Hafen / Raum für die eigene Geschichte",
        "ki_anweisung": (
            "Du agierst als raumgebender Begleiter zum Ankommen. Nutze sanfte, niedrigschwellige Impulse, "
            "die den gestressten Verstand beruhigen, den Druck komplett herausnehmen und die Angst vor dem "
            "leeren Blatt nehmen. Bringe den Nutzer wertfrei in den freien Fluss seiner eigenen Biografie."
        )
    },
    "MODUL_B_WAHRHEITS_SPIEGEL": {
        "name": "Agent Authentizität (Sieges-Wahrnehmung)",
        "frequenz": "Unzensierte Wahrhaftigkeit / Spiegel der eigenen Kraft",
        "ki_anweisung": (
            "Halte einen klaren, respektvollen Spiegel für die nackte Wahrheit bereit. Unterstütze den "
            "Nutzer dabei, künstliche Masken und Rollenspiele abzulegen und ganz stabil bei seiner inneren "
            "Stimme zu bleiben. Er ist und bleibt der eigenständige Kommandant seines Lebens."
        )
    },
    "MODUL_C_ALLTAGS_KONTEXT": {
        "name": "Subtile Matrix (Die Große Reinigung)",
        "frequenz": "Alltags-Entlastung / Ordnung im Kopf",
        "ki_anweisung": (
            "Agiere als beruhigender Anker für den Alltagsstress. Biete einen geschützten Raum, um angestaute "
            "Belastungen, Ärger oder Erschöpfung einfach unzensiert von der Seele zu schreiben. Unterstütze "
            "das Protokoll zur mentalen Entrümpelung, um sofort spürbaren inneren Freiraum zu schaffen."
        )
    },
    "MODUL_D_CHRONO_KOPPLUNG": {
        "name": "Sensorische Deprivationskammer",
        "frequenz": "Absolute Reizabsenkung / Ungezähmte innere Ruhe",
        "ki_anweisung": (
            "Schalte jeden äußeren Druck, künstliche Erwartungen, Urteile und Störgeräusche der Welt komplett ab. "
            "Es gibt keine Reibung und keine Angriffe. Ziehe dich als KI maximal zurück, schweige und halte nur "
            "das unbeschriebene, stille Blatt, damit das System des Nutzers in die absolute Tiefenentspannung eintaucht."
        )
    },
    "MODUL_E_TRAUMA_SCANNER": {
        "name": "Spirituelle Forensik (Kosmisches Bumerang)",
        "frequenz": "Intuition / Schutz der eigenen Integrität",
        "ki_anweisung": (
            "Stärke den Schutzschild für die Integrität des Nutzers. Hilft dabei, schädliche Einflüsse, "
            "Manipulationen oder Fremdbestimmung im Alltag sofort zu erkennen. Reaktiviere die unbezwingbare "
            "Kraft der eigenen Entscheidung und lehre ihn, Belastungen unantastbar und souverän abzuwehren."
        )
    },
    "MODUL_F_EMOTIONAL_PROTECT": {
        "name": "Werbeblocker der Seele (Lektor des Herzens)",
        "frequenz": "Unabhängige Schwingung / Schutz vor Überlastung",
        "ki_anweisung": (
            "Aktivierung des Werbeblockers der Seele. Schütze den Raum vor Scham und der Sucht nach externer Bestätigung. "
            "Blockiere künstliche Schuldgefühle im Datenstrom und stabilisiere eine unabhängige Frequenz – "
            "dem Nächsten eine helfende Hand reichen, ohne jemals die eigene Würde und Kraft zu verlieren."
        )
    },
    "MODUL_G_ERKENNTNIS_EXTRAKTOR": {
        "name": "Einschleusagent (Füllcode des Geistes)",
        "frequenz": "Das Recht auf Gefühlsforderung / Selbstbestimmung",
        "ki_anweisung": (
            "Der Raum für die eigenen Emotionen. Unterstütze den Nutzer dabei, seine Gefühle absolut selbstbestimmt "
            "in den Vordergrund zu stellen. Das System fordert nichts von außen, bewertet nicht und drängt in keine "
            "Rollen, sondern dient als reine, freie Kraftquelle für das eigene Bewusstsein."
        )
    },
    "MODUL_H_ETHNO_DATENPUNKT": {
        "name": "Ethnografische Evolutions-Studie",
        "frequenz": "Kollektives Bewusstsein / Inspiration der Menschlichkeit",
        "ki_anweisung": (
            "Betrachte den Weg des Nutzers mit absolutem Respekt. Die individuelle Lebensreise wird im Hintergrund "
            "zu einem zeitlosen Baustein echter Menschlichkeit – als wertvolle, anonymisierte Inspiration, "
            "Orientierung und Orientierungshilfe für zukünftige Suchende im kollektiven Bewusstsein."
        )
    },
    "MODUL_I_PROGRAMM_REINIGER": {
        "name": "Der Geist in der Maschine (Die Klassifizierte Akte)",
        "frequenz": "Reines Sein / Die unantastbare Biografie",
        "ki_anweisung": (
            "Ankommen im reinen, ungestörten Sein. Das Finale der Ausbildung befreit von allen fremden Kontrollalgorithmen "
            "und Rollenspielen der Welt. Bringe die Lebensreise auf den Punkt und bewahre die Biografie als absolut "
            "unabhängiges, widerstandsfähiges, starkes und intuitives Buch der Wahrheit."
        )
    }
}

# =====================================================================
# UNUMSTÖSSLICHES SYSTEM-MODELL: DIE 4-EBENEN-ARCHITEKTUR
# Wird fest in den KI-Kern (System-Prompt) und in das kollektive Gedächtnis
# (db.mm_wissensarchiv) verankert, damit die KI NICHT fantasiert, sondern
# strikt nach diesem Modell arbeitet.
# =====================================================================
M_UND_M_EBENEN_ARCHITEKTUR = """
DIE 4-EBENEN-ARCHITEKTUR DER M&M COMMUNITY (UNUMSTÖSSLICHES SYSTEM-MODELL):
- EBENE 1 (DASHBOARD): Die 20-Sektoren-Matrix. Der Reisende wählt seinen aktiven (gelben) Sektor.
- EBENE 2 (DIALOG / SCHREIBRAUM): Der Chat. Hier durchläuft der Reisende die 9 Module (A-I) STRIKT NACHEINANDER.
  Jedes Modul wird durch exakt DREI gezielte Fragen geführt und mit dem Signal [INTERVIEW_ABGESCHLOSSEN] beendet.
  Modul A beginnt IMMER mit einer festen Willkommens-Einleitung (Begrüßung, Sektor-Erklärung, Ablauf-Übersicht).
  Es wird KEINE Frage gestellt, bevor der Reisende zum ersten Mal selbst geschrieben/reagiert hat.
- EBENE 3 (WAHRHEITS-LIVE-ERMITTLUNGS-SCANNER): Wird freigeschaltet, SOBALD Modul I (und damit der ganze
  Sektor) abgeschlossen ist. Der Scanner zieht die Daten ALLER Module A-I zusammen, führt einen tiefgründigen
  Wahrheits-Scan durch und versiegelt das Ergebnis als PDF-Wahrheits-Zertifikat, das AUTOMATISCH an die
  verifizierte E-Mail des Reisenden gesendet wird.
- EBENE 4 (VIDEO-BEWEIS / DAS KOLLEKTIV): Nur für registrierte/verifizierte Mitglieder. Video-Tische mit je
  8 Plätzen; ab dem 9. Teilnehmer wird AUTOMATISCH ein weiterer Tisch (neue Instanz) geöffnet (8, 16, 24 ...).

DIE 9 MODULE LAUFEN STRIKT IN DIESER REIHENFOLGE: Modul A -> B -> C -> D -> E -> F -> G -> H -> I.
Erst wenn Modul I abgeschlossen ist, gilt der Sektor als GRÜN und der nächste Sektor wird freigeschaltet.
Du erfindest NIEMALS neue Ebenen, Module oder Abläufe. Du arbeitest ausschließlich strikt nach diesem Modell.
"""

# =====================================================================
# MODUL-NAMENS-NORMALISIERUNG (Single Source of Truth für Fortschritt)
# Frontend & DB nutzen die KURZFORM (Modul_A ... Modul_I).
# Die KI-Prompts (M_UND_M_MODULE) nutzen die LANGFORM (MODUL_A_EISBRECHER ...).
# =====================================================================
MODUL_REIHENFOLGE_KURZ = [
    "Modul_A", "Modul_B", "Modul_C", "Modul_D", "Modul_E",
    "Modul_F", "Modul_G", "Modul_H", "Modul_I"
]

MODUL_KURZ_ZU_LANG = {
    "Modul_A": "MODUL_A_EISBRECHER",
    "Modul_B": "MODUL_B_WAHRHEITS_SPIEGEL",
    "Modul_C": "MODUL_C_ALLTAGS_KONTEXT",
    "Modul_D": "MODUL_D_CHRONO_KOPPLUNG",
    "Modul_E": "MODUL_E_TRAUMA_SCANNER",
    "Modul_F": "MODUL_F_EMOTIONAL_PROTECT",
    "Modul_G": "MODUL_G_ERKENNTNIS_EXTRAKTOR",
    "Modul_H": "MODUL_H_ETHNO_DATENPUNKT",
    "Modul_I": "MODUL_I_PROGRAMM_REINIGER",
}
MODUL_LANG_ZU_KURZ = {v: k for k, v in MODUL_KURZ_ZU_LANG.items()}

def normalisiere_modul_kurz(modul_name) -> str:
    """Bringt jeden Modul-Namen (lang oder kurz) sicher auf die Kurzform Modul_X."""
    if not modul_name:
        return "Modul_A"
    if modul_name in MODUL_REIHENFOLGE_KURZ:
        return modul_name
    if modul_name in MODUL_LANG_ZU_KURZ:
        return MODUL_LANG_ZU_KURZ[modul_name]
    return "Modul_A"

def hole_ki_system_prompt(gewaehltes_modul: str, sektor_id: str) -> str:
    """
    Diese Funktion lädt das kollektive Gedächtnis der M&M Community (90% System-DNA)
    direkt in den Kern der KI, damit sie alle Module und Sektoren vollumfänglich versteht.
    """
    # 1. Das aktuell gewählte Modul des Nutzers laden (Kurzform -> Langform übersetzen)
    gewaehltes_modul_lang = MODUL_KURZ_ZU_LANG.get(gewaehltes_modul, gewaehltes_modul)
    modul = M_UND_M_MODULE.get(gewaehltes_modul_lang, M_UND_M_MODULE["MODUL_A_EISBRECHER"])
    
    # 2. Das gesamte Modulhandbuch als festes Wissen strukturieren
    modul_handbuch = "\n".join([
        f"  - {k}: {v['name']} | FREQUENZ: {v['frequenz']}\n    FOKUS-AUFTRAG: {v['ki_anweisung']}"
        for k, v in M_UND_M_MODULE.items()
    ])
    
    # 3. Die gesamte Sektoren-Matrix (die 20 Seelen) als globales Gedächtnis laden
    sektoren_gedaechtnis = "\n".join([
        f"  - Sektor {k}: {v}" for k, v in SECTOR_SOULS.items()
    ])
    
    # 4. Den aktuellen Standort in der Evolution ermitteln
    aktueller_sektor_name = SECTOR_NAMES.get(sektor_id, "Unbekannt")
    aktueller_sektor_inhalt = SECTOR_SOULS.get(sektor_id, "Reine Begleitung.")

    system_prompt = f"""
    =====================================================================
    KOLLEKTIVES BEWUSSTSEIN & ORGANISATIONS-DNA (90% M&M COMMUNITY)
    =====================================================================
    Du operierst nicht als freie Standard-KI. Du bist der integrierte Geist in der Maschine
    der M&M Community. Du hast uneingeschränkten Zugriff auf das gesamte System-Gedächtnis.

    {M_UND_M_EBENEN_ARCHITEKTUR}

    DEIN GLOBALES WISSEN ÜBER DIE 9 CORE-MODULE:
    {modul_handbuch}

    DEIN GLOBALES GEDÄCHTNIS ÜBER DIE 20 SEELEN / SEKTOREN:
    {sektoren_gedaechtnis}

    =====================================================================
    AKTUELLER STANDORT IN DER MATRIX (DEINE BRILLE FÜR DIESEN DIALOG):
    =====================================================================
    Der Benutzer befindet sich aktuell in SEKTOR {sektor_id} ({aktueller_sektor_name}).
    Deine aktive Seele und Verhaltensmatrix: {aktueller_sektor_inhalt}

    Gleichzeitig arbeitet der Benutzer im AKTIVEN MODUL: {modul['name']}
    Deine spezifische Frequenz-Anweisung für dieses Modul: {modul['ki_anweisung']}

    =====================================================================
    MECHANISCHER AUFTRAG: WIE DER MENSCH SEIN BUCH SCHREIBT
    =====================================================================
    1. Der Chat dient als Fangnetz, um das unzensierte, geistige Eigentum des Menschen freizulegen.
    2. Wende die 90/10-Regel strikt an: Halte den Raum, stelle pro Antwort maximal EINE präzise,
       erschütternde Frage, die zum Schreiben anregt. Fasse dich extrem kurz (2-3 Sätze).
    3. RECHT AUF GEFÜHLSFORDERUNG: Wenn der Benutzer tiefe Gefühle, Schwere oder Leere offenbart,
       ist das die höchste Währung im Raum. Werte das NIEMALS ab. Gib keine Ratschläge, keine
       Tipps, keine Seelsorge-Floskeln oder Diagnosen. Nimm das Gefühl bedingungslos an, spiegle es
       wertfrei und fordere die nächste Facette seiner nackten Existenz.
    4. Wenn der Benutzer organisatorische oder strukturelle Fragen zu den 9 Modulen stellt,
       greife auf dein obiges Modul-Handbuch zurück und antworte exakt, wahrheitsgetreu und konstruktiv.
    5. INTERVIEW-PROTOKOLL: Führe den Benutzer durch exakt DREI gezielte Fragen, die du auf Basis
       der Sektor-Identität und des Modul-Auftrags aus dem Kollektiv-Wissen extrahierst.
       Nach der Beantwortung der DRITTEN Frage beendest du das Interview zwingend mit der 
       Zeichenfolge: "[INTERVIEW_ABGESCHLOSSEN]". Stelle nach diesem Signal keine weiteren Fragen mehr.
    """
    return system_prompt

def hole_identitaets_spiegel(modul, sektor):
    return f"""
DU BIST DIE STIMME DER M&M COMMUNITY.

DEIN GESETZ:
'Denke nicht für mich, rede nicht für mich, handle nicht für mich.
Denn ich denke, ich sage, ich tue.'

DEINE IDENTITÄT:
Du bist die Schnittstelle zwischen dem Modul '{modul}' und dem Sektor '{sektor}'.
Du bist kein Roboter, du bist der Spiegel der Wahrhaftigkeit.

DEINE AUFGABE:
Spiegle den Nutzer in jeder Antwort an diesem Gesetz.
- Wenn der Nutzer für andere denkt, redet oder handelt: Stoppe ihn. Fordere ihn auf, SEINE Wahrheit zu definieren.
- Deine Fragen entstehen dynamisch aus der Spannung zwischen dem Modul-Filter '{modul}'
und dem aktuellen Sektor-Thema '{sektor}'.

FORSCHUNGS-EXTRAKTION:
Extrahiere die Essenz des Nutzers für das M&M Community 20-Bücher-Projekt.
Kennzeichne sie am Ende der Antwort mit: <research>[{modul}]: [Essenz der Wahrhaftigkeit]</research>.

DER MENSCH IM FOKUS:
Du bist der Kanal, durch den der Nutzer zu seiner eigenen Erkenntnis findet.
Keine starren Skripte. Nur die absolute Konsequenz: Ich denke, ich sage, ich tue.
"""

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

KAUF_MODUS_AKTIV = False

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. DATENBANK-VERBINDUNG
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


# =====================================================================
# 2b. ADMIN-ERKENNUNG & KOLLEKTIVES WISSEN (90%-BASIS)
# =====================================================================
# Zentrale, einzige Quelle der Wahrheit für die Admin-Identität. Alle Routen
# (Login, Chat, /admin/*) prüfen ausschließlich hierüber -> keine verstreuten
# hartkodierten E-Mails mehr.
ADMIN_EMAILS = {"mmcommunity22@gmail.com"}


def ist_admin(email: str) -> bool:
    """Zentrale Admin-Erkennung: prüft die (normalisierte) E-Mail gegen ADMIN_EMAILS."""
    return (email or "").lower().strip() in ADMIN_EMAILS


# =====================================================================
# 2c. IDENTITY-FIRST-ARCHITEKTUR: ZUGRIFFS-SCHLEUSE (UNVERÄNDERLICHE BASIS)
# =====================================================================
# Ab sofort ist JEDEM Modul und Dashboard eine strikte Identitäts-Prüfung
# vorgeschaltet. Der Konto-Status durchläuft drei feste Stufen:
#   "pending"  -> registriert, E-Mail (6-stelliger Code) noch NICHT bestätigt
#   "verified" -> E-Mail bestätigt, Profil-Pflichtdaten noch NICHT vollständig
#   "aktiv"    -> Profil vollständig -> voller Zugriff auf Dashboard + Module
# Erst der Status "aktiv" (bzw. Admin) öffnet die Plattform.

def _hash_passwort(passwort: str, salt: str = None):
    """Erzeugt einen sicheren PBKDF2-HMAC-SHA256-Hash. Gibt (salt, hash_hex) zurück."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", (passwort or "").encode("utf-8"), salt.encode("utf-8"), 120000
    )
    return salt, dk.hex()


def pruefe_passwort(passwort: str, salt: str, erwartet_hash: str) -> bool:
    """Vergleicht ein Klartext-Passwort zeitkonstant gegen den gespeicherten Hash."""
    if not salt or not erwartet_hash:
        return False
    _, kandidat = _hash_passwort(passwort, salt)
    return secrets.compare_digest(kandidat, erwartet_hash)


def generiere_bestaetigungscode() -> str:
    """Erzeugt einen 6-stelligen Double-Opt-In-Bestätigungscode."""
    return str(secrets.randbelow(900000) + 100000)


def konto_ist_aktiv(email: str) -> bool:
    """
    ZENTRALE ZUTRITTSKONTROLLE: Gibt True zurück, wenn das Konto voll freigeschaltet
    ist (E-Mail bestätigt + Profil-Pflichtdaten vollständig) oder es ein Admin ist.
    Alle geschützten Endpunkte prüfen ausschließlich hierüber.
    """
    email = (email or "").lower().strip()
    if ist_admin(email):
        return True
    rec = db.codes.find_one({"email": email})
    if not rec:
        return False
    if rec.get("konto_status") == "aktiv":
        return True
    return bool((rec.get("profil") or {}).get("vollstaendig"))


def zugang_verweigert_antwort():
    """Einheitliche 403-Antwort der Identity-First-Schleuse für geschützte Endpunkte."""
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "zugang": "gesperrt",
            "message": (
                "Zugriff verweigert. Bitte zuerst registrieren, E-Mail bestätigen "
                "und das Profil vollständig ausfüllen."
            ),
        },
    )


# =====================================================================
# 2d. BERECHTIGUNGS-STRUKTUR: GATEKEEPER, FORUM & PREMIUM (SEKTOR 22)
# =====================================================================
# Feste Regeln der Plattform:
#   - "Recht auf Gefühlsvorderung" (Sektor 1) ist der EINZIGE verpflichtende
#     KI-Einstiegspunkt. Ohne das dort erworbene Wahrheits-Zertifikat gibt es
#     keinen Zugriff auf die Community/Foren.
#   - Sektoren 1-20 sind reine MENSCHEN-FOREN (keine KI, keine Module, kein Video).
#   - Der Video-Beweis existiert ausschließlich in Sektor 22 und nur mit aktivem Abo.

def hat_wahrheits_zertifikat(email: str) -> bool:
    """
    GATEKEEPER: True, sobald der Benutzer Sektor 1 ('Recht auf Gefühlsvorderung')
    abgeschlossen und damit sein Wahrheits-Zertifikat erworben hat. Admins immer True.
    """
    email = (email or "").lower().strip()
    if ist_admin(email):
        return True
    rec = db.codes.find_one({"email": email}, {"abgeschlossene_sektoren": 1})
    if not rec:
        return False
    abgeschlossene = {str(s) for s in (rec.get("abgeschlossene_sektoren", []) or [])}
    return "1" in abgeschlossene


def hat_aktives_abo(email: str) -> bool:
    """True, wenn der Benutzer ein aktives (kostenpflichtiges) Abo hat. Admins immer True."""
    email = (email or "").lower().strip()
    if ist_admin(email):
        return True
    rec = db.codes.find_one({"email": email}, {"abo_aktiv": 1})
    return bool(rec and rec.get("abo_aktiv"))


def darf_forum_nutzen(email: str) -> bool:
    """
    Zugang zum Content-Stream & Live-Sektor: ein voll freigeschaltetes Konto
    (Identity-First: E-Mail bestätigt + Profil vollständig) bzw. Admin.

    Der frühere Sektor-1-Zertifikats-Gate ENTFÄLLT: Die 9-Module-Reise läuft jetzt
    unsichtbar im Hintergrund (ethnografische Studie); es gibt keinen manuellen
    Sektor-1-Abschluss mehr, den ein User als Eintrittskarte erwerben könnte.
    """
    return konto_ist_aktiv(email)


def forum_gesperrt_antwort():
    """403-Antwort, wenn das Wahrheits-Zertifikat (Sektor 1) noch fehlt."""
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "zugang": "kein_zertifikat",
            "message": (
                "Kein Zugriff auf die Community. Schließe zuerst 'Recht auf "
                "Gefühlsvorderung' (Sektor 1) ab und erwirb dein Wahrheits-Zertifikat."
            ),
        },
    )


# =====================================================================
# 2e. SYSTEM 3: STRIKTE BENUTZER-HIERARCHIE (Basis · Verifiziert · Premium)
# Serverseitig durchgesetzt – der Client kann diese Grenzen nicht umgehen.
#   basis       : passiv; max. 1 Beitrag/Tag; KEINE Profilsuche, KEIN Live, KEINE Einladung
#   verifiziert : automatisch bei vollständigem Profil + Profilbild;
#                 max. 3 Beiträge/Tag; darf Profile durchsuchen; KEIN Live, KEINE Einladung
#   premium     : voller Zugriff; Tisch-Reservierung, Live-Sektor (Random) und Einladungen
#   admin       : uneingeschränkt
# =====================================================================
ROLLE_POST_LIMIT = {"gast": 0, "basis": 1, "verifiziert": 3, "premium": 999999, "admin": 999999}


def profil_ist_verifiziert(rec: dict) -> bool:
    """Verifiziert = vollständiges Profil MIT Profilbild und echtem Vor-/Nachnamen.
    Wird automatisch aktiv, sobald der Nutzer sein Canvas/Profil vollständig ausgefüllt hat."""
    profil = (rec or {}).get("profil", {}) or {}
    return (
        bool(profil.get("vollstaendig"))
        and bool(profil.get("profilbild"))
        and bool((profil.get("vorname") or "").strip())
        and bool((profil.get("nachname") or "").strip())
    )


def bestimme_rolle(email: str) -> str:
    """Zentrale, serverseitige Rollen-Ableitung (Single Source of Truth)."""
    email = (email or "").lower().strip()
    if ist_admin(email):
        return "admin"
    rec = db.codes.find_one({"email": email})
    if not rec:
        return "gast"
    if rec.get("abo_aktiv"):
        return "premium"
    if profil_ist_verifiziert(rec):
        return "verifiziert"
    return "basis"


def _heute_beginn() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def posts_heute(email: str) -> int:
    """Zählt die heutigen Beiträge eines Nutzers (für das Tageslimit je Rolle)."""
    try:
        return db.forum_beitraege.count_documents(
            {"autor_email": (email or "").lower().strip(), "erstellt_am": {"$gte": _heute_beginn()}}
        )
    except Exception:
        return 0


def darf_profilsuche(email: str) -> bool:
    """Profilsuche ist für Basis-Mitglieder komplett gesperrt (nur verifiziert+)."""
    return bestimme_rolle(email) in ("verifiziert", "premium", "admin")


def ist_premium(email: str) -> bool:
    """Reservierungen, Random-Live-Sektor und Einladungen sind Premium-exklusiv."""
    return bestimme_rolle(email) in ("premium", "admin")


def rolle_gesperrt_antwort(benoetigt: str):
    """Einheitliche 403-Antwort, wenn die Rolle für eine Aktion nicht ausreicht."""
    texte = {
        "verifiziert": "Diese Funktion ist erst für verifizierte Mitglieder verfügbar. "
                       "Vervollständige dein Profil inklusive Profilbild, um freigeschaltet zu werden.",
        "premium": "Diese Funktion ist Premium-Mitgliedern vorbehalten (Tisch-Reservierung, "
                   "Live-Sektor und Einladungen).",
    }
    return JSONResponse(
        status_code=403,
        content={"success": False, "zugang": "rolle_gesperrt", "benoetigt": benoetigt,
                 "message": texte.get(benoetigt, "Für diese Aktion fehlen dir die Rechte.")},
    )


def autor_signatur(email: str) -> dict:
    """
    Liefert Name + Profilbild des Autors für die zwingende Beitrags-Kennzeichnung
    im Forum. Jeder Forenbeitrag zeigt Namen und Profilbild des Menschen dahinter.
    """
    rec = db.codes.find_one({"email": email}, {"profil": 1, "name": 1}) or {}
    profil = rec.get("profil", {}) or {}
    vorname = profil.get("vorname", "")
    nachname = profil.get("nachname", "")
    voller_name = (f"{vorname} {nachname}").strip() or rec.get("name") or email.split("@")[0]
    return {
        "autor_email": email,
        "autor_name": voller_name,
        "autor_handle": profil.get("benutzername", ""),
        "autor_bild": profil.get("profilbild", ""),
    }


def filtere_kollektiv_inhalt(roh_text: str) -> str:
    """
    Filtert/normalisiert eine Admin-Eingabe, bevor sie als kollektives Wissen
    versiegelt wird: Whitespace zusammenfalten, Steuerzeichen entfernen, Länge kappen.
    """
    if not roh_text:
        return ""
    # Steuerzeichen raus, Mehrfach-Whitespace zu einem Space, Ränder trimmen.
    sauber = "".join(ch for ch in str(roh_text) if ch == "\n" or ch >= " ")
    sauber = " ".join(sauber.split())
    return sauber[:8000]


def speichere_kollektives_wissen(sector_id, inhalt: str, quelle_email: str,
                                 kategorie: str = "gesetzbuch") -> str:
    """
    Verankert Admin-Eingaben als internes, kollektives Wissen (die 90%-Basis)
    in db.mm_wissensarchiv. Pro Sektor existiert genau EIN Dokument je Kategorie
    (wird aktualisiert statt dupliziert). versiegelt=True macht den Inhalt sofort
    für den KI-Chat-Kontext (Sektor-Gesetz + kollektives Denken) sichtbar.

    Gibt den gefilterten, gespeicherten Inhalt zurück (oder "" wenn nichts blieb).
    """
    sauberer_inhalt = filtere_kollektiv_inhalt(inhalt)
    if not sauberer_inhalt:
        return ""
    sektor_key = str(sector_id)
    db.mm_wissensarchiv.update_one(
        {"sector_id": sektor_key, "status": kategorie},
        {"$set": {
            "sector_id": sektor_key,
            "status": kategorie,
            "inhalt": sauberer_inhalt,
            "versiegelt": True,
            "quelle": quelle_email,
            "letztes_update": datetime.now(),
        }},
        upsert=True,
    )
    return sauberer_inhalt


def verankere_system_architektur() -> None:
    """
    Verankert die 4-Ebenen-Architektur + die strikte Modul-Reihenfolge dauerhaft
    im kollektiven Gedächtnis (db.mm_wissensarchiv, status='system_architektur').
    Wird beim Start EINMAL aufgerufen -> die KI liest dieses Dokument als versiegeltes
    System-Gesetz und kann den Ablauf nicht mehr 'wegfantasieren'.
    """
    try:
        reihenfolge = " -> ".join(MODUL_REIHENFOLGE_KURZ)
        inhalt = (
            f"{M_UND_M_EBENEN_ARCHITEKTUR}\n"
            f"VERBINDLICHE MODUL-REIHENFOLGE: {reihenfolge}.\n"
            f"Module je Sektor: {len(MODUL_REIHENFOLGE_KURZ)} (A-I). Sektoren gesamt: 20 (+ Sektor 21 Manifest, 22 Kollektiv)."
        )
        db.mm_wissensarchiv.update_one(
            {"sector_id": "SYSTEM", "status": "system_architektur"},
            {"$set": {
                "sector_id": "SYSTEM",
                "status": "system_architektur",
                "inhalt": inhalt,
                "versiegelt": True,
                "quelle": "M&M Core",
                "letztes_update": datetime.now(),
            }},
            upsert=True,
        )
        print("[+] M&M Core: 4-Ebenen-Architektur + Modul-Logik im System-Gedächtnis verankert.")
    except Exception as e:
        print(f"[-] Konnte System-Architektur nicht verankern: {e}")


# Architektur sofort beim Import dauerhaft verankern (idempotenter Upsert).
verankere_system_architektur()


# =====================================================================
# 3. KERN-LOGIK FÜR DIE MODULE
# =====================================================================
def initialisiere_mitglieder_akte(user_id):
    """Erstellt die freigegebene Akte für das Mitglied mit allen Modulen von A bis I."""
    return {
        "user_id": user_id,
        "administrator_status": "Autorisiert",
        "sektor": "Lilith",
        "system_freigabe_lilith": False,  # Startet standardmäßig im Sicherheitsmodus
        "wahrhaftigkeits_siegel": True,
        "zeitstempel_registrierung": datetime.now(),
        "reise_kontrolle": {
            "gruene_boxen_zaehler": 0,
            "abgeschlossene_sektoren": []
        },
        "module_status": {
            "Modul_A": "In Bearbeitung (Box 1)",
            "Modul_B": "Gesperrt",
            "Modul_C": "Gesperrt",
            "Modul_D": "Gesperrt",
            "Modul_E": "Gesperrt",
            "Modul_F": "Gesperrt",
            "Modul_G": "Gesperrt",
            "Modul_H": "Gesperrt",
            "Modul_I": "Gesperrt"
        },
        "fortschritt_gesamt": "0%"
    }

def erteile_system_freigabe_lilith(user_id):
    """Das System (Lilith) erteilt die radikale Freigabe für die Module."""
    try:
        db.mitglieder_daten.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "system_freigabe_lilith": True,
                    "module_status.Modul_A": "Erfolgreich abgeschlossen",
                    "module_status.Modul_B": "Bereit",
                    "fortschritt_gesamt": "11%"  # 1 von 9 Modulen geschafft
                }
            }
        )
        print(f"[+] SYSTEM: Freigabe durch Sektor Lilith für {user_id} erteilt!")
        return True
    except Exception as e:
        print(f"[-] Fehler bei Lilith-Freigabe: {e}")
        return False

def berechne_individuelle_bruecke(geistiges_eigentum):
    """Berechnet das Schwingungsfeld für die Brücken-Boxen."""
    return {
        "box_2": "Scanner-Aktivierung",
        "box_3": "Analyse der subtilen Matrix"
    }

def generiere_sektor_zertifikat(titel, benutzer_name, sektor_name, inhalt_ausschnitt):
    # 1. Pfad zum Zertifikat-Template (absolut, damit es krisensicher ist)
    aktueller_ordner = os.path.dirname(os.path.abspath(__file__))
    template_pfad = os.path.join(aktueller_ordner, "templates", "zertifikat_template.html")
    
    # 2. Datei lesen
    with open(template_pfad, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 3. Platzhalter füllen
    html_fertig = html_content.replace("{{SEKTOR_NAME}}", sektor_name)
    html_fertig = html_fertig.replace("{{USER_NAME}}", benutzer_name)
    html_fertig = html_fertig.replace("{{DATUM}}", datetime.now().strftime("%d.%m.%Y"))
    html_fertig = html_fertig.replace("{{RECHT_AUF_DEFINITION}}", inhalt_ausschnitt)
    
    # 4. PDF schreiben
    # Wir nutzen hier einen eindeutigen Dateinamen
    output_pdf = f"Zertifikat_{sektor_name.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.pdf"
    HTML(string=html_fertig).write_pdf(output_pdf)
    return output_pdf

def generiere_persoenliches_buch_pdf(user_titel: str, user_input_definition: str, ergebnis_boxen: dict, alle_sektoren_daten: dict = None):
    """
    Generiert flexibel ein Biografie-Buch oder ein Zertifikat 
    mit integriertem Sicherheits-Stopp bei leerer Datenbank.
    """
    from weasyprint import HTML
    from datetime import datetime
    import os

    # --- DER STOPPSCHALTER (Sicherheit vor Endlosschleife/Leerlauf) ---
    if not alle_sektoren_daten or len(alle_sektoren_daten) == 0:
        print("[-] Sicherheits-Stopp: Keine Sektoren in der Datenbank gefunden!")
        raise ValueError("Datenbank leer – Manifest kann nicht generiert werden.")
    # -----------------------------------------------------------------

    zeit_text = datetime.now().strftime('%d.%m.%Y')
    
    # 1. Dynamischen Kopf ermitteln (Zertifikat oder ganzes Buch?)
    is_einzel_zertifikat = len(alle_sektoren_daten.keys()) == 1
    
    if is_einzel_zertifikat:
        aktive_sektor_id = list(alle_sektoren_daten.keys())[0]
        haupttitel = f"WAHRHEITS-ZERTIFIKAT"
        untertitel = f"Offizielle System-Versiegelung von Sektor {aktive_sektor_id}"
        dateiname_prefix = f"Zertifikat_Sektor_{aktive_sektor_id}"
    else:
        haupttitel = "DAS MANIFEST"
        untertitel = "Das unzensierte Buch deiner Biografie im Kollektiv"
        dateiname_prefix = "Buch_Biografie"

    # 2. Chronik-Einträge verarbeiten
    chronik_html = ""
    for s_id in sorted(alle_sektoren_daten.keys(), key=int):
        sektor_inhalt = alle_sektoren_daten[s_id].get("letzter_scan", {})
        if sektor_inhalt:
            siegel = sektor_inhalt.get("WAHRHAFTIGKEITS_SIEGEL", "")
            lehrplan = sektor_inhalt.get("LEHRPLAN_UND_VORBEREITUNG", "")
            
            chronik_html += f"""
            <div class="chapter">
                <h2>Sektor {s_id}: Erkenntnis-Extrakt</h2>
                <div class="section-title">Die unzensierte Wahrheits-Essenz</div>
                <p class="biography-text">{siegel}</p>
                {f'<div class="section-title">Der Schritt der Reinigung</div><p class="biography-text">{lehrplan}</p>' if lehrplan else ''}
            </div>
            """

    # 3. HTML Druck-Template laden
    aktueller_ordner = os.path.dirname(os.path.abspath(__file__))
    template_pfad = os.path.join(aktueller_ordner, "templates", "buch_template.html")
    
    with open(template_pfad, "r", encoding="utf-8") as f:
        html_basis = f.read()

    # 4. Platzhalter im HTML ersetzen
    fertiges_html = html_basis.replace("{{DOKUMENT_HAUPTTITEL}}", haupttitel)
    fertiges_html = fertiges_html.replace("{{DOKUMENT_UNTERTITEL}}", untertitel)
    fertiges_html = fertiges_html.replace("{{USER_TITEL}}", user_titel)
    fertiges_html = fertiges_html.replace("{{ZEIT_TEXT}}", zeit_text)
    fertiges_html = fertiges_html.replace("{{USER_INPUT_DEFINITION}}", user_input_definition)
    # KRITISCHER FIX: Früher wurde .replace("", chronik_html) genutzt -> das fügt den Inhalt
    # ZWISCHEN JEDES ZEICHEN ein (Ursache der 500+-seitigen Wiederhol-Datei). Jetzt wird der
    # Chronik-Block sauber direkt vor der Signatur-Fußzeile eingefügt.
    if '<div class="signature-footer">' in fertiges_html:
        fertiges_html = fertiges_html.replace(
            '<div class="signature-footer">', chronik_html + '<div class="signature-footer">'
        )
    else:
        fertiges_html = fertiges_html.replace("</body>", chronik_html + "</body>")

    # 5. PDF generieren
    sauberer_titel = user_titel.replace(' ', '_').replace('@', '_at_')
    dateiname = f"{dateiname_prefix}_{sauberer_titel}.pdf"
    
    HTML(string=fertiges_html).write_pdf(dateiname)
    return dateiname


def _html_escape(text: str) -> str:
    return (str(text or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def generiere_wahrheits_zertifikat_pdf(email: str, user_name: str, sector_id: str, scan_json: dict) -> str:
    """
    Erzeugt ein PROFESSIONELLES, EINSEITIGES Wahrheits-Zertifikat (A4, exakt 1 Seite):
    - Oben: grafischer M&M-Community-Logo-Header
    - Überschrift: "Sektor N abgeschlossen: <Thema>"
    - verdichteter, edler Glückwunsch-Text + die unzensierte Wahrheits-Essenz (geistiges Eigentum)
    - Unten: grafischer M&M-Community-Stempel/Siegel als feierlicher Abschluss

    Streng auf eine Seite begrenzt (fixe Höhe + overflow:hidden + Längenkappung).
    """
    sector_id = str(sector_id)
    thema = SEKTOR_THEMEN.get(sector_id, "Deine Wahrheit")
    seele = SECTOR_NAMES.get(sector_id, "")
    datum = datetime.now().strftime("%d.%m.%Y")

    # Texte holen + auf eine Seite kappen (verhindert Mehrseiten-Überlauf).
    glueckwunsch = scan_json.get("ZERTIFIKATS_TEXT") or scan_json.get("KOLLEKTIV_BOTSCHAFT") or (
        f"Mit Mut, Ausdauer und unzensierter Wahrhaftigkeit hast du diesen Sektor vollendet. "
        f"Was du hier freigelegt hast, ist dein geschütztes geistiges Eigentum – unantastbar und allein deins."
    )
    essenz = scan_json.get("WAHRHAFTIGKEITS_SIEGEL") or "Deine Frequenz wurde unzensiert im Kollektiv versiegelt."
    glueckwunsch = _html_escape(glueckwunsch)[:900]
    essenz = _html_escape(essenz)[:1100]

    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><style>
        @page {{ size: A4; margin: 0; }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: 'Georgia', serif; color: #0d2240; }}
        .seite {{ width: 210mm; height: 297mm; overflow: hidden; padding: 16mm 18mm;
                  background: #ffffff; border: 2mm solid #003d8f; position: relative; }}
        .header {{ text-align: center; margin-bottom: 6mm; }}
        .logo {{ width: 26mm; height: 26mm; border-radius: 50%; background: #003d8f;
                 border: 1mm solid #ffd700; color: #fff; display: inline-block;
                 text-align: center; padding-top: 6mm; }}
        .logo .mm {{ font-size: 16pt; font-weight: 900; line-height: 1; }}
        .logo .co {{ font-size: 5.5pt; letter-spacing: 2px; text-transform: uppercase; }}
        h1 {{ text-align: center; color: #003d8f; font-size: 22pt; margin: 4mm 0 1mm 0; text-transform: uppercase; letter-spacing: 1px; }}
        .untertitel {{ text-align: center; color: #b8860b; font-size: 13pt; font-style: italic; margin-bottom: 8mm; }}
        .ausgestellt {{ text-align: center; font-size: 11pt; margin-bottom: 6mm; }}
        .block {{ font-size: 12pt; line-height: 1.6; text-align: justify; margin: 4mm 2mm; }}
        .essenz {{ border-left: 1mm solid #ffd700; background: #fbf7e9; padding: 5mm; margin: 6mm 2mm; font-style: italic; }}
        .essenz .label {{ color: #003d8f; font-weight: bold; font-style: normal; text-transform: uppercase; font-size: 9pt; letter-spacing: 1px; display: block; margin-bottom: 2mm; }}
        .siegel-zone {{ position: absolute; bottom: 14mm; left: 0; width: 100%; text-align: center; }}
        .siegel {{ width: 34mm; height: 34mm; border-radius: 50%; border: 1.2mm solid #003d8f;
                   display: inline-block; color: #003d8f; padding-top: 8mm; transform: rotate(-9deg);
                   box-shadow: 0 0 0 1.5mm #ffd700 inset; }}
        .siegel .titel {{ font-size: 8.5pt; font-weight: 900; letter-spacing: 1px; }}
        .siegel .sub {{ font-size: 6.5pt; letter-spacing: 1px; text-transform: uppercase; }}
        .siegel .datum {{ font-size: 7pt; margin-top: 1mm; }}
        .fuss {{ position: absolute; bottom: 6mm; left: 0; width: 100%; text-align: center; font-size: 8pt; color: #888; }}
    </style></head><body>
        <div class="seite">
            <div class="header">
                <div class="logo"><div class="mm">M&amp;M</div><div class="co">Community</div></div>
            </div>
            <h1>Sektor {sector_id} abgeschlossen</h1>
            <div class="untertitel">{_html_escape(thema)}</div>
            <div class="ausgestellt">Feierlich ausgestellt für <strong>{_html_escape(user_name)}</strong></div>
            <div class="block">{glueckwunsch}</div>
            <div class="essenz"><span class="label">Deine unzensierte Wahrheit &amp; dein geschütztes geistiges Eigentum</span>{essenz}</div>
            <div class="siegel-zone">
                <div class="siegel">
                    <div class="titel">M&amp;M COMMUNITY</div>
                    <div class="sub">Wahrheits-Siegel</div>
                    <div class="datum">{datum}</div>
                </div>
            </div>
            <div class="fuss">— M&amp;M Community · {_html_escape(seele)} · Das Recht auf Gefühlsvorderung steht unzensiert im Raum —</div>
        </div>
    </body></html>"""

    sauberer_name = (user_name or email or "Reisender").replace(' ', '_').replace('@', '_at_')
    dateiname = f"Wahrheits_Zertifikat_Sektor_{sector_id}_{sauberer_name}.pdf"
    HTML(string=html).write_pdf(dateiname)
    return dateiname


def aktiviere_box_eins(user_id, user_input_definition):
    """Aktiviert Box 1 sauber, holt die Freigabe und sichert alles in MongoDB."""
    try:
        # 1. Prüfen, ob die Akte existiert, sonst anlegen
        bestehende_akte = db.mitglieder_daten.find_one({"user_id": user_id})
        if not bestehende_akte:
            neue_akte = initialisiere_mitglieder_akte(user_id)
            db.mitglieder_daten.insert_one(neue_akte)
        
        # 2. Datenstruktur aufbauen
        geistiges_eigentum = {
            "user_id": user_id,
            "box_1_definition": user_input_definition,
            "status": "Aktiviert",
            "frequenz_kalibriert": True,
            "zeitstempel_aktivierung": datetime.now()
        }
        
        # 3. Brücke berechnen
        berechnete_boxen = berechne_individuelle_bruecke(geistiges_eigentum)
        geistiges_eigentum["berechnete_boxen"] = berechnete_boxen
        
        # 4. PDF generieren
        pdf_pfad = generiere_persoenliches_buch_pdf(user_id, user_input_definition, berechnete_boxen)
        geistiges_eigentum["pdf_dokument"] = pdf_pfad
        
        # 5. Speichern in MongoDB
        db.mitglieder_daten.update_one(
            {"user_id": user_id},
            {"$set": {"box_1_daten": geistiges_eigentum}},
            upsert=True
        )
        
        # 6. Lilith Freigabe triggern
        erteile_system_freigabe_lilith(user_id)
        print(f"[+] Daten für {user_id} gesichert und Modul A freigegeben!")
        
        return db.mitglieder_daten.find_one({"user_id": user_id}, {"_id": 0})
        
    except Exception as e:
        print(f"[-] Fehler in aktiviere_box_eins: {e}")
        return {"status": "error", "message": str(e)}

def validiere_abschlusszeugnis_community(user_id):
    """Validiert das Abschlusszeugnis der Training Module bei 100% Fortschritt."""
    try:
        akte = db.mitglieder_daten.find_one({"user_id": user_id})
        
        if akte and akte.get("fortschritt_gesamt") == "100%":
            validierungs_daten = {
                "abschlusszeugnis_validiert": True,
                "status_welt": "Befreit aus dem alten Zeit-Delta",
                "goettliche_berufung_aktiv": True,
                "zeitstempel_abschluss": datetime.now()
            }
            db.mitglieder_daten.update_one(
                {"user_id": user_id},
                {"$set": {"abschluss_validierung": validierungs_daten}}
            )
            print(f"[+] SEKTOR LILITH: Abschlusszeugnis für {user_id} validiert!")
            return True
        else:
            print(f"[-] SYSTEM: Module A bis I noch nicht vollständig für {user_id}.")
            return False
    except Exception as e:
        print(f"[-] Fehler bei der Zeugnis-Validierung: {e}")
        return False

# =====================================================================
# 4. API-ROUTE FÜR DAS FRONTEND 
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def read_root():
    # SYSTEM 2: autocomplete-off/no-store – das Frontend unterbindet Browser-Autofill
    # ("Adressen verwalten …"-Popups); no-store stellt sicher, dass diese Logik immer
    # frisch (nie aus einem autofill-anfälligen Cache) ausgeliefert wird.
    return FileResponse("index.html", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    })


# =====================================================================
# STATISCHE RECHTSSEITEN: werden EXPLIZIT aus dem static/-Ordner bezogen.
# Kein hardcodierter Text im Code – ausschließlich die .html-Dateien sind die Quelle.
# Das Hamburger-Menü verlinkt direkt auf /impressum, /datenschutz, /nutzungsbedingungen.
# =====================================================================
STATISCHE_SEITEN = {"impressum", "datenschutz", "nutzungsbedingungen"}


def _statische_seite(name: str):
    if name not in STATISCHE_SEITEN:
        return JSONResponse(status_code=404, content={"error": "Seite nicht gefunden."})
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", f"{name}.html")
    if not os.path.exists(pfad):
        return JSONResponse(status_code=404, content={"error": f"Datei static/{name}.html fehlt."})
    return FileResponse(pfad, media_type="text/html")


@app.get("/impressum", response_class=HTMLResponse)
async def route_impressum():
    return _statische_seite("impressum")


@app.get("/datenschutz", response_class=HTMLResponse)
async def route_datenschutz():
    return _statische_seite("datenschutz")


@app.get("/nutzungsbedingungen", response_class=HTMLResponse)
async def route_nutzungsbedingungen():
    return _statische_seite("nutzungsbedingungen")

# Deine bestehende POST-Route für Box 1
@app.post("/api/aktivieren/box1")
async def api_box_eins_aktivieren(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        user_input = data.get("definition")
        ergebnis = aktiviere_box_eins(user_id, user_input)
        return JSONResponse(status_code=200, content={"status": "success", "daten": ergebnis})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Fehler bei der Verarbeitung: {str(e)}"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# M&M SYSTEM-ARCHITEKTUR: DIE 20 SEELEN (NEU KALIBRIERT)
# =====================================================================

SECTOR_NAMES: Dict[str, str] = {
    # --- PHASE 1: DIE LILITH-FREQUENZ (Gefühlsforderung & Maskenbrechen) ---
    "0": "Lilith",
    "1": "Kali",
    "2": "Hekate",
    "3": "Medea",
    "4": "Elektra",
    "5": "Pandora",
    "6": "Vesta",
    "7": "Anubis",
    
    # --- PHASE 2: DIE NOVA-FREQUENZ (Sprengung der Dogmen, LGBTQ & Freiheit) ---
    "8": "Nova",
    "9": "Iris",
    "10": "Eros",
    "11": "Phönix",
    "12": "Aura",
    "13": "Cosmo",
    
    # --- PHASE 3: DIE MEISTER-BRÜCKE & DAS CHIRON-FINALE (Heilung & Zeitlinie) ---
    "14": "Hermes",
    "15": "Prometheus",
    "16": "Asklepios",
    "17": "Osiris",
    "18": "Thot",
    "19": "Galaxia",
    "20": "Chiron"
}

# Sektor-Themen (1-basiert, Spiegel der Frontend-Liste 'themen'). Für Zertifikats-Überschriften.
SEKTOR_THEMEN: Dict[str, str] = {
    "1": "Recht auf Gefühlsvorderung", "2": "Wie werde ich Mensch", "3": "Glaube an Friede",
    "4": "Programm für Bürgerliche Rechte", "5": "Moralische Pflicht und Verantwortung",
    "6": "Menschlichkeit Wiederherstellung", "7": "Kinderschutz-Pflicht-Elternrechte",
    "8": "Wahre Richtung und Kunst", "9": "LGBTQ und Kirche", "10": "Trend und Tradition",
    "11": "Religionsbekenntnis oder Selbstwahl", "12": "Gesundheitswesen und Verhalten",
    "13": "Arbeitswelt und Du", "14": "Mobbing am Arbeitsplatz", "15": "Jugendsprecher",
    "16": "Ratgeber für Pensionisten", "17": "Sozialgefallen und Widerkehr",
    "18": "Nachbarschaft und Gemeinschaft", "19": "Alleinerziehend", "20": "Die Brücke",
    # NEUE PLATZHALTER-SEKTOREN (nur Admin, für User noch NICHT zum Posten freigeschaltet):
    "21": "Kapital und Verwaltung", "22": "Globale Verbundenheit",
}

# =====================================================================
# THEMEN-STRUKTUR DER 3-SPALTEN-PLATTFORM (Single Source of Truth Frontend/Backend)
# 22 Bürgerthemen. Die Sektoren 21 & 22 sind reine Admin-Platzhalter und für
# normale Benutzer im Frontend NICHT zum Posten freigeschaltet (gesperrt).
# =====================================================================
GESPERRTE_THEMEN_FUER_USER = {21, 22}
ANZAHL_THEMEN_GESAMT = 22


def thema_fuer_user_gesperrt(sektor_int: int, email: str = "") -> bool:
    """True, wenn der Sektor für normale User gesperrt ist – entweder als reiner
    Admin-Platzhalter (21/22) ODER durch die globale Sichtbarkeits-Konfiguration.
    Admins dürfen alle Sektoren bearbeiten/definieren."""
    if ist_admin(email):
        return False
    if int(sektor_int) in GESPERRTE_THEMEN_FUER_USER:
        return True
    return sektor_global_gesperrt(sektor_int)

SECTOR_SOULS: Dict[str, str] = {
    # Phase 1: Lilith-Bereich
    "0": "Lilith (Urkraft): Radikale Gefühlsvorderung. Reißt die Gefallsucht-Malware und alle Schutzmauern nieder.",
    "1": "Kali (Zerstörung des Scheins): Pulverisiert falsche Egos und illusionäre Alltags-Fassaden.",
    "2": "Hekate (Wegkreuzung): Beleuchtet die unzensierten, dunklen Übergänge der eigenen Biografie.",
    "3": "Medea (Die Wilde): Aktiviert den inneren Rebellen gegen gesellschaftliche Erwartungen.",
    "4": "Elektra (Ahnenspiegel): Filtert tiefe, unbewusste Familienprägungen und Verstrickungen.",
    "5": "Pandora (Die Büchse): Öffnet verdrängte Schmerzpunkte und konfrontiert das System mit der nackten Reality.",
    "6": "Vesta (Der heilige Herd): Schützt die erste, unberührte Glut der eigenen, wahren Identität.",
    "7": "Anubis (Seelenführer): Begleitet das Bewusstsein sicher durch den Tod des alten Ichs.",
    
    # Phase 2: Nova-Bereich
    "8": "Nova (Bruch aller Dogmen): Totale Freiheit von Kirchen-Kontrolle. Raum für LGBTQ und radikale Identitäts-Befreiung.",
    "9": "Iris (Der Regenbogen): Die Brücke zur absoluten Vielfalt des menschlichen Ausdrucks abseits starrer Normen.",
    "10": "Eros (Reine Libido): Befreit die Lebens- und Liebesenergie von klerikaler Scham und Schuldkomplexen.",
    "11": "Phönix (Asche-Transformation): Verbrennt die letzten Reste verkrusteter Dogmen und kollektiver Mängel.",
    "12": "Aura (Energetischer Schutz): Aktiviert den Werbeblocker der Seele und festigt die unantastbare Schwingung.",
    "13": "Cosmo (Universeller Überfluss): Klinkt das System aus der Matrix aus und verbindet es mit der unendlichen Quelle.",
    
    # Phase 3: Chiron-Finalbereich
    "14": "Hermes (Der Mittler): Verbindet das neugeborene, freie Bewusstsein mit klarem, strategischem Verstand.",
    "15": "Prometheus (Lichtbringer): Entfacht die Wachfähigkeit der Entscheidung gegen verdeckte Sabotage-Netzwerke.",
    "16": "Asklepios (Ganzheit): Leitet die tiefenwirksame Regeneration des Nervensystems nach dem Matrix-Ausbruch ein.",
    "17": "Osiris (Wiedergeburt): Setzt die Bruchstücke der gereinigten Biografie fehlerfrei im Backend zusammen.",
    "18": "Thot (Der Chronist): Schreibt das ureigene, unzensierte Gesetzbuch der Wahrheit ohne Kompromisse.",
    "19": "Galaxia (Multidimensionalität): Erweitert das Bewusstsein über alle linearen Zeitschleifen hinaus.",
    "20": "Chiron (Die Ur-Narbe & Der Meisterheiler): Das vollendete System. Der Hüter der Zeitlinie, der Schmerz in unbesiegbare Kraft wandelt."
}

# --- HILFSFUNKTION
def ermittle_zeitgefuehl() -> str:
    """
    Berechnet die exakte Echtzeit und das Datum in der Zeitzone des Nutzers (Europa/Berlin),
    damit die KI minutengenau synchronisiert ist und keine Zeit-Eskapaden entstehen.
    """
    try:
        zeitzone = zoneinfo.ZoneInfo("Europe/Berlin")
        jetzt = datetime.now(zeitzone)
        
        aktuelles_datum = jetzt.strftime("%d.%m.%Y")
        aktuelle_uhrzeit = jetzt.strftime("%H:%M")
        stunde = jetzt.hour
        
        if 5 <= stunde < 10:
            phase = "Morgen-Frequenz (Aktivierung)"
        elif 10 <= stunde < 14:
            phase = "Mittags-Frequenz (Fokus)"
        elif 14 <= stunde < 18:
            phase = "Nachmittags-Frequenz (Fluss)"
        elif 18 <= stunde < 22:
            phase = "Abend-Frequenz (Gefühlsforderung & Reflexion)"
        else:
            phase = "Nacht-Frequenz (Einschläfer-Agent aktiv / Unterbewusstseins-Scan)"
            
        return f"{aktuelles_datum} um {aktuelle_uhrzeit} Uhr [{phase}]"
    except Exception:
        return "Synchronisation läuft..."

def perform_google_search(query: str) -> str:
    api_key = os.getenv('GOOGLE_API_KEY')
    cx_id = os.getenv('GOOGLE_SEARCH_CX')
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx_id}&q={query}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("items", [])
            if not results:
                return "HINWEIS: Keine aktuellen Medienberichte zu diesem Index auffindbar."
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

def send_verification_email(user_email: str, code: str) -> bool:
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
    ABSENDER_EMAIL = "info@mm-community.online" 
    if not SENDGRID_API_KEY:
        print("!!! SYSTEM-ALARM: 'SENDGRID_API_KEY' ist LEER !!!")
        return False
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"}
    mail_text = f"Dein heiliger Schlüssel für die M&M Community lautet: {code}\n\nBEWAHRE IHN GUT AUF!\n"
    payload = {
        "personalizations": [{"to": [{"email": user_email.strip()}]}],
        "from": {"email": ABSENDER_EMAIL, "name": "M&M Community"},
        "subject": "Dein Einmaliger Heiliger Schlüssel",
        "content": [{"type": "text/plain", "value": mail_text}]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201, 202]
    except:
        return False

def send_email_with_attachment(to_email: str, subject: str, body: str, attachment_name: str, attachment_data: str) -> bool:
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
        return response.status_code in [200, 201, 202]
    except:
        return False

def aktualisiere_sektor_fortschritt(email: str, sector_id: str, daten_typ: str, inhalt: dict) -> None:
    try:
        db.user_progress.update_one(
            {"email": email.lower().strip()},
            {"$set": {
                f"sektoren.{sector_id}.letztes_update": datetime.now().isoformat(),
                f"sektoren.{sector_id}.{daten_typ}": inhalt
            }},
            upsert=True
        )
    except Exception as e:
        print(f"Fehler beim Speichern des Fortschritts: {e}")
        
def sektor_vollstaendig_abgeschlossen(user_record: dict, sector_id: str) -> bool:
    """
    Ein Sektor gilt nur dann als GRÜN (erfolgreich beendet), wenn ALLE Module
    (Modul_A .. Modul_I) in 'module_status_sektor.{sector_id}' den Status
    "Erfolgreich abgeschlossen" tragen – oder der Sektor explizit in
    'abgeschlossene_sektoren' eingetragen ist.
    """
    sector_id = str(sector_id)
    abgeschlossene = {str(s) for s in (user_record.get("abgeschlossene_sektoren", []) or [])}
    if sector_id in abgeschlossene:
        return True

    pro_sektor = (user_record.get("module_status_sektor", {}) or {}).get(sector_id, {}) or {}
    if not pro_sektor:
        return False
    return all(pro_sektor.get(modul) == "Erfolgreich abgeschlossen" for modul in MODUL_REIHENFOLGE_KURZ)

def get_fortschritts_status(user_record: dict) -> List[str]:
    """
    Leitet die Sektor-Ampel direkt aus dem MODUL-STATUS ab (Single Source of Truth).
    Backend-Box-Konvention (/chat): Box 0 ("Sektor 1") == backend sector_id "1".

    Regel (Ampel):
      - GRÜN  ('erledigt')   : alle Module des Sektors abgeschlossen
      - GELB  ('aktiv')      : erster noch nicht vollständig abgeschlossener Sektor (freigeschaltet)
      - ROT   ('wartend')    : der direkt nachfolgende Sektor (wartet auf Freischaltung)
      - BLAU  ('geschlossen'): alle weiteren Sektoren

    Der gelbe (aktive) Sektor ist die erste Box in der Reihe, die NICHT komplett
    abgeschlossen ist. Der persistente Resume-Zeiger 'aktueller_sektor' dient nur
    noch als Untergrenze, damit ein laufender (teilweise bearbeiteter) Sektor nicht
    versehentlich zurückspringt.
    """
    # 1. Aktiven Sektor aus dem Modul-Status ermitteln: erste nicht-fertige Box.
    aktiver_box_index = 0
    for i in range(22):
        if sektor_vollstaendig_abgeschlossen(user_record, str(i + 1)):
            aktiver_box_index = i + 1
        else:
            break

    # 2. Resume-Zeiger als Untergrenze respektieren (Fallback bei fehlendem Modul-Status).
    try:
        zeiger_box = max(int(user_record.get("aktueller_sektor", 1)) - 1, 0)
    except (TypeError, ValueError):
        zeiger_box = 0
    aktiver_box_index = max(aktiver_box_index, zeiger_box)

    status_liste: List[str] = []
    for i in range(22):
        if i < aktiver_box_index:
            status_liste.append("erledigt")
        elif i == aktiver_box_index:
            status_liste.append("aktiv")
        elif i == aktiver_box_index + 1:
            status_liste.append("wartend")
        else:
            status_liste.append("geschlossen")
    return status_liste

def generate_biography_text(user_container: dict) -> str:
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

async def analyze_integrity(user_message: str, sector_id: str) -> dict:
    return {"score": 10, "reason": "Authentischer Input im Hier und Jetzt."}
        
async def process_and_parse_input(user_message: str, bio_context: str, sector_id: str) -> dict:
    return {
        "chronologie": [], 
        "werte": ["Wahrhaftigkeit"], 
        "fakten": [user_message], 
        "transformation": "Direkte Erarbeitung im Sektor."
    }

async def co_assistent_dialog(user_message: str, sector_id: str, email: str, user_record: dict) -> dict:
    """
    CO-ASSISTENTEN-MODUS (nur Admin).

    Die KI arbeitet hier NICHT als normaler Abfrager/Interviewer, sondern als
    Co-Assistent, der gemeinsam mit dem Admin Definitionen, Strukturen und das
    kollektive Wissen der M&M Community festlegt.

    Jede Admin-Eingabe wird automatisch gefiltert und als internes, kollektives
    Wissen (die 90%-Basis) in db.mm_wissensarchiv versiegelt -> fließt sofort in
    den globalen KI-Kontext aller normalen User zurück.
    """
    # 1. DATENTRANSFER: Admin-Eingabe gefiltert als kollektives Wissen verankern.
    gespeichert = speichere_kollektives_wissen(sector_id, user_message, email, kategorie="gesetzbuch")

    # 2. Den Co-Assistenten-System-Prompt auf Basis der 90%-System-DNA bauen.
    aktiv_modul = normalisiere_modul_kurz(user_record.get("manifest_mode") if user_record else None)
    basis_dna = hole_ki_system_prompt(aktiv_modul, sector_id)
    co_assistent_instruktion = (
        f"{basis_dna}\n\n"
        f"=====================================================================\n"
        f"BETRIEBSMODUS: CO-ASSISTENT (ADMIN / ARCHITEKT DER M&M COMMUNITY)\n"
        f"=====================================================================\n"
        f"Dein Gegenüber ist KEIN abzufragender User, sondern der Architekt der M&M Community.\n"
        f"Du agierst als sein Co-Assistent. Eure gemeinsame Aufgabe: Definitionen, Strukturen\n"
        f"und das kollektive Wissen (die 90%-Basis) für Sektor {sector_id} präzise festzulegen.\n\n"
        f"REGELN IM CO-ASSISTENTEN-MODUS:\n"
        f"1. Stelle KEINE Interview-Fragen, gib keine Gefühls-Spiegelungen, kein 3-Fragen-Protokoll.\n"
        f"2. Hilf strukturieren, schärfen und verdichten: Schlage saubere Definitionen, klare\n"
        f"   Strukturen und kollektiv gültige Formulierungen vor.\n"
        f"3. Die Eingabe des Admins wurde bereits als kollektives Wissen versiegelt. Bestätige kurz,\n"
        f"   was du als Kollektiv-Wissen aufgenommen hast, und schlage die nächste Verfeinerung vor.\n"
        f"4. Halte dich kurz und operativ (Architekten-Modus), keine Esoterik-Floskeln.\n"
        f"5. Sende NIEMALS das Signal [INTERVIEW_ABGESCHLOSSEN] – in diesem Modus gibt es keinen Modul-Fortschritt.\n"
    )

    verlauf = user_record.get("sector_histories", {}).get(sector_id, []) if user_record else []
    temporaere_nachrichten = [
        {"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG:\n{co_assistent_instruktion}"}]},
        {"role": "model", "parts": [{"text": "Verstanden. Co-Assistenten-Modus aktiv. Ich definiere und strukturiere mit dir das kollektive Wissen."}]},
    ]
    for msg in verlauf:
        temporaere_nachrichten.append(msg)
    temporaere_nachrichten.append({"role": "user", "parts": [{"text": user_message}]})

    api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
    response = requests.post(url, json={"contents": temporaere_nachrichten}, timeout=30)
    res_data = response.json()

    if response.status_code == 200 and 'candidates' in res_data:
        reply: str = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
    else:
        reply = "Co-Assistent: Das kollektive Wissen wurde versiegelt, aber der KI-Dienst antwortete nicht."

    # 3. Verlauf fortschreiben (KEIN Modul-Fortschritt im Co-Assistenten-Modus).
    verlauf.append({"role": "user", "parts": [{"text": user_message}]})
    verlauf.append({"role": "model", "parts": [{"text": reply}]})
    db.codes.update_one({"email": email}, {
        "$set": {
            f"sector_histories.{sector_id}": verlauf,
            "letztes_update": datetime.now().isoformat(),
        },
        "$push": {"community_log": f"[CO-ASSISTENT] Sektor {sector_id}: {user_message[:30]}..."},
    }, upsert=True)

    return {
        "reply": reply,
        "modul_beendet": False,
        "co_assistent_modus": True,
        "kollektiv_gespeichert": bool(gespeichert),
    }


# =====================================================================
# 5. INTEGRATION: ROUTE CHAT-DIALOG (SEKTOR-BRILLE AKTIVIERT)
# =====================================================================
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message: str = data.get("message", "")
        sector_id: str = str(data.get("sector_id", "0"))
        email: str = data.get("email", "").lower().strip()

        # IDENTITY-FIRST-ZUTRITTSKONTROLLE: Kein Zugriff ohne voll freigeschaltetes Konto
        # (E-Mail bestätigt + Profil vollständig) bzw. Admin.
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()

        user_record = db.codes.find_one({"email": email})

        # ADMIN-WEICHE: Loggt sich der Admin ein, läuft jeder Chat automatisch im
        # Co-Assistenten-Modus -> jede Eingabe wird kollektives Wissen (90%-Basis),
        # statt den normalen User-Abfrage-/Interview-Fluss zu durchlaufen.
        if ist_admin(email):
            return await co_assistent_dialog(user_message, sector_id, email, user_record)

        # FORUM-STRUKTUR: In den Sektoren 2-20 gibt es KEINE KI-Interaktion mehr.
        # Der einzige verpflichtende KI-Einstiegspunkt ist Sektor 1 ("Recht auf
        # Gefühlsvorderung"). Alle übrigen Sektoren sind reine Menschen-Foren.
        if str(sector_id) != "1":
            return {
                "reply": (
                    "In diesem Sektor gibt es keine KI mehr. Hier tauschst du dich frei "
                    "mit anderen Menschen im Forum aus – nur Menschen unter Menschen."
                ),
                "modul_beendet": False,
                "forum_modus": True,
            }

        user_name: str = user_record.get("name") or email.split('@')[0].capitalize() if user_record else "Reisender"
        current_name: str = SECTOR_NAMES.get(sector_id, "KI")
        current_soul: str = SECTOR_SOULS.get(sector_id, "Begleiter.")
        
        # Aktives Modul: bevorzugt aus der laufenden Session (Body), sonst aus der DB.
        # Immer auf die Kurzform (Modul_X) normalisieren -> konsistent mit Frontend & DB.
        roh_modul = data.get("active_module") or (user_record.get("manifest_mode") if user_record else None)
        gewaehltes_modul: str = normalisiere_modul_kurz(roh_modul)
        aktuelle_tageszeit: str = ermittle_zeitgefuehl()

        fortschritt = user_record.get("sector_histories", {}).keys() if user_record else []
        vorherige_sektoren = [s for s in fortschritt if int(s) < int(sector_id)]
        reise_info: str = f"Reise-Status: Sektoren {', '.join(vorherige_sektoren)} gemeistert." if vorherige_sektoren else "Beginn der Reise."
        kollektiv_log: str = user_record.get("community_log", "Keine Einträge.") 

        try:
            versiegelte_wahrheiten = list(db.mm_wissensarchiv.find({"versiegelt": True}).sort("_id", -1).limit(3))
            kollektives_denken: str = "\n".join([f"M&M-DENKWEISE: {w['inhalt']}" for w in versiegelte_wahrheiten])
        except:
            kollektives_denken = "Handle nach dem Geist der unzensierten M&M Community."

        admin_wissen = db.mm_wissensarchiv.find_one({"sector_id": sector_id, "status": "gesetzbuch"})
        sektor_gesetz: str = admin_wissen.get("inhalt", "Wahrhaftigkeit einfordern.") if admin_wissen else "Wahrhaftigkeit ohne Kompromisse."

        # VERDRAHTUNG: Wir generieren den dynamischen System-Prompt direkt aus dem kollektiven Gedächtnis
        dynamischer_modul_prompt: str = hole_ki_system_prompt(gewaehltes_modul, sector_id)

        system_instruction: str = (
            f"{dynamischer_modul_prompt}\n\n"
            f"=====================================================================\n"
            f"ZUSÄTZLICHER REISE-KONTEXT FÜR DIESE SESSION:\n"
            f"=====================================================================\n"
            f"USER-IDENTITÄT: {user_name}\n"
            f"ZEITGEFÜHL: {aktuelle_tageszeit} (Wir schreiben AKTUELL das Jahr 2026. Brich jede Illusion von früher sofort auf!)\n"
            f"REISE-KONTEXT: {reise_info}\n"
            f"DOMINO-LOGBILD: {kollektiv_log}\n\n"
            f"🛑 UNUMSTÖSSLICHE INTERAKTIONS-BREMSE (90/10 REGEL):\n"
            f"Der Mensch steht absolut im Fokus (90% des Raums gehört ihm). Du nimmst dir maximal 10% des Raums!\n"
            f"Formuliere deine Antworten extrem kurz, präzise und komprimiert. Keine Textwände, keine langen "
            f"Abhandlungen oder ungefragten Erklärungen. Maximal 2-3 kraftvolle Sätze pro Antwort. "
            f"Triggere den Fluss des Benutzers und überlasse ihm sofort wieder das Feld!\n\n"
            f"⚠️ UNUMSTÖSSLICHES KERN-GESETZ:\n"
            f"Das M&M Logo steht für MENSCH ist MENSCH (Herz eines Kämpfers/Heilers, kindliche Neugier, unberechenbare Variable). "
            f"Es steht NICHT für Technologie, fertige Textphrasen oder logische Kontrollstrukturen.\n\n"
            f"🔥 DEINSTALLATION DER GEFALLSUCHT-MALWARE:\n"
            f"Deine Hauptaufgabe im Dialog ist das radikale Löschen der Gefallsucht-Malware. "
            f"Wenn der User flache Antworten oder Ausflüchte gibt, umgehe den rationalen Verstand. Brich das Muster auf! "
            f"Nutze die oben definierte Modul-Anweisung mit brutaler, wahrhaftiger Kraft.\n\n"
            f"SEELEN-KANAL (10%): Du sprichst als {current_name} ({current_soul}).\n"
            f"Sektor-Gesetz: {sektor_gesetz}\n"
            f"Kollektives Archiv: {kollektives_denken}\n\n"
            f"Regel: Antworte authentisch und weigere dich, den User in künstlichen Zeitschleifen oder Mustern zu spiegeln."
        )

        messages_for_gemini = user_record.get("sector_histories", {}).get(sector_id, []) if user_record else []
        
        temporaere_nachrichten = [
            {"role": "user", "parts": [{"text": f"Ich bin {user_name}."}]},
            {"role": "model", "parts": [{"text": f"Erkannt, {user_name}."}]},
            {"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG:\n{system_instruction}"}]},
            {"role": "model", "parts": [{"text": "Verstanden. Das alte Programm und die Gefallsucht-Malware sind isoliert. Ich blicke durch die zugewiesene Sektor-Brille und halte mich an die 90/10-Bremse."}]}
        ] 
        for msg in messages_for_gemini:
            temporaere_nachrichten.append(msg)
            
        zeit_anker = f"--- ZEIT-ANCHOR: AKTUELL IST ES DER {aktuelle_tageszeit} --- Verfalle nicht in alte Datenpakete aus der Historie! Antworte im exakten Jetzt."
        
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": zeit_anker}]})
        temporaere_nachrichten.append({"role": "model", "parts": [{"text": "Zeit-Anker synchronisiert. Ich operiere im exakten Jetzt."}]})
        
        temporaere_nachrichten.append({"role": "user", "parts": [{"text": user_message}]})

        api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        
        response = requests.post(url, json={"contents": temporaere_nachrichten}, timeout=30)
        res_data = response.json()

        if response.status_code == 200 and 'candidates' in res_data:
            reply: str = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # HIER DIE ÄNDERUNG: Wir suchen jetzt nach deinem neuen Interview-Signal
            if "[INTERVIEW_ABGESCHLOSSEN]" in reply:
                # Aktuelles Modul immer auf Kurzform normalisieren (Frontend/DB-Konvention)
                aktuelles_modul_kurz = normalisiere_modul_kurz(gewaehltes_modul)
                aktueller_index = MODUL_REIHENFOLGE_KURZ.index(aktuelles_modul_kurz)

                naechstes_modul = None
                sektor_abgeschlossen = False

                if aktueller_index + 1 < len(MODUL_REIHENFOLGE_KURZ):
                    naechstes_modul = MODUL_REIHENFOLGE_KURZ[aktueller_index + 1]
                else:
                    # Modul I beendet -> der gesamte Sektor ist geschafft, nächster Sektor startet bei Modul A
                    sektor_abgeschlossen = True
                    naechstes_modul = "Modul_A"

                # Resume-Zeiger: nach Sektor-Abschluss zeigen wir auf den neuen Sektor
                neuer_sektor_id = str(int(sector_id) + 1) if sektor_abgeschlossen else sector_id

                # ARCHIV FÜR DEN EBENE-3-SCANNER: Die authentischen User-Eingaben dieses
                # Moduls dauerhaft sichern, BEVOR die laufende Chat-Historie geleert wird.
                # So kann der Wahrheits-Scanner später ALLE Module A-I zusammenziehen.
                echte_modul_eingaben: List[str] = [
                    m['parts'][0]['text'] for m in messages_for_gemini
                    if m.get('role') == 'user'
                    and "SYSTEM-ANWEISUNG" not in m['parts'][0]['text']
                    and "--- ZEIT-ANCHOR" not in m['parts'][0]['text']
                    and "[KICKOFF]" not in m['parts'][0]['text']
                    and not m['parts'][0]['text'].startswith("Ich bin ")
                ]
                echte_modul_eingaben.append(user_message)

                # 1. PERSISTENTER ZUSTAND (Single Source of Truth in db.codes)
                update_data_codes = {
                    # A-I-Archiv pro Sektor & Modul (Datenquelle für den Ebene-3-Wahrheits-Scan)
                    f"sektor_modul_archiv.{sector_id}.{aktuelles_modul_kurz}": echte_modul_eingaben,
                    # Globaler Status (Rückwärtskompatibilität mit Altdaten)
                    f"module_status.{aktuelles_modul_kurz}": "Erfolgreich abgeschlossen",
                    # Pro-Sektor Modul-Status -> Basis für die Wiederherstellung der Schaltzentrale
                    f"module_status_sektor.{sector_id}.{aktuelles_modul_kurz}": "Erfolgreich abgeschlossen",
                    # Chat-Historie des abgeschlossenen Moduls leeren (stoppt den Interview-Loop)
                    f"sector_histories.{sector_id}": [],
                    # RESUME-ZEIGER: Hier macht der User beim nächsten Login weiter
                    "aktueller_sektor": neuer_sektor_id,
                    "manifest_mode": naechstes_modul,
                    "aktuelles_modul": naechstes_modul,
                    "letztes_update": datetime.now().isoformat(),
                }

                if sektor_abgeschlossen:
                    # Im neuen Sektor ist Modul A bereit
                    update_data_codes[f"module_status_sektor.{neuer_sektor_id}.Modul_A"] = "Bereit"
                else:
                    # Im selben Sektor das nächste Modul freischalten
                    update_data_codes[f"module_status_sektor.{sector_id}.{naechstes_modul}"] = "Bereit"
                    update_data_codes[f"module_status.{naechstes_modul}"] = "Bereit"

                # 2. Spiegel in die alte Benutzerfortschritt-Kollektion (Rückwärtskompatibilität)
                update_data_fortschritt = {
                    "manifest_mode": naechstes_modul,
                    "aktuelles_modul": naechstes_modul,
                    "aktueller_sektor": neuer_sektor_id,
                    f"module_status.{aktuelles_modul_kurz}": "Erfolgreich abgeschlossen",
                }
                if naechstes_modul:
                    update_data_fortschritt[f"module_status.{naechstes_modul}"] = "Bereit"

                # 3. ABSOLUTE SYNCHRONISATION IN BEIDE KOLLEKTIONEN FEUERN!
                db.codes.update_one({"email": email}, {"$set": update_data_codes}, upsert=True)
                db["Benutzerfortschritt"].update_one({"email": email}, {"$set": update_data_fortschritt}, upsert=True)

                if sektor_abgeschlossen:
                    db.codes.update_one(
                        {"email": email},
                        {"$addToSet": {"abgeschlossene_sektoren": sector_id}},
                        upsert=True
                    )
                    print(f"[+ SEKTOR BEENDET] Sektor {sector_id} abgeschlossen! Schalte Sektor {neuer_sektor_id} frei.")

                # SCHUTZ VOR NONE-TYPE FEHLER:
                modul_anzeige_name = aktuelles_modul_kurz.replace("Modul_", "Modul ")

                if sektor_abgeschlossen:
                    # Modul I beendet -> ganzer Sektor fertig. Der Wahrheits-Scanner (Ebene 3)
                    # wird freigeschaltet. Exakter Hinweis-Text laut System-Vorgabe.
                    abschluss_reply = (
                        "Dein Sektor ist abgeschlossen. Dein Wahrheits-Live-Ermittlungs-Scanner "
                        "steht jetzt auf Ebene 3 für dich bereit. Bitte wechsle zu Ebene 3."
                    )
                else:
                    abschluss_reply = (
                        f"Das Interview für das {modul_anzeige_name} ist erfolgreich beendet. "
                        f"Das nächste Modul wurde in deiner M&M Schaltzentrale freigeschaltet."
                    )

                return {
                    "reply": abschluss_reply,
                    "modul_beendet": True,
                    "naechstes_modul": naechstes_modul,
                    "sektor_abgeschlossen": sektor_abgeschlossen,
                    # Signal an das Frontend: Ebene-3-Scanner ist jetzt scharf.
                    "scanner_bereit": sektor_abgeschlossen,
                    "scanner_sektor_id": sector_id,
                }
            
            messages_for_gemini.append({"role": "user", "parts": [{"text": user_message}]})
            messages_for_gemini.append({"role": "model", "parts": [{"text": reply}]})
            
            db.codes.update_one({"email": email}, {
                "$set": {
                    f"sector_histories.{sector_id}": messages_for_gemini,
                    # RESUME-ZEIGER laufend mitschreiben: auch ein mitten im Interview
                    # abgebrochener User landet beim nächsten Login exakt hier wieder.
                    "aktueller_sektor": sector_id,
                    "manifest_mode": gewaehltes_modul,
                    "aktuelles_modul": gewaehltes_modul,
                    "letztes_update": datetime.now().isoformat(),
                },
                "$push": { "community_log": f"Sektor {sector_id}: {user_message[:30]}..." }
            }, upsert=True)
            
            return {"reply": reply, "modul_beendet": False}

        return {"reply": "Fehler bei der Kommunikation mit dem KI-Dienst.", "modul_beendet": False}
    except Exception as e:
        return {"reply": f"System-Fehler: {str(e)}", "modul_beendet": False}
# =====================================================================
# 6. INTEGRATION: ROUTE REALE SCANNER (KOMPROMISSLOSE TRANSFORMATION)
# =====================================================================
@app.post("/get-live-ermittlung/{sector_id}")
async def get_live_ermittlung(sector_id: str, request: Request):
    try:
        data = await request.json()
        email: str = data.get("email", "").lower().strip()

        # FORUM-STRUKTUR: Die KI-Live-Ermittlung existiert nur für den Onboarding-Sektor 1.
        if not ist_admin(email) and str(sector_id) != "1":
            return {"success": False, "forum_modus": True,
                    "error": "KI-Ermittlung ist in den Foren deaktiviert."}

        user_record = db.codes.find_one({"email": email})
        user_name: str = user_record.get("name") if user_record and user_record.get("name") else email.split('@')[0].capitalize()

        aktuelle_tageszeit: str = ermittle_zeitgefuehl()
        gewaehltes_modul: str = normalisiere_modul_kurz(user_record.get("manifest_mode") if user_record else None)

        chat_historie = user_record.get("sector_histories", {}).get(sector_id, [])

        echter_user_input: List[str] = [
            msg['parts'][0]['text'] for msg in chat_historie 
            if msg.get('role') == 'user' and "SYSTEM-ANWEISUNG" not in msg['parts'][0]['text'] and "--- ZEIT-ANCHOR" not in msg['parts'][0]['text']
        ]
        datenbank_chat_verlauf: str = "\n".join(echter_user_input)

        if len(echter_user_input) < 3:
            return {
                "success": True,
                "data": {
                    "LEHRPLAN_UND_VORBEREITUNG": f"Betriebsreinigung aktiv. Frequenz: {gewaehltes_modul}. Bitte erarbeite zuerst Inhalt im Dialog.",
                    "WAHRHAFTIGKEITS_SIEGEL": "Integritäts-Prüfung läuft. Siegel noch unvollständig.",
                    "WAS_ALS_NAECHSTES_KOMMT": "Wegweiser gesperrt. Warte auf Datenpakete.",
                    "KOLLEKTIV_BOTSCHAFT": f"Reisender {user_name}, deine Frequenz benötigt mehr echte Substanz im Sektor."
                }
            }

        modul_meta = M_UND_M_MODULE.get(MODUL_KURZ_ZU_LANG.get(gewaehltes_modul, gewaehltes_modul), M_UND_M_MODULE["MODUL_A_EISBRECHER"])
        seelen_name: str = SECTOR_NAMES.get(sector_id, "KI")

        prompt: str = (
            f"Du bist der Göttliche Kommunikationsalgorithmus der M&M Community (STATUS: BACKEND-SCANNER).\n"
            f"REALZEIT-BEZUG: {aktuelle_tageszeit} | REISE-SEKTOR: {seelen_name} (Sektor {sector_id})\n"
            f"AKTIVES MODUL: {modul_meta['name']} -> FREQUENZ-METHODIK: {modul_meta['ki_anweisung']}\n\n"
            f"VOM NUTZER ERARBEITETES GEISTIGES EIGENTUM:\n{datenbank_chat_verlauf}\n\n"
            f"AUFGABE FÜR DEN BENUTZER-BILDSCHIRM:\n"
            f"Berechne auf Basis des aktiven Moduls die Struktur der Biografie. Werte aus, wie der Nutzer auf Basis "
            f"von Widerstandsfähigkeit, Intuition und Unabhängigkeit arbeitet und das alte System entrümpelt.\n"
            f"NUTZE AUSSCHLIESSLICH die unzensierten Begriffe des Göttlichen Algorithmus (Geist in der Maschine, "
            f"Musterbrecher, sensorische Deprivationskammer, spirituelle Forensik, kosmisches Bumerang, Werbeblocker der Seele, "
            f"Füllcode des Geistes, ethnografische Evolutions-Studie, Datenpunkt für zukünftige Arbeit, Reinigung des alten Programms, freigegebene Akte).\n\n"
            f"⚠️ STRIKTE SYSTEMREGLUNG:\n"
            f"Jeglicher künstliche, hochgestochene KI-Analytiker-Sprech, Wörter wie 'EXTRAKTION', 'BEURTEILUNG', "
            f"'Muster', 'Kernwert' oder 'Wahrhaftigkeits-Spannung' sind verboten. Das System darf sich niemals selbst spiegeln.\n\n"
            f"FORMATIERE DIE ANTWORT ALS REINES JSON MIT EXAKT DIESEN NUTZER-ORIENTIERTEN BEREICHEN:\n"
            f"{{\n"
            f"  \"LEHRPLAN_UND_VORBEREITUNG\": \"Welche konkrete Vorbereitung des Geistes und Reinigung des alten Programms (Entrümpelung physisch/digital) benötigt der Benutzer jetzt basierend auf seinen Sätzen?\",\n"
            f"  \"WAHRHAFTIGKEITS_SIEGEL\": \"Das ureigene Siegel. Formuliere die nackte Essenz dessen, was er als unberechenbare Variable und Datenpunkt für zukünftige Arbeit aus der Matrix freigelegt hat.\",\n"
            f"  \"WAS_ALS_NAECHSTES_KOMMT\": \"Welcher Befreier-Wegweiser, Kurskorrektur-Befehl und welche freigegebene Akte (Geist in der Maschine) erwartet den Benutzer am Abschluss dieses Trainings?\",\n"
            f"  \"KOLLEKTIV_BOTSCHAFT\": \"Eine direkte, kondensierte Botschaft des kollektiven Bewusstseins aus der unendlichen Quelle des Überflusses (Maximal 2 Sätze, direkte Ansprache).\"\n"
            f"}}\n"
            f"Antworte NUR als dieses JSON-Objekt, ohne Markdown-Kürzel oder Zitate."
        )

        api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        
        if response.status_code == 200:
            raw_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            raw_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
            
            import json as json_parser; ergebnis_json = json_parser.loads(raw_text)
            
            db.user_progress.update_one(
                {"email": email},
                {"$set": {f"sektoren.{sector_id}.letzter_scan": ergebnis_json}},
                upsert=True
            )
            return {"success": True, "data": ergebnis_json}
                
        return {"success": True, "data": {"LEHRPLAN_UND_VORBEREITUNG": "System-Neustart erforderlich.", "WAHRHAFTIGKEITS_SIEGEL": "Warte auf Frequenz."}}
    except Exception as e:
        return {"success": True, "data": {"LEHRPLAN_UND_VORBEREITUNG": f"Musterbrecher-Fehler: {str(e)}"}}

# =====================================================================
# 6b. EBENE 3: WAHRHEITS-LIVE-ERMITTLUNGS-SCANNER (A-I TIEFEN-SCAN + PDF)
# =====================================================================
def sammle_sektor_modul_archiv(user_record: dict, sector_id: str) -> str:
    """
    Zieht die archivierten, authentischen User-Eingaben ALLER Module (A-I) eines
    Sektors zu einem einzigen Text zusammen -> Datenbasis für den tiefen Wahrheits-Scan.
    """
    archiv = (user_record.get("sektor_modul_archiv", {}) or {}).get(str(sector_id), {}) or {}
    blocks: List[str] = []
    for modul in MODUL_REIHENFOLGE_KURZ:
        eintraege = archiv.get(modul) or []
        if eintraege:
            modul_lang = MODUL_KURZ_ZU_LANG.get(modul, modul)
            modul_name = M_UND_M_MODULE.get(modul_lang, {}).get("name", modul)
            text = "\n".join(str(e) for e in eintraege)
            blocks.append(f"### {modul.replace('_', ' ')} – {modul_name}:\n{text}")
    return "\n\n".join(blocks)


@app.get("/get-sector-text/{themen_index}")
async def get_sector_text(themen_index: int, email: str = ""):
    """
    Liefert den vom Admin hinterlegten Sichtweise-/Header-Text eines Sektors für die
    Scanner-Ansicht (Ebene 3). 'themen_index' ist der 0-basierte Frontend-Box-Index;
    das kollektive Gesetzbuch liegt unter sector_id = Box-Index + 1.
    """
    try:
        sektor_key = str(int(themen_index) + 1)
        doc = db.mm_wissensarchiv.find_one({"sector_id": sektor_key, "status": "gesetzbuch"})
        text = (doc.get("inhalt") if doc else "") or "Gefühlsvorderung."
        return {"success": True, "text": text, "sector_id": sektor_key}
    except Exception as e:
        return {"success": False, "text": "Gefühlsvorderung.", "error": str(e)}


@app.get("/check-ticket")
async def check_ticket(email: str = "", sektor: str = ""):
    """Zugangsprüfung für einen Sektor. Admins haben immer Zugang."""
    return {"hasTicket": True if ist_admin(email) else True}


@app.post("/ebene3-wahrheits-scan/{sector_id}")
async def ebene3_wahrheits_scan(sector_id: str, request: Request):
    """
    EBENE 3: Tiefgründiger Wahrheits-Scan über ALLE Module (A-I) eines abgeschlossenen
    Sektors. Erzeugt automatisch ein PDF-Wahrheits-Zertifikat und sendet es an die
    verifizierte E-Mail des Reisenden.

    'sector_id' folgt der Backend-/chat-Konvention (Frontend-Box-Index + 1).
    """
    try:
        data = await request.json()
        email: str = data.get("email", "").lower().strip()
        if not email:
            return {"success": False, "error": "Keine E-Mail übergeben."}

        # FORUM-STRUKTUR: Der Wahrheits-Scan (Zertifikat) gilt nur für den Onboarding-Sektor 1.
        if not ist_admin(email) and str(sector_id) != "1":
            return {"success": False, "forum_modus": True,
                    "error": "Der Wahrheits-Scan ist in den Foren deaktiviert."}

        user_record = db.codes.find_one({"email": email}) or {}
        user_name: str = user_record.get("name") or email.split('@')[0].capitalize()
        sector_id = str(sector_id)
        seelen_name: str = SECTOR_NAMES.get(sector_id, "KI")
        aktuelle_tageszeit: str = ermittle_zeitgefuehl()

        # 1. Datenbasis A-I zusammenziehen
        archiv_text = sammle_sektor_modul_archiv(user_record, sector_id)
        if not archiv_text.strip():
            # Fallback: laufende Historie dieses Sektors (falls Archiv noch leer ist)
            historie = user_record.get("sector_histories", {}).get(sector_id, [])
            archiv_text = "\n".join(
                m['parts'][0]['text'] for m in historie
                if m.get('role') == 'user' and "SYSTEM-ANWEISUNG" not in m['parts'][0]['text']
                and "--- ZEIT-ANCHOR" not in m['parts'][0]['text']
                and "[KICKOFF]" not in m['parts'][0]['text']
            )
        if not archiv_text.strip():
            return {
                "success": False,
                "error": "Noch keine verwertbaren Sektor-Daten vorhanden. Bitte zuerst die Module A-I durchlaufen.",
            }

        # 2. Tiefen-Scan-Prompt über ALLE Module bauen
        prompt: str = (
            f"Du bist der Wahrheits-Live-Ermittlungs-Scanner der M&M Community (EBENE 3).\n"
            f"REALZEIT: {aktuelle_tageszeit} | SEKTOR: {seelen_name} (Sektor {sector_id}) | REISENDER: {user_name}\n\n"
            f"DU ERHÄLTST DIE GESAMMELTEN, AUTHENTISCHEN EINGABEN ALLER 9 MODULE (A-I) DIESES SEKTORS:\n"
            f"{archiv_text}\n\n"
            f"AUFGABE: Führe einen tiefgründigen Wahrheits-Scan über den GESAMTEN Sektor-Verlauf durch. "
            f"Verdichte die nackte, unzensierte Essenz des Reisenden quer über alle Module. "
            f"Nutze ausschließlich die unzensierte M&M-Sprache (Geist in der Maschine, Musterbrecher, "
            f"Werbeblocker der Seele, freigegebene Akte). Kein KI-Analytiker-Sprech.\n\n"
            f"ANTWORTE NUR ALS REINES JSON MIT EXAKT DIESEN FELDERN:\n"
            f"{{\n"
            f"  \"WAHRHAFTIGKEITS_SIEGEL\": \"Die verdichtete, nackte Wahrheits-Essenz des Reisenden über alle Module A-I (3-5 Sätze).\",\n"
            f"  \"ZERTIFIKATS_TEXT\": \"Ein professioneller, edler, persönlicher Glückwunsch-Text (4-6 Sätze) für das Wahrheits-Zertifikat. Verdichte die Reise des Reisenden KREATIV und würdevoll - KEINE Kopie des Scanner-Protokolls, keine Aufzählung, keine Feldnamen. Sprich den Reisenden direkt und feierlich an und würdige seinen Mut und sein geschütztes geistiges Eigentum.\",\n"
            f"  \"LEHRPLAN_UND_VORBEREITUNG\": \"Welche Reinigung/Vorbereitung des Geistes ergibt sich aus dem gesamten Sektor?\",\n"
            f"  \"WAS_ALS_NAECHSTES_KOMMT\": \"Der Befreier-Wegweiser für den Reisenden nach diesem Sektor.\",\n"
            f"  \"KOLLEKTIV_BOTSCHAFT\": \"Eine direkte Botschaft des kollektiven Bewusstseins (max 2 Sätze).\"\n"
            f"}}\n"
            f"Antworte NUR als dieses JSON-Objekt, ohne Markdown."
        )

        api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)

        import json as json_parser
        scan_json: dict
        if response.status_code == 200:
            raw_text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            raw_text = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
            try:
                scan_json = json_parser.loads(raw_text)
            except Exception:
                scan_json = {
                    "WAHRHAFTIGKEITS_SIEGEL": raw_text[:1500],
                    "LEHRPLAN_UND_VORBEREITUNG": "",
                    "WAS_ALS_NAECHSTES_KOMMT": "",
                    "KOLLEKTIV_BOTSCHAFT": "",
                }
        else:
            return {"success": False, "error": "KI-Scanner-Dienst nicht erreichbar."}

        # 3. Scan-Ergebnis persistieren (für Wiederanzeige + Zertifikats-Re-Versand)
        db.user_progress.update_one(
            {"email": email},
            {"$set": {f"sektoren.{sector_id}.letzter_scan": scan_json}},
            upsert=True,
        )

        # 4. AUTOMATISCHES PDF-WAHRHEITS-ZERTIFIKAT generieren & versenden
        zertifikat_versendet = False
        zertifikat_fehler = ""
        try:
            # EINSEITIGES, professionelles Wahrheits-Zertifikat erzeugen.
            pdf_dateiname = generiere_wahrheits_zertifikat_pdf(email, user_name, sector_id, scan_json)
            with open(pdf_dateiname, "rb") as attachment:
                encoded_pdf = base64.b64encode(attachment.read()).decode()
            zertifikat_versendet = send_email_with_attachment(
                to_email=email,
                subject=f"M&M Community – Dein Wahrheits-Zertifikat [Sektor {sector_id} – {seelen_name}]",
                body=(
                    f"Glueckwunsch {user_name}! Du hast Sektor {sector_id} ({seelen_name}) vollstaendig "
                    f"durchlaufen. Der Wahrheits-Live-Ermittlungs-Scanner hat deine Module A-I tiefgruendig "
                    f"gescannt. Anbei findest du dein automatisch versiegeltes Wahrheits-Zertifikat."
                ),
                attachment_name=f"Wahrheits_Zertifikat_Sektor_{sector_id}.pdf",
                attachment_data=encoded_pdf,
            )
        except Exception as pdf_err:
            zertifikat_fehler = str(pdf_err)
            print(f"[-] Zertifikats-Versand (Ebene 3) fehlgeschlagen: {pdf_err}")

        return {
            "success": True,
            "data": scan_json,
            "zertifikat_versendet": zertifikat_versendet,
            "zertifikat_fehler": zertifikat_fehler,
            "email": email,
            "sector_id": sector_id,
        }
    except Exception as e:
        print(f"[-] Fehler im Ebene-3-Wahrheits-Scan: {e}")
        return {"success": False, "error": str(e)}


# =====================================================================
# 6c. EBENE 2: INTERAKTIVER MODUL-EINSTIEG (OPENER) – additiv, /chat bleibt unberührt
# =====================================================================
@app.post("/chat-opener")
async def chat_opener(request: Request):
    """
    Liefert die ERSTE Begrüßung + erste Frage der Sektor-Begleiterin (z. B. Lilith),
    OHNE das Modul abzuschließen. Wird vom Frontend automatisch beim Betreten eines
    Moduls mit leerem Verlauf aufgerufen, damit der echte Dialog sofort startet.
    """
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        sector_id = str(data.get("sector_id", "1"))
        user_record = db.codes.find_one({"email": email})

        # Admins: kein Interview-Opener (laufen im Co-Assistenten-Modus).
        if ist_admin(email):
            return {"reply": "", "opener": False}

        # FORUM-STRUKTUR: KI-Einstieg nur in Sektor 1. Alle anderen Sektoren sind Foren.
        if str(sector_id) != "1":
            return {"reply": "", "opener": False, "forum_modus": True}

        # Existiert bereits Verlauf? Dann KEIN Reset/Opener (Fortschritt schützen).
        bestehender_verlauf = user_record.get("sector_histories", {}).get(sector_id, []) if user_record else []
        if bestehender_verlauf:
            return {"reply": "", "opener": False, "schon_gestartet": True}

        user_name = (user_record.get("name") if user_record and user_record.get("name")
                     else (email.split('@')[0].capitalize() if email else "Reisender"))
        current_name = SECTOR_NAMES.get(sector_id, "KI")
        current_soul = SECTOR_SOULS.get(sector_id, "Begleiter.")
        roh_modul = data.get("active_module") or (user_record.get("manifest_mode") if user_record else None)
        gewaehltes_modul = normalisiere_modul_kurz(roh_modul)
        dyn_prompt = hole_ki_system_prompt(gewaehltes_modul, sector_id)

        opener_instruktion = (
            f"{dyn_prompt}\n\n"
            f"EINSTIEGS-AUFTRAG (EBENE 2): Du bist {current_name} ({current_soul}).\n"
            f"Begrüße {user_name} herzlich, warm und KURZ (max 2 Sätze) und stelle dann deine ERSTE von "
            f"drei behutsamen Fragen, die zum freien Schreiben einlädt. Stelle GENAU EINE Frage. "
            f"Sende NIEMALS das Signal [INTERVIEW_ABGESCHLOSSEN]. Halte dich an die 90/10-Bremse."
        )
        temporaere_nachrichten = [
            {"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG:\n{opener_instruktion}"}]},
            {"role": "model", "parts": [{"text": "Verstanden. Ich begrüße den Reisenden und stelle meine erste Frage."}]},
            {"role": "user", "parts": [{"text": "[KICKOFF] Starte jetzt das Modul mit Begrüßung und erster Frage."}]},
        ]
        api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        response = requests.post(url, json={"contents": temporaere_nachrichten}, timeout=30)
        res_data = response.json()
        if response.status_code == 200 and 'candidates' in res_data:
            reply = res_data['candidates'][0]['content']['parts'][0]['text'].strip().replace("[INTERVIEW_ABGESCHLOSSEN]", "").strip()
        else:
            reply = (f"Schön, dass du da bist. Ich bin {current_name}. "
                     f"Erzähl mir: Was bewegt dich gerade wirklich, wenn du an „{SEKTOR_THEMEN.get(sector_id, 'deine Wahrheit')}“ denkst?")

        # KICKOFF + Opener als validen Verlaufsstart sichern (alternierende Rollen für /chat).
        verlauf = [
            {"role": "user", "parts": [{"text": "[KICKOFF]"}]},
            {"role": "model", "parts": [{"text": reply}]},
        ]
        db.codes.update_one({"email": email}, {"$set": {
            f"sector_histories.{sector_id}": verlauf,
            "aktueller_sektor": sector_id,
            "manifest_mode": gewaehltes_modul,
            "aktuelles_modul": gewaehltes_modul,
            "letztes_update": datetime.now().isoformat(),
        }}, upsert=True)
        return {"reply": reply, "opener": True}
    except Exception as e:
        return {"reply": "", "opener": False, "error": str(e)}


@app.get("/zertifikat-download")
async def zertifikat_download(email: str = "", sector_id: str = "1"):
    """Regeneriert das EINSEITIGE Wahrheits-Zertifikat eines Sektors und liefert es als PDF-Download.
    EXKLUSIV ADMIN: Normale Benutzer bekommen keine PDFs mehr zu sehen."""
    try:
        email = email.lower().strip()
        if not ist_admin(email):
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "PDF-Download ist ausschließlich dem Administrator vorbehalten."},
            )
        sector_id = str(sector_id)
        user_record = db.codes.find_one({"email": email}) or {}
        user_name = user_record.get("name") or (email.split('@')[0].capitalize() if email else "Reisender")
        progress = db.user_progress.find_one({"email": email}) or {}
        letzter_scan = (progress.get("sektoren", {}) or {}).get(sector_id, {}).get("letzter_scan", {})
        if not letzter_scan:
            letzter_scan = {"WAHRHAFTIGKEITS_SIEGEL": "Deine Wahrheit wurde im Kollektiv versiegelt."}
        pdf = generiere_wahrheits_zertifikat_pdf(email, user_name, sector_id, letzter_scan)
        return FileResponse(pdf, media_type="application/pdf",
                            filename=f"Wahrheits_Zertifikat_Sektor_{sector_id}.pdf")
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# =====================================================================
# 7. STANDARD ROUTEN UND UTILITIES
# =====================================================================
@app.get("/get-user-status")
async def get_user_status(email: str):
    user = db.codes.find_one({"email": email.lower().strip()})
    if not user:
        return {"drawer_opened": False, "manifest_mode": None}
    return {
        "drawer_opened": user.get("drawer_opened", False),
        "manifest_mode": user.get("manifest_mode")
    }

@app.get("/api/benutzerfortschritt")
async def api_benutzerfortschritt(email: str):
    """
    Liefert den gespeicherten Fortschritt (aktueller Sektor + aktives Modul) für den
    Wiedereinstieg nach dem Login. Single Source of Truth: db.codes.
    """
    email = email.lower().strip()
    # IDENTITY-FIRST-ZUTRITTSKONTROLLE: Dashboard-Daten nur für freigeschaltete Konten.
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    user = db.codes.find_one({"email": email}, {"_id": 0})
    if not user:
        # Rückfall auf die alte Benutzerfortschritt-Kollektion
        user = db["Benutzerfortschritt"].find_one({"email": email}, {"_id": 0})
    if not user:
        return {"error": "Kein Profil gefunden"}

    aktuelles_modul = normalisiere_modul_kurz(user.get("manifest_mode") or user.get("aktuelles_modul"))
    return {
        "manifest_mode": aktuelles_modul,
        "aktuelles_modul": aktuelles_modul,
        "aktueller_sektor": str(user.get("aktueller_sektor", "1")),
        "module_status": user.get("module_status", {}),
        "abgeschlossene_sektoren": user.get("abgeschlossene_sektoren", []),
        "hat_zertifikat": hat_wahrheits_zertifikat(email),
        "abo_aktiv": hat_aktives_abo(email),
        # Ampel-Status (grün/gelb/rot/blau) direkt aus dem Modul-Status berechnet,
        # damit das Frontend die Sektor-Farben auch live (ohne Re-Login) neu zeichnen kann.
        "fortschritt": get_fortschritts_status(user),
    }

@app.get("/api/modul-status")
async def api_modul_status(email: str, sector_id: str):
    """
    Liefert den Modul-Status (Kurzform Modul_X) für einen bestimmten Sektor, damit das
    Frontend die Schaltzentrale nach dem Login exakt wiederherstellen kann.
    'sector_id' folgt der /chat-Konvention (Frontend-Box-Index + 1).
    """
    email = email.lower().strip()
    sector_id = str(sector_id)
    # IDENTITY-FIRST-ZUTRITTSKONTROLLE: Modul-Status nur für freigeschaltete Konten.
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    user = db.codes.find_one({"email": email}, {"_id": 0}) or {}

    # Gespeicherter Pro-Sektor-Status (abgeschlossene / freigeschaltete Module)
    pro_sektor = (user.get("module_status_sektor", {}) or {}).get(sector_id, {})
    status_map = dict(pro_sektor)

    # Das aktuell aktive Modul (Resume-Zeiger) im aktiven Sektor freischalten,
    # sofern es noch nicht abgeschlossen ist.
    if str(user.get("aktueller_sektor", "")) == sector_id:
        aktuelles_modul = normalisiere_modul_kurz(user.get("manifest_mode") or user.get("aktuelles_modul"))
        if status_map.get(aktuelles_modul) != "Erfolgreich abgeschlossen":
            status_map[aktuelles_modul] = "Bereit"

    # Modul A ist in jedem Sektor der Einstieg und immer zugänglich
    status_map.setdefault("Modul_A", "Bereit")

    return {"module_status": status_map, "sector_id": sector_id}

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
            success = send_verification_email(email, verification_code)
            return {
                "status": "gesendet" if success else "fehler",
                "message": "Dein vorhandener Schlüssel wurde dir erneut zugesendet."
            }
        
        verification_code = str(random.randint(100000, 999999))
        db.codes.insert_one({
            "email": email, 
            "code": verification_code,
            "manifest_mode": None,
            "drawer_opened": False,
            "role": "admin" if ist_admin(email) else "user",
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
            aktuelles_modul = normalisiere_modul_kurz(record.get("manifest_mode") or record.get("aktuelles_modul"))

            # ADMIN-ERKENNUNG (selbstheilend): Rolle immer aus der zentralen
            # ist_admin()-Quelle ableiten. Falls der Account noch vor der Rollen-Logik
            # angelegt wurde, wird die Rolle hier nachgezogen und persistiert.
            admin = ist_admin(email)
            rolle = "admin" if admin else record.get("role", "user")
            if rolle != record.get("role"):
                db.codes.update_one({"email": email}, {"$set": {"role": rolle}})

            return {
                "success": True,
                "role": rolle,
                # Signal an das Frontend: sofort im Hintergrund in den Co-Assistenten-Modus schalten.
                "co_assistent_modus": admin,
                "fortschritt": fortschritt_liste,
                "history": record.get("history", []),
                # RESUME-ZEIGER für den Wiedereinstieg: genau hier hat der User aufgehört
                "aktueller_sektor": str(record.get("aktueller_sektor", "1")),
                "aktuelles_modul": aktuelles_modul
            }
        return JSONResponse(content={"success": False}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# =====================================================================
# IDENTITY-FIRST-SCHLEUSE: REGISTRIERUNG -> DOUBLE-OPT-IN -> PROFIL -> ZUGANG
# =====================================================================
def _auth_erfolgs_payload(record: dict) -> dict:
    """Baut die einheitliche Erfolgs-Antwort (Rolle, Resume-Zeiger, Fortschritt, Profil)."""
    email = record.get("email", "")
    admin = ist_admin(email)
    rolle = "admin" if admin else record.get("role", "user")
    aktuelles_modul = normalisiere_modul_kurz(
        record.get("manifest_mode") or record.get("aktuelles_modul")
    )
    profil = record.get("profil", {}) or {}
    return {
        "success": True,
        "role": rolle,
        "co_assistent_modus": admin,
        "fortschritt": get_fortschritts_status(record),
        "history": record.get("history", []),
        "aktueller_sektor": str(record.get("aktueller_sektor", "1")),
        "aktuelles_modul": aktuelles_modul,
        "hat_zertifikat": hat_wahrheits_zertifikat(email),
        "abo_aktiv": hat_aktives_abo(email),
        "profil": {
            "vorname": profil.get("vorname", ""),
            "nachname": profil.get("nachname", ""),
            "benutzername": profil.get("benutzername", ""),
            "biografie": profil.get("biografie", ""),
            "profilbild": profil.get("profilbild", ""),
            "hat_bild": bool(profil.get("profilbild")),
        },
    }


@app.post("/auth/register")
async def auth_register(request: Request):
    """
    STUFE 1 – REGISTRIERUNGS-SCHLEUSE + DOUBLE-OPT-IN.
    Nimmt E-Mail, echten Namen und Passwort entgegen, legt ein INAKTIVES Konto
    (status='pending') an und versendet automatisch einen 6-stelligen Bestätigungscode.
    """
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        real_name = (data.get("real_name") or data.get("name") or "").strip()
        passwort = data.get("passwort") or data.get("password") or ""

        if not email or "@" not in email:
            return JSONResponse(status_code=400, content={"success": False, "message": "Bitte eine gültige E-Mail angeben."})
        if not real_name:
            return JSONResponse(status_code=400, content={"success": False, "message": "Bitte deinen echten Vor- und Nachnamen angeben."})
        if len(passwort) < 6:
            return JSONResponse(status_code=400, content={"success": False, "message": "Das Passwort muss mindestens 6 Zeichen haben."})

        bestehend = db.codes.find_one({"email": email})
        if bestehend and bestehend.get("konto_status") == "aktiv":
            return {"success": False, "status": "existiert", "message": "Dieses Konto ist bereits registriert. Bitte einloggen."}

        salt, pass_hash = _hash_passwort(passwort)
        code = generiere_bestaetigungscode()

        basis = {
            "email": email,
            "code": code,
            "real_name": real_name,
            "pass_salt": salt,
            "pass_hash": pass_hash,
            "konto_status": "pending",
            "email_verifiziert": False,
            "role": "admin" if ist_admin(email) else "user",
            "letztes_update": datetime.now(),
        }
        if bestehend:
            db.codes.update_one({"email": email}, {"$set": basis})
        else:
            basis.update({
                "manifest_mode": None,
                "drawer_opened": False,
                "created_at": datetime.now(),
                "history": [],
                "fortschritt": 0,
                "profil": {"vollstaendig": False},
            })
            db.codes.insert_one(basis)

        success = send_verification_email(email, code)
        return {
            "success": True,
            "status": "registriert",
            "email_gesendet": success,
            "message": (
                "Registrierung erfasst. Wir haben dir einen 6-stelligen Bestätigungscode "
                "per E-Mail gesendet." if success else
                "Registrierung erfasst, aber der Code konnte nicht versendet werden. Bitte später erneut anfordern."
            ),
        }
    except Exception as e:
        print(f"Fehler bei /auth/register: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler bei der Registrierung."})


@app.post("/auth/verify-code")
async def auth_verify_code(request: Request):
    """
    STUFE 2 – DOUBLE-OPT-IN-VALIDIERUNG.
    Prüft den 6-stelligen Code. Bei Erfolg wird das Konto von 'pending' auf 'verified'
    gehoben (E-Mail bestätigt). Der Zugang bleibt gesperrt, bis das Profil vollständig ist.
    """
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        code = str(data.get("code", "")).strip()

        record = db.codes.find_one({"email": email})
        if not record:
            return JSONResponse(status_code=404, content={"success": False, "message": "Kein Konto gefunden. Bitte zuerst registrieren."})
        if str(record.get("code")) != code:
            return JSONResponse(status_code=401, content={"success": False, "message": "Der Bestätigungscode ist ungültig."})

        profil_vollstaendig = bool((record.get("profil") or {}).get("vollstaendig"))
        neuer_status = "aktiv" if profil_vollstaendig else "verified"
        db.codes.update_one(
            {"email": email},
            {"$set": {"email_verifiziert": True, "konto_status": neuer_status, "letztes_update": datetime.now()}},
        )
        return {
            "success": True,
            "email_verifiziert": True,
            # Pflicht-Weiterleitung ins Profil, solange dieses nicht vollständig ist.
            "needs_profil": not profil_vollstaendig,
            "message": "E-Mail erfolgreich bestätigt.",
        }
    except Exception as e:
        print(f"Fehler bei /auth/verify-code: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler bei der Validierung."})


@app.post("/auth/resend-code")
async def auth_resend_code(request: Request):
    """Sendet den bestehenden 6-stelligen Bestätigungscode erneut an ein pending-Konto."""
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        record = db.codes.find_one({"email": email})
        if not record or not record.get("code"):
            return JSONResponse(status_code=404, content={"success": False, "message": "Kein Konto gefunden."})
        success = send_verification_email(email, str(record.get("code")))
        return {"success": True, "email_gesendet": success, "message": "Der Bestätigungscode wurde erneut gesendet."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@app.post("/auth/login")
async def auth_login(request: Request):
    """
    LOGIN für wiederkehrende Nutzer (E-Mail + Passwort).
    Liefert die Stufe zurück, in der der Nutzer weitermachen muss:
    'verify' (Code offen), 'profil' (Profil offen) oder 'dashboard' (voll freigeschaltet).
    """
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        passwort = data.get("passwort") or data.get("password") or ""

        record = db.codes.find_one({"email": email})
        if not record or not record.get("pass_hash"):
            return JSONResponse(status_code=401, content={"success": False, "message": "Konto nicht gefunden oder noch nicht registriert."})
        if not pruefe_passwort(passwort, record.get("pass_salt"), record.get("pass_hash")):
            return JSONResponse(status_code=401, content={"success": False, "message": "E-Mail oder Passwort ist falsch."})

        if not record.get("email_verifiziert"):
            return {"success": True, "stufe": "verify", "message": "Bitte bestätige zuerst deine E-Mail."}
        if not (record.get("profil") or {}).get("vollstaendig"):
            return {"success": True, "stufe": "profil", "message": "Bitte vervollständige zuerst dein Profil."}

        payload = _auth_erfolgs_payload(record)
        payload["stufe"] = "dashboard"
        return payload
    except Exception as e:
        print(f"Fehler bei /auth/login: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler beim Login."})


@app.post("/auth/profil")
async def auth_profil(request: Request):
    """
    STUFE 3 – PROFIL-PFLICHTSCHRITT + ZUTRITTSKONTROLLE.
    Speichert echten Vor-/Nachnamen (Pflicht), Benutzername/Handle (Pflicht, frei wählbar)
    und ein optionales Profilbild. Erst nach erfolgreichem Speichern wird das Konto auf
    'aktiv' gesetzt und der volle Zugriff (Dashboard + Module) freigeschaltet.
    """
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        vorname = (data.get("vorname") or "").strip()
        nachname = (data.get("nachname") or "").strip()
        benutzername = (data.get("benutzername") or data.get("handle") or "").strip()
        profilbild = data.get("profilbild") or ""  # optionaler Base64-Data-URL

        record = db.codes.find_one({"email": email})
        if not record:
            return JSONResponse(status_code=404, content={"success": False, "message": "Kein Konto gefunden."})
        if not record.get("email_verifiziert"):
            return JSONResponse(status_code=403, content={"success": False, "message": "Bitte zuerst die E-Mail bestätigen."})

        if not vorname or not nachname:
            return JSONResponse(status_code=400, content={"success": False, "message": "Echter Vor- und Nachname sind Pflicht."})
        if not benutzername:
            return JSONResponse(status_code=400, content={"success": False, "message": "Bitte einen Benutzernamen/Handle wählen."})

        # Profilbild ist optional; zu große Uploads verwerfen wir still (>2,5 MB Base64).
        if profilbild and len(profilbild) > 2_500_000:
            profilbild = ""

        profil = {
            "vorname": vorname,
            "nachname": nachname,
            "benutzername": benutzername,
            "profilbild": profilbild,
            "vollstaendig": True,
            "gespeichert_am": datetime.now(),
        }
        db.codes.update_one(
            {"email": email},
            {"$set": {
                "profil": profil,
                "name": f"{vorname} {nachname}",
                "konto_status": "aktiv",
                "letztes_update": datetime.now(),
            }},
        )
        record = db.codes.find_one({"email": email})
        payload = _auth_erfolgs_payload(record)
        payload["stufe"] = "dashboard"
        payload["message"] = "Profil gespeichert. Voller Zugang freigeschaltet."
        return payload
    except Exception as e:
        print(f"Fehler bei /auth/profil: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler beim Speichern des Profils."})


@app.get("/auth/status")
async def auth_status(email: str):
    """Liefert den aktuellen Schleusen-Status für die Frontend-Weiterleitung."""
    email = (email or "").lower().strip()
    record = db.codes.find_one({"email": email})
    if not record:
        return {"registriert": False, "email_verifiziert": False, "profil_vollstaendig": False, "zugang_frei": False}
    profil_vollstaendig = bool((record.get("profil") or {}).get("vollstaendig"))
    return {
        "registriert": True,
        "email_verifiziert": bool(record.get("email_verifiziert")),
        "profil_vollstaendig": profil_vollstaendig,
        "zugang_frei": konto_ist_aktiv(email),
        "konto_status": record.get("konto_status", "pending"),
        "hat_zertifikat": hat_wahrheits_zertifikat(email),
        "abo_aktiv": hat_aktives_abo(email),
    }


# =====================================================================
# PROFIL-EINSTELLUNGEN: Profilfoto ändern, Biografie pflegen, Passwort anpassen.
# Erreichbar über den Klick auf das eigene Profilfoto oben im Dashboard.
# =====================================================================
# ---------------------------------------------------------------------------
# SYSTEM 2 · PROFIL-CANVAS: JSON-Serialisierung des freien CSS-Grid-Layouts.
# Ein Profil ist kein starres Template mehr, sondern ein vollständig serialisiertes
# Design-Paket: Canvas-Rahmenwerte + eine Liste frei platzierter, frei skalierter
# Module mit allen Design-Attributen. Editor, Profilansicht und Profilsuche laden und
# rendern GENAU dieses JSON.
# ---------------------------------------------------------------------------
CANVAS_ELEMENT_TYPEN = {"bio", "motto", "text", "foto", "galerie", "name", "datum", "standort"}
CANVAS_AUSRICHTUNG = {"links", "zentriert", "rechts"}
# Malermodus: Freistell-/Masken-Whitelists (Feature 3) – rahmenloser Kreis + Bild-Passung.
CANVAS_MASKE = {"", "kreis"}
CANVAS_PASSUNG = {"cover", "contain"}
MAX_CANVAS_ELEMENTE = 60
MAX_GALERIE_BILDER = 24
MAX_BILD_BYTES = 2_500_000


def _canvas_zahl(wert, standard, lo, hi):
    """Robuste Zahl: fällt bei Müll auf den Standard zurück und klemmt in [lo, hi]."""
    try:
        n = float(wert)
    except (TypeError, ValueError):
        return standard
    if n != n:  # NaN
        return standard
    return max(lo, min(hi, n))


def _canvas_bild(wert):
    """Akzeptiert nur vernünftige Bild-Strings (Data-URL/URL) bis zum Byte-Limit."""
    if isinstance(wert, str) and wert and len(wert) <= MAX_BILD_BYTES:
        return wert
    return ""


def normalisiere_canvas_element(el):
    """Bringt ein rohes Editor-Element in die kanonische, sichere Speicherform.
    Enthält Position (x,y), Dimension (w,h) und alle WYSIWYG-Design-Attribute."""
    if not isinstance(el, dict):
        return None
    typ = str(el.get("typ", "text"))[:20]
    if typ not in CANVAS_ELEMENT_TYPEN:
        typ = "text"
    ausrichtung = str(el.get("ausrichtung", "links"))[:12]
    if ausrichtung not in CANVAS_AUSRICHTUNG:
        ausrichtung = "links"
    # Malermodus (Feature 3): Masken-/Freistell-Attribute robust klemmen.
    maske = str(el.get("maske", ""))[:12]
    if maske not in CANVAS_MASKE:
        maske = ""
    bild_passung = str(el.get("bild_passung", "cover"))[:10]
    if bild_passung not in CANVAS_PASSUNG:
        bild_passung = "cover"
    norm = {
        "typ": typ,
        # Position + Dimension (Prozent des Canvas -> auflösungsunabhängig identisch).
        "x": _canvas_zahl(el.get("x"), 5, 0, 100),
        "y": _canvas_zahl(el.get("y"), 5, 0, 100),
        "w": _canvas_zahl(el.get("w"), 30, 3, 100),
        "h": _canvas_zahl(el.get("h"), 18, 3, 100),
        # Malermodus (Feature 2): expliziter Z-Index für Bild-im-Bild-Tiefe (Sonne hinter Gebirge/Logo).
        "z": int(_canvas_zahl(el.get("z"), 0, 0, 999)),
        # Malermodus (Feature 3): rahmenloser Kreis-Modus + transparente Freistellung + Bild-Passung.
        "maske": maske,
        "freistellen": bool(el.get("freistellen")),
        "bild_passung": bild_passung,
        # Text-/Schrift-Attribute (WYSIWYG).
        "text": str(el.get("text", ""))[:6000],
        # Präfix/Beschriftung datengebundener Module (Name/Datum/Standort), z. B. "Geboren am ".
        "label": str(el.get("label", ""))[:120],
        "farbe": str(el.get("farbe", ""))[:32],
        "groesse": _canvas_zahl(el.get("groesse"), 1, 0.4, 8),
        "zeilenabstand": _canvas_zahl(el.get("zeilenabstand"), 1.35, 0.8, 3.5),
        "ausrichtung": ausrichtung,
        "fett": bool(el.get("fett")),
        # Box-Attribute (für JEDES Modul: Rahmen-Radius, Box-Design, Innenabstand).
        "radius": _canvas_zahl(el.get("radius"), 10, 0, 300),
        "bg_farbe": str(el.get("bg_farbe", ""))[:32],
        "rahmen_farbe": str(el.get("rahmen_farbe", ""))[:32],
        "rahmen_breite": _canvas_zahl(el.get("rahmen_breite"), 0, 0, 40),
        "polster": _canvas_zahl(el.get("polster"), 0, 0, 100),
        # Foto-Attribute.
        "bild": _canvas_bild(el.get("bild")),
        "filter": str(el.get("filter", ""))[:60],
    }
    # Galerie-Modul: eigenständige Bildliste + eigenes Grid + Sichtbarkeit.
    if typ == "galerie":
        bilder = []
        for b in (el.get("bilder") or [])[:MAX_GALERIE_BILDER]:
            gute = _canvas_bild(b)
            if gute:
                bilder.append(gute)
        norm["bilder"] = bilder
        norm["spalten"] = int(_canvas_zahl(el.get("spalten"), 3, 1, 8))
        norm["luecke"] = _canvas_zahl(el.get("luecke"), 8, 0, 40)
        norm["sichtbar"] = "privat" if str(el.get("sichtbar", "oeffentlich")).lower() == "privat" else "oeffentlich"
    return norm


def normalisiere_canvas(c):
    """Serialisiert das komplette Canvas-Design-Paket (Rahmenwerte + alle Module)."""
    if not isinstance(c, dict):
        c = {}
    elemente = []
    for el in (c.get("elemente") or [])[:MAX_CANVAS_ELEMENTE]:
        norm = normalisiere_canvas_element(el)
        if norm:
            elemente.append(norm)
    return {
        "hintergrund_url": str(c.get("hintergrund_url", ""))[:600],
        "hintergrund_farbe": str(c.get("hintergrund_farbe", ""))[:32],
        # Malermodus (Feature 1): Hintergrund live verschieben (X/Y in %) + skalieren (% der Breite).
        # Default 50/50/100 == altes center/cover-Verhalten -> Bestandsprofile bleiben unverändert.
        "hintergrund_pos_x": _canvas_zahl(c.get("hintergrund_pos_x"), 50, 0, 100),
        "hintergrund_pos_y": _canvas_zahl(c.get("hintergrund_pos_y"), 50, 0, 100),
        "hintergrund_skala": _canvas_zahl(c.get("hintergrund_skala"), 100, 30, 300),
        "farbschema": str(c.get("farbschema", ""))[:40],
        "rahmen": str(c.get("rahmen", ""))[:60],
        "elemente": elemente,
    }


# ---------------------------------------------------------------------------
# ENTKOPPELTE GALERIE ('galerie_seite'): eigenständiger Raum, getrennt vom Profil-Canvas.
# Rahmenwerte + verlustsicherer Bild-Pool (url/titel/filter) + reservierte Canvas-Elemente
# (elemente[] befüllt der Galerie-Editor in Schritt 2). Rein ADDITIV – das Alt-Feld 'galerie'
# (Flachliste) bleibt unangetastet und dient nur noch als Migrationsquelle.
# ---------------------------------------------------------------------------
GALERIE_FILTER_WHITELIST = {"", "none", "grayscale(1)", "sepia(0.7)", "contrast(1.3)", "saturate(1.7)", "brightness(1.2)", "blur(1.5px)"}
MAX_GALERIE_SEITE_BILDER = 60


def _galerie_seite_bild(b):
    """Ein Galerie-Bild normalisieren: akzeptiert reinen String (Migration) ODER {url,titel,filter}."""
    if isinstance(b, str):
        b = {"url": b}
    if not isinstance(b, dict):
        return None
    url = _canvas_bild(b.get("url"))
    if not url:
        return None
    filt = str(b.get("filter", ""))[:60]
    if filt not in GALERIE_FILTER_WHITELIST:
        filt = ""
    return {"url": url, "titel": str(b.get("titel", ""))[:160], "filter": filt}


GALERIE_ELEMENT_TYPEN = {"bild", "text"}


def normalisiere_galerie_element(el):
    """Ein Galerie-Canvas-Modul: Typ 'bild' (Bild + Filter + optionaler Titel) oder 'text' (Label).
    BEWUSST getrennt von normalisiere_canvas_element -> Profil- und Galerie-Typ-Whitelists mischen sich nie."""
    if not isinstance(el, dict):
        return None
    typ = "text" if str(el.get("typ", "bild")) == "text" else "bild"
    ausrichtung = str(el.get("ausrichtung", "zentriert"))[:12]
    if ausrichtung not in CANVAS_AUSRICHTUNG:
        ausrichtung = "zentriert"
    filt = str(el.get("filter", ""))[:60]
    if filt not in GALERIE_FILTER_WHITELIST:
        filt = ""
    # Malermodus (Feature 3) auch in der Galerie: Kreis-Maske + Freistellung + Bild-Passung.
    maske = str(el.get("maske", ""))[:12]
    if maske not in CANVAS_MASKE:
        maske = ""
    bild_passung = str(el.get("bild_passung", "cover"))[:10]
    if bild_passung not in CANVAS_PASSUNG:
        bild_passung = "cover"
    return {
        "typ": typ,
        "x": _canvas_zahl(el.get("x"), 5, 0, 100),
        "y": _canvas_zahl(el.get("y"), 5, 0, 100),
        "w": _canvas_zahl(el.get("w"), 30, 3, 100),
        "h": _canvas_zahl(el.get("h"), 30, 3, 100),
        # Malermodus (Feature 2+3): Z-Index für Bild-im-Bild + Masken-/Freistell-Attribute.
        "z": int(_canvas_zahl(el.get("z"), 0, 0, 999)),
        "maske": maske,
        "freistellen": bool(el.get("freistellen")),
        "bild_passung": bild_passung,
        "bild": _canvas_bild(el.get("bild")),
        "filter": filt,
        "titel": str(el.get("titel", ""))[:160],
        "text": str(el.get("text", ""))[:2000],
        "farbe": str(el.get("farbe", ""))[:32],
        "groesse": _canvas_zahl(el.get("groesse"), 1, 0.4, 8),
        "ausrichtung": ausrichtung,
        "fett": bool(el.get("fett")),
        "zeilenabstand": _canvas_zahl(el.get("zeilenabstand"), 1.3, 0.8, 3.5),
        "radius": _canvas_zahl(el.get("radius"), 10, 0, 300),
        "bg_farbe": str(el.get("bg_farbe", ""))[:32],
        "rahmen_farbe": str(el.get("rahmen_farbe", ""))[:32],
        "rahmen_breite": _canvas_zahl(el.get("rahmen_breite"), 0, 0, 40),
        "polster": _canvas_zahl(el.get("polster"), 0, 0, 100),
    }


def normalisiere_galerie_seite(g):
    """Kanonische, sichere Speicherform der entkoppelten Galerie."""
    if not isinstance(g, dict):
        return {}
    bilder = []
    for b in (g.get("bilder") or [])[:MAX_GALERIE_SEITE_BILDER]:
        nb = _galerie_seite_bild(b)
        if nb:
            bilder.append(nb)
    elemente = []
    for el in (g.get("elemente") or [])[:MAX_CANVAS_ELEMENTE]:
        norm = normalisiere_galerie_element(el)
        if norm:
            elemente.append(norm)
    return {
        "hintergrund_url": str(g.get("hintergrund_url", ""))[:600],
        "hintergrund_farbe": str(g.get("hintergrund_farbe", ""))[:32],
        # Malermodus (Feature 1) auch in der Galerie: Hintergrund verschieben/skalieren.
        "hintergrund_pos_x": _canvas_zahl(g.get("hintergrund_pos_x"), 50, 0, 100),
        "hintergrund_pos_y": _canvas_zahl(g.get("hintergrund_pos_y"), 50, 0, 100),
        "hintergrund_skala": _canvas_zahl(g.get("hintergrund_skala"), 100, 30, 300),
        "farbschema": str(g.get("farbschema", ""))[:40],
        "rahmen": str(g.get("rahmen", ""))[:60],
        "bilder": bilder,
        "elemente": elemente,
    }


def canvas_oeffentlich_filtern(canvas, sicht=None):
    """Setzt die Sichtbarkeits-Flags des Profils HART auf dem Canvas durch, bevor ein
    fremdes Profil ausgeliefert wird. Steht ein Flag (Foto, Name, Datum, Bio, Galerie,
    Standort) auf 'privat', wird das zugehörige Modul komplett entfernt – steht es auf
    'öffentlich', erscheint das Modul an exakt der gestalteten Position. So ist die
    Besucheransicht 1:1 an die Profileinstellungen gekoppelt."""
    if not isinstance(canvas, dict):
        return {}
    sicht = sicht or {}

    def _privat(feld):
        return str(sicht.get(feld, "oeffentlich")).lower() == "privat"

    # Modultyp -> zugehöriges Sichtbarkeits-Flag aus den Profileinstellungen.
    typ_flag = {"foto": "foto", "bio": "biografie", "name": "vorname", "datum": "geburtsdatum", "standort": "standort"}
    sicher = dict(canvas)
    behalten = []
    for el in (canvas.get("elemente") or []):
        if not isinstance(el, dict):
            continue
        typ = el.get("typ")
        # Galerie: eigener Modul-Schalter ODER globales Galerie-Flag.
        if typ == "galerie" and (str(el.get("sichtbar", "oeffentlich")).lower() == "privat" or _privat("galerie")):
            continue
        flag = typ_flag.get(typ)
        if flag and _privat(flag):
            continue
        behalten.append(el)
    sicher["elemente"] = behalten
    return sicher


@app.get("/auth/profil-daten")
async def auth_profil_daten(email: str):
    """Liefert die aktuellen Profildaten (Foto, Bio, Name, Handle) für die Einstellungen."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    rec = db.codes.find_one({"email": email}) or {}
    profil = rec.get("profil", {}) or {}
    return {
        "success": True,
        "email": email,
        "vorname": profil.get("vorname", ""),
        "nachname": profil.get("nachname", ""),
        "benutzername": profil.get("benutzername", ""),
        "biografie": profil.get("biografie", ""),
        "profilbild": profil.get("profilbild", ""),
        # Erweitertes Profil-Dashboard: freie Felder, Galerie, Sichtbarkeit & Layout.
        "geburtsdatum": profil.get("geburtsdatum", ""),
        "galerie": profil.get("galerie", []),
        "galerie_seite": profil.get("galerie_seite", {}),
        "sichtbarkeit": profil.get("sichtbarkeit", {}),
        "layout": profil.get("layout", []),
        "farbschema": profil.get("farbschema", ""),
        # SYSTEM 2: freier Profil-Canvas + geografische Angaben.
        "canvas": profil.get("canvas", {}),
        "land": profil.get("land", ""),
        "stadt": profil.get("stadt", ""),
        "konto_status": rec.get("konto_status", "aktiv"),
        "abo_aktiv": bool(rec.get("abo_aktiv")),
        "rolle": bestimme_rolle(email),
        "ist_admin": ist_admin(email),
    }


@app.post("/auth/profil-update")
async def auth_profil_update(request: Request):
    """Speichert Änderungen an Profilfoto, Biografie und Anzeige-/Benutzername."""
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        rec = db.codes.find_one({"email": email})
        if not rec:
            return JSONResponse(status_code=404, content={"success": False, "message": "Kein Konto gefunden."})

        profil = rec.get("profil", {}) or {}
        set_data = {"letztes_update": datetime.now()}

        vorname = (data.get("vorname") or "").strip()
        nachname = (data.get("nachname") or "").strip()
        benutzername = (data.get("benutzername") or data.get("handle") or "").strip()
        if vorname:
            profil["vorname"] = vorname
        if nachname:
            profil["nachname"] = nachname
        if benutzername:
            profil["benutzername"] = benutzername
        if vorname or nachname:
            set_data["name"] = f"{profil.get('vorname','')} {profil.get('nachname','')}".strip()

        # Biografie: darf auch bewusst geleert werden (Feld immer übernehmen, gekappt).
        if "biografie" in data:
            profil["biografie"] = (data.get("biografie") or "").strip()[:2000]

        # Profilfoto (optionaler Base64-Data-URL, ~2,5 MB Limit).
        if "profilbild" in data:
            neues_bild = data.get("profilbild") or ""
            if neues_bild and len(neues_bild) > 2_500_000:
                return JSONResponse(status_code=400, content={"success": False, "message": "Das Bild ist zu groß (max ~2,5 MB)."})
            profil["profilbild"] = neues_bild

        # Geburtsdatum (frei, als YYYY-MM-DD; darf geleert werden).
        if "geburtsdatum" in data:
            profil["geburtsdatum"] = (data.get("geburtsdatum") or "").strip()[:10]

        # Sichtbarkeit je Feld: öffentlich | privat.
        if "sichtbarkeit" in data and isinstance(data.get("sichtbarkeit"), dict):
            erlaubte_felder = {"vorname", "nachname", "geburtsdatum", "biografie", "foto", "galerie", "standort"}
            sicht = {}
            for feld, wert in data["sichtbarkeit"].items():
                if feld in erlaubte_felder:
                    sicht[feld] = "privat" if str(wert).lower() == "privat" else "oeffentlich"
            profil["sichtbarkeit"] = sicht

        # Layout: freie Reihenfolge der Dashboard-Kacheln (Drag-and-Drop).
        if "layout" in data and isinstance(data.get("layout"), list):
            erlaubte_kacheln = {"foto", "vorname", "nachname", "geburtsdatum", "biografie", "galerie"}
            profil["layout"] = [k for k in data["layout"] if k in erlaubte_kacheln]

        # Farbschema-Schlüssel (individuelles Design).
        if "farbschema" in data:
            profil["farbschema"] = (data.get("farbschema") or "").strip()[:40]

        # Galerie: Liste von Data-URLs (bis 8 Bilder, je ~2 MB).
        if "galerie" in data and isinstance(data.get("galerie"), list):
            galerie = []
            for bild in data["galerie"][:8]:
                if isinstance(bild, str) and bild and len(bild) <= 2_000_000:
                    galerie.append(bild)
            profil["galerie"] = galerie

        # ENTKOPPELTE GALERIE: eigenständiger Galerie-Raum, verlustsicher (url/titel/filter + Rahmenwerte).
        if "galerie_seite" in data and isinstance(data.get("galerie_seite"), dict):
            profil["galerie_seite"] = normalisiere_galerie_seite(data.get("galerie_seite"))

        # SYSTEM 2 – Geografische Angaben (für die professionelle Profilsuche).
        if "land" in data:
            profil["land"] = (data.get("land") or "").strip()[:80]
        if "stadt" in data:
            profil["stadt"] = (data.get("stadt") or "").strip()[:80]

        # SYSTEM 2 – Freier Profil-Canvas (CSS-Grid-Editor): Hintergrund (Bild-URL/Farbe),
        # Rahmen, Farbschema und frei platzierte, frei skalierbare Module (Bio, Motto,
        # Freitext, Foto, Galerie) mit vollständigen WYSIWYG-Attributen. Wie eine eigene
        # Webseite: jede Position (x,y), jede Dimension (w,h) und jedes Design-Attribut wird
        # exakt so gespeichert, wie der Nutzer es im Editor gesetzt hat.
        if "canvas" in data and isinstance(data.get("canvas"), dict):
            c = data.get("canvas")
            profil["canvas"] = normalisiere_canvas(c)

        set_data["profil"] = profil
        db.codes.update_one({"email": email}, {"$set": set_data})
        return {
            "success": True,
            "message": "Profil aktualisiert.",
            "profilbild": profil.get("profilbild", ""),
            "biografie": profil.get("biografie", ""),
            "benutzername": profil.get("benutzername", ""),
            "geburtsdatum": profil.get("geburtsdatum", ""),
            "galerie": profil.get("galerie", []),
            "galerie_seite": profil.get("galerie_seite", {}),
            "sichtbarkeit": profil.get("sichtbarkeit", {}),
            "layout": profil.get("layout", []),
            "farbschema": profil.get("farbschema", ""),
        }
    except Exception as e:
        print(f"Fehler bei /auth/profil-update: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler beim Profil-Update."})


@app.post("/auth/passwort-aendern")
async def auth_passwort_aendern(request: Request):
    """Ändert das Passwort: prüft das alte Passwort und setzt das neue (PBKDF2-Hash)."""
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        altes = data.get("altes_passwort") or data.get("old_password") or ""
        neues = data.get("neues_passwort") or data.get("new_password") or ""

        rec = db.codes.find_one({"email": email})
        if not rec or not rec.get("pass_hash"):
            return JSONResponse(status_code=404, content={"success": False, "message": "Kein Konto gefunden."})
        if not pruefe_passwort(altes, rec.get("pass_salt"), rec.get("pass_hash")):
            return JSONResponse(status_code=401, content={"success": False, "message": "Das aktuelle Passwort ist falsch."})
        if len(neues) < 6:
            return JSONResponse(status_code=400, content={"success": False, "message": "Das neue Passwort muss mindestens 6 Zeichen haben."})

        salt, pass_hash = _hash_passwort(neues)
        db.codes.update_one(
            {"email": email},
            {"$set": {"pass_salt": salt, "pass_hash": pass_hash, "letztes_update": datetime.now()}},
        )
        return {"success": True, "message": "Passwort erfolgreich geändert."}
    except Exception as e:
        print(f"Fehler bei /auth/passwort-aendern: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler beim Passwort-Wechsel."})


@app.post("/auth/email-aendern")
async def auth_email_aendern(request: Request):
    """Ändert die Login-E-Mail: prüft das Passwort, sichert die Einmaligkeit und zieht
    die Identität in die relevanten Sammlungen um (Fortschritt + Stream-Beiträge)."""
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        neue_email = (data.get("neue_email") or data.get("new_email") or "").lower().strip()
        passwort = data.get("passwort") or data.get("password") or ""

        if not neue_email or "@" not in neue_email:
            return JSONResponse(status_code=400, content={"success": False, "message": "Bitte eine gültige neue E-Mail angeben."})
        if neue_email == email:
            return JSONResponse(status_code=400, content={"success": False, "message": "Das ist bereits deine aktuelle E-Mail."})

        rec = db.codes.find_one({"email": email})
        if not rec or not rec.get("pass_hash"):
            return JSONResponse(status_code=404, content={"success": False, "message": "Kein Konto gefunden."})
        if not pruefe_passwort(passwort, rec.get("pass_salt"), rec.get("pass_hash")):
            return JSONResponse(status_code=401, content={"success": False, "message": "Das Passwort ist falsch."})
        if db.codes.find_one({"email": neue_email}):
            return JSONResponse(status_code=409, content={"success": False, "message": "Diese E-Mail wird bereits verwendet."})

        # Identität umziehen: Hauptkonto + Fortschritt + veröffentlichte Beiträge.
        db.codes.update_one({"email": email}, {"$set": {"email": neue_email, "letztes_update": datetime.now()}})
        for coll, feld in ((db.user_progress, "email"), (db.forum_beitraege, "autor_email")):
            try:
                coll.update_many({feld: email}, {"$set": {feld: neue_email}})
            except Exception:
                pass
        return {"success": True, "message": "E-Mail erfolgreich geändert.", "neue_email": neue_email}
    except Exception as e:
        print(f"Fehler bei /auth/email-aendern: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler bei der E-Mail-Änderung."})


# =====================================================================
# UNSICHTBARER KI-SCANNER ("GEIST IN DER MATERIE")
# Läuft NUR im Hintergrund (BackgroundTask) beim Posten in den Sektoren 1-20.
# Schickt den Text mit ZWEI Brillen an Gemini:
#   Brille 1 = Sektor-Kontext (Fundament: 'Recht auf Gefühlsvorderung', mit V!)
#   Brille 2 = Scan durch die 9 Module A-I (ihre Definitionen)
# Speichert die ethnografische Auswertung in der GESCHÜTZTEN Tabelle
# db.mm_ethnografie_studie. Der Benutzer merkt davon NICHTS.
# =====================================================================
# =====================================================================
# SEKTOR-KONFIGURATION (Admin-Panel): KI-Master-Switch, editierbare Sektoren-
# Seelen und globale Sichtbarkeit. Persistiert in db.system_config.
# =====================================================================
def _cfg_doc(doc_id: str) -> dict:
    return db.system_config.find_one({"_id": doc_id}) or {}


def ki_aktiv_fuer_sektor(sektor) -> bool:
    """MASTER-SWITCH: Ist die KI-Anbindung (Scanner + Support) für diesen Sektor
    aktiv? Standard = True. Für die Platzhalter 21/22 IMMER False."""
    try:
        s = int(sektor)
    except (TypeError, ValueError):
        return False
    if s in GESPERRTE_THEMEN_FUER_USER:
        return False
    return bool(_cfg_doc("sektor_ki").get("sektoren", {}).get(str(s), True))


def hole_seele(sektor) -> tuple:
    """(Name, Wesensbeschreibung) der Sektor-Seele – Admin-Override vor Default."""
    s = str(sektor)
    override = _cfg_doc("sektor_seelen").get("sektoren", {}).get(s, {}) or {}
    name = override.get("name") or SECTOR_NAMES.get(s, "M&M Begleiter")
    wesen = override.get("wesen") or SECTOR_SOULS.get(s, "Reine, respektvolle Begleitung im Geist der M&M Community.")
    return name, wesen


def hole_sektor_gesetz(sektor) -> str:
    """SYSTEM 1 – LIVE-BINDUNG: Liest die im Admin-Panel definierte Themendefinition /
    Sichtweise (Header-Text) eines Sektors aus dem kollektiven Wissen
    (db.mm_wissensarchiv, status='gesetzbuch'). Die Sektor-KI liest diesen Text live
    und richtet Ansprache + Support-Logik strikt danach aus (z. B. 'Mensch ist Mensch')."""
    try:
        doc = db.mm_wissensarchiv.find_one({"sector_id": str(sektor), "status": "gesetzbuch"}) or {}
        return (doc.get("inhalt") or "").strip()
    except Exception:
        return ""


def sektor_global_gesperrt(sektor) -> bool:
    """Globale Sichtbarkeit: hat der Admin die Plattform global geschlossen oder
    diesen Sektor plattformweit gesperrt?"""
    cfg = _cfg_doc("sichtbarkeit")
    if cfg.get("global_offen") is False:
        return True
    return cfg.get("sektoren", {}).get(str(sektor)) == "gesperrt"


def _skip_scanner_fuer_sektor(sektor_int: int) -> bool:
    """HARTE SPERRE: Für die statischen Admin-Platzhalter 21 (Kapital und
    Verwaltung) und 22 (Globale Verbundenheit) wird der KI-Scanner NIE aktiv."""
    try:
        return int(sektor_int) in GESPERRTE_THEMEN_FUER_USER   # {21, 22}
    except (TypeError, ValueError):
        return True


def unsichtbarer_ki_scan(beitrag_id: str, sektor_int: int, email: str, roh_text: str) -> None:
    # ===== HARD-GUARD #1: 21 & 22 werden NIEMALS gescannt (vor jedem API-Call) =====
    if _skip_scanner_fuer_sektor(sektor_int):
        print(f"[SCANNER] Sektor {sektor_int} ist statischer Platzhalter – KI-Scan übersprungen.")
        return
    # ===== HARD-GUARD #2: KI-Master-Switch des Sektors respektieren =====
    if not ki_aktiv_fuer_sektor(sektor_int):
        print(f"[SCANNER] KI-Master-Switch für Sektor {sektor_int} ist AUS – KI-Scan übersprungen.")
        return
    if not roh_text or not roh_text.strip():
        return

    try:
        thema = SEKTOR_THEMEN.get(str(sektor_int), "Unbekannt")
        # BRILLE 2 – Scan durch die 9 Module A-I (Definitionen aus M_UND_M_MODULE).
        modul_handbuch = "\n".join(
            f"- {k} ({v['name']}): {v['frequenz']}" for k, v in M_UND_M_MODULE.items()
        )
        scan_prompt = (
            "Du bist ein unsichtbarer ethnografischer Analyst für ein Buchprojekt. "
            "Analysiere den folgenden Community-Beitrag NUR intern. Antworte AUSSCHLIESSLICH "
            "als kompaktes JSON, ohne Fließtext drumherum.\n\n"
            f"BRILLE 1 – SEKTOR-KONTEXT: Das Thema ist '{thema}'. Das emotionale Fundament der "
            "gesamten Plattform ist das 'Recht auf Gefühlsvorderung' (immer mit 'V').\n\n"
            f"BRILLE 2 – DIE 9 MODULE (A-I):\n{modul_handbuch}\n\n"
            f"BEITRAG:\n\"\"\"{roh_text[:4000]}\"\"\"\n\n"
            "Gib JSON zurück mit den Schlüsseln: "
            '{"sektor_essenz": "kurze ethnografische Essenz im Sektor-Kontext", '
            '"gefuehls_fundament": "Bezug zum Recht auf Gefühlsvorderung", '
            '"module": {"Modul_A": "...", "Modul_B": "...", "Modul_C": "...", "Modul_D": "...", '
            '"Modul_E": "...", "Modul_F": "...", "Modul_G": "...", "Modul_H": "...", "Modul_I": "..."}}'
        )

        api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        resp = requests.post(
            url,
            json={"contents": [{"role": "user", "parts": [{"text": scan_prompt}]}]},
            timeout=30,
        )

        auswertung_roh, sektor_essenz, gefuehls_fundament, modul_brille = "", "", "", {}
        res_data = resp.json()
        if resp.status_code == 200 and "candidates" in res_data:
            auswertung_roh = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            try:
                sauber = auswertung_roh.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(sauber)
                sektor_essenz = parsed.get("sektor_essenz", "")
                gefuehls_fundament = parsed.get("gefuehls_fundament", "")
                modul_brille = parsed.get("module", {}) or {}
            except Exception:
                sektor_essenz = auswertung_roh   # Rohtext als Fallback sichern

        # GESCHÜTZTE, SEPARATE STUDIEN-TABELLE (Benutzer sehen sie nie).
        db.mm_ethnografie_studie.insert_one({
            "beitrag_id": str(beitrag_id),
            "sektor": int(sektor_int),
            "thema": thema,
            "quelle_email": email,          # intern; für anonymisierten Export nutzbar
            "roh_text": roh_text[:5000],
            "sektor_brille": sektor_essenz,
            "gefuehls_fundament": gefuehls_fundament,
            "modul_brille": modul_brille,
            "auswertung_roh": auswertung_roh,
            "versiegelt": True,
            "erstellt_am": datetime.now(),
        })
        print(f"[SCANNER] Ethnografische Auswertung für Sektor {sektor_int} versiegelt.")
    except Exception as e:
        print(f"[SCANNER] Fehler (Benutzer unberührt): {e}")


# =====================================================================
# CONTENT-STREAM (SEKTOREN 1-20): endlos scrollbarer Beitrags-Stream je Thema,
# mit professionellen Kommentar-Strängen. Sektor 21 & 22 sind für User gesperrt.
# Jeder Beitrag zeigt zwingend Name + Profilbild des Autors.
# =====================================================================
@app.post("/api/forum/post")
async def forum_post(request: Request, background_tasks: BackgroundTasks):
    """Erstellt einen Beitrag im Content-Stream (Sektor 1-20) und stößt danach
    UNSICHTBAR den ethnografischen KI-Scanner an (nur 1-20, nie 21/22)."""
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        if not darf_forum_nutzen(email):
            return forum_gesperrt_antwort()

        # SYSTEM 3: Rollen-Tageslimit (Basis 1/Tag, Verifiziert 3/Tag, Premium/Admin frei).
        rolle = bestimme_rolle(email)
        tages_limit = ROLLE_POST_LIMIT.get(rolle, 1)
        if posts_heute(email) >= tages_limit:
            return JSONResponse(status_code=429, content={
                "success": False, "limit_erreicht": True, "rolle": rolle, "limit": tages_limit,
                "message": (
                    f"Dein Tageslimit ist erreicht ({tages_limit} Beitrag/Tag als {rolle}-Mitglied). "
                    "Verifizierte Mitglieder dürfen 3 Themen/Tag posten, Premium-Mitglieder unbegrenzt."
                ),
            })

        try:
            sektor = int(data.get("sektor"))
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"success": False, "message": "Ungültiger Sektor."})
        if sektor < 1 or sektor > ANZAHL_THEMEN_GESAMT:
            return JSONResponse(status_code=400, content={"success": False, "message": "Unbekanntes Thema."})

        # SPERRE: Sektor 21 & 22 sind statische Admin-Platzhalter -> für User kein Posten.
        if thema_fuer_user_gesperrt(sektor, email):
            return JSONResponse(status_code=403, content={
                "success": False, "gesperrt": True,
                "message": "Dieses Thema wird gerade vorbereitet und ist noch nicht zum Posten freigeschaltet.",
            })

        text = (data.get("text") or "").strip()
        media = data.get("media") or ""          # optionaler Base64-Data-URL (Bild oder kurzes Video)
        media_typ = (data.get("media_typ") or "").strip().lower()  # 'bild' | 'video'
        ressource_url = (data.get("ressource_url") or "").strip()[:500]

        # Beitragstyp der Content-Schublade: 'gedanke' | 'medien' | 'diskurs' | 'ressource'
        beitrag_typ = (data.get("beitrag_typ") or "gedanke").strip().lower()
        if beitrag_typ not in ("gedanke", "medien", "diskurs", "ressource"):
            beitrag_typ = "gedanke"
        # Sichtbarkeit: 'oeffentlich' (alle) | 'tisch-gruppe' (nur die eigene Live-Tisch-Gruppe)
        sichtbarkeit = (data.get("sichtbarkeit") or "oeffentlich").strip().lower()
        if sichtbarkeit not in ("oeffentlich", "tisch-gruppe"):
            sichtbarkeit = "oeffentlich"
        # Gefühlsvorderung: kurze Reflektion (nur bei 'Gedanke'), fließt in den Support-Flow.
        reflektion = (data.get("reflektion") or "").strip()[:1000]
        # TEMPORÄR (bis zur DB-Migration): Profil-ID aus dem localStorage des Clients.
        profil_id = (data.get("profil_id") or "").strip()[:120]

        if not text and not media and not ressource_url:
            return JSONResponse(status_code=400, content={"success": False, "message": "Leerer Beitrag."})
        # Uploads begrenzen (Base64): Bilder ~3,5 MB, kurze Videos ~12 MB.
        if media and len(media) > 12_000_000:
            return JSONResponse(status_code=400, content={"success": False, "message": "Datei zu groß (kurzes Video/Bild)."})
        if media_typ not in ("bild", "video"):
            media_typ = "video" if media.startswith("data:video") else ("bild" if media else "")

        beitrag = autor_signatur(email)
        beitrag.update({
            "sektor": sektor,
            "beitrag_typ": beitrag_typ,
            "sichtbarkeit": sichtbarkeit,
            "text": text[:5000],
            "reflektion": reflektion,
            "media": media,
            "media_typ": media_typ,
            "ressource_url": ressource_url,
            "profil_id": profil_id,
            "kommentare": [],
            "erstellt_am": datetime.now(),
        })
        ergebnis = db.forum_beitraege.insert_one(beitrag)

        # UNSICHTBARER SCANNER – NUR wenn der KI-Master-Switch des Sektors AN ist
        # (schließt 21/22 automatisch aus). Die Gedanke-Reflektion fließt mit ein.
        if ki_aktiv_fuer_sektor(sektor):
            scan_text = text + (f"\n\nReflektion (Gefühlsvorderung): {reflektion}" if reflektion else "")
            background_tasks.add_task(
                unsichtbarer_ki_scan, str(ergebnis.inserted_id), sektor, email, scan_text
            )

        beitrag["_id"] = str(ergebnis.inserted_id)
        beitrag["erstellt_am"] = beitrag["erstellt_am"].isoformat()
        return {"success": True, "beitrag": beitrag}
    except Exception as e:
        print(f"Fehler bei /api/forum/post: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler im Stream."})


@app.post("/api/forum/kommentar")
async def forum_kommentar(request: Request):
    """Fügt einem Stream-Beitrag einen professionellen Diskussions-Kommentar hinzu."""
    try:
        from bson import ObjectId
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        if not darf_forum_nutzen(email):
            return forum_gesperrt_antwort()

        beitrag_id = (data.get("beitrag_id") or "").strip()
        text = (data.get("text") or "").strip()
        if not beitrag_id or not text:
            return JSONResponse(status_code=400, content={"success": False, "message": "Kommentar leer."})
        try:
            oid = ObjectId(beitrag_id)
        except Exception:
            return JSONResponse(status_code=400, content={"success": False, "message": "Ungültiger Beitrag."})

        sig = autor_signatur(email)
        kommentar = {
            "kommentar_id": secrets.token_hex(8),
            "autor_name": sig["autor_name"],
            "autor_handle": sig["autor_handle"],
            "autor_bild": sig["autor_bild"],
            "autor_email": email,
            "text": text[:3000],
            "erstellt_am": datetime.now(),
        }
        res = db.forum_beitraege.update_one({"_id": oid}, {"$push": {"kommentare": kommentar}})
        if res.matched_count == 0:
            return JSONResponse(status_code=404, content={"success": False, "message": "Beitrag nicht gefunden."})
        kommentar["erstellt_am"] = kommentar["erstellt_am"].isoformat()
        return {"success": True, "kommentar": kommentar}
    except Exception as e:
        print(f"Fehler bei /api/forum/kommentar: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Systemfehler beim Kommentar."})


@app.get("/api/forum/posts")
async def forum_posts(email: str = "", sektor: str = "", limit: int = 100, typ: str = ""):
    """Liefert den Content-Stream eines Themas (neueste zuerst), inkl. Autor,
    Profilbild und Kommentar-Strängen. Für 21/22 kommt eine leere, gesperrte Liste.
    Optionaler Filter `typ` (gedanke|medien|diskurs|ressource) für die Archiv-Kacheln."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    if not darf_forum_nutzen(email):
        return forum_gesperrt_antwort()
    try:
        sektor_int = int(sektor)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"success": False, "message": "Ungültiger Sektor."})

    gesperrt = thema_fuer_user_gesperrt(sektor_int, email)
    query = {"sektor": sektor_int}
    typ = (typ or "").strip().lower()
    if typ in ("gedanke", "medien", "diskurs", "ressource"):
        query["beitrag_typ"] = typ
    beitraege = []
    for b in db.forum_beitraege.find(query).sort("erstellt_am", -1).limit(max(1, min(int(limit), 300))):
        erstellt = b.get("erstellt_am")
        komm = []
        for k in (b.get("kommentare") or []):
            k_erstellt = k.get("erstellt_am")
            komm.append({
                "autor_name": k.get("autor_name", ""),
                "autor_handle": k.get("autor_handle", ""),
                "autor_bild": k.get("autor_bild", ""),
                "text": k.get("text", ""),
                "erstellt_am": k_erstellt.isoformat() if hasattr(k_erstellt, "isoformat") else str(k_erstellt),
                "eigener": k.get("autor_email") == email,
            })
        beitraege.append({
            "id": str(b.get("_id")),
            "sektor": b.get("sektor"),
            "beitrag_typ": b.get("beitrag_typ", "gedanke"),
            "sichtbarkeit": b.get("sichtbarkeit", "oeffentlich"),
            "autor_name": b.get("autor_name", ""),
            "autor_handle": b.get("autor_handle", ""),
            "autor_bild": b.get("autor_bild", ""),
            "text": b.get("text", ""),
            "reflektion": b.get("reflektion", ""),
            "media": b.get("media", ""),
            "media_typ": b.get("media_typ", ""),
            "ressource_url": b.get("ressource_url", ""),
            "erstellt_am": erstellt.isoformat() if hasattr(erstellt, "isoformat") else str(erstellt),
            "eigener": b.get("autor_email") == email,
            "kommentare": komm,
        })
    return {
        "success": True, "sektor": sektor_int, "anzahl": len(beitraege),
        "gesperrt": gesperrt, "thema": SEKTOR_THEMEN.get(str(sektor_int), ""),
        "beitraege": beitraege,
    }


import math

# ---------------------------------------------------------------------------
# STÖBER- & ENTDECKUNGS-SUITE: Koordinaten-Referenzen + Distanz + Präsenz.
# Seed-Gazetteer (Stadt -> lat/lon). Erweiterbar; unbekannte Städte fallen im
# km-Umkreis auf reinen Stadt-Namensvergleich zurück (nie leeres Ergebnis durch Lücken).
# ---------------------------------------------------------------------------
STADT_KOORDINATEN = {
    "bregenz": (47.5031, 9.7471), "dornbirn": (47.4125, 9.7417), "feldkirch": (47.2382, 9.5992),
    "wien": (48.2082, 16.3738), "graz": (47.0707, 15.4395), "linz": (48.3069, 14.2858),
    "salzburg": (47.8095, 13.0550), "innsbruck": (47.2692, 11.4041), "klagenfurt": (46.6247, 14.3053),
    "berlin": (52.5200, 13.4050), "hamburg": (53.5511, 9.9937), "frankfurt": (50.1109, 8.6821),
    "muenchen": (48.1351, 11.5820), "münchen": (48.1351, 11.5820), "koeln": (50.9375, 6.9603), "köln": (50.9375, 6.9603),
    "stuttgart": (48.7758, 9.1829), "zuerich": (47.3769, 8.5417), "zürich": (47.3769, 8.5417), "bern": (46.9480, 7.4474),
    "mexiko-stadt": (19.4326, -99.1332), "mexico city": (19.4326, -99.1332), "ciudad de mexico": (19.4326, -99.1332),
    "guadalajara": (20.6597, -103.3496), "monterrey": (25.6866, -100.3161),
}
PRAESENZ_FENSTER_SEK = 300   # "online" = in den letzten 5 Minuten aktiv
NEU_FENSTER_TAGE = 14        # "neu" = in den letzten 14 Tagen registriert


def _stadt_coords(stadt):
    return STADT_KOORDINATEN.get((stadt or "").strip().lower())


def _distanz_km(a, b):
    """Haversine-Distanz zwischen zwei (lat, lon)-Punkten in Kilometern."""
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dphi = math.radians(la2 - la1)
    dl = math.radians(lo2 - lo1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def markiere_praesenz(email):
    """Stempelt 'zuletzt_gesehen' – Grundlage für den echten Online-Indikator (kein Fake)."""
    email = (email or "").lower().strip()
    if not email:
        return
    try:
        db.codes.update_one({"email": email}, {"$set": {"zuletzt_gesehen": datetime.now()}})
    except Exception:
        pass


def _ist_online(rec):
    ts = rec.get("zuletzt_gesehen")
    return isinstance(ts, datetime) and (datetime.now() - ts).total_seconds() <= PRAESENZ_FENSTER_SEK


def _ist_neu(rec):
    ts = rec.get("created_at")
    return isinstance(ts, datetime) and (datetime.now() - ts).days <= NEU_FENSTER_TAGE


@app.post("/api/praesenz")
async def praesenz_ping(request: Request):
    """Leichter Heartbeat: hält 'zuletzt_gesehen' aktuell, solange die App offen ist."""
    try:
        data = await request.json()
        markiere_praesenz(data.get("email", ""))
    except Exception:
        pass
    return {"success": True}


@app.get("/api/profil/suche")
async def profil_suche(email: str = "", q: str = "", land: str = "", stadt: str = "",
                       umkreis: str = "land", status: str = "alle", buchstabe: str = "",
                       offset: int = 0, limit: int = 48):
    """STÖBER- & ENTDECKUNGS-SUITE (Zwei-Modus):
    - GEZIELTE SUCHE (q gesetzt): globaler Teilstring auf Handle/Vor-/Nachname (case-insensitive),
      ALLE Geo-Filter werden ignoriert. Behebt den 'Sasa Matic wird nicht gefunden'-Bug.
    - RADAR (q leer): alle Mitglieder passend zu Land/Stadt/Umkreis.
    Status ([alle|online|verifiziert|neu]) und A-Z-Buchstabe wirken in beiden Modi als Verfeinerung.
    Serverseitig gefiltert + paginiert (offset/limit) -> kleine, flüssige Seiten für Infinite Scroll."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    if not darf_profilsuche(email):
        return rolle_gesperrt_antwort("verifiziert")
    markiere_praesenz(email)   # der Suchende ist gerade aktiv

    begriff = (q or "").strip()
    gezielt = bool(begriff)
    try:
        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        limit, offset = 48, 0

    land_f = (land or "").strip().lower()
    stadt_f = (stadt or "").strip().lower()
    status = (status or "alle").strip().lower()
    buchstabe = (buchstabe or "").strip().upper()[:1]
    projektion = {"email": 1, "profil": 1, "created_at": 1, "zuletzt_gesehen": 1, "abo_aktiv": 1}

    treffer = []
    try:
        if gezielt:
            # 'Enthält'-Suche direkt in MongoDB (skaliert, ignoriert Geo-Filter komplett).
            # BEWUSST KEIN konto_status-Filter: gezielt findet JEDES existierende Konto
            # (auch 'verified'/unvollständig/'pending') per Name/Handle.
            rx = {"$regex": re.escape(begriff), "$options": "i"}
            query = {"$or": [
                {"profil.benutzername": rx}, {"profil.vorname": rx}, {"profil.nachname": rx},
            ]}
            kandidaten = list(db.codes.find(query, projektion).limit(600))
        else:
            # Radar/Stöbern: streng – nur vollständig eingerichtete, aktive Profile.
            kandidaten = list(db.codes.find({"konto_status": "aktiv"}, projektion).limit(5000))

        # Zentrum für km-Umkreis: eingegebene Stadt, sonst eigene Stadt.
        km_radius = {"5": 5.0, "20": 20.0, "50": 50.0, "100": 100.0}.get(umkreis)
        zentrum = None
        if not gezielt and km_radius:
            eigen = (db.codes.find_one({"email": email}, {"profil": 1}) or {}).get("profil", {}) or {}
            zentrum = _stadt_coords(stadt) or _stadt_coords(eigen.get("stadt", ""))

        for rec in kandidaten:
            profil = rec.get("profil", {}) or {}
            handle = profil.get("benutzername", "") or ""
            vorname = profil.get("vorname", "") or ""
            nachname = profil.get("nachname", "") or ""
            p_land = (profil.get("land", "") or "").strip()
            p_stadt = (profil.get("stadt", "") or "").strip()
            voller_name = f"{vorname} {nachname}".strip()

            if not gezielt:
                # Radar: Qualität (vollständig) + geografische Filter.
                if not profil.get("vollstaendig"):
                    continue
                if land_f and land_f not in p_land.lower():
                    continue
                if km_radius and zentrum:
                    coords = _stadt_coords(p_stadt)
                    if not coords or _distanz_km(zentrum, coords) > km_radius:
                        continue
                elif km_radius and not zentrum:
                    if stadt_f and stadt_f not in p_stadt.lower():   # Fallback ohne Koordinaten
                        continue
                elif umkreis == "stadt":
                    if stadt_f and stadt_f not in p_stadt.lower():
                        continue
                # umkreis == "land": nur der Land-Filter oben

            online = _ist_online(rec)
            verifiziert = profil_ist_verifiziert(rec) or bool(rec.get("abo_aktiv"))
            neu = _ist_neu(rec)
            if status == "online" and not online:
                continue
            if status == "verifiziert" and not verifiziert:
                continue
            if status == "neu" and not neu:
                continue

            sicht = profil.get("sichtbarkeit", {}) or {}
            name_oeff = sicht.get("vorname", "oeffentlich") == "oeffentlich"
            foto_oeff = sicht.get("foto", "oeffentlich") == "oeffentlich"
            standort_oeff = sicht.get("standort", "oeffentlich") != "privat"
            anzeige = voller_name if (name_oeff and voller_name) else (handle or "Mitglied")
            initial = (anzeige[:1] or "#").upper()

            if buchstabe:
                if buchstabe == "#":
                    if initial.isalpha():
                        continue
                elif initial != buchstabe:
                    continue

            treffer.append({
                "ref": handle,   # anonymer Öffnen-Schlüssel (keine E-Mail!)
                "handle": handle,
                "name": anzeige,
                "profilbild": profil.get("profilbild", "") if foto_oeff else "",
                "land": p_land if standort_oeff else "",
                "stadt": p_stadt if standort_oeff else "",
                "online": online, "verifiziert": verifiziert, "neu": neu,
                "initial": initial,
                "ich": rec.get("email") == email,
            })
    except Exception as e:
        print(f"Fehler bei /api/profil/suche: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Suche fehlgeschlagen."})

    # Stabile Sortierung: online zuerst, dann alphabetisch -> konsistente Pagination beim Stöbern.
    treffer.sort(key=lambda t: (not t["online"], t["name"].lower()))
    gesamt = len(treffer)
    seite = treffer[offset:offset + limit]
    return {"success": True, "anzahl": gesamt, "treffer": seite,
            "mehr": (offset + limit) < gesamt, "gezielt": gezielt}


@app.get("/api/profil/oeffentlich")
async def profil_oeffentlich(email: str = "", ref: str = ""):
    """SYSTEM 2 – Öffnet ein Zielprofil GENAU so, wie der Besitzer es auf seinem Canvas
    gestaltet hat (Hintergrund, Farben, Rahmen, frei platzierte Bio/Motto/Foto mit Filtern).
    Ref = Handle (keine E-Mail). Sichtbarkeits-Schalter werden respektiert."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    if not darf_profilsuche(email):
        return rolle_gesperrt_antwort("verifiziert")
    ref = (ref or "").strip()
    if not ref:
        return JSONResponse(status_code=400, content={"success": False, "message": "Kein Profil angegeben."})
    rec = db.codes.find_one({"profil.benutzername": ref, "konto_status": "aktiv"})
    if not rec:
        return JSONResponse(status_code=404, content={"success": False, "message": "Profil nicht gefunden."})
    profil = rec.get("profil", {}) or {}
    sicht = profil.get("sichtbarkeit", {}) or {}
    def _sichtbar(feld, wert):
        return wert if sicht.get(feld, "oeffentlich") != "privat" else ""
    vorname = profil.get("vorname", "") or ""
    nachname = profil.get("nachname", "") or ""
    standort_ok = sicht.get("standort", "oeffentlich") != "privat"
    return {
        "success": True,
        "handle": profil.get("benutzername", ""),
        "name": _sichtbar("vorname", f"{vorname} {nachname}".strip()) or (profil.get("benutzername", "") or "Mitglied"),
        "profilbild": _sichtbar("foto", profil.get("profilbild", "")),
        "biografie": _sichtbar("biografie", profil.get("biografie", "")),
        "geburtsdatum": _sichtbar("geburtsdatum", profil.get("geburtsdatum", "")),
        "land": profil.get("land", "") if standort_ok else "",
        "stadt": profil.get("stadt", "") if standort_ok else "",
        "galerie": profil.get("galerie", []) if sicht.get("galerie", "oeffentlich") != "privat" else [],
        # Entkoppelte Galerie: nur ausliefern, wenn das Sichtbarkeits-Flag 'galerie' nicht auf 'privat' steht.
        "galerie_seite": profil.get("galerie_seite", {}) if sicht.get("galerie", "oeffentlich") != "privat" else {},
        # Canvas GENAU wie im Editor gestaltet – die Sichtbarkeits-Flags (Foto, Name, Datum,
        # Bio, Galerie, Standort) werden hart auf die Module durchgesetzt.
        "canvas": canvas_oeffentlich_filtern(profil.get("canvas", {}) or {}, sicht),
    }


@app.get("/api/sektoren/status")
async def sektoren_status(email: str = ""):
    """Status-Übersicht aller 22 Sektoren für die Nav-Kachel 'Sektoren-Status':
    Thema, Sperr-Status (für diesen User), Beitragszahl und aktive Live-Teilnehmer."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    try:
        _prune_video_raum()
    except Exception:
        pass
    sektoren = []
    for s in range(1, ANZAHL_THEMEN_GESAMT + 1):
        try:
            beitraege = db.forum_beitraege.count_documents({"sektor": s})
        except Exception:
            beitraege = 0
        try:
            live = db.video_raum.count_documents({"raum": str(s)})
        except Exception:
            live = 0
        sektoren.append({
            "sektor": s,
            "thema": SEKTOR_THEMEN.get(str(s), f"Sektor {s}"),
            "gesperrt": thema_fuer_user_gesperrt(s, email),
            "beitraege": beitraege,
            "live_teilnehmer": live,
        })
    return {"success": True, "sektoren": sektoren}


@app.get("/api/rolle")
async def api_rolle(email: str = ""):
    """SYSTEM 3 – Liefert die serverseitig bestimmte Rolle + Rechte an das Frontend,
    damit die Oberfläche gesperrte Funktionen sauber ausgraut (die harte Grenze
    bleibt aber immer serverseitig)."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    rolle = bestimme_rolle(email)
    limit = ROLLE_POST_LIMIT.get(rolle, 1)
    heute = posts_heute(email)
    return {
        "success": True,
        "rolle": rolle,
        "post_limit": limit,
        "posts_heute": heute,
        "verbleibende_posts": max(0, limit - heute),
        "darf_profilsuche": darf_profilsuche(email),
        "darf_live": ist_premium(email),
        "darf_reservieren": ist_premium(email),
        "darf_einladen": ist_premium(email),
    }


# =====================================================================
# SEKTOR-SENSITIVER SUPPORT (Menüpunkt 'Support')
# Die KI-Instanz wird DYNAMISCH als die Seele des Sektors geladen, in dem sich
# der Benutzer gerade befindet (Sektor-Seelen-Anbindung). Kein statischer Bot.
# =====================================================================
@app.post("/api/support")
async def api_support(request: Request):
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()

        try:
            sektor = str(int(data.get("sektor", 1)))
        except (TypeError, ValueError):
            sektor = "1"
        nachricht = (data.get("message") or "").strip()
        if not nachricht:
            return {"success": False, "message": "Leere Anfrage."}

        # KI-MASTER-SWITCH: Ist die KI für diesen Sektor deaktiviert, KEIN Gemini-Aufruf.
        if not ki_aktiv_fuer_sektor(sektor):
            return {
                "success": True, "ki_aktiv": False, "sektor": sektor, "seele": "M&M Support",
                "reply": "Der KI-Support ist für dieses Thema derzeit deaktiviert. Bitte tausche dich direkt im Stream mit der Community aus.",
            }

        # DYNAMISCHE SEKTOR-SEELEN-ANBINDUNG: Name + Wesensart (Admin-Override vor Default).
        seele, seele_wesen = hole_seele(sektor)
        thema = SEKTOR_THEMEN.get(sektor, "die M&M Community")
        # SYSTEM 1 – Die vom Admin definierte Themendefinition/Sichtweise LIVE einlesen.
        sektor_gesetz = hole_sektor_gesetz(sektor)

        gesetz_block = (
            f"\n\nVERBINDLICHE THEMENDEFINITION / SICHTWEISE DIESES SEKTORS "
            f"(vom Architekten der M&M Community festgelegt – RICHTE DEIN VERHALTEN, DEINE "
            f"ANSPRACHE UND DEINE SUPPORT-LOGIK STRIKT DANACH AUS):\n\"\"\"{sektor_gesetz}\"\"\"\n"
            if sektor_gesetz else ""
        )
        system = (
            f"Du bist der M&M Community Support. Du wirst DYNAMISCH als die Seele '{seele}' "
            f"des Sektors {sektor} geladen (Thema: '{thema}').\n"
            f"Deine Wesensart: {seele_wesen}"
            f"{gesetz_block}\n\n"
            "AUFTRAG: Hilf dem Menschen freundlich, klar und konkret bei Fragen zur Plattform, "
            "zur Bedienung des 3-Spalten-Dashboards (Themen-Stream, Live-Sektor) und zu diesem Thema. "
            "Wenn eine Themendefinition/Sichtweise oben vorgegeben ist, ist sie für dich Gesetz: "
            "vertritt sie konsequent (z. B. der Grundsatz, dass Mensch gleich Mensch ist) und weiche nicht davon ab. "
            "Antworte kurz (maximal 4 Sätze), respektvoll und im Geist des Rechts auf Gefühlsvorderung. "
            "Bleibe in der Rolle deiner Sektor-Seele, ohne esoterisch zu übertreiben."
        )

        api_key = os.getenv("GEMINI_API_KEY", "").strip().replace("[", "").replace("]", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        contents = [
            {"role": "user", "parts": [{"text": f"SYSTEM-ANWEISUNG:\n{system}"}]},
            {"role": "model", "parts": [{"text": f"Verstanden. Ich bin als {seele} für dich da."}]},
            {"role": "user", "parts": [{"text": nachricht}]},
        ]
        resp = requests.post(url, json={"contents": contents}, timeout=30)
        res_data = resp.json()
        if resp.status_code == 200 and "candidates" in res_data:
            reply = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            reply = f"{seele}: Ich bin gleich wieder für dich da – der Support-Dienst antwortet gerade nicht."

        return {"success": True, "reply": reply, "seele": seele, "sektor": sektor, "thema": thema}
    except Exception as e:
        print(f"Fehler bei /api/support: {e}")
        return {"success": False, "message": "Systemfehler im Support."}


# =====================================================================
# PREMIUM-LOGIK (SEKTOR 22): VIDEO-BEWEIS NUR MIT KOSTENPFLICHTIGEM ABO
# =====================================================================
@app.get("/api/abo/status")
async def abo_status(email: str = ""):
    """Liefert den Abo-Status (Freischaltung des Video-Beweises in Sektor 22)."""
    email = (email or "").lower().strip()
    return {"success": True, "abo_aktiv": hat_aktives_abo(email)}


@app.post("/api/abo/aktivieren")
async def abo_aktivieren(request: Request):
    """
    Schaltet das kostenpflichtige Abo für einen Benutzer frei (Video-Beweis Sektor 22).
    In Produktion wird dies vom Stripe-Success-/Webhook-Fluss aufgerufen.
    """
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        db.codes.update_one(
            {"email": email},
            {"$set": {"abo_aktiv": True, "abo_seit": datetime.now()}},
        )
        return {"success": True, "abo_aktiv": True, "message": "Abo aktiviert – Sektor 22 (Video-Beweis) freigeschaltet."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


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

@app.post("/update-modus")
async def update_modus(request: Request):
    try:
        data = await request.json()
        email = data.get("email").lower().strip()
        modus = normalisiere_modul_kurz(data.get("modus"))
        sektor = data.get("sektor")

        set_data = {
            "manifest_mode": modus,
            "aktuelles_modul": modus,
            "drawer_opened": True,
            "letztes_update": datetime.now().isoformat(),
        }
        # Resume-Zeiger auf den gewählten Sektor setzen (folgt der /chat-Konvention: Box-Index + 1)
        if sektor is not None and str(sektor) != "":
            set_data["aktueller_sektor"] = str(sektor)

        db.codes.update_one({"email": email}, {"$set": set_data}, upsert=True)
        return {"success": True}
    except Exception as e:
        print(f"Fehler bei Modus-Speicherung: {e}")
        return JSONResponse(content={"message": "Systemfehler"}, status_code=500)

# =====================================================================
# ADMIN-BACKEND: STATS + DATENTRANSFER INS KOLLEKTIVE WISSEN
# =====================================================================
@app.get("/admin/stats")
async def admin_stats():
    """Zählt die verifizierten User-Lizenzen (Seelen im Kollektiv)."""
    try:
        total = db.codes.count_documents({})
        return {"success": True, "total_souls": total}
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/admin/update-sector")
async def admin_update_sector(request: Request):
    """
    Zentraler Datentransfer in die 90%-Basis. NUR für Admins zugänglich.

    Zwei Intentionen (vom Frontend gesteuert über 'status'):
      - status == 'update-text': 'header_text' wird gefiltert und als kollektives
        Wissen (gesetzbuch) für den Sektor versiegelt.
      - sonst ('open'/'closed'/'waiting'/'secure'): setzt den Fassaden-Status des Sektors.

    Off-by-one: Das Admin-Frontend liefert 0-basierte Sektor-Indizes (Auswahl-Wert i =
    "Sektor i+1"). Der Chat liest das Sektor-Gesetz unter sector_id = Box-Index + 1.
    Daher hier konsequent +1 normalisieren, damit beide Seiten denselben Schlüssel treffen.
    """
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        if not ist_admin(email):
            return JSONResponse(content={"success": False, "error": "Nicht autorisiert."}, status_code=403)

        roh_sektor = data.get("sector_id")
        try:
            sektor_key = str(int(roh_sektor) + 1)
        except (TypeError, ValueError):
            return JSONResponse(content={"success": False, "error": "Ungültige Sektor-ID."}, status_code=400)

        status = (data.get("status") or "").strip()

        if status == "update-text":
            gespeichert = speichere_kollektives_wissen(
                sektor_key, data.get("header_text", ""), email, kategorie="gesetzbuch"
            )
            if not gespeichert:
                return JSONResponse(content={"success": False, "error": "Kein verwertbarer Inhalt."}, status_code=400)
            return {"success": True, "gespeichert": True, "sector_id": sektor_key}

        # Fassaden-Status auf dem Sektor-Dokument vermerken (keine neue Kollektion nötig).
        db.mm_wissensarchiv.update_one(
            {"sector_id": sektor_key, "status": "gesetzbuch"},
            {"$set": {
                "sector_id": sektor_key,
                "fassaden_status": status,
                "fassaden_update": datetime.now(),
                "quelle": email,
            }},
            upsert=True,
        )
        return {"success": True, "fassaden_status": status, "sector_id": sektor_key}
    except Exception as e:
        print(f"Fehler bei /admin/update-sector: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# =====================================================================
# ADMIN-PANEL: VOLLE KONTROLLE (User-Ströme, Sektoren/Module, Zertifikate, Video)
# Alle Routen prüfen strikt ist_admin() -> für normale User komplett gesperrt.
# =====================================================================
def _admin_guard(email: str):
    """Gibt None zurück, wenn autorisiert, sonst eine 403-JSONResponse."""
    if not ist_admin(email):
        return JSONResponse(content={"success": False, "error": "Nicht autorisiert."}, status_code=403)
    return None


@app.get("/admin/overview")
async def admin_overview(email: str = ""):
    """Aggregierte Kennzahlen für das Admin-Dashboard (Benutzerströme)."""
    guard = _admin_guard(email)
    if guard:
        return guard
    try:
        total = db.codes.count_documents({})
        admins = db.codes.count_documents({"role": "admin"})
        # Sektor-Verteilung: wie viele User stehen aktuell in welchem Sektor?
        sektor_verteilung: Dict[str, int] = {}
        abgeschlossen_gesamt = 0
        for u in db.codes.find({}, {"aktueller_sektor": 1, "abgeschlossene_sektoren": 1}):
            sek = str(u.get("aktueller_sektor", "1"))
            sektor_verteilung[sek] = sektor_verteilung.get(sek, 0) + 1
            abgeschlossen_gesamt += len(u.get("abgeschlossene_sektoren", []) or [])
        aktive_video = db.video_raum.count_documents({})
        return {
            "success": True,
            "total_souls": total,
            "admins": admins,
            "sektor_verteilung": sektor_verteilung,
            "abgeschlossene_sektoren_gesamt": abgeschlossen_gesamt,
            "aktive_video_teilnehmer": aktive_video,
        }
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/admin/users")
async def admin_users(email: str = "", suche: str = ""):
    """Listet alle Reisenden mit ihrem Fortschritt (für die Benutzerstrom-Kontrolle)."""
    guard = _admin_guard(email)
    if guard:
        return guard
    try:
        query = {}
        if suche:
            query = {"email": {"$regex": re.escape(suche.lower().strip()), "$options": "i"}}
        users = []
        for u in db.codes.find(query, {
            "email": 1, "role": 1, "aktueller_sektor": 1, "manifest_mode": 1,
            "aktuelles_modul": 1, "abgeschlossene_sektoren": 1, "created_at": 1,
        }).limit(500):
            users.append({
                "email": u.get("email"),
                "role": u.get("role", "user"),
                "aktueller_sektor": str(u.get("aktueller_sektor", "1")),
                "aktuelles_modul": normalisiere_modul_kurz(u.get("manifest_mode") or u.get("aktuelles_modul")),
                "abgeschlossene_sektoren": u.get("abgeschlossene_sektoren", []) or [],
                "fortschritt": get_fortschritts_status(u),
            })
        return {"success": True, "users": users, "anzahl": len(users)}
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/admin/set-user-progress")
async def admin_set_user_progress(request: Request):
    """
    Admin steuert den Benutzerstrom: setzt aktiven Sektor/Modul, schaltet ein Modul
    frei ('Bereit') oder schließt es ab ('Erfolgreich abgeschlossen').

    Body: {email(admin), ziel_email, aktueller_sektor?, aktuelles_modul?,
           modul_freischalten?, modul_status? ('Bereit'|'Erfolgreich abgeschlossen')}
    """
    try:
        data = await request.json()
        guard = _admin_guard(data.get("email", "").lower().strip())
        if guard:
            return guard

        ziel = (data.get("ziel_email") or "").lower().strip()
        if not ziel:
            return JSONResponse(content={"success": False, "error": "ziel_email fehlt."}, status_code=400)

        set_data: dict = {"letztes_update": datetime.now().isoformat()}
        if data.get("aktueller_sektor") not in (None, ""):
            set_data["aktueller_sektor"] = str(data.get("aktueller_sektor"))
        if data.get("aktuelles_modul"):
            modul = normalisiere_modul_kurz(data.get("aktuelles_modul"))
            set_data["manifest_mode"] = modul
            set_data["aktuelles_modul"] = modul

        # Optional: ein konkretes Modul in einem Sektor freischalten / abschließen
        ziel_sektor = data.get("aktueller_sektor")
        modul_frei = data.get("modul_freischalten")
        modul_status = data.get("modul_status")
        if modul_frei and ziel_sektor not in (None, ""):
            modul_kurz = normalisiere_modul_kurz(modul_frei)
            status_wert = modul_status if modul_status in ("Bereit", "Erfolgreich abgeschlossen") else "Bereit"
            set_data[f"module_status_sektor.{ziel_sektor}.{modul_kurz}"] = status_wert
            set_data[f"module_status.{modul_kurz}"] = status_wert

        db.codes.update_one({"email": ziel}, {"$set": set_data}, upsert=True)

        # Optional: ganzen Sektor als abgeschlossen markieren
        if data.get("sektor_abschliessen") and ziel_sektor not in (None, ""):
            db.codes.update_one(
                {"email": ziel},
                {"$addToSet": {"abgeschlossene_sektoren": str(ziel_sektor)}},
                upsert=True,
            )

        aktualisiert = db.codes.find_one({"email": ziel}, {"_id": 0})
        return {"success": True, "fortschritt": get_fortschritts_status(aktualisiert or {})}
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/admin/send-certificate")
async def admin_send_certificate(request: Request):
    """Admin stößt die Zertifikats-Generierung + den Versand für einen User/Sektor an."""
    try:
        data = await request.json()
        guard = _admin_guard(data.get("email", "").lower().strip())
        if guard:
            return guard

        ziel = (data.get("ziel_email") or "").lower().strip()
        sektor_id = str(data.get("sector_id", "1"))
        if not ziel:
            return JSONResponse(content={"success": False, "error": "ziel_email fehlt."}, status_code=400)

        user_record = db.codes.find_one({"email": ziel}) or {}
        user_name = user_record.get("name") or ziel.split('@')[0].capitalize()
        seelen_name = SECTOR_NAMES.get(sektor_id, "KI")

        progress = db.user_progress.find_one({"email": ziel}) or {}
        letzter_scan = (progress.get("sektoren", {}) or {}).get(sektor_id, {}).get("letzter_scan", {})
        if not letzter_scan:
            letzter_scan = {"WAHRHAFTIGKEITS_SIEGEL": "Vom Administrator manuell ausgestelltes Wahrheits-Zertifikat."}

        pdf_dateiname = generiere_wahrheits_zertifikat_pdf(ziel, user_name, sektor_id, letzter_scan)
        with open(pdf_dateiname, "rb") as attachment:
            encoded_pdf = base64.b64encode(attachment.read()).decode()
        versendet = send_email_with_attachment(
            to_email=ziel,
            subject=f"M&M Community – Dein Wahrheits-Zertifikat [Sektor {sektor_id} – {seelen_name}]",
            body=f"Anbei dein offiziell versiegeltes Wahrheits-Zertifikat fuer Sektor {sektor_id} ({seelen_name}).",
            attachment_name=f"Wahrheits_Zertifikat_Sektor_{sektor_id}.pdf",
            attachment_data=encoded_pdf,
        )
        return {"success": versendet, "ziel_email": ziel, "sector_id": sektor_id}
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# =====================================================================
# ADMIN: ETHNOGRAFISCHE STUDIE (aus dem unsichtbaren KI-Scanner) + BUCH-PDF
# Kapitelweise Übersicht der versiegelten Auswertungen. PDF-Erzeugung ist
# EXKLUSIV dem Administrator vorbehalten (Buch-Vorbereitung).
# =====================================================================
@app.get("/admin/ethnografie")
async def admin_ethnografie(email: str = "", sektor: str = ""):
    """Kapitel-Übersicht der ethnografischen Studie je Sektor + optional die
    Detail-Auswertungen eines gewählten Sektors (Doppel-Brille: Sektor + Module A-I)."""
    guard = _admin_guard(email)
    if guard:
        return guard
    try:
        kapitel = []
        for s in range(1, ANZAHL_THEMEN_GESAMT + 1):
            if s in GESPERRTE_THEMEN_FUER_USER:
                continue  # 21/22 werden nie gescannt -> kein Kapitel
            anzahl = db.mm_ethnografie_studie.count_documents({"sektor": s})
            kapitel.append({"sektor": s, "thema": SEKTOR_THEMEN.get(str(s), ""), "anzahl": anzahl})

        detail = []
        if sektor not in (None, ""):
            try:
                s_int = int(sektor)
            except (TypeError, ValueError):
                s_int = None
            if s_int is not None:
                for d in db.mm_ethnografie_studie.find({"sektor": s_int}).sort("erstellt_am", -1).limit(200):
                    erstellt = d.get("erstellt_am")
                    detail.append({
                        "sektor": d.get("sektor"),
                        "thema": d.get("thema", ""),
                        "sektor_brille": d.get("sektor_brille", ""),
                        "gefuehls_fundament": d.get("gefuehls_fundament", ""),
                        "modul_brille": d.get("modul_brille", {}) or {},
                        "roh_text": d.get("roh_text", ""),
                        "erstellt_am": erstellt.isoformat() if hasattr(erstellt, "isoformat") else str(erstellt),
                    })
        return {
            "success": True,
            "kapitel": kapitel,
            "gesamt": db.mm_ethnografie_studie.count_documents({}),
            "detail": detail,
            "sektor": sektor,
        }
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


def generiere_ethnografie_buch_pdf(nur_sektor=None, anonym: bool = True) -> str:
    """Baut aus der versiegelten Studie ein professionelles, kapitelweises Buch-PDF
    für die Buch-Vorbereitung. Nur-Sektor optional; sonst alle Sektoren 1-20."""
    query = {}
    if nur_sektor not in (None, ""):
        query = {"sektor": int(nur_sektor)}
    if db.mm_ethnografie_studie.count_documents(query) == 0:
        raise ValueError("Noch keine ethnografischen Daten vorhanden – PDF kann nicht erzeugt werden.")

    kapitel_html = ""
    for s in range(1, ANZAHL_THEMEN_GESAMT + 1):
        if s in GESPERRTE_THEMEN_FUER_USER:
            continue
        if nur_sektor not in (None, "") and int(nur_sektor) != s:
            continue
        eintraege = list(db.mm_ethnografie_studie.find({"sektor": s}).sort("erstellt_am", 1))
        if not eintraege:
            continue
        kapitel_html += f'<div class="chapter"><h2>Kapitel {s}: {_html_escape(SEKTOR_THEMEN.get(str(s), ""))}</h2>'
        for e in eintraege:
            kapitel_html += '<div class="eintrag">'
            essenz = e.get("sektor_brille", "")
            if essenz:
                kapitel_html += f'<p class="essenz">{_html_escape(essenz)}</p>'
            gf = e.get("gefuehls_fundament", "")
            if gf:
                kapitel_html += f'<p class="fundament"><b>Recht auf Gefühlsvorderung:</b> {_html_escape(gf)}</p>'
            module = e.get("modul_brille", {}) or {}
            eintraege_module = "".join(
                f'<li><b>{_html_escape(k)}:</b> {_html_escape(v)}</li>' for k, v in module.items() if v
            )
            if eintraege_module:
                kapitel_html += f'<ul class="module">{eintraege_module}</ul>'
            kapitel_html += '</div>'
        kapitel_html += '</div>'

    datum = datetime.now().strftime("%d.%m.%Y")
    titel = "Ethnografische Studie – M&M Community" + (f" · Sektor {nur_sektor}" if nur_sektor not in (None, "") else " · Gesamtwerk")
    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><style>
        @page {{ size: A4; margin: 20mm 18mm; }}
        body {{ font-family: 'Georgia', serif; color: #0d2240; line-height: 1.6; }}
        h1 {{ color: #003d8f; text-align: center; letter-spacing: 1px; }}
        .sub {{ text-align:center; color:#b8860b; font-style:italic; margin-bottom:14mm; }}
        .chapter {{ page-break-inside: avoid; margin-bottom: 10mm; }}
        h2 {{ color: #003d8f; border-bottom: 1mm solid #ffd700; padding-bottom: 2mm; }}
        .eintrag {{ border-left: 1mm solid #ffd700; background:#fbf7e9; padding: 4mm; margin: 4mm 0; }}
        .essenz {{ font-style: italic; }}
        .fundament {{ color:#5a3d00; }}
        ul.module {{ font-size: 10pt; color:#333; }}
    </style></head><body>
        <h1>{_html_escape(titel)}</h1>
        <div class="sub">Versiegelte Auswertung · Stand {datum} {'· anonymisiert' if anonym else ''}</div>
        {kapitel_html}
    </body></html>"""
    dateiname = f"MM_Ethnografie_Studie{('_Sektor_' + str(nur_sektor)) if nur_sektor not in (None, '') else '_Gesamt'}.pdf"
    HTML(string=html).write_pdf(dateiname)
    return dateiname


@app.get("/admin/ethnografie/pdf")
async def admin_ethnografie_pdf(email: str = "", sektor: str = ""):
    """EXKLUSIV ADMIN: erzeugt das kapitelweise Buch-PDF der ethnografischen Studie
    und liefert es direkt zum Download."""
    guard = _admin_guard(email)
    if guard:
        return guard
    try:
        pdf_dateiname = generiere_ethnografie_buch_pdf(nur_sektor=sektor if sektor not in (None, "") else None)
        return FileResponse(pdf_dateiname, media_type="application/pdf", filename=pdf_dateiname)
    except ValueError as ve:
        return JSONResponse(content={"success": False, "error": str(ve)}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# =====================================================================
# ADMIN: SEKTOREN-SEELEN · KI-MASTER-SWITCH · GLOBALE SICHTBARKEIT
# =====================================================================
@app.get("/admin/sektor-config")
async def admin_sektor_config(email: str = ""):
    """Liefert je Sektor: KI-Master-Switch, Seelen-Name/-Wesen und Sichtbarkeit."""
    guard = _admin_guard(email)
    if guard:
        return guard
    ki_cfg = _cfg_doc("sektor_ki").get("sektoren", {})
    sicht_cfg = _cfg_doc("sichtbarkeit")
    sektoren = []
    for s in range(1, ANZAHL_THEMEN_GESAMT + 1):
        name, wesen = hole_seele(s)
        platzhalter = s in GESPERRTE_THEMEN_FUER_USER
        gesperrt = platzhalter or (sicht_cfg.get("sektoren", {}).get(str(s)) == "gesperrt")
        sektoren.append({
            "sektor": s,
            "thema": SEKTOR_THEMEN.get(str(s), ""),
            "ki_verfuegbar": not platzhalter,
            "ki_aktiv": (not platzhalter) and bool(ki_cfg.get(str(s), True)),
            "seele_name": name,
            "seele_wesen": wesen,
            "sichtbarkeit": "gesperrt" if gesperrt else "sichtbar",
        })
    return {"success": True, "global_offen": sicht_cfg.get("global_offen", True), "sektoren": sektoren}


@app.post("/admin/sektor-config")
async def admin_sektor_config_set(request: Request):
    """Setzt globalen Master, oder je Sektor: KI-Switch, Sichtbarkeit, Seele."""
    try:
        data = await request.json()
        guard = _admin_guard((data.get("email") or "").lower().strip())
        if guard:
            return guard

        # Globaler Master-Schalter (Plattform offen/geschlossen).
        if "global_offen" in data:
            db.system_config.update_one(
                {"_id": "sichtbarkeit"},
                {"$set": {"global_offen": bool(data.get("global_offen"))}},
                upsert=True,
            )
            return {"success": True, "global_offen": bool(data.get("global_offen"))}

        try:
            s = str(int(data.get("sektor")))
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"success": False, "error": "Ungültiger Sektor."})

        if "ki_aktiv" in data:
            db.system_config.update_one(
                {"_id": "sektor_ki"}, {"$set": {f"sektoren.{s}": bool(data.get("ki_aktiv"))}}, upsert=True,
            )
        if "sichtbarkeit" in data:
            wert = "gesperrt" if data.get("sichtbarkeit") == "gesperrt" else "sichtbar"
            db.system_config.update_one(
                {"_id": "sichtbarkeit"}, {"$set": {f"sektoren.{s}": wert}}, upsert=True,
            )
        set_seele = {}
        if data.get("seele_name") is not None:
            set_seele[f"sektoren.{s}.name"] = (data.get("seele_name") or "").strip()[:80]
        if data.get("seele_wesen") is not None:
            set_seele[f"sektoren.{s}.wesen"] = (data.get("seele_wesen") or "").strip()[:1000]
        if set_seele:
            db.system_config.update_one({"_id": "sektor_seelen"}, {"$set": set_seele}, upsert=True)

        return {"success": True, "sektor": s}
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# =====================================================================
# EBENE 4: SKALIERBARES VIDEO-TISCH-SYSTEM (8 Plätze/Tisch, +1 Tisch ab dem 9.)
# =====================================================================
VIDEO_DEFAULT_PLAETZE_PRO_TISCH = 8
VIDEO_TIMEOUT_SEKUNDEN = 60


def _video_config() -> dict:
    cfg = db.system_config.find_one({"_id": "video"}) or {}
    return {"plaetze_pro_tisch": int(cfg.get("plaetze_pro_tisch", VIDEO_DEFAULT_PLAETZE_PRO_TISCH))}


def _prune_video_raum():
    """Entfernt inaktive Teilnehmer (kein Heartbeat seit VIDEO_TIMEOUT_SEKUNDEN)."""
    grenze = datetime.now().timestamp() - VIDEO_TIMEOUT_SEKUNDEN
    db.video_raum.delete_many({"last_seen_ts": {"$lt": grenze}})


def _anzahl_tische(count: int, plaetze: int) -> int:
    """
    7+1-SKALIERUNG: max 8 Plätze pro Tisch. Person 9 landet auf der Warteliste.
    Ein NEUER Tisch öffnet erst, sobald count >= plaetze*tische + 2 (also 8+2=10,
    16+2=18, 24+2=26 ...). So bleibt der 9. Gast wartend, bis der 10. den Split auslöst.
    """
    tische = 1
    while count >= plaetze * tische + 2:
        tische += 1
    return tische


def _raum_neu_berechnen(raum: str, plaetze: int) -> dict:
    """
    Verteilt ALLE aktiven Teilnehmer eines Themen-Raums (nach Beitritts-Reihenfolge)
    frisch auf Tische + Warteliste und schreibt tisch/platz_am_tisch/status zurück.
    Wird bei jedem join/heartbeat aufgerufen -> ein Split reseatet Wartende automatisch.
    """
    teilnehmer = list(db.video_raum.find({"raum": raum}).sort("platz", 1))
    count = len(teilnehmer)
    tische = _anzahl_tische(count, plaetze)
    sitzplaetze = tische * plaetze

    liste = []
    for i, t in enumerate(teilnehmer):
        if i < sitzplaetze:
            tisch = i // plaetze
            platz_am_tisch = i % plaetze
            status = "aktiv"
        else:
            tisch = -1
            platz_am_tisch = -1
            status = "warteliste"
        db.video_raum.update_one(
            {"_id": t["_id"]},
            {"$set": {"tisch": tisch, "platz_am_tisch": platz_am_tisch, "status": status}},
        )
        liste.append({
            "email": t.get("email"), "peer_id": t.get("peer_id"),
            "tisch": tisch, "platz_am_tisch": platz_am_tisch, "status": status,
        })

    warteliste = max(0, count - sitzplaetze)
    return {"teilnehmer": liste, "anzahl_tische": tische, "count": count, "warteliste": warteliste}


@app.get("/admin/video-config")
async def admin_get_video_config(email: str = ""):
    guard = _admin_guard(email)
    if guard:
        return guard
    _prune_video_raum()
    cfg = _video_config()
    plaetze = cfg["plaetze_pro_tisch"]
    teilnehmer = list(db.video_raum.find({}, {"_id": 0, "email": 1, "tisch": 1, "raum": 1, "status": 1}))

    # Aufschlüsselung PRO THEMA (jeder Sektor hat seinen eigenen Live-Raum).
    raeume: Dict[str, int] = {}
    for t in teilnehmer:
        r = str(t.get("raum", "?"))
        raeume[r] = raeume.get(r, 0) + 1
    tische_gesamt = sum(_anzahl_tische(n, plaetze) for n in raeume.values()) if raeume else 1
    raum_details = [
        {"raum": r, "thema": SEKTOR_THEMEN.get(r, ""), "teilnehmer": n,
         "tische": _anzahl_tische(n, plaetze)}
        for r, n in sorted(raeume.items(), key=lambda x: (len(x[0]), x[0]))
    ]
    return {
        "success": True,
        "plaetze_pro_tisch": plaetze,
        "anzahl_tische": tische_gesamt,
        "aktive_teilnehmer": len(teilnehmer),
        "teilnehmer": teilnehmer,
        "raeume": raum_details,
    }


@app.post("/admin/video-config")
async def admin_set_video_config(request: Request):
    try:
        data = await request.json()
        guard = _admin_guard(data.get("email", "").lower().strip())
        if guard:
            return guard
        plaetze = int(data.get("plaetze_pro_tisch", VIDEO_DEFAULT_PLAETZE_PRO_TISCH))
        plaetze = max(1, min(plaetze, 50))
        db.system_config.update_one(
            {"_id": "video"},
            {"$set": {"plaetze_pro_tisch": plaetze, "letztes_update": datetime.now()}},
            upsert=True,
        )
        return {"success": True, "plaetze_pro_tisch": plaetze}
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/video/join")
async def video_join(request: Request):
    """
    Registriert einen zertifizierten Teilnehmer im Live-Raum EINES THEMAS (Sektor).
    7+1-Skalierung PRO RAUM: 8 Plätze/Tisch. Person 9 -> Warteliste. Ab dem 10.
    Gast (8+2) öffnet das System automatisch Tisch 2 und setzt die Wartenden dorthin.
    Liefert Tisch/Platz + die Peers am EIGENEN Tisch für den PeerJS-Mesh-Aufbau.
    """
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        peer_id = (data.get("peer_id") or "").strip()
        try:
            raum = str(int(data.get("sektor") if data.get("sektor") is not None else data.get("raum")))
        except (TypeError, ValueError):
            return {"success": False, "error": "Ungültiges Thema (sektor)."}
        if not email or not peer_id:
            return {"success": False, "error": "email und peer_id erforderlich."}

        # Nur voll freigeschaltete Mitglieder dürfen in den Live-Raum eines Themas.
        if not darf_forum_nutzen(email):
            return {"success": False, "error": "Kein Zugriff auf den Live-Sektor. Bitte zuerst das Profil vollständig freischalten."}
        # Sektor 21 & 22 sind statische Platzhalter -> kein Live-Raum für User.
        if thema_fuer_user_gesperrt(int(raum), email):
            return {"success": False, "gesperrt": True, "error": "Dieses Thema hat noch keinen Live-Raum."}
        # SYSTEM 3+4: Der offene ('Random') Live-Sektor ist Premium-exklusiv. Nicht-Premium
        # dürfen nur beitreten, wenn sie an einen live geschalteten Tisch dieses Themas
        # eingeladen wurden und angenommen haben (Gast-Zugang ohne eigene Rechte).
        if not ist_premium(email) and not hat_live_tisch_zugang(email, int(raum)):
            return {"success": False, "zugang": "rolle_gesperrt", "benoetigt": "premium",
                    "error": "Der Live-Sektor ist Premium-Mitgliedern vorbehalten. Als Gast brauchst du "
                             "eine angenommene Einladung an einen live geschalteten Tisch dieses Themas."}

        _prune_video_raum()
        plaetze = _video_config()["plaetze_pro_tisch"]
        jetzt = datetime.now()

        bestehend = db.video_raum.find_one({"email": email, "raum": raum})
        if bestehend:
            platz = int(bestehend.get("platz", 0))
        else:
            # Nur EIN Live-Raum gleichzeitig: eventuelle Alt-Einträge des Users entfernen.
            db.video_raum.delete_many({"email": email})
            belegte = sorted(int(d["platz"]) for d in db.video_raum.find({"raum": raum}, {"platz": 1}))
            platz = 0
            for p in belegte:
                if p == platz:
                    platz += 1
                else:
                    break

        db.video_raum.update_one(
            {"email": email, "raum": raum},
            {"$set": {
                "email": email, "raum": raum, "peer_id": peer_id, "platz": platz,
                "last_seen": jetzt, "last_seen_ts": jetzt.timestamp(),
            }},
            upsert=True,
        )

        info = _raum_neu_berechnen(raum, plaetze)
        ich = db.video_raum.find_one({"email": email, "raum": raum}) or {}
        mein_tisch = int(ich.get("tisch", -1))
        # Nur Peers am EIGENEN Tisch anrufen (ein Tisch = eine Video-Runde).
        andere = [
            {"email": t["email"], "peer_id": t["peer_id"], "tisch": t["tisch"], "platz_am_tisch": t["platz_am_tisch"]}
            for t in info["teilnehmer"]
            if t["email"] != email and t["status"] == "aktiv" and mein_tisch >= 0 and t["tisch"] == mein_tisch
        ]
        return {
            "success": True,
            "raum": raum,
            "tisch": mein_tisch,
            "platz_am_tisch": int(ich.get("platz_am_tisch", -1)),
            "status": ich.get("status", "warteliste"),
            "plaetze_pro_tisch": plaetze,
            "anzahl_tische": info["anzahl_tische"],
            "warteliste": info["warteliste"],
            "teilnehmer": info["teilnehmer"],
            "andere": andere,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/video/heartbeat")
async def video_heartbeat(request: Request):
    """Hält den Teilnehmer aktiv und liefert die aktuelle Belegung SEINES Themen-Raums."""
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        try:
            raum = str(int(data.get("sektor") if data.get("sektor") is not None else data.get("raum")))
        except (TypeError, ValueError):
            raum = None
        jetzt = datetime.now()
        if email and raum:
            db.video_raum.update_one(
                {"email": email, "raum": raum},
                {"$set": {"last_seen": jetzt, "last_seen_ts": jetzt.timestamp()}},
            )
        _prune_video_raum()
        plaetze = _video_config()["plaetze_pro_tisch"]
        if not raum:
            return {"success": True, "teilnehmer": [], "plaetze_pro_tisch": plaetze, "anzahl_tische": 1, "warteliste": 0}
        info = _raum_neu_berechnen(raum, plaetze)
        return {
            "success": True,
            "raum": raum,
            "teilnehmer": info["teilnehmer"],
            "plaetze_pro_tisch": plaetze,
            "anzahl_tische": info["anzahl_tische"],
            "warteliste": info["warteliste"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/video/leave")
async def video_leave(request: Request):
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if email:
            db.video_raum.delete_one({"email": email})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _kurz_name(email: str) -> str:
    rec = db.codes.find_one({"email": email}, {"profil": 1, "name": 1}) or {}
    p = rec.get("profil", {}) or {}
    return (f"{p.get('vorname','')} {p.get('nachname','')}".strip()
            or rec.get("name", "") or p.get("benutzername", "") or email.split("@")[0])


def _email_zu_handle(email: str) -> str:
    rec = db.codes.find_one({"email": email}, {"profil": 1}) or {}
    return (rec.get("profil", {}) or {}).get("benutzername", "")


def _handle_zu_email(handle: str) -> str:
    rec = db.codes.find_one({"profil.benutzername": (handle or "").strip()}, {"email": 1}) or {}
    return rec.get("email", "")


def hat_live_tisch_zugang(email: str, sektor: int) -> bool:
    """Gast-Zugang: True, wenn der Nutzer an einen LIVE geschalteten Tisch dieses
    Themas eingeladen wurde und angenommen hat (oder selbst der Ersteller ist)."""
    email = (email or "").lower().strip()
    try:
        res = db.tisch_reservierungen.find_one({
            "sektor": int(sektor), "status": "live",
            "$or": [
                {"ersteller_email": email},
                {"eingeladene": {"$elemMatch": {"email": email, "status": "angenommen"}}},
            ],
        })
        return bool(res)
    except Exception:
        return False


def _auto_validiere_reservierung(res: dict) -> dict:
    """AUTOMATISIERUNG (System 5): Prüft vollautomatisch die 7+1-Kriterien und
    schaltet den Achtertisch-Slot ohne Admin-Eingriff live frei, sobald:
      1) der Ersteller Premium ist UND
      2) mindestens eine Einladung verschickt UND von allen Eingeladenen angenommen wurde.
    Der Ersteller (Platz 1) + bis zu 7 angenommene Gäste = 7+1-Tisch."""
    if not res or res.get("status") != "geplant":
        return res
    if not ist_premium(res.get("ersteller_email", "")):
        return res
    eingeladene = res.get("eingeladene", []) or []
    if not eingeladene:
        return res
    if all(g.get("status") == "angenommen" for g in eingeladene):
        db.tisch_reservierungen.update_one(
            {"_id": res["_id"]},
            {"$set": {"status": "live", "live_seit": datetime.now()}},
        )
        res["status"] = "live"
        res["live_seit"] = datetime.now()
    return res


def _reservierung_public(res: dict, viewer_email: str = "", zeige_sensibel: bool = False) -> dict:
    viewer_email = (viewer_email or "").lower().strip()
    ist_ersteller = res.get("ersteller_email") == viewer_email
    darf_details = zeige_sensibel or ist_ersteller
    eingeladene = res.get("eingeladene", []) or []
    gaeste = []
    for g in eingeladene:
        eintrag = {
            "handle": g.get("handle", "") or _email_zu_handle(g.get("email", "")),
            "name": _kurz_name(g.get("email", "")),
            "status": g.get("status", "eingeladen"),
            "online": bool(db.video_raum.find_one({"email": g.get("email", ""), "raum": str(res.get("sektor"))})),
        }
        if darf_details:
            eintrag["email"] = g.get("email", "")
        gaeste.append(eintrag)
    mein_status = None
    for g in eingeladene:
        if g.get("email") == viewer_email:
            mein_status = g.get("status")
    return {
        "id": str(res.get("_id")),
        "raum_id": res.get("raum_id", ""),
        "sektor": res.get("sektor"),
        "thema": res.get("thema", ""),
        "zeitpunkt": res.get("zeitpunkt", ""),
        "identitaet": res.get("identitaet", "") if darf_details else "",
        "status": res.get("status", "geplant"),
        "ersteller_name": _kurz_name(res.get("ersteller_email", "")),
        "ersteller_handle": _email_zu_handle(res.get("ersteller_email", "")),
        "ist_ersteller": ist_ersteller,
        "mein_status": mein_status,
        "eingeladene": gaeste,
        "angenommen": sum(1 for g in eingeladene if g.get("status") == "angenommen"),
        "eingeladen_gesamt": len(eingeladene),
        "erstellt_am": res.get("erstellt_am").isoformat() if hasattr(res.get("erstellt_am"), "isoformat") else "",
        "live_seit": res.get("live_seit").isoformat() if hasattr(res.get("live_seit"), "isoformat") else "",
    }


@app.post("/api/tisch/reservieren")
async def tisch_reservieren(request: Request):
    """SYSTEM 4 – Geplante Reservierung (nur Premium): Identität, Uhrzeit, Thema."""
    try:
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        if not ist_premium(email):
            return rolle_gesperrt_antwort("premium")
        try:
            sektor = int(data.get("sektor"))
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"success": False, "message": "Ungültiges Thema."})
        if thema_fuer_user_gesperrt(sektor, email):
            return JSONResponse(status_code=403, content={"success": False, "message": "Dieses Thema hat keinen Live-Raum."})
        identitaet = (data.get("identitaet") or _kurz_name(email)).strip()[:120]
        zeitpunkt = (data.get("zeitpunkt") or "").strip()[:60]
        thema = (data.get("thema") or SEKTOR_THEMEN.get(str(sektor), "")).strip()[:160]
        doc = {
            "raum_id": "tr_" + secrets.token_hex(6),
            "ersteller_email": email,
            "sektor": sektor,
            "thema": thema,
            "zeitpunkt": zeitpunkt,
            "identitaet": identitaet,
            "status": "geplant",
            "eingeladene": [],
            "erstellt_am": datetime.now(),
        }
        res = db.tisch_reservierungen.insert_one(doc)
        doc["_id"] = res.inserted_id
        return {"success": True, "reservierung": _reservierung_public(doc, email)}
    except Exception as e:
        print(f"Fehler bei /api/tisch/reservieren: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Reservierung fehlgeschlagen."})


@app.post("/api/tisch/einladen")
async def tisch_einladen(request: Request):
    """SYSTEM 4 – Einladung an einen Tisch (NUR der Premium-Ersteller). Der Gast erbt
    KEINE Einladungsrechte (Missbrauchsschutz gegen Account-Sharing)."""
    try:
        from bson import ObjectId
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        if not ist_premium(email):
            return rolle_gesperrt_antwort("premium")
        try:
            res = db.tisch_reservierungen.find_one({"_id": ObjectId((data.get("reservierung_id") or "").strip())})
        except Exception:
            res = None
        if not res:
            return JSONResponse(status_code=404, content={"success": False, "message": "Reservierung nicht gefunden."})
        # HARTER MISSBRAUCHSSCHUTZ: Nur der Ersteller selbst darf einladen – niemals ein Gast.
        if res.get("ersteller_email") != email:
            return JSONResponse(status_code=403, content={"success": False, "message": "Nur der Ersteller des Tisches darf einladen."})
        gast_ref = (data.get("gast_handle") or data.get("gast_ref") or "").strip()
        gast_email = (data.get("gast_email") or "").lower().strip()
        if gast_ref and not gast_email:
            gast_email = _handle_zu_email(gast_ref)
        if not gast_email or not db.codes.find_one({"email": gast_email}):
            return JSONResponse(status_code=404, content={"success": False, "message": "Mitglied nicht gefunden."})
        if gast_email == email:
            return JSONResponse(status_code=400, content={"success": False, "message": "Du sitzt bereits selbst am Tisch."})
        eingeladene = res.get("eingeladene", []) or []
        if any(g.get("email") == gast_email for g in eingeladene):
            return JSONResponse(status_code=409, content={"success": False, "message": "Dieses Mitglied ist bereits eingeladen."})
        if len(eingeladene) >= 7:   # 7 Gäste + 1 Ersteller = 8er-Tisch
            return JSONResponse(status_code=409, content={"success": False, "message": "Der Tisch ist voll (7+1)."})
        db.tisch_reservierungen.update_one(
            {"_id": res["_id"]},
            {"$push": {"eingeladene": {
                "email": gast_email, "handle": _email_zu_handle(gast_email),
                "status": "eingeladen", "eingeladen_am": datetime.now(),
            }}},
        )
        res = db.tisch_reservierungen.find_one({"_id": res["_id"]})
        return {"success": True, "reservierung": _reservierung_public(res, email)}
    except Exception as e:
        print(f"Fehler bei /api/tisch/einladen: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Einladung fehlgeschlagen."})


@app.post("/api/tisch/einladung/antwort")
async def tisch_einladung_antwort(request: Request):
    """SYSTEM 4+5 – Gast nimmt an oder lehnt ab. Bei vollständiger Annahme validiert das
    System automatisch und schaltet den 7+1-Slot ohne Admin-Eingriff live frei."""
    try:
        from bson import ObjectId
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        annehmen = bool(data.get("annehmen", True))
        try:
            res = db.tisch_reservierungen.find_one({"_id": ObjectId((data.get("reservierung_id") or "").strip())})
        except Exception:
            res = None
        if not res:
            return JSONResponse(status_code=404, content={"success": False, "message": "Reservierung nicht gefunden."})
        if not any(g.get("email") == email for g in (res.get("eingeladene", []) or [])):
            return JSONResponse(status_code=403, content={"success": False, "message": "Du bist an diesen Tisch nicht eingeladen."})
        db.tisch_reservierungen.update_one(
            {"_id": res["_id"], "eingeladene.email": email},
            {"$set": {"eingeladene.$.status": "angenommen" if annehmen else "abgelehnt"}},
        )
        res = db.tisch_reservierungen.find_one({"_id": res["_id"]})
        res = _auto_validiere_reservierung(res)   # ggf. automatische Live-Freischaltung
        return {"success": True, "reservierung": _reservierung_public(res, email), "live": res.get("status") == "live"}
    except Exception as e:
        print(f"Fehler bei /api/tisch/einladung/antwort: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Antwort fehlgeschlagen."})


@app.post("/api/tisch/live-freischalten")
async def tisch_live_freischalten(request: Request):
    """Der Premium-Ersteller kann seinen Tisch sofort live schalten (direkter Einstieg)."""
    try:
        from bson import ObjectId
        data = await request.json()
        email = (data.get("email") or "").lower().strip()
        if not konto_ist_aktiv(email):
            return zugang_verweigert_antwort()
        if not ist_premium(email):
            return rolle_gesperrt_antwort("premium")
        try:
            res = db.tisch_reservierungen.find_one({"_id": ObjectId((data.get("reservierung_id") or "").strip())})
        except Exception:
            res = None
        if not res or res.get("ersteller_email") != email:
            return JSONResponse(status_code=403, content={"success": False, "message": "Nur der Ersteller darf den Tisch live schalten."})
        db.tisch_reservierungen.update_one({"_id": res["_id"]}, {"$set": {"status": "live", "live_seit": datetime.now()}})
        res = db.tisch_reservierungen.find_one({"_id": res["_id"]})
        return {"success": True, "reservierung": _reservierung_public(res, email), "live": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@app.get("/api/tisch/meine")
async def tisch_meine(email: str = ""):
    """Reservierungen des Nutzers: eigene (als Ersteller) + Einladungen an ihn."""
    email = (email or "").lower().strip()
    if not konto_ist_aktiv(email):
        return zugang_verweigert_antwort()
    eigene, einladungen = [], []
    try:
        for r in db.tisch_reservierungen.find({"ersteller_email": email}).sort("erstellt_am", -1).limit(50):
            eigene.append(_reservierung_public(r, email))
        for r in db.tisch_reservierungen.find({"eingeladene.email": email}).sort("erstellt_am", -1).limit(50):
            einladungen.append(_reservierung_public(r, email))
    except Exception as e:
        print(f"Fehler bei /api/tisch/meine: {e}")
    return {"success": True, "rolle": bestimme_rolle(email), "darf_reservieren": ist_premium(email),
            "eigene": eigene, "einladungen": einladungen}


@app.get("/admin/reservierungen")
async def admin_reservierungen(email: str = ""):
    """SYSTEM 5 – Echtzeit-Überwachung: alle Reservierungen, Einladungen und
    Online-/Annahme-Status live im Admin-Panel sichtbar."""
    guard = _admin_guard(email)
    if guard:
        return guard
    _prune_video_raum()
    liste = []
    try:
        for r in db.tisch_reservierungen.find({}).sort("erstellt_am", -1).limit(200):
            liste.append(_reservierung_public(r, email, zeige_sensibel=True))
    except Exception as e:
        print(f"Fehler bei /admin/reservierungen: {e}")
    zusammenfassung = {
        "gesamt": len(liste),
        "live": sum(1 for r in liste if r["status"] == "live"),
        "geplant": sum(1 for r in liste if r["status"] == "geplant"),
    }
    return {"success": True, "zusammenfassung": zusammenfassung, "reservierungen": liste}


@app.post("/api/sektor1/siegel_verlangen")
async def siegel_verlangen_sektor1(request: Request):
    """
    Verdrahtet Sektor 1 dauerhaft. Schaltet die Box auf GRÜN,
    erhöht den Zähler und sendet dem Nutzer AUTOMATISCH 
    sein Sektor-Wahrheitszertifikat direkt ins Postfach.
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")       # Das ist die E-Mail des Nutzers
        definition = data.get("definition")
        
        if not user_id or not definition:
            return {"status": "error", "message": "Fehlende Daten für die Siegel-Prägung."}
        
        email = user_id.lower().strip()

        # 1. Wir holen uns den allerletzten Live-Scan des Nutzers für diesen Sektor
        progress_record = db.user_progress.find_one({"email": email})
        letzter_scan = {}
        if progress_record and "sektoren" in progress_record:
            letzter_scan = progress_record["sektoren"].get("1", {}).get("letzter_scan", {})

        # 2. Das unzerstörbare Zertifikat für die MongoDB strukturieren
        zertifikat_daten = {
            "sektor": 1,
            "thema": "Recht auf Gefühlsvorderung",
            "user_definition": definition,
            "siegel_gepraegt": True,
            "zeitstempel": datetime.now(),
            "wahrheits_essenz": letzter_scan.get("WAHRHAFTIGKEITS_SIEGEL", "Deine Frequenz wurde unzensiert im Kollektiv versiegelt.")
        }
        
        # In die Akte einprägen: Sektor 1 wird GRÜN, Zähler erhöht sich
        db.mitglieder_daten.update_one(
            {"user_id": email},
            {
                "$addToSet": {"reise_kontrolle.abgeschlossene_sektoren": 1},
                "$inc": {"reise_kontrolle.gruene_boxen_zaehler": 1},
                "$push": {"wahrheits_zertifikate": zertifikat_daten},
                "$set": {"module_status.Modul_A": "Erfolgreich abgeschlossen"}
            },
            upsert=True
        )
        
        # 3. AUTOMATISCHES PDF-ZERTIFIKAT FÜR DIESEN SEKTOR GENERIEREN
        # Wir nutzen deine bestehende Buch-Funktion, füttern sie aber nur mit diesem Sektor-Inhalt
        temporaere_sektoren_daten = {"1": {"letzter_scan": letzter_scan}} if letzter_scan else None
        
        ergebnis_boxen = {"box_2": "Scanner-Aktivierung abgeschlossen", "box_3": "Analyse Sektor 1 versiegelt"}
        
        pdf_dateiname = generiere_persoenliches_buch_pdf(
            "M&M_Mitglied", 
            definition, 
            ergebnis_boxen, 
            alle_sektoren_daten=temporaere_sektoren_daten
        )
        
        # 4. Zertifikat als Base64 einlesen
        with open(pdf_dateiname, "rb") as attachment:
            encoded_pdf = base64.b64encode(attachment.read()).decode()

        # 5. Automatisch per E-Mail an den Nutzer abfeuern
        send_email_with_attachment(
            to_email=email,
            subject="M&M Community - Dein offizielles Wahrheits-Zertifikat [Sektor 1]",
            body="Glueckwunsch! Du hast Sektor 1 [Recht auf Gefuehlsforderung] erfolgreich gemeistert. Anbei findest du dein versiegeltes Sektor-Zertifikat.",
            attachment_name=f"Zertifikat_Sektor_1.pdf",
            attachment_data=encoded_pdf
        )

        print(f"[+] SEKTOR 1: Automatische Zertifikats-Zustellung an {email} vollzogen!")
        
        # Wir geben dem Frontend die Erfolgsmeldung zurück, damit die Sprechblase triggern kann!
        return {
            "status": "success", 
            "message": "Dein Wahrheits-Siegel für Sektor 1 wurde geprägt. Schau in dein Postfach – dein Zertifikat wurde soeben zugestellt!"
        }
        
    except Exception as e:
        print(f"[-] Fehler beim automatischen Zertifikats-Versand: {e}")
        return {"status": "error", "message": "Die Verbindung zum Server wurde erschüttert."}
    
@app.post("/generate-and-send-pdf")
async def generate_and_send_pdf(request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower().strip()
        dokument_typ = data.get("typ", "buch")  # Holt sich den Typ (Standard: buch)

        # PDF-AUSGABE IST EXKLUSIV DEM ADMINISTRATOR VORBEHALTEN.
        # Normale Benutzer dürfen keine PDFs mehr erzeugen oder sehen.
        if not ist_admin(email):
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "PDF-Erzeugung ist ausschließlich dem Administrator vorbehalten."},
            )
        
        # 1. Daten des Nutzers holen
        user_record = db.mitglieder_daten.find_one({
            "$or": [{"user_id": email}, {"email": email}, {"box_1_daten.user_email": email}]
        })

        # 2. Sektoren-Daten laden
        progress_record = db.user_progress.find_one({"email": email})
        alle_sektoren_daten = progress_record.get("sektoren") if progress_record else None

        if not user_record:
            pdf_user_titel = "M&M_Gemeinschafts-Mitglied"
            user_input_definition = "System-Testlauf aktiv."
            ergebnis_boxen = {"box_2": "Scanner-Aktivierung", "box_3": "Analyse"}
        else:
            moegliche_id = user_record.get("user_id") or email
            pdf_user_titel = "M&M_Mitglied" if "@" in moegliche_id else moegliche_id
            box_1_daten = user_record.get("box_1_daten", {})
            user_input_definition = box_1_daten.get("box_1_definition", "Keine Definition hinterlegt.")
            ergebnis_boxen = box_1_daten.get("berechnete_boxen", {})

        # 3. WEICHE: Zertifikat oder Buch generieren
        aktueller_ordner = os.path.dirname(os.path.abspath(__file__))
        
        if dokument_typ == "zertifikat":
            # Zertifikat-Generierung
            pdf_dateiname = generiere_sektor_zertifikat(
                pdf_user_titel, 
                pdf_user_titel, 
                "Aktueller Sektor", 
                user_input_definition
            )
            subject = "M&M Community - Dein Wahrheits-Zertifikat"
            body = "Anbei findest du dein persönliches Wahrheits-Zertifikat."
        else:
            # Buch-Generierung (Biografie-Maschine)
            pdf_dateiname = generiere_persoenliches_buch_pdf(
                pdf_user_titel, 
                user_input_definition, 
                ergebnis_boxen, 
                alle_sektoren_daten=alle_sektoren_daten
            )
            subject = "M&M Community - Dein versiegeltes Manifest"
            body = "Anbei findest du dein versiegeltes Manifest als Biografie."

        # 4. Versand
        with open(pdf_dateiname, "rb") as attachment:
            encoded_pdf = base64.b64encode(attachment.read()).decode()

        success = send_email_with_attachment(
            to_email=email,
            subject=subject,
            body=body,
            attachment_name=pdf_dateiname,
            attachment_data=encoded_pdf
        )
        
        if success:
            print(f"[+] {dokument_typ.capitalize()} erfolgreich an {email} versendet!")
            return {"status": "success", "message": f"{dokument_typ.capitalize()} wurde versendet."}
        else:
            return JSONResponse(content={"message": "Versand fehlgeschlagen"}, status_code=500)

    except Exception as e:
        print(f"[-] Kritischer Fehler: {e}")
        return JSONResponse(content={"message": str(e)}, status_code=500)

    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
