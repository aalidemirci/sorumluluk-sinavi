# Plan

Bu dosya **açık işleri** tutar: yapılacaklar, bilinen borçlar ve takvime
bağlı zorunluluklar. Yapılıp bitenler buradan silinir, CHANGELOG.md'ye
geçer. Kapsam dışı olduğuna karar verilmiş şeyler en altta durur ki
tekrar tekrar tartışılmasın.

Son gözden geçirme: 28.08.2026 (sürüm 0.4.0).

## Şimdi

- [ ] **Kurulu 0.3.0 paketlerini güncelle.** 0.3.0 numarasıyla iki farklı
      paket derlendi (aradaki farkta başvuru kapısı var), yani o numara
      hangi içeriği taşıdığını söylemiyor. Kurulu olduğu her yer 0.4.0 ile
      güncellensin. Yapım klasöründeki kopya 28.08.2026'da silindi.
- [ ] **Etiketleri uzağa gönder.** `v0.4.0` yerelde atıldı; `git push --tags`
      henüz yapılmadı.

## Takvime bağlı

- [ ] **2027-2028 öğretim yılı öncesi:** `cekirdek/kurallar.py` içindeki
      `SINIRSIZ_OGRETIM_YILLARI` sabiti güncellenmeli. 8. Dönem Toplu
      Sözleşme md.4 gereği 12/15 görev sınırları 2025-2026 ve 2026-2027'de
      uygulanmıyor; yeni toplu sözleşme çıkınca bu liste gözden geçirilecek.

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

## Kapsam dışı

Bunlar bilinçli olarak yapılmıyor. Yeniden gündeme gelirse karar kaydı
yazılarak gelsin.

- Sınav sonrası işlemler: sonuç ve puan girişi, itiraz, telafi, ek sınav,
  diploma tarihi, disiplin. Bunlar e-Okul'da yürütülür.
- Ek ders ücreti hesabı. Uygulama yalnız Karar md.12/2-a'daki 12 komisyon /
  15 gözcülük sınırı için görev sayacı tutar; tutar hesabı MYS'de yapılır.
- Ağ, bulut, telemetri, çevrimiçi güncelleme (bkz.
  `kararlar/0001-cevrimdisi-ve-yerel-veri.md`).
