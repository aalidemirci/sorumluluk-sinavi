# Plan

Bu dosya **açık işleri** tutar: yapılacaklar, bilinen borçlar ve takvime
bağlı zorunluluklar. Yapılıp bitenler buradan silinir, CHANGELOG.md'ye
geçer. Kapsam dışı olduğuna karar verilmiş şeyler en altta durur ki
tekrar tekrar tartışılmasın.

Son gözden geçirme: 04.09.2026 (sürüm 0.5.0).

## Şimdi

- [ ] **Okuldaki makineleri güncelle.** Yordam KURULUM.md → "Kurulu
      makineleri güncelleme" başlığında. 04.09.2026: yayımlanan sürüm 0.5.0;
      okul makineleri bekliyor.
- [ ] **Pardus paketi gerçek bir makinede denenmedi.** 0.5.0 ile yayımlanan
      `.deb` yalnız `debian:12` kabında (GitHub Actions ve yerelde Docker)
      kuruldu ve xvfb altında açıldı. Okulda bir Pardus 23 makinesinde
      kurulup menüden açılması, e-Okul raporu içe aktarılması ve evrak
      üretilmesi denenmeli; ilk gerçek deneme sonucu buraya yazılsın.
- [ ] **Sürüm numarasını bir daha yerinde değiştirme.** 0.3.0 ve 0.4.0'ın
      ikisi de aynı numarayla iki kez derlendi; hangi kurulumun ne taşıdığı
      SHA-256'ya bakmadan anlaşılmıyor. Sonraki değişiklik görsel bile olsa
      numarayı yükseltin.

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
