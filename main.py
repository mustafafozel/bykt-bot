import os
import time
import requests
import json
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
            print("📨 Fotoğraflı mesaj gönderildi.")
            time.sleep(1)
        else:
             print(f"⚠️ Mesaj hatası: {response.text}")
    except Exception as e:
        print(f"Hata: {e}")

# --- DETAYLARI VE DURUMU ÇEKME (HTML YAPISINA GÖRE) ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detay sayfasına gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 15)
    
    logo_url = "https://bykt.org/favicon.ico" # Varsayılan
    sebep_metni = "Detaylı bilgi sitede mevcut."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # 1. LOGO BULMA
        # Verdiğin HTML: class="w-20 h-20 rounded-lg object-contain..."
        try:
            logo_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.w-20.h-20.object-contain")))
            src = logo_element.get_attribute("src")
            # Eğer resim yüklenemediyse 'onerror' tetiklenir ve SVG gelir, biz src'yi alalım
            if src: logo_url = src
        except:
            print("⚠️ Logo bulunamadı.")

        # 2. SEBEP METNİ BULMA
        # Verdiğin HTML: class="... whitespace-pre-line" olan <p> etiketi
        try:
            # whitespace-pre-line sınıfı açıklamaya özel görünüyor.
            aciklama_elementi = driver.find_element(By.CSS_SELECTOR, "p.whitespace-pre-line")
            ham_metin = aciklama_elementi.text.strip()
            
            if ham_metin:
                if len(ham_metin) > 600: 
                     sebep_metni = ham_metin[:600] + "... (devamı sitede)"
                else:
                    sebep_metni = ham_metin
        except:
            print("⚠️ Açıklama metni bulunamadı.")

        # 3. DURUM TESPİTİ (Etiketten Okuma)
        # Verdiğin HTML: class="... rounded-full" olan <span> etiketi
        try:
            # px-3, py-0.5 ve rounded-full sınıfları durum etiketini işaret ediyor
            durum_etiketi = driver.find_element(By.CSS_SELECTOR, "span.px-3.py-0.5.rounded-full")
            durum_metni = durum_etiketi.text.strip()
            
            # Emojiyi metne göre belirle
            if "Kesin" in durum_metni:
                durum_emoji = "🔴"
            elif "İnsafa" in durum_metni:
                durum_emoji = "🟠"
            elif "Alınabilir" in durum_metni:
                durum_emoji = "🟢"
            else:
                durum_emoji = "⚪️"
                
        except Exception as e:
            print(f"⚠️ Durum etiketi bulunamadı: {e}")

    except Exception as e:
        print(f"⚠️ Genel detay hatası: {e}")

    return logo_url, sebep_metni, durum_emoji, durum_metni

def siteyi_tara():
    print("🌍 Bulut Chrome hazırlanıyor (HTML Yapısına Uygun)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    sitedeki_markalar = [] 

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        wait = WebDriverWait(driver, 25)

        # Sıralama: En Yeni
        try:
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, "//select[./option[@value='newest']]")))
            Select(select_element).select_by_value("newest")
            time.sleep(5)
        except:
            pass

        # Linkleri Topla (Ana Sayfa)
        link_elementleri = driver.find_elements(By.CSS_SELECTOR, "a[href^='/?marka=']")
        
        for eleman in link_elementleri[:10]: # İlk 10'u tara
            try:
                marka_linki = eleman.get_attribute("href")
                # Marka adı h3 class="text-lg" içinde
                marka_adi_element = eleman.find_element(By.CSS_SELECTOR, "h3.text-lg")
                marka_adi = marka_adi_element.text.strip()
                if marka_adi and marka_linki:
                    sitedeki_markalar.append((marka_adi, marka_linki))
            except:
                continue
        
        print(f"✅ {len(sitedeki_markalar)} marka bulundu.")

    except Exception as e:
        print(f"❌ Hata: {e}")
        if driver: driver.quit()
        return

    if not sitedeki_markalar:
        if driver: driver.quit()
        return

    # KONTROL
    eski_son_marka = ""
    if os.path.exists(KAYIT_DOSYASI):
        with open(KAYIT_DOSYASI, "r", encoding="utf-8") as f:
            eski_son_marka = f.read().strip()

    bildirilecekler = []
    if not eski_son_marka:
        # İlk kez çalışıyorsa sadece en üsttekini al
        bildirilecekler.append(sitedeki_markalar[0])
    else:
        for marka_adi, marka_linki in sitedeki_markalar:
            if marka_adi == eski_son_marka:
                break
            else:
                bildirilecekler.append((marka_adi, marka_linki))

    # GÖNDERİM
    if bildirilecekler:
        print(f"🔔 {len(bildirilecekler)} yeni marka işleniyor...")
        
        for marka_adi, marka_linki in reversed(bildirilecekler):
            # Verileri çek
            logo, sebep, durum_ikon, durum_yazi = detaylari_getir(driver, marka_linki)
            
            # Mesaj
            mesaj = (
                f"🚨 **LİSTEYE YENİ MARKA EKLENDİ!**\n\n"
                f"🏷 **Marka:** {marka_adi}\n"
                f"{durum_ikon} **Durum:** {durum_yazi}\n\n"
                f"❓ **Neden?**\n"
                f"{sebep}\n\n"
                f"#Boykot #{marka_adi.replace(' ','')}"
            )
            
            telegrama_gonder_foto(logo, mesaj, marka_linki, marka_adi)
        
        with open(KAYIT_DOSYASI, "w", encoding="utf-8") as f:
            f.write(sitedeki_markalar[0][0]) 
            
    else:
        print("💤 Değişiklik yok.")
    
    if driver: driver.quit()

if __name__ == "__main__":
    siteyi_tara()