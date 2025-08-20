from flask import Flask, render_template_string, request, send_file, jsonify, Response
import threading
import os
import json
import datetime
import csv
import requests


app = Flask(__name__)

progress = {
    "percent": 0,
    "status": "Bereit",
    "error": "",
    "file_ready": False,
    "filename": "alle_projekte.xlsx"
}

TARGETS_FILE = "scrape_targets.csv"

# Datei anlegen, falls sie noch nicht existiert
if not os.path.exists(TARGETS_FILE):
    with open(TARGETS_FILE, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "URL", "Selector"])
        writer.writeheader()


# --- Utility Functions ---
def normalize_selector(selector):
    if not selector:
        return ""
    selector = selector.strip()
    if ' ' in selector:
        selector = '.'.join(selector.split())
    if not selector.startswith(('div', '.', '#')):
        selector = 'div.' + selector
    return selector

def read_targets():
    targets = []
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                targets.append({
                    "name": row.get("Name", ""),
                    "url": row.get("URL", ""),
                    "selector": row.get("Selector", "")
                })
    return targets

def write_targets(targets):
    with open(TARGETS_FILE, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "URL", "Selector"])
        writer.writeheader()
        for t in targets:
            writer.writerow({
                "Name": t.get("name", ""),
                "URL": t.get("url", ""),
                "Selector": t.get("selector", "")
            })


import tempfile

# --- Crawling Logic ---
def run_crawling():
    global progress
    progress.update({
        "status": "Starte Crawling...",
        "percent": 0,
        "error": "",
        "file_ready": False,
        "filename": os.path.join(
            tempfile.gettempdir(),
            f"alle_projekte_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx"
        )
    })
    try:
        from utils.scraper_utils import smart_ki_extraction, load_scrape_targets
        import pandas as pd
        from urllib.parse import urlparse, urljoin
        import re

        targets = load_scrape_targets()
        all_rows = []
        total = len(targets)

        for idx, target in enumerate(targets, start=1):
            name = target.get('name', 'website')
            url = target.get('url')
            selector = target.get('selector')
            progress["status"] = f"Extrahiere Daten von {name} ({idx}/{total})..."
            progress["percent"] = int((idx / total) * 100)

            try:
                result = smart_ki_extraction(target)
                if not isinstance(result, list):
                    match = re.search(r"```json\s*(\[.*?\])\s*```", str(result), re.DOTALL)
                    if match:
                        result = json.loads(match.group(1))
                    else:
                        match = re.search(r"(\[.*?\])", str(result), re.DOTALL)
                        if match:
                            result = json.loads(match.group(1))
                        else:
                            continue

                parsed = urlparse(url) if url else None
                domain = f"{parsed.scheme}://{parsed.netloc}" if parsed else ""

                for proj in result:
                    raw_link = proj.get("Link")
                    full_link = urljoin(domain, raw_link) if raw_link and not raw_link.startswith("http") and domain else raw_link
                    all_rows.append({
                        "Website": name,
                        "Projektname": proj.get("Projektname"),
                        "Link": full_link
                    })
            except Exception as e:
                progress["error"] = str(e)

        df = pd.DataFrame(all_rows)
        df.to_excel(progress["filename"], index=False)
        progress.update({
            "status": "Fertig! Excel-Datei erstellt.",
            "percent": 100,
            "file_ready": True
        })
    except Exception as e:
        progress.update({
            "status": "Fehler beim Crawling!",
            "error": str(e)
        })

