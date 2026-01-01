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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- AYARLAR ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
KANAL_ID = os.environ["KANAL_ID"]
URL = "https://bykt.org/" 
KAYIT_DOSYASI = "son_marka.txt"

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
        print(f"📨 Telegram'a yükleniyor: {marka_adi}")
        
        if resim_datalari:
            # Resmi dosya formatında gönderiyoruz (Screenshot verisi)
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
            time.sleep(1) # Spam olmaması için bekleme
        else:
            print(f"⚠️ Telegram Hatası: {response.text}")
            # Hata durumunda metin dene
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})

    except Exception as e:
        print(f"⚠️ Gönderim hatası: {e}")

# --- DETAYLARI ÇEKME (HD + Akıllı Eşleşme) ---
def detaylari_getir(driver, link, aranan_marka_adi):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    wait = WebDriverWait(driver, 15)
    
    logo_data = None 
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # 1. LOGO (İSİM EŞLEŞTİRMELİ + HD KALİTE)
        print(f"🔍 '{aranan_marka_adi}' logusu aranıyor ve HD yapılacak...")
        try:
            # Tüm potansiyel logoları bul
            potansiyel_logolar = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img.object-contain")))
            
            hedef_logo = None
            
            # Doğru logoyu bul (İsim kontrolü)
            for img in potansiyel_logolar:
                try:
                    alt_text = img.get_attribute("alt")
                    # Marka adı alt text içinde geçiyor mu?
                    if alt_text and (aranan_marka_adi.lower() in alt_text.lower() or alt_text.lower() in aranan_marka_adi.lower()):
                        hedef_logo = img
                        print(f"✅ Eşleşen logo bulundu! (Alt: {alt_text})")
                        break
                except: continue
            
            # Bulunamazsa varsayılanı (ilk w-20'yi) al
            if not hedef_logo:
                try: 
                    print("⚠️ İsimle eşleşmedi, varsayılan logo alınıyor...")
                    hedef_logo = driver.find_element(By.CSS_SELECTOR, "img.w-20.h-20.object-contain")
                except: pass

            if hedef_logo:
                # 🔥 HD YAPMA İŞLEMİ (JS Injection)
                script = """
                arguments[0].style.width = '500px';
                arguments[0].style.height = '500px';
                arguments[0].style.objectFit = 'contain';
                arguments[0].style.backgroundColor = 'white';
                arguments[0].style.padding = '20px';
                """
                driver.execute_script(script, hedef_logo)
                time.sleep(1) # Büyümesi için bekle
                
                # Ekran görüntüsünü al
                logo_data = hedef_logo.screenshot_as_png
                print("📸 HD Ekran görüntüsü alındı.")
            else:
                print("❌ Uygun logo bulunamadı.")
            
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

def siteyi_tara():
    print("🌍 Ana Bot Çalışıyor (HD + Link Üretme Modu)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None
    sitedeki_markalar = [] 

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        wait = WebDriverWait(driver, 25)

        # --- ÖNEMLİ: SIRALAMAYI "EN YENİ" YAP ---
        # Ana bot için bu çok önemli çünkü yeni eklenenleri bulması lazım
        try:
            print("⏳ Sıralama 'En Yeni' yapılıyor...")
            # XPath ile daha güvenli seçim
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, "//select[./option[@value='newest']]")))
            Select(select_element).select_by_value("newest")
            time.sleep(5) # Listenin güncellenmesi için bekle
            print("✅ Sıralama değiştirildi.")
        except Exception as e:
            print(f"⚠️ Sıralama değiştirilemedi (Varsayılan liste taranacak): {e}")

        # --- LİNK ÜRETME YÖNTEMİ ---
        # Sayfanın yüklenmesini bekle (Başlıkları bekle)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.text-lg.font-bold")))
        
        # İlk 15 markayı al (Çoklu ekleme ihtimaline karşı)
        basliklar = driver.find_elements(By.CSS_SELECTOR, "h3.text-lg.font-bold")
        
        for h3 in basliklar[:15]:
            text = h3.text.strip()
            if not text: continue
            
            # Link Üretme Formülü
            slug = text.lower().replace(" ", "-")
            safe_slug = urllib.parse.quote(slug)
            generated_link = f"https://bykt.org/?marka={safe_slug}"
            
            # Listeye ekle: (Marka Adı, Link)
            sitedeki_markalar.append((text, generated_link))
            
        print(f"✅ Siteden {len(sitedeki_markalar)} marka çekildi.")

    except Exception as e:
        print("❌ Tarayıcı Başlatma Hatası:")
        traceback.print_exc()
        if driver: driver.quit()
        return

    if not sitedeki_markalar:
        if driver: driver.quit()
        return

    # --- KONTROL VE GÖNDERİM ---
    eski_son_marka = ""
    if os.path.exists(KAYIT_DOSYASI):
        with open(KAYIT_DOSYASI, "r", encoding="utf-8") as f:
            eski_son_marka = f.read().strip()

    bildirilecekler = []
    # İlk kez çalışıyorsa (dosya yoksa) sadece en yenisini al
    if not eski_son_marka:
        bildirilecekler.append(sitedeki_markalar[0])
    else:
        # Yeni markaları bul (Eski markayı görene kadar listeyi tara)
        for marka_adi, marka_linki in sitedeki_markalar:
            if marka_adi == eski_son_marka:
                break
            else:
                bildirilecekler.append((marka_adi, marka_linki))

    if bildirilecekler:
        print(f"🔔 {len(bildirilecekler)} yeni marka bulundu. İşleniyor...")
        
        # Eskiden yeniye doğru gönder (Telegram sırası için ters çevir)
        for marka_adi, marka_linki in reversed(bildirilecekler):
            
            # Detayları Çek (HD Logo + Akıllı Eşleşme)
            logo_data, sebep, durum_ikon, durum_yazi = detaylari_getir(driver, marka_linki, marka_adi)
            
            mesaj = (
                f"🚨 **LİSTEYE YENİ MARKA EKLENDİ!**\n\n"
                f"🏷 **Marka:** {marka_adi}\n"
                f"{durum_ikon} **Durum:** {durum_yazi}\n\n"
                f"❓ **Neden?**\n"
                f"{sebep}\n\n"
                f"#Boykot #{marka_adi.replace(' ','')}"
            )
            
            telegrama_gonder_foto(logo_data, mesaj, marka_linki, marka_adi)
        
        # En son (yani en yeni) eklenen markayı kaydet
        with open(KAYIT_DOSYASI, "w", encoding="utf-8") as f:
            f.write(sitedeki_markalar[0][0]) 
            
    else:
        print("💤 Yeni marka yok, her şey güncel.")
    
    if driver: driver.quit()

if __name__ == "__main__":
    siteyi_tara()