# 🎭 Tiyatro Günlüğü - Veri Deposu

İstanbul tiyatro oyunları ve gösterim bilgilerini toplayan otomatik veri sistemi.

## 📊 Veri Kaynakları

| Kaynak | Durum |
|--------|-------|
| İBB Şehir Tiyatroları | ✅ Aktif |
| Biletinial | ✅ Aktif |

## 🔄 Otomatik Güncelleme

GitHub Actions ile her gün **saat 09:00 (TR)** otomatik güncellenir.

## 🔒 Veri Modeli (Stabil)

`data/plays.json` dosyası aşağıdaki alanları garanti eder.
Alan adları **geriye dönük uyumluluk korunarak** değiştirilir.

Detaylı şema: `data/schema.json`

## 📥 Veri Kullanımı (iOS App için)
```
https://raw.githubusercontent.com/ozgeozler93/tiyatrodata/main/data/plays.json
```

## 🛠 Lokal Çalıştırma
```bash
pip install -r requirements.txt
cd scraper
python main.py
```

## 📱 İlgili Proje

- [tiyatro-gunlugu-app](https://github.com/ozgeozler93/tiyatro-gunlugu-app)


<!-- trigger -->
