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

# --- MESAJ GÖNDERME ---
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
                 requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                               data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

# --- DETAYLARI ÇEKME ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    time.sleep(2) # Sayfanın oturması için kısa bekleme
    
    logo_url = "https://bykt.org/favicon.ico"
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # LOGO (SVG harici ilk resmi al)
        try:
            imgs = driver.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                src = img.get_attribute("src")
                # Küçük ikonları ve svgleri ele, ana resmi bulmaya çalış
                if src and "svg" not in src and "data:image" not in src:
                    if "logo" in src or "uploads" in src or "images" in src:
                        logo_url = src
                        break
        except: pass

        # AÇIKLAMA (En uzun paragrafı al)
        try:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            en_uzun_p = ""
            for p in paragraphs:
                txt = p.text.strip()
                if len(txt) > len(en_uzun_p):
                    en_uzun_p = txt
            
            if len(en_uzun_p) > 20:
                sebep_metni = en_uzun_p[:600] + "..."
        except: pass

        # DURUM
        try:
            src = driver.page_source
            if "Kesin Boykot" in src: durum_emoji, durum_metni = "🔴", "KESİN BOYKOT"
            elif "İnsafa Bağlı" in src: durum_emoji, durum_metni = "🟠", "İNSAFA BAĞLI"
            elif "Alınabilir" in src: durum_emoji, durum_metni = "🟢", "ALINABİLİR"
        except: pass

    except: pass
    return logo_url, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı Başlıyor (Geniş Arama Modu)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        
        # Sadece sayfanın tamamen yüklenmesini bekle (body tag'i)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5) # Garanti bekleme
        
        # Sayfadaki TÜM linkleri al
        tum_linkler = driver.find_elements(By.TAG_NAME, "a")
        
        site_listesi = []
        
        # Python tarafında filtrele (Selenium'dan daha güvenilir)
        for eleman in tum_linkler:
            try:
                href = eleman.get_attribute("href")
                text = eleman.text.strip() # Linkin içindeki yazı (Marka adı genelde buradadır)
                
                # Eğer link boşsa veya marka linki değilse geç
                if not href or "?marka=" not in href:
                    continue
                
                # Eğer text boşsa, belki h3 içindedir, onu kontrol et
                if not text:
                    try:
                        h3 = eleman.find_element(By.TAG_NAME, "h3")
                        text = h3.text.strip()
                    except:
                        pass
                
                # Hala isim yoksa geç, varsa listeye ekle
                if text and href:
                    # Aynı markayı tekrar eklememek için kontrol
                    if (text, href) not in site_listesi:
                        site_listesi.append((text, href))
                        
            except:
                continue

        print(f"✅ Toplam {len(site_listesi)} marka bulundu.")
        
        if not site_listesi:
            print("❌ HATA: Sayfa yüklendi ama marka linki bulunamadı. Site yapısı değişmiş olabilir.")
            print("Sayfa Kaynağı Özeti:", driver.page_source[:500]) # Hata ayıklama için
            return

        # HAFIZA VE SEÇİM
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