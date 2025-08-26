DeepSeek Immo Crawler

Dieses Projekt ist ein webbasiertes Crawler-Dashboard, das mit Flask entwickelt wurde.
Es kombiniert klassisches Web-Scraping (BeautifulSoup) mit KI-gestützter Extraktion (Groq DeepSeek) und ermöglicht es, Webseiten per CSS-Selector zu definieren, zu crawlen und die Ergebnisse in Excel-Dateien zu exportieren.

Features

Web-Dashboard (Flask) zur Verwaltung von Zielseiten (Name, URL, CSS-Selector)

Visuelle Auswahl von CSS-Selektoren über ein eingebettetes IFrame

KI-gestützte Extraktion von Projektnamen und Links mit Groq DeepSeek R1 Llama 70B

Export der Ergebnisse in Excel-Dateien

Fortschrittsanzeige mit Status, Prozentanzeige und Download-Link

Asynchrones Crawling mit Crawl4AI für umfangreiche Datenmengen

Projektstruktur
.
├── app.py                # Flask-App mit Dashboard und Crawling-Logik
├── scrape_targets.csv     # Gespeicherte Zielseiten (Name, URL, Selector)
├── utils/
│   ├── scraper_utils.py   # smart_ki_extraction und weitere Hilfsfunktionen
│   └── data_utils.py      # Duplicate-Check, Validierung usw.
├── models/
│   └── venue.py           # Datenmodell
├── requirements.txt       # Python-Abhängigkeiten
├── .env                   # API Keys und Einstellungen (nicht in Git)
└── README.md              # Projektdokumentation

Installation

Virtuelle Umgebung erstellen und aktivieren, z. B. mit Conda:

conda create -n immo-crawler python=3.12 -y
conda activate immo-crawler


Abhängigkeiten installieren:

pip install -r requirements.txt


Umgebungsvariablen konfigurieren:
Erstelle eine .env-Datei im Projektverzeichnis mit folgendem Inhalt:

GROQ_API_KEY=your_groq_api_key_here
MAX_TEXT_LEN=300


MAX_TEXT_LEN definiert die maximale Zeichenlänge pro Textabschnitt, der an die KI übergeben wird (Standard: 300).

Nutzung

Starte die Flask-Anwendung mit:

python dashboard.py


Öffne anschließend http://localhost:5000 im Browser.
Dort können Zielseiten mit Namen, URL und Selektor hinzugefügt werden.
Nach Start des Crawlings zeigt das Dashboard den Fortschritt an und ermöglicht den Download der Ergebnisse als Excel-Datei.

Konfiguration

Zielseiten werden in der Datei scrape_targets.csv gespeichert.

Jede Zeile enthält Name, URL und CSS-Selector.

Änderungen können direkt über das Dashboard oder manuell in der CSV-Datei erfolgen.

Hinweise

Logging erfolgt derzeit über einfache Konsolenausgaben. Für den produktiven Einsatz empfiehlt sich die Nutzung des Python-Logging-Frameworks.

Die Modulare Struktur (utils, models, app.py) ermöglicht eine leichte Erweiterung und Anpassung.

Alle API-Schlüssel und sensiblen Konfigurationswerte sind über .env steuerbar und sollten nicht in die Versionskontrolle gelangen.
