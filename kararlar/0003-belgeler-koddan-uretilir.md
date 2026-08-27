# 0003 — Belgeler koddan üretilir, şablondan değil

**Durum:** Kabul — 27.08.2026

## Bağlam

Uygulama sekiz resmî belge üretir. Alternatif, hazır `.docx` şablonlarını
doldurmaktı.

## Karar

Belgeler `evrak/belge.py` üzerinden koddan üretilir. Sayfa düzeni tek yerde
tanımlıdır.

## Gerekçe

Şablon dosyası ile kod zamanla birbirinden kopar: şablondaki bir alan
silinir, kod hâlâ doldurmaya çalışır; ya da kod yeni alan yazar, şablonda
yeri yoktur. Düzen kodda olunca bu kopma imkânsızdır ve belge değişikliği
testle korunabilir.

## Sonuçlar

- Belge düzenini değiştirmek kod değişikliğidir; kullanıcı şablon
  düzenleyerek çıktıyı değiştiremez.
- Kuruma özel şablon ihtiyacı doğarsa `sablonlar/ozel/` altında ayrı bir yol
  gerekir; o klasör KVKK gereği yoksayılır.
