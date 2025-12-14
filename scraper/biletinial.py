"""
Biletinial Web Scraper
Biletinial sitesinden tiyatro oyunlarını çeker.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import time

BASE_URL = "https://biletinial.com"
THEATER_URL = f"{BASE_URL}/tr-tr/tiyatro"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
}


def get_soup(url: str) -> BeautifulSoup:
    """URL'den BeautifulSoup objesi döndürür."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'lxml')
    except requests.RequestException as e:
        print(f"❌ Hata: {url} - {e}")
        return None


def get_theater_events(city: str = "istanbul") -> list:
    """Belirli bir şehirdeki tiyatro etkinliklerini çeker."""
    events = []
    page = 1
    max_pages = 10
    
    while page <= max_pages:
        url = f"{THEATER_URL}?city={city}&page={page}"
        print(f"📄 Sayfa {page} çekiliyor...")
        
        soup = get_soup(url)
        if not soup:
            break
        
        event_cards = soup.select('.event-card, .card, [class*="etkinlik"], [data-event]')
        
        if not event_cards:
            event_cards = soup.select('a[href*="/tiyatro/"], a[href*="/etkinlik/"]')
        
        if not event_cards:
            print(f"⚠️ Sayfa {page}'de etkinlik bulunamadı, durduruluyor")
            break
        
        print(f"  → {len(event_cards)} etkinlik bulundu")
        
        for card in event_cards:
            try:
                event = parse_event_card(card)
                if event and event.get('title'):
                    events.append(event)
            except Exception as e:
                print(f"⚠️ Kart işlenirken hata: {e}")
                continue
        
        page += 1
        time.sleep(1)
    
    return events


def parse_event_card(card) -> dict:
    """Etkinlik kartından bilgi çıkarır."""
    event = {}
    
    link = card.get('href') if card.name == 'a' else None
    if not link:
        link_elem = card.select_one('a')
        link = link_elem.get('href') if link_elem else None
    
    if link and not link.startswith('http'):
        link = BASE_URL + link
    
    event['detail_url'] = link
    event['source'] = 'biletinial'
    
    event['title'] = ""
    
    img = card.select_one('img')
    if img:
        img_url = img.get('src') or img.get('data-src') or img.get('data-lazy')
        if img_url and not img_url.startswith('http'):
            img_url = BASE_URL + img_url
        event['image_url'] = img_url
    
    date = card.select_one('.date, [class*="tarih"], [class*="date"]')
    if date:
        event['next_date'] = date.get_text(strip=True)
    
    venue = card.select_one('.venue, .location, [class*="mekan"], [class*="venue"]')
    if venue:
        event['venue'] = venue.get_text(strip=True)
    
    price = card.select_one('.price, [class*="fiyat"], [class*="price"]')
    if price:
        event['price'] = price.get_text(strip=True)
    
    category = card.select_one('.category, .genre, [class*="tur"], [class*="kategori"]')
    if category:
        event['category'] = category.get_text(strip=True)
    
    return event


def get_event_details(event_url: str) -> dict:
    """Tek bir etkinliğin detaylarını çeker."""
    soup = get_soup(event_url)
    if not soup:
        return None
    
    details = {
        'detail_url': event_url,
        'source': 'biletinial',
        'scraped_at': datetime.now().isoformat()
    }
    
    try:
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            details["title"] = meta_title["content"].replace(" - Tiyatro", "").strip()
        else:
            h1 = soup.select_one("h1")
            details["title"] = h1.get_text(strip=True) if h1 else ""
        
        img = soup.select_one('.event-image img, .poster img, [class*="gorsel"] img')
        if img:
            img_url = img.get('src') or img.get('data-src')
            if img_url and not img_url.startswith('http'):
                img_url = BASE_URL + img_url
            details['image_url'] = img_url
        
        desc = soup.select_one('.description, .content, [class*="aciklama"]')
        details['summary'] = desc.get_text(strip=True)[:500] if desc else ""
        
        genre = soup.select_one('.genre, .type, [class*="tur"]')
        details['category'] = genre.get_text(strip=True) if genre else "Tiyatro"
        
        duration = soup.select_one('[class*="sure"], .duration')
        if duration:
            details['duration'] = duration.get_text(strip=True)
        
        details['dates_and_locations'] = parse_biletinial_showtimes(soup)
        
        venue = soup.select_one('.venue-name, [class*="mekan"]')
        if venue:
            details['venue'] = venue.get_text(strip=True)
        
    except Exception as e:
        print(f"⚠️ Detay işlenirken hata: {event_url} - {e}")

    
    
    return details


def parse_biletinial_showtimes(soup: BeautifulSoup) -> list:
    """Biletinial'den gösterim tarihlerini parse eder."""
    showtimes = []
    
    session_cards = soup.select('.session, .showtime, [class*="seans"], [class*="tarih"]')
    
    for card in session_cards:
        try:
            date_elem = card.select_one('.date, [class*="gun"], [class*="tarih"]')
            time_elem = card.select_one('.time, [class*="saat"]')
            venue_elem = card.select_one('.venue, [class*="mekan"], [class*="salon"]')
            
            date_str = ""
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            if time_elem:
                date_str += f" {time_elem.get_text(strip=True)}"
            
            if date_str:
                showtime = {
                    'date': date_str.strip(),
                    'location': venue_elem.get_text(strip=True) if venue_elem else ""
                }
                showtimes.append(showtime)
                
        except Exception:
            continue
    
    return showtimes


def scrape_istanbul_theater() -> list:
    """İstanbul'daki tüm tiyatro etkinliklerini çeker."""
    print("🎭 Biletinial İstanbul tiyatro etkinlikleri çekiliyor...")
    
    events = get_theater_events(city="istanbul")
    print(f"📋 Toplam {len(events)} etkinlik bulundu")
    
    detailed_events = []
    for i, event in enumerate(events, 1):
        if not event.get('detail_url'):
            continue
            
        print(f"🔍 [{i}/{len(events)}] {event.get('title', 'Bilinmeyen')}...")
        
        details = get_event_details(event['detail_url'])
        if details:
            for k, v in event.items():
                if k == "title":
                    continue  # title sadece detaydan gelsin
                if k not in details or not details[k]:
                    details[k] = v
            detailed_events.append(details)
        
        time.sleep(1)
    
    print(f"✅ {len(detailed_events)} etkinlik detayı başarıyla çekildi")
    return detailed_events


if __name__ == "__main__":
    import os

    OUTPUT_PATH = "data/plays.json"
    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"💾 {OUTPUT_PATH} dosyasına kaydedildi")