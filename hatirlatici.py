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

# --- FOTOĞRAF GÖNDERME (Byte Verisi İle) ---
def telegrama_gonder_foto(resim_datalari, mesaj, buton_linki, marka_adi):
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    clean_kanal_id = KANAL_ID.replace('@','')
    kanal_paylas_linki = f"https://t.me/share/url?url=https://t.me/{clean_kanal_id}"
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"🔗 {marka_adi} Detayları", "url": buton_linki}],
            [{"text": "📢 Kanalı Paylaş", "url": kanal_paylas_linki}]
        ]
    }
    
    try:
        print(f"📨 Telegram'a yükleniyor...")
        
        if resim_datalari:
            files = {'photo': ('logo.png', resim_datalari, 'image/png')}
            data = {
                "chat_id": KANAL_ID,
                "caption": mesaj,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(reply_markup)
            }
            response = requests.post(send_url, data=data, files=files)
        else:
            print("⚠️ Resim verisi yok, metin gönderiliyor.")
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})
            return

        if response.status_code == 200:
            print("✅ BAŞARILI: Fotoğraflı mesaj iletildi.")
        else:
            print(f"⚠️ Telegram Hatası: {response.text}")
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})

    except Exception as e:
        print(f"⚠️ Gönderim hatası: {e}")

# --- DETAYLARI ÇEKME (DOĞRU LOGOYU BULMA) ---
def detaylari_getir(driver, link, aranan_marka_adi):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 15)
    
    logo_data = None 
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # 1. LOGO (İSİM EŞLEŞTİRMELİ)
        print(f"🔍 '{aranan_marka_adi}' için doğru logo aranıyor...")
        try:
            # Sayfadaki potansiyel logoları bul (object-contain class'ı olanlar)
            # Hem ana logo hem alternatif logolar bu class'ı kullanıyor olabilir.
            potansiyel_logolar = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img.object-contain")))
            
            hedef_logo = None
            
            # Bulunan resimler arasında döngü kur
            for img in potansiyel_logolar:
                try:
                    alt_text = img.get_attribute("alt") # Resmin ismi (Örn: "Adidas")
                    if alt_text:
                        # Küçük harfe çevirip karşılaştır (adidas == adidas)
                        # contains kontrolü yapıyoruz (Gedik Piliç içinde Gedik var mı?)
                        if aranan_marka_adi.lower() in alt_text.lower() or alt_text.lower() in aranan_marka_adi.lower():
                            hedef_logo = img
                            print(f"✅ Eşleşen logo bulundu! (Alt: {alt_text})")
                            break
                except:
                    continue
            
            # Eğer isimle bulamadıysak, mecburen sayfadaki İLK 'w-20 h-20' boyutundaki resmi al (En yüksek ihtimal)
            if not hedef_logo:
                print("⚠️ İsimle eşleşen logo bulunamadı, ana resim deneniyor...")
                try:
                    hedef_logo = driver.find_element(By.CSS_SELECTOR, "img.w-20.h-20.object-contain")
                except:
                    pass

            # Eğer bir logo belirlediysek ekran görüntüsünü al
            if hedef_logo:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", hedef_logo)
                time.sleep(1) # Kaydırma sonrası bekle
                logo_data = hedef_logo.screenshot_as_png
                print("📸 Doğru logonun görüntüsü alındı.")
            else:
                print("❌ Hiçbir uygun logo bulunamadı.")
            
        except Exception as e:
            print(f"⚠️ Logo işlem hatası: {e}")

        # 2. AÇIKLAMA
        try:
            aciklama = driver.find_element(By.CSS_SELECTOR, "p.whitespace-pre-line")
            text = aciklama.text.strip()
            if text:
                sebep_metni = text[:700] + "..." if len(text) > 700 else text
        except: pass

        # 3. DURUM
        try:
            durum_etiketi = driver.find_element(By.CSS_SELECTOR, "span.rounded-full")
            raw_text = durum_etiketi.text.strip()
            if "Kesin" in raw_text: durum_emoji, durum_metni = "🔴", "KESİN BOYKOT"
            elif "İnsafa" in raw_text: durum_emoji, durum_metni = "🟠", "İNSAFA BAĞLI"
            elif "Alınabilir" in raw_text: durum_emoji, durum_metni = "🟢", "ALINABİLİR"
        except: pass

    except Exception as e:
        print(f"⚠️ Detay fonksiyonunda hata: {e}")

    return logo_data, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı Başlıyor (Akıllı Eşleşme Modu)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
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

        # DETAYLARI ÇEK (Marka adını da gönderiyoruz ki kontrol etsin)
        logo_data, sebep, durum_ikon, durum_yazi = detaylari_getir(driver, marka_linki, marka_adi)

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

        telegrama_gonder_foto(logo_data, mesaj, marka_linki, marka_adi)

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