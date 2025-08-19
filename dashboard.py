from flask import Flask, render_template_string, request, send_file, jsonify
import threading
import os
import json
import datetime

app = Flask(__name__)

progress = {
    "percent": 0,
    "status": "Bereit",
    "error": "",
    "file_ready": False,
    "filename": "alle_projekte.xlsx"
}

TARGETS_FILE = "scrape_targets.csv"

def read_targets():
    import csv
    targets = []
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                targets.append({
                    "name": row.get("Name", ""),
                    "url": row.get("URL", ""),
                    "selector": row.get("Selector", "")
                })
    return targets


def write_targets(targets):
    import csv
    with open(TARGETS_FILE, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "URL", "Selector"])
        writer.writeheader()
        for t in targets:
            writer.writerow({
                "Name": t.get("name", ""),
                "URL": t.get("url", ""),
                "Selector": t.get("selector", "")
            })

# ---- Crawling (echter Scraper) ----
def run_crawling():
    global progress
    progress["status"] = "Starte Crawling..."
    progress["percent"] = 0
    progress["error"] = ""
    progress["file_ready"] = False
    progress["filename"] = f"alle_projekte_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx"

    try:
        from utils.scraper_utils import smart_ki_extraction, load_scrape_targets
        import json, re, pandas as pd
        from urllib.parse import urlparse, urljoin

        targets = load_scrape_targets()
        all_rows = []
        step = 0
        total = len(targets)

        for target in targets:
            step += 1
            name = target.get('name', 'website')
            url = target.get('url')
            selector = target.get('selector')
            progress["status"] = f"Extrahiere Daten von {name} ({step}/{total})..."
            progress["percent"] = int((step/total)*100)

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
        progress["status"] = "Fertig! Excel-Datei erstellt."
        progress["percent"] = 100
        progress["file_ready"] = True

    except Exception as e:
        progress["status"] = "Fehler beim Crawling!"
        progress["error"] = str(e)

# ---- Routes ----
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
</style>
</head>
<body>
<h2>🌐 Web-Crawler Dashboard</h2>
<p>Ziele verwalten und Crawling starten:</p>

<form id="addform" onsubmit="addTarget();return false;">
  <input name="name" placeholder="Name" required>
  <input name="url" placeholder="URL" required>
  <input name="selector" placeholder="Selector" required>
  <button type="submit">+ Hinzufügen</button>
</form>

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

<button id="crawlbtn" style="margin-top:20px;" onclick="startCrawling()">🚀 Crawling starten</button>
<div id="status">Bereit</div>
<div id="progressbar"><div id="bar"></div></div>
<div id="download"></div>

<script>
function startCrawling() { fetch('/start', {method:'POST'}).then(()=>update()); }
function update() {
  fetch('/progress').then(r=>r.json()).then(data=>{
    let status = data.status;
    if(data.error) status += " ⚠️ "+data.error;
    document.getElementById('status').innerText = status;
    document.getElementById('bar').style.width = data.percent+'%';
    if(data.file_ready) {
      document.getElementById('download').innerHTML='<a href="/download">📥 Excel herunterladen</a>';
    } else {
      document.getElementById('download').innerHTML='';
      setTimeout(update,1000);
    }
  });
}
function addTarget() {
  let f=document.getElementById('addform');
  let data=new FormData(f);
  fetch('/add_target',{method:'POST',body:data}).then(()=>location.reload());
}
function deleteTarget(name,url) {
    fetch('/delete_target',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name,url})
    }).then(r=>r.json()).then(targets=>{
        // Tabelle neu rendern
        location.reload();
    });
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
    selector = request.form.get("selector")
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
    # Nach dem Löschen die aktualisierte Liste zurückgeben
    return jsonify(targets)

@app.route("/start", methods=["POST"])
def start():
    t = threading.Thread(target=run_crawling)
    t.start()
    return "OK"

@app.route("/progress")
def get_progress():
    return jsonify(progress)

@app.route("/download")
def download():
    filepath = os.path.join(os.getcwd(), progress["filename"])
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "Datei nicht gefunden",404

if __name__=="__main__":
    app.run(debug=True)
