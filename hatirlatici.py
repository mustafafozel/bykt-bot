import os
import time
import requests
import json
import urllib.parse
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
URL = "https://bykt.org/"
HAFIZA_DOSYASI = "hatirlatilanlar.txt"

# --- FOTOĞRAFLI MESAJ GÖNDERME ---
def telegrama_gonder_foto(resim_url, mesaj, buton_linki, marka_adi):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    kanal_paylas_linki = f"https://t.me/share/url?url=https://t.me/{KANAL_ID.replace('@','')}"
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": f"🔗 {marka_adi} Detayları", "url": buton_linki}
            ],
            [
                {"text": "📢 Kanalı Paylaş", "url": kanal_paylas_linki}
            ]
        ]
    }

    data = {
        "chat_id": KANAL_ID,
        "photo": resim_url,
        "caption": mesaj,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(reply_markup)
    }
    
    try:
        response = requests.post(send_url, data=data)
        if response.status_code == 200:
            print("📨 Günlük hatırlatma gönderildi.")
        else:
             print(f"⚠️ Mesaj hatası: {response.text}")
    except Exception as e:
        print(f"Hata: {e}")

# --- DETAYLARI VE DURUMU ÇEKME ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detay sayfasına gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 15)
    
    logo_url = "https://bykt.org/favicon.ico"
    sebep_metni = "Detaylı bilgi sitede mevcut."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # 1. LOGO
        try:
            logo_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.w-20.h-20.object-contain")))
            src = logo_element.get_attribute("src")
            if src: logo_url = src
        except:
            pass

        # 2. AÇIKLAMA
        try:
            aciklama_elementi = driver.find_element(By.CSS_SELECTOR, "p.whitespace-pre-line")
            ham_metin = aciklama_elementi.text.strip()
            if ham_metin:
                if len(ham_metin) > 600: 
                     sebep_metni = ham_metin[:600] + "... (devamı sitede)"
                else:
                    sebep_metni = ham_metin
        except:
            pass

        # 3. DURUM
        try:
            durum_etiketi = driver.find_element(By.CSS_SELECTOR, "span.px-3.py-0.5.rounded-full")
            durum_metni = durum_etiketi.text.strip()
            
            if "Kesin" in durum_metni: durum_emoji = "🔴"
            elif "İnsafa" in durum_metni: durum_emoji = "🟠"
            elif "Alınabilir" in durum_metni: durum_emoji = "🟢"
            else: durum_emoji = "⚪️"
        except:
            pass

    except Exception as e:
        print(f"⚠️ Detay hatası: {e}")

    return logo_url, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı çalışıyor (Detaylı Mod)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    site_listesi = [] # Format: [(Ad, Link), (Ad, Link)...]

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        wait = WebDriverWait(driver, 25)

        # Ana sayfadaki marka linklerini ve isimlerini topla
        link_elementleri = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/?marka=']")))
        
        for eleman in link_elementleri:
            try:
                link = eleman.get_attribute("href")
                ad_element = eleman.find_element(By.CSS_SELECTOR, "h3.text-lg")
                ad = ad_element.text.strip()
                if ad and link:
                    site_listesi.append((ad, link))
            except:
                continue
        
        print(f"✅ Toplam {len(site_listesi)} marka listelendi.")

    except Exception as e:
        print(f"❌ Hata: {e}")
        if driver: driver.quit()
        return

    if not site_listesi:
        if driver: driver.quit()
        return

    # --- SIRA KİMDE? ---
    hatirlatilanlar = []
    if os.path.exists(HAFIZA_DOSYASI):
        with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f:
            hatirlatilanlar = [satir.strip() for satir in f.readlines()]

    secilen_veri = None # (Ad, Link) olacak
    sifirlama_yapildi = False

    # Listeyi tara, hatırlatılmamış ilkini bul
    for veri in site_listesi:
        ad = veri[0]
        if ad not in hatirlatilanlar:
            secilen_veri = veri
            break
    
    # Liste bitmişse başa dön
    if secilen_veri is None:
        print("♻️ Liste bitti! Başa dönülüyor...")
        secilen_veri = site_listesi[0]
        sifirlama_yapildi = True

    marka_adi = secilen_veri[0]
    marka_linki = secilen_veri[1]
    
    print(f"🎯 Bugünün Seçimi: {marka_adi}")

    # --- DETAYLARI ÇEKMEK İÇİN GİT ---
    # Driver hala açık, seçilen linke gidiyoruz
    logo, sebep, durum_ikon, durum_yazi = detaylari_getir(driver, marka_linki)

    # --- MESAJI HAZIRLA ---
    mesaj = (
        f"🎗 **GÜNLÜK HATIRLATMA**\n\n"
        f"Bu markayı unutmayalım! ⚠️\n\n"
        f"🏷 **Marka:** {marka_adi}\n"
        f"{durum_ikon} **Durum:** {durum_yazi}\n\n"
        f"❓ **Neden?**\n"
        f"{sebep}\n\n"
        f"#BoykotHatırlatma #{marka_adi.replace(' ','')}"
    )

    # --- GÖNDER ---
    telegrama_gonder_foto(logo, mesaj, marka_linki, marka_adi)

    # --- KAYDET ---
    if sifirlama_yapildi:
        with open(HAFIZA_DOSYASI, "w", encoding="utf-8") as f:
            f.write(marka_adi + "\n")
    else:
        with open(HAFIZA_DOSYASI, "a", encoding="utf-8") as f:
            f.write(marka_adi + "\n")
            
    if driver: driver.quit()

if __name__ == "__main__":
    hatirlat()