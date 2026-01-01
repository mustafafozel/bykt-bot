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

# Ayarları GitHub'dan al
BOT_TOKEN = os.environ["BOT_TOKEN"]
KANAL_ID = os.environ["KANAL_ID"]
URL = "https://bykt.org/"

def telegrama_gonder(mesaj):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(send_url, params=params)
        print("📨 Hatırlatma mesajı gönderildi.")
    except Exception as e:
        print(f"Hata: {e}")

def hatirlat():
    print("🌍 Hatırlatıcı çalışıyor...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    secilen_marka = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        wait = WebDriverWait(driver, 25)

        # İstersen burada da "En Yeniler" sıralamasını yapabilirsin.
        # Varsayılan olarak sitenin en üstünde ne varsa onu alır.
        try:
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, "//select[./option[@value='newest']]")))
            select = Select(select_element)
            select.select_by_value("newest")
            time.sleep(5)
        except:
            pass

        # En üstteki markayı al
        marka_elementi = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg")))
        secilen_marka = marka_elementi.text.strip()
        
        print(f"✅ Seçilen Marka: {secilen_marka}")

    except Exception as e:
        print(f"❌ Hata: {e}")
        return
    finally:
        if driver: driver.quit()

    if secilen_marka:
        # Link oluşturma (Senin istediğin format: taşkesti-su)
        slug_hazirlik = secilen_marka.lower().replace(" ", "-")
        marka_slug = urllib.parse.quote(slug_hazirlik)
        ozel_link = f"https://bykt.org/?marka={marka_slug}"
        
        # MESAJ FORMATI
        mesaj = (
            f"🎗 **GÜNLÜK HATIRLATMA**\n\n"
            f"Bu markayı da unutma! ⚠️\n\n"
            f"🏷 **Marka:** {secilen_marka}\n"
            f"🔗 **Detay:** {ozel_link}\n\n"
            f"#BoykotHatırlatma"
        )
        
        telegrama_gonder(mesaj)

if __name__ == "__main__":
    hatirlat()