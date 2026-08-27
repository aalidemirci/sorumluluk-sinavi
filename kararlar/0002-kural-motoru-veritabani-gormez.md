# 0002 — Kural motoru veritabanı görmez

**Durum:** Kabul — 26.08.2026

## Bağlam

Planlama kuralları mevzuattan gelir ve sayıca çoktur (ilk sürümde 16). Her
biri olumsuz senaryosuyla test edilmelidir. Kurallar doğrudan veritabanından
okusaydı her kural testi bir şema, bir göç ve örnek kayıt kurulumu isterdi.

## Karar

`cekirdek/` katmanı `veri/`yi içe aktarmaz. Kuralların ihtiyaç duyduğu bilgi
`DogrulamaBaglami` gibi taşıyıcı nesnelerle dışarıdan verilir. Bağımlılık
yönü tek yönlüdür: `arayuz` → `veri` → `cekirdek`.

## Gerekçe

Kurallar saf işlev hâline gelince test etmek ucuzlar; ucuz test, her kuralın
olumsuz senaryosunun da yazılmasını mümkün kılar. Mevzuat değiştiğinde
değişen yer tek ve dar olur.

## Sonuçlar

- Yeni bir kural veritabanından bilgi istiyorsa o bilgi önce bağlama
  eklenir; kural doğrudan sorgu yazmaz.
- Elle düzenlenen planlar da aynı kapıdan geçmelidir; motorun ürettiği plan
  ile kullanıcının değiştirdiği plan aynı doğrulayıcıyı kullanır.
