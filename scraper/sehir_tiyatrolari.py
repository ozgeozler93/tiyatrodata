"""
Şehir Tiyatroları Web Scraper
İBB Şehir Tiyatroları sitesinden oyun ve gösterim bilgilerini çeker.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import time

BASE_URL = "https://sehirtiyatrolari.ibb.istanbul"

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


def get_all_plays() -> list:
    """Tüm oyunların listesini çeker."""
    plays = []
    url = f"{BASE_URL}/oyunlar"
    
    soup = get_soup(url)
    if not soup:
        return plays
    
    # Oyun kartlarını bul
    play_cards = soup.select('.play-card, .card, [class*="oyun"], [class*="play"]')
    
    if not play_cards:
        play_cards = soup.select('a[href*="/oyun/"]')
    
    print(f"📋 {len(play_cards)} oyun kartı bulundu")
    
    for card in play_cards:
        try:
            link = card.get('href') or card.select_one('a')
            if link and hasattr(link, 'get'):
                link = link.get('href')
            
            if not link or '/oyun/' not in str(link):
                continue
                
            if not link.startswith('http'):
                link = BASE_URL + link
            
            title = card.select_one('.title, .name, h3, h4')
            title = title.get_text(strip=True) if title else link.split('/')[-1].replace('-', ' ').title()
            
            plays.append({
                'title': title,
                'detail_url': link
            })
            
        except Exception as e:
            print(f"⚠️ Kart işlenirken hata: {e}")
            continue
    
    return plays


def get_play_details(play_url: str) -> dict:
    """Tek bir oyunun detaylarını çeker."""
    soup = get_soup(play_url)
    if not soup:
        return None
    
    details = {
        'detail_url': play_url,
        'scraped_at': datetime.now().isoformat()
    }
    
    try:
        title = soup.select_one('h1, .play-title, .title')
        details['title'] = title.get_text(strip=True) if title else ""
        
        img = soup.select_one('.play-image img, .poster img, [class*="image"] img')
        if img:
            img_url = img.get('src') or img.get('data-src')
            if img_url and not img_url.startswith('http'):
                img_url = BASE_URL + img_url
            details['image_url'] = img_url
        
        summary = soup.select_one('.summary, .description, .content p, [class*="ozet"]')
        details['summary'] = summary.get_text(strip=True) if summary else ""
        
        category = soup.select_one('.category, .type, [class*="kategori"]')
        details['category'] = category.get_text(strip=True) if category else "Yetişkin"
        
        duration = soup.select_one('[class*="sure"], [class*="duration"], .duration')
        if duration:
            duration_text = duration.get_text(strip=True)
            details['duration'] = parse_duration(duration_text)
        
        act = soup.select_one('[class*="perde"], [class*="act"]')
        if act:
            act_text = act.get_text(strip=True)
            match = re.search(r'(\d+)', act_text)
            details['act_count'] = match.group(1) if match else "1"
        
        details['crew'] = parse_crew(soup)
        details['dates_and_locations'] = parse_showtimes(soup)
        
    except Exception as e:
        print(f"⚠️ Detay işlenirken hata: {play_url} - {e}")
    
    return details


def parse_duration(duration_text: str) -> str:
    """Süre metnini HH:MM:SS formatına çevirir."""
    if not duration_text:
        return None
    
    hours = 0
    minutes = 0
    
    hour_match = re.search(r'(\d+)\s*saat', duration_text, re.IGNORECASE)
    min_match = re.search(r'(\d+)\s*dakika', duration_text, re.IGNORECASE)
    
    if hour_match:
        hours = int(hour_match.group(1))
    if min_match:
        minutes = int(min_match.group(1))
    
    if hours or minutes:
        return f"{hours:02d}:{minutes:02d}:00"
    
    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', duration_text)
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2))
        s = int(time_match.group(3)) if time_match.group(3) else 0
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    return None


def parse_crew(soup: BeautifulSoup) -> dict:
    """Kadro bilgilerini parse eder."""
    crew = {}
    
    crew_section = soup.select_one('.crew, .cast, [class*="kadro"], [class*="ekip"]')
    
    if crew_section:
        items = crew_section.select('li, p, div')
        for item in items:
            text = item.get_text(strip=True)
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    role = parts[0].strip()
                    name = parts[1].strip()
                    crew[role] = name
    
    if not crew:
        for pattern in ['Yazan', 'Yöneten', 'Çeviren', 'Oyuncular']:
            elem = soup.find(string=re.compile(pattern, re.IGNORECASE))
            if elem:
                parent = elem.find_parent()
                if parent:
                    text = parent.get_text(strip=True)
                    if ':' in text:
                        parts = text.split(':', 1)
                        crew[parts[0].strip()] = parts[1].strip()
    
    return crew


def parse_showtimes(soup: BeautifulSoup) -> list:
    """Gösterim tarihlerini parse eder."""
    showtimes = []
    
    showtime_cards = soup.select('.showtime, .session, .seans, [class*="gosterim"], [class*="tarih"]')
    
    for card in showtime_cards:
        try:
            date_elem = card.select_one('.date, [class*="tarih"]')
            location_elem = card.select_one('.venue, .location, .theater, [class*="sahne"], [class*="mekan"]')
            
            if date_elem:
                showtime = {
                    'date': date_elem.get_text(strip=True),
                    'location': location_elem.get_text(strip=True) if location_elem else ""
                }
                showtimes.append(showtime)
        except Exception:
            continue
    
    if not showtimes:
        ticket_buttons = soup.select('a[href*="bilet"], .ticket-btn, [class*="bilet"]')
        for btn in ticket_buttons:
            parent = btn.find_parent('div') or btn.find_parent('li')
            if parent:
                text = parent.get_text(strip=True)
                date_match = re.search(r'(\d{1,2}\s+\w+\s+\w+,?\s*\d{2}:\d{2})', text)
                if date_match:
                    showtimes.append({
                        'date': date_match.group(1),
                        'location': text.replace(date_match.group(1), '').strip()
                    })
    
    return showtimes


def scrape_all() -> list:
    """Tüm oyunları ve detaylarını çeker."""
    print("🎭 Şehir Tiyatroları scraping başlıyor...")
    
    plays = get_all_plays()
    print(f"📋 Toplam {len(plays)} oyun bulundu")
    
    detailed_plays = []
    for i, play in enumerate(plays, 1):
        print(f"🔍 [{i}/{len(plays)}] {play.get('title', 'Bilinmeyen')}...")
        
        details = get_play_details(play['detail_url'])
        if details:
            detailed_plays.append(details)
        
        time.sleep(1)
    
    print(f"✅ {len(detailed_plays)} oyun detayı başarıyla çekildi")
    return detailed_plays


if __name__ == "__main__":
    plays = scrape_all()
    
    with open('sehir_tiyatrolari.json', 'w', encoding='utf-8') as f:
        json.dump(plays, f, ensure_ascii=False, indent=2)
    
    print(f"💾 sehir_tiyatrolari.json dosyasına kaydedildi")