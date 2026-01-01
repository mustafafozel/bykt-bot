import os
import time
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Ayarları GitHub'dan al
BOT_TOKEN = os.environ["BOT_TOKEN"]
KANAL_ID = os.environ["KANAL_ID"]
URL = "https://bykt.org/"
HAFIZA_DOSYASI = "hatirlatilanlar.txt"

def telegrama_gonder(mesaj):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(send_url, params=params)
        print("📨 Hatırlatma mesajı gönderildi.")
    except Exception as e:
        print(f"Hata: {e}")

def hatirlat():
    print("🌍 Hatırlatıcı çalışıyor (Akıllı Sıra Modu)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    site_listesi = []

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        wait = WebDriverWait(driver, 25)

        # Varsayılan sıralamada sayfadaki tüm markaları çek
        elemanlar = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h3.text-lg")))
        
        for e in elemanlar:
            text = e.text.strip()
            if text:
                site_listesi.append(text)
        
        print(f"✅ Siteden {len(site_listesi)} marka çekildi.")

    except Exception as e:
        print(f"❌ Hata: {e}")
        return
    finally:
        if driver: driver.quit()

    if not site_listesi:
        return

    # --- HAFIZAYI OKU ---
    hatirlatilanlar = []
    if os.path.exists(HAFIZA_DOSYASI):
        with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f:
            hatirlatilanlar = [satir.strip() for satir in f.readlines()]

    # --- SEÇİM MANTIĞI ---
    secilen_marka = None
    sifirlama_yapildi = False

    # Listeyi baştan sona tara, daha önce hatırlatılmamış İLK markayı bul
    for marka in site_listesi:
        if marka not in hatirlatilanlar:
            secilen_marka = marka
            break
    
    # Eğer listedeki HERKES hatırlatılmışsa (Liste sonuna geldik)
    if secilen_marka is None:
        print("♻️ Liste bitti! Başa dönülüyor...")
        secilen_marka = site_listesi[0] # Listenin en başındakini seç
        sifirlama_yapildi = True

    print(f"🎯 Seçilen Marka: {secilen_marka}")

    # --- MESAJ GÖNDER ---
    slug_hazirlik = secilen_marka.lower().replace(" ", "-")
    marka_slug = urllib.parse.quote(slug_hazirlik)
    ozel_link = f"https://bykt.org/?marka={marka_slug}"
    
    mesaj = (
        f"🎗 **GÜNLÜK HATIRLATMA**\n\n"
        f"Bu markayı da unutma! ⚠️\n\n"
        f"🏷 **Marka:** {secilen_marka}\n"
        f"🔗 **Detay:** {ozel_link}\n\n"
        f"#BoykotHatırlatma"
    )
    
    telegrama_gonder(mesaj)

    # --- HAFIZAYI GÜNCELLE ---
    if sifirlama_yapildi:
        # Eğer başa döndüysek, dosyayı silip sadece yeni seçileni yaz (w modu)
        with open(HAFIZA_DOSYASI, "w", encoding="utf-8") as f:
            f.write(secilen_marka + "\n")
    else:
        # Devam ediyorsak, yeni markayı listenin altına ekle (a modu)
        with open(HAFIZA_DOSYASI, "a", encoding="utf-8") as f:
            f.write(secilen_marka + "\n")

if __name__ == "__main__":
    hatirlat()