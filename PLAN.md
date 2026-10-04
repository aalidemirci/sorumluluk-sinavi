# Plan

Bu dosya **açık işleri** tutar: yapılacaklar, bilinen borçlar ve takvime
bağlı zorunluluklar. Yapılıp bitenler buradan silinir, CHANGELOG.md'ye
geçer. Kapsam dışı olduğuna karar verilmiş şeyler en altta durur ki
tekrar tekrar tartışılmasın.

Son gözden geçirme: 04.10.2026 (0.8.5 yayımı: günlüğe ad girmiyor, kurulum
günlük bırakıyor). Bu dosyadaki açık işlerin kodla yapılabilen kısmı bitti;
kalanlar kullanıcının gözle turu, okul makinesi ya da ağı, gerçek Pardus
kurulumu, Uygulamalar kaydı için kurulum günlüğü ya da takvim bekliyor.

## Şimdi

- [ ] **Qt arayüzünü gerçek kullanımda dene.** Arayüz 0.8.0'da baştan
      yazıldı (karar 0016). 04.10.2026: bütün sayfalar Full HD %125, %150 ve
      1366×768'de incelendi. Aynı gün bu makinedeki gerçek veritabanının
      geçici kopyasında ekransız tur yapıldı (kopya sonra silindi; çıktıya
      yalnız süre, sayı ve hata türü yazıldı): bütün sayfalar açıldı, plan
      bir saniyenin altında üretildi; görevli değiştirme, kaydetme, evrak,
      teslim çizelgesi, Türkçe harfli ve harfsiz arama, bütün öğrencilere
      toplu işaret ve numara listesi çalıştı. Turda üç kusur bulunup
      düzeltildi (0.8.4): hafta sonuna sürükleme hep geri alınıyordu, dolu
      salona taşıma boş salona geçmiyordu, plan iletisi işe yaramayan bir
      öneride bulunuyordu. Kalan: kullanıcının gözle turu; özellikle 0.8.4'teki
      hafta sonuna taşıma gerekçesi ve boş salona geçişin elde nasıl durduğu.
