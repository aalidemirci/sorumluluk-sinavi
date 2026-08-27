# 0008 — Kurulum kullanıcı başınadır

**Durum:** Kabul — 27.08.2026

## Bağlam

Okul bilgisayarlarında yönetici hakkı çoğu zaman yoktur ya da uygulamayı
kullanacak kişinin hesabında bulunmaz.

## Karar

Kurulum kullanıcı başınadır: yönetici hakkı istemez, `Program Files` altına
yazmaz. Varsayılan yer `%LOCALAPPDATA%\SorumlulukSinavi\uygulama`.

## Gerekçe

Yönetici hakkı isteyen bir kurulum, uygulamayı asıl kullanacak kişinin
kuramadığı bir uygulama hâline gelir.

## Sonuçlar

- Kullanıcı verisi kurulum klasöründe değil, ayrı bir veri klasöründedir;
  kaldırma ve yükseltme veritabanına dokunmaz.
- Uygulama aynı makinede birden çok kullanıcı için kurulacaksa her kullanıcı
  kendi kurulumunu yapar ve kendi verisini tutar.
