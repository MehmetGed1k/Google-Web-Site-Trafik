import os
import random
import asyncio
from playwright.async_api import async_playwright
import re
import difflib

# Proxy ve site dosyalarının dizin yolları
OUTPUT_DIR = r"C:\\Users\\alone\\Desktop\\proxler"
proxies_file = os.path.join(OUTPUT_DIR, "sifresizsock.txt")
sites_file = os.path.join(OUTPUT_DIR, "sites.txt")
keywords_file = os.path.join(OUTPUT_DIR, "aranacakkelime.txt")

# User-Agent listesi
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.64 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

# Dosyadan veri okuma fonksiyonu
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]

# Sayfa kaynak kodundan IP adresini al
async def get_ip_address(page):
    try:
        # Sayfanın HTML içeriğini al
        content = await page.content()
        
        # IP adresini bulmak için regex kullan
        match = re.search(r'<h2 class="text-center"><strong class="mycurrentip" id="mycurrentip" style="opacity: 1;">(.*?)</strong>', content)
        if match:
            ip_address = match.group(1)
            print(f"📡 Proxy'nin IP adresi: {ip_address}")
            return ip_address
        else:
            print("❌ IP adresi bulunamadı.")
            return None
    except Exception as e:
        print(f"❌ IP adresi alınırken hata oluştu: {e}")
        return None

# Google'da arama ve en yakın sonucu bulma fonksiyonu
async def google_search_and_visit(page, keyword, site):
    clean_site = site.replace("https://", "").replace("http://", "").rstrip("/")
    search_query = f"site:{clean_site} \"{keyword}\""
    
    url = f"https://www.google.com/search?q={search_query}"
    
    for _ in range(3):  # Maksimum 3 kez dene
        try:
            print(f"🔍 Google'da arama yapılıyor: {search_query}")
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("load")
            
            # Arama kutusunun görünür olmasını bekleyelim
            await page.wait_for_selector('input[name="q"]', timeout=5000)  # Arama kutusunun görünüp görünmediğine bak
            search_input = await page.query_selector('input[name="q"]')
            if search_input:
                await search_input.fill(search_query)  # Hızlıca doldur
                await search_input.press('Enter')  # Arama yap
                await page.wait_for_load_state('load')  # Arama sonuçlarının yüklenmesini bekle
                break  # Başarıyla arama yapılırsa döngüden çık
        except Exception as e:
            print(f"❌ Google'a erişirken hata oluştu: {e}")
            await asyncio.sleep(5)  # 5 saniye bekleyip tekrar dene

    # Arama sonuçlarını al
    results = await page.query_selector_all("div.tF2Cxc")
    if not results:
        print("❌ Arama sonucu bulunamadı.")
        return False

    # En iyi eşleşen sonucu bulmak için metin benzerliği kontrolü yapalım
    best_match = await find_best_match(keyword, results)
    
    if best_match:
        print(f"🌍 Ziyaret edilecek site: {best_match}")
        try:
            await page.goto(best_match, timeout=60000)
            await page.wait_for_load_state("load")
            print(f"✅ Site başarıyla ziyaret edildi: {best_match}")
            
            # Sayfada belirli bir süre bekleyin
            wait_time = random.randint(30, 90)
            print(f"⏳ Sayfada bekleniyor: {wait_time} saniye...")
            await asyncio.sleep(wait_time)
            return True
        except Exception as e:
            print(f"❌ Siteye erişirken hata oluştu: {e}")
    
    return False

# Metin benzerliği ile en iyi sonucu bulma
async def find_best_match(keyword, results):
    best_match = None
    highest_score = 0
    
    # İlk 5 sonucu kontrol et
    for result in results[:5]:
        link_element = await result.query_selector("a")
        best_match = await link_element.get_attribute("href") if link_element else None
        if best_match:
            # Burada, sonuçların metin içeriği ile keyword'ü karşılaştırabiliriz
            result_text = await result.inner_text()  # Sonuç metnini al
            similarity_score = difflib.SequenceMatcher(None, keyword, result_text).ratio()
            if similarity_score > highest_score:
                highest_score = similarity_score
                best_match = best_match

    return best_match

# Web sitesine bağlanmayı deneyin
async def visit_site_with_proxy(browser, page, site, proxy_ip, proxy_port):
    try:
        # Proxy'yi doğru şekilde ayarla
        proxy = {
            "server": f"socks5://{proxy_ip}:{proxy_port}"
        }

        # Proxy ayarı ile yeni bir context oluştur
        context = await browser.new_context(proxy=proxy)
        page = await context.new_page()

        # Siteyi aç
        print(f"🔗 {site} adresine bağlanılıyor... Proxy: {proxy_ip}:{proxy_port}")
        await page.goto(site, timeout=60000)
        await page.wait_for_load_state("load")

        # IP adresini al
        ip_address = await get_ip_address(page)
        if ip_address:
            print(f"✅ IP adresi alındı: {ip_address}")
        else:
            print("❌ IP adresi alınamadı.")

        # **10 saniye bekle**
        await asyncio.sleep(10)

        return page  # Burada page döndürülüyor
    except Exception as e:
        print(f"❌ Proxy {proxy_ip}:{proxy_port} ile bağlantı hatası: {e}")
        return None

# Proxy ve site gezintisi
async def visit_sites_with_proxies():
    proxies = read_file(proxies_file)
    sites = read_file(sites_file)
    keywords = read_file(keywords_file)

    async with async_playwright() as p:
        # Tarayıcıyı başlat
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])

        for proxy in proxies:
            proxy_ip, proxy_port = proxy.split(":")
            print(f"\n🔄 Yeni proxy kullanılıyor: {proxy}")

            # Proxy ayarlarıyla yeni bir context oluştur
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={'width': random.randint(1024, 1920), 'height': random.randint(768, 1080)},
                locale='en-US'
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # İlk olarak ip-adresim.net adresine bağlan
            ip_site = "https://ip-adresim.net/"
            print(f"🔗 IP adresini almak için {ip_site} adresine bağlanılıyor...")
            page = await visit_site_with_proxy(browser, context.new_page(), ip_site, proxy_ip, proxy_port)

            # IP adresi alındıysa, kelimeler üzerinde arama yap
            if page:
                for site in sites:
                    print(f"🔍 Site üzerinde arama yapılacak: {site}")
                    for keyword in keywords:
                        print(f"🔍 Kelime arama: {keyword}")
                        await google_search_and_visit(page, keyword, site)

            # Başarı mesajı
            print(f"✅ {proxy} ile tüm işlemler başarıyla tamamlandı!")

            # Sayfayı kapat
            await page.close()

        # Tarayıcıyı kapat
        await browser.close()

# Ana fonksiyonu çalıştır
asyncio.run(visit_sites_with_proxies())
