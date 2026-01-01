import os
import time
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- AYARLAR ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
KANAL_ID = os.environ["KANAL_ID"]
URL = "https://bykt.org/" 
KAYIT_DOSYASI = "son_marka.txt"

def telegrama_gonder(mesaj):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(send_url, params=params)
        time.sleep(1) 
    except Exception as e:
        print(f"Mesaj hatası: {e}")

def siteyi_tara():
    print("🌍 Bulut Chrome hazırlanıyor...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    yeni_markalar_listesi = []

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        wait = WebDriverWait(driver, 25)

        # --- SIRALAMA DEĞİŞTİRME ---
        try:
            print("⏳ Sıralama 'En Yeni' yapılıyor...")
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, "//select[./option[@value='newest']]")))
            select = Select(select_element)
            select.select_by_value("newest")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Sıralama hatası: {e}")

        # --- VERİ ÇEKME ---
        # İlk 15 markayı al
        marka_elementleri = driver.find_elements(By.CSS_SELECTOR, "h3.text-lg")
        
        for eleman in marka_elementleri[:15]:
            text = eleman.text.strip()
            if text:
                yeni_markalar_listesi.append(text)
        
        print(f"✅ Çekilen liste: {yeni_markalar_listesi[:5]}")

    except Exception as e:
        print(f"❌ Hata: {e}")
        return
    finally:
        if driver: driver.quit()

    if not yeni_markalar_listesi:
        return

    # --- KONTROL ---
    eski_son_marka = ""
    if os.path.exists(KAYIT_DOSYASI):
        with open(KAYIT_DOSYASI, "r", encoding="utf-8") as f:
            eski_son_marka = f.read().strip()

    bildirilecek_markalar = []

    if not eski_son_marka:
        bildirilecek_markalar.append(yeni_markalar_listesi[0])
    else:
        for marka in yeni_markalar_listesi:
            if marka == eski_son_marka:
                break
            else:
                bildirilecek_markalar.append(marka)

    # --- BİLDİRİM GÖNDERME ---
    if bildirilecek_markalar:
        print(f"🔔 {len(bildirilecek_markalar)} yeni marka var.")
        
        for marka in reversed(bildirilecek_markalar):
            # --- LİNK DÜZELTME KISMI ---
            # 1. Harfleri küçült (Taşkesti -> taşkesti)
            # 2. Boşlukları tire yap (Su -> -su)
            slug_hazirlik = marka.lower().replace(" ", "-")
            
            # 3. URL uyumlu hale getir (Türkçe karakterler %C3%.. gibi kodlanır)
            marka_slug = urllib.parse.quote(slug_hazirlik)
            
            ozel_link = f"https://bykt.org/?marka={marka_slug}"
            # ---------------------------
            
            mesaj = f"🚨 **LİSTEYE YENİ MARKA EKLENDİ!**\n\n🏷 **Marka:** {marka}\n🔗 **Detaylı İncele:** {ozel_link}\n\n#Boykot #YeniEkleme"
            telegrama_gonder(mesaj)
        
        with open(KAYIT_DOSYASI, "w", encoding="utf-8") as f:
            f.write(yeni_markalar_listesi[0])
            
    else:
        print("💤 Değişiklik yok.")

if __name__ == "__main__":
    siteyi_tara()