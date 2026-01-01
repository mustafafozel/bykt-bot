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

# --- GÜNCELLENMİŞ MESAJ GÖNDERME (İndir ve Yükle Yöntemi) ---
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
    
    # 1. Önce sadece Metin gönderme fonksiyonu (Yedek plan)
    def sadece_metin_gonder():
        print("🔄 Resim gönderilemedi, sadece metin gönderiliyor...")
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          data={"chat_id": KANAL_ID, 
                                "text": mesaj, 
                                "parse_mode": "Markdown", 
                                "reply_markup": json.dumps(reply_markup)})
            print("✅ Metin mesajı iletildi.")
        except Exception as e:
            print(f"❌ Metin de gönderilemedi: {e}")

    # 2. Resmi indirmeyi ve yüklemeyi dene
    try:
        print(f"📥 Resim indiriliyor: {resim_url}")
        
        # Resmi Python ile indir
        img_response = requests.get(resim_url, timeout=10)
        
        if img_response.status_code == 200:
            # İndirilen veriyi Telegram'a dosya olarak gönder (files parametresi)
            files = {'photo': img_response.content}
            data = {
                "chat_id": KANAL_ID,
                "caption": mesaj,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(reply_markup)
            }
            
            print(f"📨 Telegram'a yükleniyor...")
            response = requests.post(send_url, data=data, files=files)
            
            if response.status_code == 200:
                print("✅ BAŞARILI: Resim ve mesaj iletildi.")
            else:
                print(f"⚠️ Telegram Yükleme Hatası: {response.text}")
                sadece_metin_gonder() # Hata varsa metin at
        else:
            print(f"⚠️ Resim indirilemedi (Status: {img_response.status_code})")
            sadece_metin_gonder()

    except Exception as e:
        print(f"⚠️ Resim işleme hatası: {e}")
        sadece_metin_gonder()

# --- DETAYLARI ÇEKME ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 15)
    
    # Varsayılanlar
    logo_url = None # Boş bırak, bulunamazsa metin gitsin
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # LOGO
        try:
            # HTML yapına uygun (SVG olmayan, object-contain olan)
            logo_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.w-20.h-20.object-contain")))
            src = logo_element.get_attribute("src")
            if src and "svg" not in src and "data:image" not in src: 
                logo_url = src
                # Eğer relative link ise (başında https yoksa) ekle
                if logo_url.startswith("/"):
                    logo_url = "https://bykt.org" + logo_url
        except:
            pass

        # AÇIKLAMA
        try:
            aciklama = driver.find_element(By.CSS_SELECTOR, "p.whitespace-pre-line")
            text = aciklama.text.strip()
            if text:
                sebep_metni = text[:700] + "..." if len(text) > 700 else text
        except:
            pass

        # DURUM
        try:
            durum_etiketi = driver.find_element(By.CSS_SELECTOR, "span.rounded-full")
            raw_text = durum_etiketi.text.strip()
            
            if "Kesin" in raw_text: durum_emoji, durum_metni = "🔴", "KESİN BOYKOT"
            elif "İnsafa" in raw_text: durum_emoji, durum_metni = "🟠", "İNSAFA BAĞLI"
            elif "Alınabilir" in raw_text: durum_emoji, durum_metni = "🟢", "ALINABİLİR"
        except:
             pass

    except Exception as e:
        print(f"⚠️ Detay fonksiyonunda hata: {e}")

    return logo_url, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı Başlıyor (İndir-Yükle Modu)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        
        wait = WebDriverWait(driver, 25)
        print("⏳ Marka isimleri bekleniyor...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg.font-bold")))
        
        basliklar = driver.find_elements(By.CSS_SELECTOR, "h3.text-lg.font-bold")
        
        site_listesi = []
        print(f"🔍 {len(basliklar)} adet başlık bulundu.")

        for h3 in basliklar:
            text = h3.text.strip()
            if not text: continue
            
            slug = text.lower().replace(" ", "-")
            safe_slug = urllib.parse.quote(slug)
            generated_link = f"https://bykt.org/?marka={safe_slug}"
            
            if (text, generated_link) not in site_listesi:
                site_listesi.append((text, generated_link))

        print(f"✅ Toplam {len(site_listesi)} marka listeye alındı.")
        
        if not site_listesi:
            print("❌ HATA: Liste boş.")
            return

        # HAFIZA
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

        # DETAY
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

        # GÖNDERİM KISMI
        if logo:
            telegrama_gonder_foto(logo, mesaj, marka_linki, marka_adi)
        else:
            print("⚠️ Logo bulunamadı, metin gönderiliyor...")
            # Logo yoksa metin gönder fonksiyonunu burada simüle ediyoruz
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})

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