# --- Flask Routes ---
@app.route("/")
def index():
    targets = read_targets()
    return render_template_string("""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Web-Crawler Dashboard</title>
<style>
body {font-family: Arial,sans-serif; background:#f9f9f9; color:#333; margin:40px;}
h2 {color:#222;}
form, table, button {margin-top:20px;}
input, button {padding:8px 12px; margin:5px; border:1px solid #ccc; border-radius:6px; font-size:14px;}
button {background:#4caf50; color:white; cursor:pointer; transition:background 0.2s;}
button:hover {background:#45a049;}
table {border-collapse:collapse; width:100%; margin-top:20px; background:white; box-shadow:0 2px 6px rgba(0,0,0,0.1);}
th, td {border:1px solid #ddd; padding:10px; text-align:left;}
th {background:#f2f2f2;}
tr:nth-child(even) {background:#fafafa;}
#progressbar {width:100%; max-width:400px; height:25px; background:#eee; border-radius:12px; overflow:hidden; margin-top:15px;}
#bar {height:100%; background:linear-gradient(90deg,#4caf50,#66bb6a); width:0%; transition:width 0.5s;}
#status {margin-top:15px; font-weight:bold;}
#download {margin-top:15px;}
a {color:#4caf50; font-weight:bold; text-decoration:none;}
a:hover {text-decoration:underline;}
#iframe-preview {width:100%; height:800px; border:1px solid #ccc; margin-top:20px;}
.outline-red { outline: 2px solid red !important; }
</style>
</head>
<body>
<h2>🌐 Immo-Web-Crawler Dashboard</h2>
<p>Ziele verwalten und Crawling starten:</p>

<form id="addform" onsubmit="addTarget();return false;">
  <input name="name" placeholder="Name" required>
  <input name="url" placeholder="URL" required onchange="updateIframe(this.value)">
  <input name="selector" placeholder="Selector" required id="selector-input">
  <button type="submit">+ Hinzufügen</button>
</form>

<iframe id="iframe-preview"></iframe>
<p>Klicke auf ein Element in der Vorschau, um den Selector automatisch auszufüllen.</p>

<table>
<tr><th>Name</th><th>URL</th><th>Selector</th><th>Löschen</th></tr>
{% for t in targets %}
<tr>
<td>{{ t['name'] }}</td>
<td>{{ t['url'] }}</td>
<td>{{ t['selector'] }}</td>
<td><button onclick="deleteTarget('{{ t['name'] }}','{{ t['url'] }}')">🗑️</button></td>
</tr>
{% endfor %}
</table>

<button id="crawlbtn" onclick="startCrawling()">🚀 Crawling starten</button>
<div id="status">Bereit</div>
<div id="progressbar"><div id="bar"></div></div>
<div id="download"></div>

<script>
const iframe = document.getElementById('iframe-preview');
const selectorInput = document.getElementById('selector-input');

function updateIframe(url) {
    if(!url.startsWith('http')) url = 'https://' + url;
    // Proxy nutzen, um CORS zu umgehen
    iframe.src = '/proxy?url=' + encodeURIComponent(url);
    iframe.onload = attachSelectorClick;
}

function attachSelectorClick() {
    try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        if (!doc) return;

        // Entferne alte Listener und Outlines
        doc.querySelectorAll('*').forEach(el => {
            el.onclick = null;
            el.classList.remove('outline-red');
        });

        // Füge auffälliges CSS ein
        let style = doc.getElementById('highlight-style');
        if (!style) {
            style = doc.createElement('style');
            style.id = 'highlight-style';
            style.innerHTML = `
                .outline-red {
                    outline: 4px solid red !important;
                    background: rgba(255,0,0,0.1) !important;
                    transition: all 0.2s;
                }
            `;
            doc.head.appendChild(style);
        }

        // Neue Listener setzen
        doc.querySelectorAll('*').forEach(el => {
            el.addEventListener('click', function(e){
                e.preventDefault();
                e.stopPropagation();

                // Selector ins Input eintragen
                const selector = generateSelector(e.target);
                selectorInput.value = selector;

                // Nur das geklickte Element markieren
                doc.querySelectorAll('.outline-red').forEach(x => x.classList.remove('outline-red'));
                e.target.classList.add('outline-red');
            });
        });
    } catch(err) {
        console.warn("Konnte Selector-Click nicht setzen:", err);
    }
}


function removeCookieBanners() {
    const doc = iframe.contentDocument || iframe.contentWindow.document;
    if (!doc) return;

    const banners = doc.querySelectorAll(
        '[class*="cookie"], [id*="cookie"], [class*="banner"], [id*="banner"], [class*="consent"], [id*="consent"]'
    );

    banners.forEach(b => {
        try {
            const btn = b.querySelector('button');
            if (btn) btn.click();
            b.style.display = 'none';
        } catch(e){}
    });
}

// Laufende Überprüfung alle 500ms
setInterval(removeCookieBanners, 500);



function generateSelector(el) {
    if (!el) return '';
    let selector = el.tagName.toLowerCase();
    if (el.classList.length > 0) {
        // Alle Klassen außer 'outline-red' nehmen
        let classes = Array.from(el.classList).filter(c => c !== 'outline-red');
        if (classes.length > 0) selector += '.' + classes.join('.');
    }
    return selector; // Nur das geklickte Element, kein Pfad nach oben
}



// Optional: direkt beim Laden die Liste aktualisieren
updateIframe(document.querySelector('input[name="url"]').value);

function startCrawling(){ fetch('/start',{method:'POST'}).then(()=>update()); }

function update(){
    fetch('/progress').then(r=>r.json()).then(data=>{
        let status = data.status + (data.error ? " ⚠️ " + data.error : "");
        document.getElementById('status').innerText = status;
        document.getElementById('bar').style.width = data.percent+'%';
        if(data.file_ready){
            document.getElementById('download').innerHTML='<a href="/download">📥 Excel herunterladen</a>';
        } else {
            setTimeout(update,1000);
        }
    });
}

function addTarget(){
    let f=document.getElementById('addform');
    let data=new FormData(f);
    fetch('/add_target',{method:'POST',body:data}).then(()=>location.reload());
}

function deleteTarget(name,url){
    fetch('/delete_target',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name,url})
    }).then(()=>location.reload());
}

update();
</script>
</body>
</html>
""", targets=targets)

@app.route("/add_target", methods=["POST"])
def add_target():
    name = request.form.get("name")
    url = request.form.get("url")
    selector = normalize_selector(request.form.get("selector"))
    targets = read_targets()
    targets.append({"name": name, "url": url, "selector": selector})
    write_targets(targets)
    return "OK"

@app.route("/delete_target", methods=["POST"])
def delete_target():
    data = request.get_json()
    name = data.get("name")
    url = data.get("url")
    targets = [t for t in read_targets() if not (t["name"]==name and t["url"]==url)]
    write_targets(targets)
    return jsonify(targets)

@app.route("/start", methods=["POST"])
def start():
    threading.Thread(target=run_crawling).start()
    return "OK"

@app.route("/progress")
def get_progress():
    return jsonify(progress)

@app.route("/proxy")
def proxy():
    url = request.args.get("url")
    if not url:
        return "Keine URL angegeben", 400
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url)
        html = r.text
        # Optional: Skripte deaktivieren, um Klickprobleme zu vermeiden
        html = html.replace("<head>", "<head><base href='{}'>".format(url))
        return Response(html, mimetype="text/html")
    except Exception as e:
        return f"Fehler beim Laden der Seite: {e}", 500

@app.route("/download")
def download():
    filepath = progress["filename"]
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "Datei nicht gefunden", 404


if __name__=="__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
