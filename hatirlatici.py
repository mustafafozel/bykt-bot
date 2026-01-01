import os
import time
import requests
import json
import urllib.parse
import traceback # Hata detayını görmek için
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
    
    # Kanal linkini güvenli oluştur
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
             # Eğer resim yüzünden hata verdiyse, sadece metin gönder
             if "Wrong file identifier" in response.text or "image" in response.text:
                 print("🔄 Resim hatalı olduğu için sadece metin deneniyor...")
                 requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                               data={"chat_id": KANAL_ID, "text": mesaj, "parse_mode": "Markdown"})

    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

# --- DETAYLARI ÇEKME (ESNEK MOD) ---
def detaylari_getir(driver, link):
    print(f"🕵️‍♂️ Detaylara gidiliyor: {link}")
    driver.get(link)
    
    # Bekleme süresini azalttık, takılmasın
    wait = WebDriverWait(driver, 10)
    
    # Varsayılan Değerler (Hata olursa bunlar gidecek)
    logo_url = "https://bykt.org/favicon.ico"
    sebep_metni = "Detaylı bilgi için butona tıklayınız."
    durum_emoji = "❓"
    durum_metni = "Belirtilmemiş"

    try:
        # 1. LOGO (Daha genel arama)
        try:
            # Önce spesifik ara, bulamazsan genel 'img' ara
            logo_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.object-contain")))
            src = logo_element.get_attribute("src")
            if src and "svg" not in src: # SVG hatalarını engelle
                logo_url = src
        except:
            print("⚠️ Logo bulunamadı, varsayılan kullanılacak.")

        # 2. AÇIKLAMA
        try:
            # Sayfadaki uzun paragrafları bul
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            for p in paragraphs:
                text = p.text.strip()
                # 50 karakterden uzun ilk paragrafı açıklama olarak al
                if len(text) > 50:
                    sebep_metni = text[:600] + "..."
                    break
        except:
            pass

        # 3. DURUM (Sayfa kaynağında metin arama - En garantisi)
        try:
            page_source = driver.page_source
            if "Kesin Boykot" in page_source:
                durum_emoji = "🔴"
                durum_metni = "KESİN BOYKOT"
            elif "İnsafa Bağlı" in page_source:
                durum_emoji = "🟠"
                durum_metni = "İNSAFA BAĞLI"
            elif "Alınabilir" in page_source:
                durum_emoji = "🟢"
                durum_metni = "ALINABİLİR"
        except:
            pass

    except Exception as e:
        print(f"⚠️ Detay çekilirken önemsiz bir hata oldu: {e}")

    return logo_url, sebep_metni, durum_emoji, durum_metni

def hatirlat():
    print("🌍 Hatırlatıcı Başlıyor...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080") # Ekran boyutu hatayı çözebilir
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = None

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(URL)
        
        # Sayfanın yüklenmesi için kesin bekleme
        time.sleep(5) 
        
        # Linkleri topla
        # CSS Selector yerine XPath kullanıyoruz (Daha sağlam)
        link_elementleri = driver.find_elements(By.XPATH, "//a[contains(@href, '?marka=')]")
        
        site_listesi = []
        for eleman in link_elementleri:
            try:
                link = eleman.get_attribute("href")
                # Linkin içindeki herhangi bir H3 başlığını al
                ad = eleman.find_element(By.TAG_NAME, "h3").text.strip()
                if ad and link:
                    site_listesi.append((ad, link))
            except:
                continue

        print(f"✅ Toplam {len(site_listesi)} marka bulundu.")
        
        if not site_listesi:
            print("❌ HATA: Siteden marka çekilemedi!")
            return

        # --- SIRA KİMDE? ---
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

        # Detayları çek
        logo, sebep, durum_ikon, durum_yazi = detaylari_getir(driver, marka_linki)

        # Mesajı hazırla
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

        # Kaydet
        mod = "w" if sifirlama_yapildi else "a"
        with open(HAFIZA_DOSYASI, mod, encoding="utf-8") as f:
            f.write(marka_adi + "\n")

    except Exception as e:
        print("❌ KRİTİK HATA:")
        traceback.print_exc() # Hatanın tam yerini gösterir
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    hatirlat()