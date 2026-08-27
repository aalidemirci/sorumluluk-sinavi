# 0004 — Şema göçlerle ilerler, veri ayrı klasörde

**Durum:** Kabul — 27.08.2026

## Bağlam

Uygulamanın önceki bir sürümü `…\SorumlulukSinavi\veri` altına uyumsuz
şemalı bir veritabanı bırakmıştı. Kurulu uygulamanın üzerine yeni sürüm
gelince şema çakıştı.

## Karar

Şema `veri/gocler/NNN_*.sql` dosyalarıyla ilerler; uygulanan göç numarası
`PRAGMA user_version` ile izlenir. Mevcut göç dosyaları değiştirilmez,
yenisi eklenir. Yeni şema ayrı klasörde durur: `…\SorumlulukSinavi\plan`.

## Gerekçe

Ayrı klasör, eski dosyaya hiç dokunmadan yan yana durmayı sağlar; kullanıcı
eski veriyi kaybetmez. Göç dosyalarının değiştirilmemesi, farklı sürümlerin
aynı numaradan farklı şema üretmesini engeller.

## Sonuçlar

- Şema değişikliği her zaman yeni bir göç dosyasıdır.
- Göç öncesi otomatik yedek alınır; yedek WAL içeriğini de kapsar.
- Bir göç ölü şemayı sökebilir, sonraki göç geri getirebilir (006 ve 007
  böyle oldu); kayıt tutulduğu sürece bu sorun değildir.
