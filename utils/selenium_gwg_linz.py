from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

URL = "https://www.gwg-linz.at/bauprojekte/"
SELECTOR = "article.bauprojekt-teaser"

options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Headless-Modus für Server
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)

driver.get(URL)

try:
    # Warte bis zu 15 Sekunden, bis die Projekt-Container geladen sind
    project_containers = WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, SELECTOR))
    )
    print(f"Erfolg! {len(project_containers)} Projekte gefunden.")
    rows = []
    for container in project_containers:
        # Projektname (meist im h3 oder h2)
        try:
            title = container.find_element(By.CSS_SELECTOR, "h3, h2").text.strip()
        except:
            title = ""
        # Link (im <a> Tag)
        try:
            link = container.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        except:
            link = ""
        rows.append({
            "Website": "GWG Linz",
            "Projektname": title,
            "Link": link
        })
    # In Excel speichern
    df = pd.DataFrame(rows)
    df.to_excel("gwg_linz_projekte.xlsx", index=False)
    print("Excel-Datei 'gwg_linz_projekte.xlsx' wurde erstellt.")
except Exception as e:
    print(f"Fehler bei GWG Linz: {e}")
finally:
    driver.quit()
