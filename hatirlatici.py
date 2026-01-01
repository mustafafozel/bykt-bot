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
        if response.status_code != 200:
             print(f"⚠️ Telegram Hatası: {response.text}")
             # Resim hatası varsa sadece metin gönder
             if "Wrong file identifier" in response.text or "image" in response.text:
                 requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                               data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

# --- DETAYLARI ÇEKME (Senin Verdiğin HTML Kodlarına Göre) ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 15)
    
    # Varsayılanlar
    logo_url = "https://bykt.org/favicon.ico"
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # 1. LOGO: class="w-20 h-20 rounded-lg object-contain..."
        try:
            logo_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.w-20.h-20.object-contain")))
            src = logo_element.get_attribute("src")
            if src: logo_url = src
        except:
            print("⚠️ Logo bulunamadı.")

        # 2. AÇIKLAMA: class="... whitespace-pre-line"
        try:
            # whitespace-pre-line sınıfını arıyoruz
            aciklama = driver.find_element(By.CSS_SELECTOR, "p.whitespace-pre-line")
            text = aciklama.text.strip()
            if text:
                sebep_metni = text[:700] + "..." if len(text) > 700 else text
        except:
            print("⚠️ Açıklama bulunamadı.")

        # 3. DURUM: class="... rounded-full" -> Kesin Boykot
        try:
            # rounded-full sınıfına sahip span'i bul
            durum_etiketi = driver.find_element(By.CSS_SELECTOR, "span.rounded-full")
            raw_text = durum_etiketi.text.strip()
            
            if "Kesin" in raw_text: durum_emoji, durum_metni = "🔴", "KESİN BOYKOT"
            elif "İnsafa" in raw_text: durum_emoji, durum_metni = "🟠", "İNSAFA BAĞLI"
            elif "Alınabilir" in raw_text: durum_emoji, durum_metni = "🟢", "ALINABİLİR"
        except:
             print("⚠️ Durum etiketi bulunamadı.")

    except Exception as e:
        print(f"⚠️ Detay fonksiyonunda hata: {e}")

    return logo_url, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı Başlıyor (HTML Hedefli Mod)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        
        # Marka isimlerinin yüklenmesini bekle (Verdiğin h3 class'ına göre)
        wait = WebDriverWait(driver, 25)
        # Class: text-lg font-bold
        print("⏳ Marka isimleri aranıyor...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg.font-bold")))
        
        # Sayfadaki TÜM marka başlıklarını al
        basliklar = driver.find_elements(By.CSS_SELECTOR, "h3.text-lg.font-bold")
        
        site_listesi = []
        
        print(f"🔍 {len(basliklar)} adet başlık bulundu. Linkleri çözümleniyor...")

        for h3 in basliklar:
            try:
                ad = h3.text.strip()
                if not ad: continue

                # ÖNEMLİ KISIM: Başlığın içindeki veya üstündeki Linki (a tag) bul
                # XPath ile: Bu h3 elementinin bir üstündeki veya kapsayan 'a' etiketini bul.
                try:
                    # "./ancestor::a" -> Bu elementin atalarından 'a' olanı bul demektir.
                    link_element = h3.find_element(By.XPATH, "./ancestor::a")
                    link = link_element.get_attribute("href")
                    
                    if link and "?marka=" in link:
                        if (ad, link) not in site_listesi:
                            site_listesi.append((ad, link))
                except:
                    # Link bulunamadıysa geç
                    continue
            except:
                continue

        print(f"✅ Toplam {len(site_listesi)} adet marka ve link eşleştirildi.")
        
        if not site_listesi:
            print("❌ HATA: Başlıklar bulundu ama linkleri çıkarılamadı.")
            return

        # HAFIZA VE SEÇİM İŞLEMLERİ
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