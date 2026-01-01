import os
import time
import requests
import urllib.parse # Linkleri düzeltmek için (boşlukları %20 yapar)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- AYARLAR ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
KANAL_ID = os.environ["KANAL_ID"]

# ÖNEMLİ: Site eğer varsayılan olarak "En Yenileri" göstermiyorsa,
# bot sayfadaki en üstteki (belki de en popüler) markayı alır.
# Genelde sitelerde "?sort=new" veya "?orderby=date" gibi parametreler olur.
# Şimdilik ana sayfayı tarıyoruz.
URL = "https://bykt.org/" 

KAYIT_DOSYASI = "son_marka.txt"

def telegrama_gonder(mesaj):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # disable_web_page_preview=False yaptık ki resim görünsün
    params = {"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(send_url, params=params)
        print("📨 Mesaj gönderildi.")
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
    yeni_marka = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        
        # Sayfanın yüklenmesini bekle
        wait = WebDriverWait(driver, 25)
        # İlk sıradaki markayı al
        marka_elementi = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg")))
        
        yeni_marka = marka_elementi.text.strip()
        print(f"✅ Siteden Gelen Veri: {yeni_marka}")

    except Exception as e:
        print(f"❌ Hata: {e}")
        return
    finally:
        if driver: driver.quit()

    if not yeni_marka: return

    # --- KONTROL VE KAYIT ---
    eski_marka = ""
    if os.path.exists(KAYIT_DOSYASI):
        with open(KAYIT_DOSYASI, "r", encoding="utf-8") as f:
            eski_marka = f.read().strip()

    if yeni_marka != eski_marka:
        print(f"🔔 Yeni marka tespit edildi: {yeni_marka}")
        
        # --- LİNKİ DÜZENLEME KISMI ---
        # Marka adındaki boşlukları ve özel karakterleri link formatına çevirir
        # Örnek: "Mars Inc." -> "Mars+Inc." veya "Mars%20Inc."
        marka_slug = urllib.parse.quote(yeni_marka)
        ozel_link = f"https://bykt.org/?marka={marka_slug}"
        
        mesaj = f"🚨 **LİSTEYE YENİ MARKA EKLENDİ!**\n\n🏷 **Marka:** {yeni_marka}\n🔗 **Detaylı İncele:** {ozel_link}\n\n#Boykot #YeniEkleme"
        telegrama_gonder(mesaj)
        
        # Yeni markayı dosyaya yaz (HATA BURADAYDI, ARTIK İZİN VAR)
        with open(KAYIT_DOSYASI, "w", encoding="utf-8") as f:
            f.write(yeni_marka)
    else:
        print("💤 Değişiklik yok.")

if __name__ == "__main__":
    siteyi_tara()