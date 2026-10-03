# Plan

Bu dosya **açık işleri** tutar: yapılacaklar, bilinen borçlar ve takvime
bağlı zorunluluklar. Yapılıp bitenler buradan silinir, CHANGELOG.md'ye
geçer. Kapsam dışı olduğuna karar verilmiş şeyler en altta durur ki
tekrar tekrar tartışılmasın.

Son gözden geçirme: 03.10.2026 (0.6.2 yayımı; ayrıntılı taramanın sonuçları
CHANGELOG 0.6.0 başlığında).

## Şimdi

- [ ] **Okuldaki makineleri güncelle.** Yordam KURULUM.md → "Kurulu
      makineleri güncelleme" başlığında. 03.10.2026: yayımlanan sürüm 0.6.2;
      okul makineleri bekliyor. 0.6 ilk açılışta veritabanını şema 8'e
      geçirir (öncesinde yedek alır); geçişten sonra tatil günleri girilmeli.
- [ ] **Pardus paketi gerçek bir makinede denenmedi.** Yayımlanan `.deb`'ler
      (0.5.0, 0.6.x) yalnız `debian:12` kabında (GitHub Actions ve yerelde
      Docker) kuruldu ve xvfb altında açıldı. Okulda bir Pardus 23
      makinesinde kurulup menüden açılması, e-Okul raporu içe aktarılması ve
      evrak üretilmesi denenmeli; arayüzün o masaüstündeki yazı tipiyle
      görünüşüne de bakılsın (0.6.0'daki kilit emojisi kapta kare çıkmıştı).
      İlk gerçek deneme sonucu buraya yazılsın.
- [ ] **Tatil günlerini gir.** 2026-2027 için Kurum Ayarları'na resmî tatil
      ve idari izin günleri girilmeli; özellikle sınav pencerelerine düşenler.

## Takvime bağlı

- [ ] **9. Dönem Toplu Sözleşme (Ağustos 2027):** `cekirdek/kurallar.py`
      içindeki `SINIR_ASKILARI` güncellenmeli. 8. Dönem eğitim hizmet kolu
      md.4 gereği 12/15 görev sınırları 01.01.2026 – 31.12.2027 arasındaki
      görevlerde uygulanmıyor; 01.01.2028 sonrası görevler için yeni metne
      bakılacak (bkz. `kararlar/0013`). Aynı metinde yabancı dil yazılı ve
      sözlü komisyon üyeliklerinin ayrı değerlendirilmesi hükmü (7. ve 8.
      Dönemde md.17) de aranmalı; madde numarası ya da hüküm değişirse EK-05
      dayanağı, yardım metni ve görev sayacı raporunun notu güncellenir.

## Bilinen borçlar

- **SG-05 nakil kaynağı — gerçek raporda bakılacak:** OOK12001R010'da
  nakil/geçiş kaynağını gösteren bir sütun olup olmadığı bilinmiyor; elde
  gerçek rapor yok. 03.10.2026'dan beri önizleme, okunan dört sütun dışındaki
  başlıkları "okunmayan sütunlar" olarak gösteriyor: ilk gerçek aktarımda o
  satıra bakın. Böyle bir sütun varsa ayrıştırıcı onu okuyup kaydın kaynağını
  `nakil_gecis` yapmalı (veritabanı alanı hazır); yoksa madde kapsam dışına
  alınır. Program 3/6 sayacını hesaplamadığı için bugün hiçbir sonucu
  etkilemez.

## İzlenen kırılganlıklar

Bunlar bugün sorun değil ama dışarıdan bir değişiklikle sorun hâline
gelebilir. Kırıldıklarında sessizce değil, anlaşılır hatayla kırılmaları
sağlanmıştır.

- **e-Okul rapor biçimi.** OOK01001R1 ve OOK12001R010 raporlarının sütun
  düzeni değişirse ayrıştırıcı güncellenmeli. Ayrıştırıcı sessizce yanlış
  okumaz, hata verir.
- **Kurum sicil numarası sütunu.** Personel raporunda bu sütun yoksa aynı
  adlı iki öğretmen ayırt edilemez; içe aktarma hata vererek durur.
- **Inno Setup sürüm ayrıştırması.** `SURUM = "x.y.z"` satırının biçimi
  betik tarafından metin olarak okunur; `testler/test_surum.py` koruyor
  (bkz. `kararlar/0007-surum-tek-kaynakta.md`).
- **Planlayıcı bütçesi.** Düğüm bütçesi gerçekçi uydurma okullarla ayarlandı
  (`kararlar/0012`); çok daha büyük bir okulda son gün sayısı denemesi
  bütçeye takılırsa plan "üretilemedi" der. Gerçek veriyle süre gözlenmeli.

## Kapsam dışı

Bunlar bilinçli olarak yapılmıyor. Yeniden gündeme gelirse karar kaydı
yazılarak gelsin.

- Sınav sonrası işlemler: sonuç ve puan girişi, itiraz, telafi, diploma
  tarihi, disiplin. Bunlar e-Okul'da yürütülür. (Tek ders sınavının —
  OKY md.58/6 — **planı** 03.10.2026'dan beri kapsamdadır, sonucu yine
  e-Okul'dadır; bkz. `kararlar/0010`.)
- Ek ders ücreti hesabı. Uygulama yalnız Karar md.12/2-a'daki 12 komisyon /
  15 gözcülük sınırı için görev sayacı tutar; tutar hesabı MYS'de yapılır.
- Ağ, bulut, telemetri, çevrimiçi güncelleme (bkz.
  `kararlar/0001-cevrimdisi-ve-yerel-veri.md`).