- [ ] **Güncelleme denetimini okul ağında dene.** Denetim 0.8.0'la geldi
      (karar 0015). GitHub'ın engelli olduğu okul ağında açılışın sessiz
      kaldığı, elle denetimin anlaşılır ileti ve indirme sayfası düğmesi
      gösterdiği görülmeli; bugüne dek yalnız ulaşılamayan vekille taklit
      edildi.
      04.10.2026: akışın geri kalanı yayımlanmış paketlerle uçtan uca
      denendi. Bu makinede 0.7.0'ın üzerine 0.8.1 kuruldu; kurulu 0.8.1 boş
      bir deneme veri klasörüyle açılınca şeridi gösterdi. Hakkında'da
      "Doğrula ve indir" 0.8.2 kurulum dosyasını (24 MB, yaklaşık 40
      saniye) indirip doğruladı; "Kurulumu başlat" programı kapatıp
      sihirbazı açtı. Sihirbaz kurulum klasörünü ve masaüstü kısayolu
      seçimini önceki kurulumdan aldı; 0.8.2 kuruldu, açıldı, "Program
      güncel" dedi. Gerçek veri klasörüne dokunulmadı. Aynı denemede
      Ayarlar → Uygulamalar kaydının 0.4.0'da kalmış olduğu görüldü
      (dosyalar 0.7.0'dı); 0.8.1 ve 0.8.2 kurulumları kaydı yeniledi.
      Eskide kalmasının nedeni bulunamadı, durum yeniden üretilemedi.
      0.8.3 yayımlanınca kurulu 0.8.2 de yeni sürümü buldu, kurulum
      dosyasını 9 saniyede indirip doğruladı ve sihirbazı açtı; kurulumu
      kullanıcı tamamladı. 0.8.3'ün düzeltmeleri bu gerçek yükseltmede
      görüldü: eski İngilizce kaldırma kısayolu silindi, ilk açılışta
      önbellekteki iki kurulum dosyası (0.8.2 ve az önce kullanılan 0.8.3)
      silindi; kurulum dosyasının kilidi 4 saniye içinde kalkmıştı.
      0.8.4 yayımlanınca yayımlanmış 0.8.3 taşınabilir paketi ekransız
      açıldı; günlükte "kurulu 0.8.3, yayımlanan 0.8.4".
- [ ] **Okuldaki makineleri güncelle.** Yordam KURULUM.md → "Kurulu
      makineleri güncelleme" başlığında. 04.10.2026: yayımlanan sürüm 0.8.5;
      okul makineleri bekliyor. 0.6.x ya da daha eskisinden gelen makinede
      veritabanı ilk açılışta şema 9'a geçer (öncesinde yedek alınır); 0.5.x
      ya da daha eskisinden gelen makinede geçişten sonra tatil günleri
      girilmeli. 0.8.0'dan sonraki sürümleri program kendisi haber verir.
- [ ] **Pardus paketi gerçek bir makinede denenmedi.** Yayımlanan `.deb`'ler
      (0.5.0 – 0.8.5) yalnız kapta kuruldu ve xvfb altında açıldı:
      `debian:12` (GitHub Actions ve yerelde Docker), 0.8.3'ten beri ayrıca
      resmî Pardus 23 ve Pardus 25 görüntülerinde. Okulda bir Pardus 23
      makinesinde kurulup menüden açılması, e-Okul raporu içe aktarılması ve
      evrak üretilmesi denenmeli; arayüzün o masaüstündeki yazı tipiyle
      görünüşüne de bakılsın (0.6.0'daki kilit emojisi kapta kare çıkmıştı).
      Qt sürümüyle ayrıca: GNOME'un Wayland oturumunda XWayland üzerinden
      açılması, dosya seçme penceresinin (GTK teması) çalışması.
      04.10.2026, temiz `debian:12` kabında 0.8.0 paketiyle: GNOME Wayland
      oturumunun ortam değişkenleriyle program Wayland eklentisini bulamayıp
      X11'e düştü ve açıldı (Weston kapta çöktüğü için X sunucusu Xvfb idi);
      XFCE ortamında Qt GTK temasını yükledi, "Rapor seç ve önizle" GTK'nin
      kendi dosya seçme penceresini açtı.
      04.10.2026, 0.8.3 ve 0.8.4 paketleriyle resmî `pardus/yirmiuc` (Pardus 23, glibc
      2.36) ve `pardus/yirmibes` (Pardus 25, glibc 2.41) görüntülerinde:
      bağımlılıklar Pardus'un kendi deposundan çözüldü, menü dosyası
      `desktop-file-validate`den geçti (tek ipucu: iki ana kategori, Ofis ve
      Eğitim; bilerek), program açıldı ve veritabanını kurdu. Pardus 25'te
      ilk deneme.
      İlk gerçek deneme sonucu buraya yazılsın.

## Takvime bağlı

- [ ] **Şubat 2027 dönemi (Ocak 2027'de bakılacak).** Pencere 08.02.2027'de
      açıldığı için başvurunun en geç günü (5 iş günü önce) yarıyıl
      tatiline, 01.02.2027'ye düşer: duyuruyu yarıyıldan önce yayımlayıp
      başvuruyu okul kapanmadan toplamak ya da yarıyılda dilekçe kabulünü
      düzenlemek gerekir. Bu okulun verisinde bir öğrencinin yükü 10 iş
      gününe günde üç sınavla da sığmıyor; plan hafta sonu açılarak üretilir
      (hafta sonu oturumları gerekçeli olur). 2026-2027 resmî tatilleri
      04.10.2026'da bu makinede Kurum Ayarları'na girildi (2429 sayılı Kanun;
      Diyanet 2027 takvimi; arife yarım günleri iş günü sayıldı, girilmedi);
      idari izin kararı çıkarsa eklenir.

- [ ] **9. Dönem Toplu Sözleşme (Ağustos 2027):** `cekirdek/kurallar.py`
      içindeki `SINIR_ASKILARI` güncellenmeli. 8. Dönem eğitim hizmet kolu
      md.4 gereği 12/15 görev sınırları 01.01.2026 – 31.12.2027 arasındaki
      görevlerde uygulanmıyor; 01.01.2028 sonrası görevler için yeni metne
      bakılacak (bkz. `kararlar/0013`). Aynı metinde yabancı dil yazılı ve
      sözlü komisyon üyeliklerinin ayrı değerlendirilmesi hükmü (7. ve 8.
      Dönemde md.17) de aranmalı; madde numarası ya da hüküm değişirse EK-05
      dayanağı, yardım metni ve görev sayacı raporunun notu güncellenir.

## Bilinen borçlar

- **Uygulamalar kaydı kullanıcının başlattığı yükseltmede yenilenmiyor.**
  04.10.2026: kullanıcı bu makinede 0.8.3'ten programın kendi akışıyla 0.8.4'e
  geçti; dosyalar, kısayollar ve kaldırma günlüğü 21.32'de yazıldı ama HKCU'daki
  kaldırma kaydı 14.38'deki 0.8.3 değerlerinde kaldı (yönetici alanında kayıt
  yok, izin sorunu yok). Aynı belirti 0.5.0 ve 0.7.0'da da vardı; bu oturumda
  başlatılan üç kurulum (0.8.1 sessiz, 0.8.2 ve 0.8.3 sihirbazla) kaydı
  yeniledi. Inno kaynağına göre kayıt, kaldırma günlüğü kaydedilmeden hemen
  önce yazılır. Günlük olmadığından neden bulunamadı; `SetupLogging=yes`
  0.8.5'le geldi. Bu makinede 0.8.4'ten 0.8.5'e program içinden yükseltilince
  günlük ilk kez oluşur: `%TEMP%\Setup Log …` dosyasına bakılacak.
  Programın çalışmasını etkilemez; kurulu sürüm Hakkında sayfasında ve exe'nin
  dosya özelliklerinde doğrudur (KURULUM.md'deki doğrulama komutu buna bakar).

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
  bütçeye takılırsa plan "üretilemedi" der. 04.10.2026'da gerçek bir okulun
  verisiyle plan bir saniyenin altında üretildi; çok daha büyük okulda yine
  gözlenmeli.
- **GitHub yayım düzeni.** Güncelleme denetimi `releases/latest` ucunu ve
  yayımdaki dosya adlarını okur (`kararlar/0015`). GitHub API'si ya da dosya
  adları değişirse denetim susar ya da indiremez; program etkilenmez.
  `testler/test_guncelleme.py` yanıt biçimini sahte ağla korur.
- **Qt sürümü ve LGPL bildirimi.** PySide6 `pyproject.toml`'da tam sabittir;
  yükseltirken NOTICE'taki sürüm ve kaynak adresi, yardım metnindeki
  bildirim de değişir (`testler/test_lisans.py`). Yeni Qt sürümü yeni bir
  sistem kitaplığı isterse Pardus derlemesi `bagimlilik_sorunlari` ile durur.

## Kapsam dışı

Bunlar bilinçli olarak yapılmıyor. Yeniden gündeme gelirse karar kaydı
yazılarak gelsin.

- Sınav sonrası işlemler: sonuç ve puan girişi, itiraz, telafi, diploma
  tarihi, disiplin. Bunlar e-Okul'da yürütülür. (Tek ders sınavının —
  OKY md.58/6 — **planı** 03.10.2026'dan beri kapsamdadır, sonucu yine
  e-Okul'dadır; bkz. `kararlar/0010`.)
- Ek ders ücreti hesabı. Uygulama yalnız Karar md.12/2-a'daki 12 komisyon /
  15 gözcülük sınırı için görev sayacı tutar; tutar hesabı MYS'de yapılır.
- Ağ, bulut, telemetri, hata bildirimi, uzak yedek (bkz.
  `kararlar/0001-cevrimdisi-ve-yerel-veri.md`). Yeni sürüm denetimi
  03.10.2026'dan beri kapsamdadır (`kararlar/0015`); kendiliğinden indirip
  kurmak kapsam dışıdır.
