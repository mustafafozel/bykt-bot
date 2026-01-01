import os
import time
import requests
import json
import urllib.parse
import traceback
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
    
    clean_kanal_id = KANAL_ID.replace('@','')
    kanal_paylas_linki = f"https://t.me/share/url?url=https://t.me/{clean_kanal_id}"
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"🔗 {marka_adi} Detayları", "url": buton_linki}],
            [{"text": "📢 Kanalı Paylaş", "url": kanal_paylas_linki}]
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
        print(f"📨 Mesaj gönderiliyor: {marka_adi}")
        response = requests.post(send_url, data=data)
        if response.status_code == 200:
            print("✅ BAŞARILI: Mesaj iletildi.")
        else:
             print(f"⚠️ Telegram Hatası: {response.text}")
             if "Wrong file identifier" in response.text or "image" in response.text:
                 print("🔄 Resim hatalı, sadece metin gönderiliyor...")
                 requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                               data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

# --- DETAYLARI ÇEKME ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 10)
    
    logo_url = "https://bykt.org/favicon.ico"
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # LOGO
        try:
            logo_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.w-20.h-20.object-contain")))
            src = logo_element.get_attribute("src")
            if src and "svg" not in src: logo_url = src
        except:
            pass # Varsayılan kalır

        # AÇIKLAMA
        try:
            aciklama = driver.find_element(By.CSS_SELECTOR, "p.whitespace-pre-line")
            text = aciklama.text.strip()
            if text: sebep_metni = text[:600] + "..." if len(text) > 600 else text
        except:
            pass

        # DURUM
        try:
            source = driver.page_source
            if "Kesin Boykot" in source:
                durum_emoji = "🔴"
                durum_metni = "KESİN BOYKOT"
            elif "İnsafa Bağlı" in source:
                durum_emoji = "🟠"
                durum_metni = "İNSAFA BAĞLI"
            elif "Alınabilir" in source:
                durum_emoji = "🟢"
                durum_metni = "ALINABİLİR"
        except:
            pass

    except Exception as e:
        print(f"⚠️ Detay çekme uyarısı: {e}")

    return logo_url, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı Başlıyor (Garantili Mod)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        
        wait = WebDriverWait(driver, 20)
        
        # --- DÜZELTME BURADA ---
        # Önce sayfanın yüklendiğinden emin olmak için 'h3' etiketini bekle
        print("⏳ Markaların yüklenmesi bekleniyor...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg")))
        
        # Şimdi linkleri 'CSS Selector' ile topla (Bu yöntem daha önce çalışıyordu)
        # href içinde 'marka=' geçen tüm a etiketlerini al
        link_elementleri = driver.find_elements(By.CSS_SELECTOR, "a[href*='marka=']")
        
        site_listesi = []
        for eleman in link_elementleri:
            try:
                link = eleman.get_attribute("href")
                # Linkin içindeki h3'ü bul
                ad = eleman.find_element(By.CSS_SELECTOR, "h3.text-lg").text.strip()
                if ad and link:
                    site_listesi.append((ad, link))
            except:
                continue # Bazı linklerde h3 olmayabilir, geç

        print(f"✅ Toplam {len(site_listesi)} marka bulundu.")
        
        if not site_listesi:
            print("❌ HATA: Listelenen marka sayısı 0! CSS Selector uymadı.")
            return

        # HAFIZA İŞLEMLERİ
        hatirlatilanlar = []
        if os.path.exists(HAFIZA_DOSYASI):
            with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f:
                hatirlatilanlar = [satir.strip() for satir in f.readlines()]

        secilen_veri = None
        sifirlama_yapildi = False

        for veri in site_listesi:
            if veri[0] not in hatirlatilanlar:
                secilen_veri = veri
                break
        
        if secilen_veri is None:
            print("♻️ Liste bitti! Başa dönülüyor...")
            secilen_veri = site_listesi[0]
            sifirlama_yapildi = True

        marka_adi = secilen_veri[0]
        marka_linki = secilen_veri[1]
        
        print(f"🎯 Seçilen: {marka_adi}")

        # DETAYLARI ÇEK
        logo, sebep, durum_ikon, durum_yazi = detaylari_getir(driver, marka_linki)

        # MESAJ
        mesaj = (
            f"🎗 **GÜNLÜK HATIRLATMA**\n\n"
            f"Unutmayalım! ⚠️\n\n"
            f"🏷 **Marka:** {marka_adi}\n"
            f"{durum_ikon} **Durum:** {durum_yazi}\n\n"
            f"❓ **Neden?**\n"
            f"{sebep}\n\n"
            f"#BoykotHatırlatma #{marka_adi.replace(' ','')}"
        )

        telegrama_gonder_foto(logo, mesaj, marka_linki, marka_adi)

        # KAYDET
        mod = "w" if sifirlama_yapildi else "a"
        with open(HAFIZA_DOSYASI, mod, encoding="utf-8") as f:
            f.write(marka_adi + "\n")

    except Exception as e:
        print("❌ KRİTİK HATA:")
        traceback.print_exc()
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    hatirlat()