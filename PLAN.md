# Plan

Bu dosya **açık işleri** tutar: yapılacaklar, bilinen borçlar ve takvime
bağlı zorunluluklar. Yapılıp bitenler buradan silinir, CHANGELOG.md'ye
geçer. Kapsam dışı olduğuna karar verilmiş şeyler en altta durur ki
tekrar tekrar tartışılmasın.

Son gözden geçirme: 04.10.2026 (0.8.2 yayımı). Bu dosyadaki açık işlerin
kodla yapılabilen kısmı bitti; kalanlar gerçek veri, okul makinesi, gerçek
Pardus kurulumu ya da takvim (Ağustos 2027) bekliyor.

## Şimdi

- [ ] **Qt arayüzünü gerçek kullanımda dene.** Arayüz 0.8.0'da baştan
      yazıldı (karar 0016); testler, ekran görüntüleri ve paket denemeleri
      yeşil ama gerçek kullanımda denenmedi. Windows'ta gerçek bir e-Okul
      listesiyle (yerel `/yerel/`
      klasöründe) başvuru işaretleme (arama, toplu işaret, numara listesi),
      plan ekranında sürükle-bırak ve görevli değiştirme, evrak üretimi ve
      teslim çizelgesi bir tur yürütülsün.
      04.10.2026: bütün sayfalar Full HD %125, %150 ve 1366×768'de
      incelendi; plan takviminde sıkışan kartlar, kırpılan yan panel ve
      yatay kaydırma isteyen tablolar düzeltildi. Evrak üretimi, teslim
      çizelgesi ve toplu işlemlerin akışı teste girdi; toplu işlemde hata
      sonrası başarı bildirimi hatası bulunup düzeltildi. Gerçek veriyle tur
      hâlâ bekliyor (`/yerel/` boş).
- [ ] **Güncelleme denetimini yayımda dene.** Denetim 0.8.0'la geldi;
      ilk gerçek deneme artık yapılabilir: 0.8.0 ya da 0.8.1'in kurulu
      olduğu makinede şeridin çıktığı, "Doğrula ve indir"in
      dosyayı indirip özetini doğruladığı ve "Kurulumu başlat"ın kurulumu
      açtığı görülmeli (karar 0015). GitHub'ın engelli olduğu okul ağında
      sessiz kaldığı da görülsün.
      04.10.2026: akış arayüzden 0.8.0 yayımıyla uçtan uca denendi (program
      0.7.0 sayıldı; kurulum dosyası indirildi, doğrulandı, çalıştırılmadı)
      ve ulaşılamayan vekille GitHub engeli taklit edildi: açılış sessiz,
      elle denetim anlaşılır ileti ve indirme sayfası düğmesi gösterdi.
      0.8.1 yayımlanınca yayımlanmış 0.8.0 taşınabilir paketi ekransız
      açıldı; günlükte "kurulu 0.8.0, yayımlanan 0.8.1": denetim gerçek
      yayımı buldu (0.8.2 yayımında 0.8.1 paketiyle de aynı sonuç). Kalan: 0.8.x kurulu bir makinede şeridi görüp Hakkında'da
      "Doğrula ve indir" → "Kurulumu başlat"ı tıklamak. Kurulu sürümü 0.7.0
      olan bir makinede kolay yol: 0.8.1 taşınabilir paketini açıp aynı
      düğmelerle 0.8.2'yi kurmak; kurulum eski sürümün üzerine yapılır.
- [ ] **Okuldaki makineleri güncelle.** Yordam KURULUM.md → "Kurulu
      makineleri güncelleme" başlığında. 04.10.2026: yayımlanan sürüm 0.8.2;
      okul makineleri bekliyor. 0.6.x ya da daha eskisinden gelen makinede
      veritabanı ilk açılışta şema 9'a geçer (öncesinde yedek alınır); 0.5.x
      ya da daha eskisinden gelen makinede geçişten sonra tatil günleri
      girilmeli. 0.8.0'dan sonraki sürümleri program kendisi haber verir.
- [ ] **Pardus paketi gerçek bir makinede denenmedi.** Yayımlanan `.deb`'ler
      (0.5.0 – 0.8.2) yalnız `debian:12` kabında (GitHub Actions ve yerelde
      Docker) kuruldu ve xvfb altında açıldı. Okulda bir Pardus 23
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
      İlk gerçek deneme sonucu buraya yazılsın.
- [ ] **Tatil günlerini gir.** 2026-2027 için Kurum Ayarları'na resmî tatil
      ve idari izin günleri girilmeli; özellikle sınav pencerelerine düşenler.
      04.10.2026'da resmî kaynaklardan derlenen liste (2429 sayılı Kanun;
      Diyanet 2027 dinî günler takvimi; MEB 2026-2027 çalışma takvimi,
      meb.gov.tr 13.06.2026):
      29.10.2026 Cumhuriyet Bayramı · 01.01.2027 Yılbaşı ·
      09–11.03.2027 Ramazan Bayramı · 23.04.2027 · 01.05.2027 (Cumartesi) ·
      16–19.05.2027 Kurban Bayramı (19 Mayıs aynı güne düşer).
      Arife yarım günleri (28.10.2026, 08.03.2027, 15.05.2027) öğleden önce
      iş günüdür; tam gün girilirse o gün sınav konmaz. Hiçbiri 2026-2027
      sınav pencerelerine düşmüyor. Ara tatiller ve yarıyıl tatili resmî
      tatil değildir, idare çalışır; girilmez. İdari izin kararı çıkarsa
      eklenir. Dikkat: Şubat penceresi 08.02.2027'de açıldığı için başvurunun
      en geç günü (5 iş günü önce) yarıyıl tatiline, 01.02.2027'ye düşer;
      duyuruyu yarıyıldan önce yayımlayıp başvuruyu okul kapanmadan toplamak
      ya da yarıyılda dilekçe kabulünü düzenlemek gerekir.

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
