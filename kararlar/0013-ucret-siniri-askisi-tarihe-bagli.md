# 0013 — Ücret sınırı askısı görev tarihine bağlıdır

**Durum:** Kabul — 03.10.2026

## Bağlam

Karar md.12/2-a (2006/11350): "Bir öğretim yılında bir kişiye 12'den fazla
sınav komisyon üyeliği ve 15'ten fazla sınav gözcülüğü görevleri … için ücret
ödenmez." 8. Dönem Toplu Sözleşme, Eğitim, Öğretim ve Bilim Hizmet Kolu md.4
(RG 27.08.2025/32999) bu sınırların uygulanmayacağını söyler; hüküm
01.01.2026 – 31.12.2027 arasında uygulanır. Aynı hüküm harfi harfine 7. Dönem
Toplu Sözleşmede de vardır (RG 03.09.2023/32298, aynı hizmet kolu md.4;
01.01.2024 – 31.12.2025). Hizmet kolu hükümleri Hakem Kurulu kararı değil
Çalışma ve Sosyal Güvenlik Bakanlığı tebliği olarak yayımlanır.

Program askıyı öğretim yılına bağlamıştı (`SINIRSIZ_OGRETIM_YILLARI =
{"2025-2026", "2026-2027"}`). Toplu sözleşme takvim yılına bağlıdır: Eylül
2027 sınavları hâlâ askıdayken 2027-2028 yılı "sınırlı" sayılıyordu. Ayrıca
kural motoru yıllık sınırı yalnız tek planın görevleriyle sınıyordu.

## Karar

Askı tarih aralığıdır (`cekirdek.kurallar.SINIR_ASKILARI`). Bir kişinin
öğretim yılındaki bütün görevleri tarih sırasıyla sayılır; askı dışındaki bir
görevin yıl içi sırası sınırı aşıyorsa o görev ücretlendirilemez sayılır.
Askıdaki görevler sayaca girer ama kendileri sınıra takılmaz. Doğrulayıcı
diğer dönemlerin görevlerini `DogrulamaBaglami.onceki_gorevler` ile alır.

## Gerekçe

İki hüküm birlikte okunduğunda sınırın ölçüsü öğretim yılıdır, askının
ölçüsü görev tarihidir. Askı bittikten sonraki bir görevin "yılın kaçıncı
görevi" olduğu sorusuna mevzuat ayrıca cevap vermez; program yıl içindeki
bütün görevleri saymayı seçer. Bu programın yorumudur ve yardım metninde
böyle yazar. Kural uyarı düzeyindedir, planı engellemez; tutar hesabı
yapılmaz.

## Sonuçlar

- 9. Dönem Toplu Sözleşme (Ağustos 2027) yayımlanınca `SINIR_ASKILARI`
  güncellenir (PLAN.md, "Takvime bağlı").
- 7. Dönem hükmünün madde numarası 03.10.2026'da Resmî Gazete'nin taranmış
  sayfasından okunarak teyit edildi ve dayanak metnine yazıldı.
