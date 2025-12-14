"""
Tiyatro Günlüğü - Ana Scraper
Tüm kaynaklardan veri çekip birleştirir.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path

from sehir_tiyatrolari import scrape_all as scrape_sehir_tiyatrolari
from biletinial import scrape_istanbul_theater as scrape_biletinial


def generate_id(title: str, source: str) -> str:
    """Oyun için benzersiz ID oluşturur."""
    unique_string = f"{title.lower().strip()}_{source}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]


def normalize_play(play: dict, source: str) -> dict:
    """Oyun verisini standart formata dönüştürür."""
    normalized = {
        'id': generate_id(play.get('title', ''), source),
        'title': play.get('title', '').strip(),
        'category': play.get('category', 'Yetişkin'),
        'image_url': play.get('image_url', ''),
        'detail_url': play.get('detail_url', ''),
        'summary': play.get('summary', ''),
        'crew': play.get('crew', {}),
        'duration': play.get('duration'),
        'act_count': play.get('act_count'),
        'dates_and_locations': play.get('dates_and_locations', []),
        'venue': play.get('venue', ''),
        'source': source,
        'scraped_at': play.get('scraped_at', datetime.now().isoformat()),
    }
    
    normalized = {k: v for k, v in normalized.items() if v is not None and v != '' and v != {} and v != []}
    
    return normalized


def merge_plays(all_plays: list) -> list:
    """Farklı kaynaklardan gelen oyunları birleştirir."""
    seen_titles = {}
    merged = []
    
    for play in all_plays:
        title_key = play.get('title', '').lower().strip()
        
        if not title_key:
            continue
        
        if title_key in seen_titles:
            existing = seen_titles[title_key]
            
            existing_dates = existing.get('dates_and_locations', [])
            new_dates = play.get('dates_and_locations', [])
            
            all_dates = existing_dates + new_dates
            unique_dates = []
            seen_date_keys = set()
            
            for d in all_dates:
                date_key = f"{d.get('date', '')}_{d.get('location', '')}"
                if date_key not in seen_date_keys:
                    seen_date_keys.add(date_key)
                    unique_dates.append(d)
            
            existing['dates_and_locations'] = unique_dates
            
            if not existing.get('summary') and play.get('summary'):
                existing['summary'] = play['summary']
            if not existing.get('image_url') and play.get('image_url'):
                existing['image_url'] = play['image_url']
            if not existing.get('crew') and play.get('crew'):
                existing['crew'] = play['crew']
                
        else:
            seen_titles[title_key] = play
            merged.append(play)
    
    return merged


def sort_plays(plays: list) -> list:
    """Oyunları sıralar: önce gösterimi olanlar."""
    def sort_key(play):
        has_dates = bool(play.get('dates_and_locations'))
        title = play.get('title', '').lower()
        return (not has_dates, title)
    
    return sorted(plays, key=sort_key)


def generate_stats(plays: list) -> dict:
    """Veri istatistiklerini oluşturur."""
    stats = {
        'total_plays': len(plays),
        'plays_with_showtimes': sum(1 for p in plays if p.get('dates_and_locations')),
        'plays_without_showtimes': sum(1 for p in plays if not p.get('dates_and_locations')),
        'categories': {},
        'sources': {},
        'last_updated': datetime.now().isoformat(),
    }
    
    for play in plays:
        cat = play.get('category', 'Bilinmeyen')
        stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
        
        src = play.get('source', 'bilinmeyen')
        stats['sources'][src] = stats['sources'].get(src, 0) + 1
    
    return stats


def main():
    """Ana scraping işlemi."""
    print("=" * 60)
    print("🎭 TİYATRO GÜNLÜĞÜ - VERİ GÜNCELLEME")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_plays = []
    
    # 1. Şehir Tiyatroları
    print("\n📍 Kaynak 1: İBB Şehir Tiyatroları")
    print("-" * 40)
    try:
        sehir_plays = scrape_sehir_tiyatrolari()
        normalized = [normalize_play(p, 'sehir_tiyatrolari') for p in sehir_plays]
        all_plays.extend(normalized)
        print(f"✅ {len(normalized)} oyun eklendi")
    except Exception as e:
        print(f"❌ Şehir Tiyatroları hatası: {e}")
    
    # 2. Biletinial
    print("\n📍 Kaynak 2: Biletinial")
    print("-" * 40)
    try:
        biletinial_plays = scrape_biletinial()
        normalized = [normalize_play(p, 'biletinial') for p in biletinial_plays]
        all_plays.extend(normalized)
        print(f"✅ {len(normalized)} etkinlik eklendi")
    except Exception as e:
        print(f"❌ Biletinial hatası: {e}")
    
    # Birleştir ve sırala
    print("\n🔄 Veriler birleştiriliyor...")
    merged_plays = merge_plays(all_plays)
    sorted_plays = sort_plays(merged_plays)
    
    stats = generate_stats(sorted_plays)
    
    # Kaydet
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / 'plays.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_plays, f, ensure_ascii=False, indent=2)
    print(f"\n💾 {output_file} kaydedildi")
    
    stats_file = output_dir / 'stats.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"📊 {stats_file} kaydedildi")
    
    # Özet
    print("\n" + "=" * 60)
    print("📊 ÖZET")
    print("=" * 60)
    print(f"  Toplam oyun: {stats['total_plays']}")
    print(f"  Gösterimi olan: {stats['plays_with_showtimes']}")
    print(f"  Gösterimi olmayan: {stats['plays_without_showtimes']}")
    print("=" * 60)


if __name__ == "__main__":
    main()