# 0006 — Başvuru kapısı oturuma değil pencereye bağlı

**Durum:** Kabul — 28.08.2026

## Bağlam

OKY md.58/2-d, okuldan mezun olamayan 12. sınıf öğrencileri ile devamsızlık
tebligatı yapıldığı hâlde katılımı sağlanamayan öğrencilerin sınava ancak
yazılı başvuruları hâlinde alınmasını ister.

## Karar

Başvuru bilgisi tek tek sınav oturumuna değil, sınav **penceresine**
bağlanır. Kapı tek noktada, `sorumluluk_kayitlari()` içinde uygulanır.

## Gerekçe

Mevzuat başvuruyu plandan önce ister: duyuru → başvuru toplama → plan →
takvim ilanı. Başvuruyu oturuma bağlamak bu sırayı tersine çevirir, çünkü
oturum ancak plan üretildikten sonra vardır. Kapının tek noktada olması,
planlayıcı zincirinin tamamının aynı süzgeçten beslenmesini sağlar.

## Sonuçlar

- Elle yapılan plan düzenlemeleri SP-07 doğrulayıcıda ayrıca denetlenir;
  motorun ürettiği plan da elle değiştirilen plan da aynı kapıdan geçer.
- Kural motoru veritabanı görmediği için başvuru bilgisi
  `DogrulamaBaglami` üzerinden verilir (bkz. 0002).
- İki yeni belge doğar: başvuru duyurusu ve plan dışı tutanağı.
