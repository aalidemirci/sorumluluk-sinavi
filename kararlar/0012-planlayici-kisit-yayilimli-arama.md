# 0012 — Planlayıcı kısıt yayılımıyla arar, bütçesi düğümle tutulur

**Durum:** Kabul — 03.10.2026

## Bağlam

Yerleştirme araması birimleri sabit bir zorluk sırasıyla deniyor ve kör geri
izliyordu: bir birim hiçbir yere sığmadığında yalnız bir önceki birimi
oynatıyordu. Uydurma ama gerçekçi ölçekte okullarla (≈850 kayıt, ≈270
öğrenci, 10–15 ders, ağır yüklü birkaç öğrenci) yapılan denemede bu arama
denemelerin bir kısmında on dakikalık bütçeyle bile plan bulamadı.

Bütçe ayrıca süreyle tutuluyordu (gün sayısı denemesi başına 2 saniye). Aynı
girdi hızlı makinede bir gün sayısında çözülürken yavaş okul bilgisayarında
bütçe dolup bir sonraki gün sayısına geçiliyor, "aynı girdi aynı programı
üretir" sözü makineye göre bozuluyordu.

## Karar

Arama her birimin hâlâ konabileceği (gün, slot) kümesini tutar; her adımda
kümesi en dar birimi yerleştirir (eşitlikte eski statik zorluk sırası) ve
bir yerleştirmeden sonra yalnız o günün yerlerini yeniden denetler — öğrenci
çakışması, günlük yük ve slot kapasitesi hep aynı güne aittir. Kümesi boşalan
birim olursa dal hemen kesilir.

Bütçe düğüm sayısıyla tutulur: ara gün sayılarında 6 000, kullanıcının
istediği tek gün sayısında, hafta içinin son gün sayısında (sığmazsa hafta
sonuna taşınır) ve pencerenin son gün sayısında 40 000. Süre yalnız 60
saniyelik güvenlik sınırıdır.

Öğretmen müsaitliği (SP-09) ızgaraya (gün, slot) başına görevli ve branş arzı
olarak girer.

## Gerekçe

Ölçümde başarılı denemeler çoğunlukla 250, en çok 3 000 düğümde bitti;
sığmayan gün sayısını kanıtlamak ise bütçeyi tüketir. Bu yüzden ara
denemelere küçük, geri çekilecek yeri olmayan denemelere geniş bütçe verilir.
Eski aramanın çözemediği test okullarını yeni arama 0,05–3 saniyede çözdü;
bunlar `test_gercekci_olcekte_plan_uretilir` ile korunur.

Elenen seçenek: açgözlü klik alt sınırıyla imkânsız gün sayılarını önceden
elemek. Denemelerde sınır gerçek gereğin çok altında kaldı, kazanç getirmedi.

## Sonuçlar

- Aynı girdi her makinede aynı planı üretir (60 saniyelik güvenlik sınırına
  takılan aşırı durumlar dışında).
- Sığmayan gün sayılarını denemek yavaş makinede birkaç saniye sürebilir.
