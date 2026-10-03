# Değişiklik günlüğü

Biçim [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) esaslıdır,
sürümleme [Semantic Versioning](https://semver.org/lang/tr/) uyarınca yapılır.
Tarihler `gg.aa.yyyy`.

Sürüm numarası `cekirdek/surum.py` içindedir; yeni sürüm çıkarırken önce
oradaki `SURUM` güncellenir, sonra buraya başlık açılır, sonra paket
derlenir.

> **Not.** Bu günlük geriye dönük, git geçmişinden yazıldı. Etiketlenen ilk
> sürüm `v0.4.0`'dır; öncesi etiketsiz dağıtıldı. `pyproject.toml` ilk
> commit'ten beri 0.2.0 diyordu ama o numarayla hiçbir paket dağıtılmadı;
> dağıtılan ilk paket 27.08.2026 tarihli 0.3.0'dır. Bu yüzden 0.3.0 öncesi
> tek başlık altında toplandı.

> **Dikkat — 0.4.0 iki kez derlendi.** 28.08.2026 sabahı yayımlanan 0.4.0
> paketi eski lacivert-turkuaz arayüzü taşıyordu. Aynı gün arayüz paleti ve
> logo değiştirildi ve paket **aynı numarayla** yeniden derlenip yayımlanan
> dosyaların üzerine yazıldı. Ayırt etmek için SHA-256 özetine bakın:
>
> | Derleme | Kurulum dosyası SHA-256 (ilk 16) |
> |---|---|
> | İlk (sabah, turkuaz) | `ea635b65bd539ca5` |
> | Geçerli (bordo) | `9da05566062a3853` |
>
> Aynı sorun 0.3.0'da da yaşandı: 27.08.2026 tarihli asıl 0.3.0 ile
> 28.08.2026'da yeniden derlenen 0.3.0 farklıdır. Elinizde 0.3.0 varsa
> ayırt etmeye uğraşmayın, 0.4.0 ile değiştirin.

## [Yayımlanmamış]

### Eklendi
- Sorumluluk raporu önizlemesi, programın okumadığı sütun başlıklarını
  gösterir. Raporda nakil/geçiş kaynağını gösteren bir sütun olup olmadığı
  (SG-05) ilk gerçek aktarımda görülsün diye; yalnız başlık adı gösterilir.

### Düzeltildi
- **Onaylı belge değişince uyarı.** Belge sürümleri hiçbir zaman "onaylı"
  işaretlenmediği için onaylı bir belgenin sonradan değiştiğini kaydeden
  değişiklik föyü hiç oluşmuyordu. Artık kesinleşmiş plandan üretilen belge
  onaylı sürüm sayılır. Kesin planda örneğin görevli değişikliğinden sonra
  evrak yeniden üretilince değişen belgeler için föy kaydedilir ve evrak
  ekranı imzalanmış eski çıktıların yerine yeni sürümün imzaya sunulmasını
  söyler.
- Belgelerin dosya özellikleri python-docx şablonundan kalıyordu (yazar
  "python-docx", oluşturma 2013, program "Microsoft Macintosh Word"). Artık
  yazar ve program uygulamanın adı ve sürümü, başlık belgenin adı, tarih
  üretim zamanıdır; kişi adı yazılmaz.
- **Uzun uygulama sınavı sonraki saatle çakışıyordu.** Planlayıcı her
  oturuma tek oturum saati ayırıyordu; süresi bir sonraki saate taşan
  uygulama sınavının (ör. 60 dakika arayla dizilmiş saatlerde 90 dakika)
  sürdüğü saate aynı öğrencinin başka sınavı, aynı görevli ya da aynı salon
  verilebiliyordu. Doğrulayıcı da yalnız başlangıç saatlerini karşılaştırdığı
  için bunu görmüyordu. Artık uygulama sürdüğü bütün saatleri tutar, çakışma
  denetimi sürelere bakar ("MATEMATİK başlarken İNGİLİZCE (09:00–10:30)
  sürüyor"), görevli değiştirme penceresi o sırada başka sınavda olanı aday
  göstermez ve takvim kartında bitiş saati yazar. Varsayılan 40 dakikalık
  sürede program eskisiyle aynı planı üretir.

### Değiştirildi
- Servis katmanı (`veri/hizmet.py`, ~2 400 satır) konu modüllerine bölündü
  (`veri/hizmet/` paketi). Davranış değişmedi.

### Kaldırıldı
- Hiç kullanılmayan `kural_karari` tablosu ve görevleri taslak planlarla
  birlikte sayan `v_gorev_sayaci` görünümü (şema göçü
  `009_olu_sema.sql`; göç öncesi yedek kendiliğinden alınır).

## [0.6.2] — 03.10.2026

### Eklendi
- Site görselleri için iki yardımcı betik: `araclar/site_ornekleri.py`
  (örnek okul, belgeler ve PDF önizlemeleri) ve
  `araclar/site_ekranlari.py` (Debian 12 kabında sanal ekrandan ekran
  görüntüleri). Yayım sonrası indirme alanı ve site adımları KURULUM.md'ye
  yazıldı.

### Düzeltildi
- Plan dışı bırakılanlar tutanağı, karar bekleyen öğrenci olmasa da
  "Karar bekliyor durumundaki öğrenciler için henüz başvuru kararı
  girilmemiştir…" cümlesini basıyordu; kesinleşmiş bir dönemin tutanağı
  olmayan bir eksikten söz ediyordu. Cümle artık yalnız karar bekleyen varsa
  ve kaç öğrenci olduğunu söyleyerek yazılır. Plan dışı kimse yoksa
  "Toplam 0 öğrenci…" cümlesi de basılmaz.

## [0.6.1] — 03.10.2026

### Düzeltildi
- Kesinleşmiş sınavın takvim kartındaki kilit işareti bir emojiydi
  (U+1F512). Tk Linux'ta renkli emoji çizemiyor, varsayılan DejaVu yazı
  tipinde de bu karakter yok; kart Pardus'un tabanı olan Debian 12'de ders
  adının yanında boş bir kareyle görünüyordu. İşaret ✓ oldu; kesin kartın
  rengi değişmedi. Arayüz ve evrak kaynaklarında emoji kalmadığını bir test
  denetler.

## [0.6.0] — 03.10.2026

03.10.2026 tarihli ayrıntılı gözden geçirmenin (mevzuat, mimari, arayüz,
evrak) sonucu. Mevzuat atıfları resmî metinlerden yeniden doğrulandı.

**Yükseltme:** veritabanı ilk açılışta şema 8'e göç eder
(`008_takvim_musaitlik_tek_ders.sql`); göçten önce yedeği kendiliğinden
alınır. Kesinleşmiş eski planlar olduğu gibi açılır. Yükseltmeden sonra
Kurum Ayarları'na o yılın tatil günlerini girin.

### Eklendi
- **Tatil ve idari izin günleri** (SP-08): Kurum Ayarları'ndan girilir. Plan
  bu günlere sınav koymaz; başvurudaki 5 iş günü (OKY md.58/2-d) ve evrak
  teslim süresi bu günleri iş günü saymaz. Eski sürüm tatil listesini hiç
  kullanmıyordu.
- **Öğretmen müsaitliği** (SP-09, OKY md.58/2-ç "dersleri aksatmayacak
  şekilde"): haftalık dolu saatler ve tarih aralıklı izin/görev. Planlayıcı
  bu saatlere görev vermez; elle verilen görev engel görünür.
- **Görevliyi elle değiştirme**: sınav kartına tıklayınca görevliler görünür;
  uygun adaylar gerekçeleriyle listelenir. Taslakta geri alınabilir;
  kesinleşmiş planda müdür onay numarası ve gerekçeyle kaydedilir ve
  görevlendirme çizelgesinde listelenir. İki aşamalı derste değişiklik eş
  oturuma da uygulanır (OKY md.58/2-e).
- **Tek ders sınavı (OKY md.58/6)**: olağan plandaki 12. sınıf öğrencilerinden
  tek dersi seçilen için takip eden haftaya ayrı plan. Gerekçe:
  [kararlar/0010](kararlar/0010-tek-ders-sinavi-kapsamda.md).
- **Kişi bazlı görev çizelgesi**: her görevlinin kendi görev dökümü ve
  tebellüğ imzası.
- Gözcü–salon eşleşmesi: hangi gözcünün hangi salonda olduğu kaydedilir ve
  evrakta yazılır; ilan çizelgesinde öğrencinin kendi salonu görünür.
- Uygulama sınavı süresi ayrı girilir (OKY md.45/1-f: zümre belirler).
- **Yedek al** düğmesi (Kurum Ayarları).
- Yardım sayfasına kısaltmalar ve dayanaklar, tek ders sınavı ve evrak biçimi
  bölümleri.

### Değiştirildi
- **Planlama motoru**: kısıt yayılımlı arama (en dar alanlı birim önce, ileri
  denetim); bütçe süreyle değil düğümle. Eski arama gerçekçi ölçekte uydurma
  okullarda on dakikada bile plan bulamıyordu; aynı girdi yavaş makinede farklı
  plan üretebiliyordu. Gerekçe:
  [kararlar/0012](kararlar/0012-planlayici-kisit-yayilimli-arama.md).
- **Günlük sınav sınırı (ÖDY md.5/1-k)**: kısa takvim korunur ama ikiyi aşan
  gün uyarı, üçü aşan gün engeldir; kişisel sınır en çok üçe yükseltilir,
  ekrandaki sınır 1–3. Eski sürüm sınırı tavansız yükseltiyor ve uyarı
  vermiyordu. Gerekçe: [kararlar/0014](kararlar/0014-gunluk-sinav-siniri.md).
- **İki aşamalı dersler**: uygulama oturumu plan ekranında tek başına başka
  güne taşınabilir (OKY md.58/2-e son cümle, RG 22.02.2025); yazılı taşınınca
  uygulama saat farkıyla gelir.
- **SP-10** yalnız yazılı oturumu denetler; uygulamalı sınavın süresini zümre
  belirler.
- **EK-05 ücret sınırı**: toplu sözleşme askısı öğretim yılına değil görev
  tarihine bağlandı (01.01.2024 – 31.12.2027); yıllık sayaç tek planı değil
  yılın bütün geçerli planlarını sayar. Dayanak iki toplu sözleşmenin eğitim
  hizmet kolu md.4'üdür: 7. Dönem (RG 03.09.2023/32298) ve 8. Dönem
  (RG 27.08.2025/32999). Gerekçe:
  [kararlar/0013](kararlar/0013-ucret-siniri-askisi-tarihe-bagli.md).
- **Evrak Resmî Yazışma Yönetmeliği biçiminde**: "T.C. / … KAYMAKAMLIĞI /
  Okul Müdürlüğü" başlığı, Times New Roman, 1,5 cm kenar, siyah-beyaz;
  imza bloğunda düzenleyenin adı ve unvanı, OLUR tarih satırı ve "Okul
  Müdürü". Gerekçe: [kararlar/0011](kararlar/0011-evrak-resmi-yazisma-bicimi.md).
- Tarihler arayüzde gg.aa.yyyy yazılır (eski YYYY-AA-GG de kabul edilir).
- Ekranlar dönemi bugüne göre seçerek açılır; evrak ekranı başlamış son dönemle.
- Başvuru işaretinin konduğu öğretim yılı tutulur; önceki yıldan kalan
  işaretler gözden geçirilmek üzere bildirilir.
- Kurulum sihirbazı Türkçe (`Turkish.isl`).
- İki aşamalı ders önerisi Almanca, Fransızca vb. yabancı dilleri de tanır.
- İş akışları yalnız belge değiştiren itmelerde koşmuyor (`paths-ignore`:
  `**.md`, `LICENSE`, `NOTICE`). Pardus paketinin yayıma eklenmesi artık
  etiket itmesine değil **yayımın açılmasına** (`release: published`) bağlı;
  süzgeç `push` olayına takılı olduğu için etiket itmesi sessizce atlanırdı.

### Düzeltildi
- Kesinleşmiş planın üstüne aynı dönem için yeni taslak kaydedilebiliyordu;
  ekran ve evrak taslağı gösteriyor, görev sayaçları iki planı birden
  sayıyordu.
- Yeni plan üretilirken aynı dönemin eski planı "önceki dönem" sayılıyor,
  görev dengesi bozuluyordu.
- Plan seçimi öğretim yılına bakmıyordu: yeni yılda Eylül ekranı geçen yılın
  planını açıyor, yeni plan geçen yılın taslağını siliyordu.
- Plan ekranında dönem değiştirilince o dönemin planı yüklenmiyordu;
  "kesinleştir" ekranda kalan başka dönemin planını kesinleştirebiliyordu.
- Kaydedilmemiş plan başka sayfaya gidip dönünce kayboluyordu.
- Başvuru ekranında seçili öğrencinin işaretleri kutulara gelmiyordu;
  "İşaretlemeyi kaydet" öbür bayrağı sessizce silebiliyor, öğrenci başvurusuz
  plana giriyordu. Durum kutusu "basvurdu/basvurmadi" kodlarını gösteriyordu.
- Öğrenciler salonlara kapasiteye bakılmadan sırayla dağıtılıyordu.
- Takvimde bir hücreye üçten fazla oturum düşünce fazlası çizilmiyordu.
- Ders/branş ekranı "yabancı dil" bayrağını iki aşamalı kutusundan
  kopyalıyordu.
- Dayanak metinleri: salon ekranındaki "en çok 30 öğrenci — OKY md.58/2-b"
  (30 okul kararıdır), SP-05 gerekçe şartı (okul uygulamasıdır), EK-03
  (OKY md.58/2-a + Karar md.12/2-b), diploma tarihi atfı (OKY md.69/2-b,
  md.43 değil), SG-05 (nakil kaynağı okunmuyor) düzeltildi.

### Kaldırıldı
- Kullanılmayan PyYAML bağımlılığı.

## [0.5.0] — 29.08.2026

Windows tarafında işleyiş değişmedi; bu sürüm uygulamayı **Pardus'a** taşır
ve testleri geliştirme makinesinden çıkarıp GitHub'a alır.

### Eklendi
- **Pardus paketi.** Pardus 23 ve üzeri için `.deb` paketi üretiliyor
  (`yapim/deb_paketi.py`). Paket bütünleşiktir: Python, kitaplıklar ve Tcl/Tk
  içindedir, kurulum internet istemez. Gerekçe:
  [kararlar/0009](kararlar/0009-pardus-paketi-pyinstaller-ile.md).
- **GitHub Actions.** Testler artık her itmede Windows (Python 3.11, 3.12) ve
  Debian 12 kabında da koşuyor; Pardus paketi orada üretilip kuruluyor ve
  açılıp açılmadığı deneniyor. Sürüm etiketi itildiğinde paket yayıma
  kendiliğinden ekleniyor.

### Değiştirildi
- `SorumlulukSinavi.spec` iki platformu birden üretiyor: Windows'a özgü sürüm
  kaynağı ve `.ico` simge koşula bağlandı, ikinci bir spec dosyası tutulmadı.

### Düzeltildi
- Arayüz testleri kararsızdı: ekran olduğu hâlde her koşuda rastgele bir test
  "Tkinter ekranı yok" diyerek atlanıyordu. Fikstür artık oturum başına tek
  bir Tk kökü kurup her teste bir `Toplevel` veriyor; atlama da yalnızca
  gerçekten ekransız ortamda yapılıyor, başka her Tk hatası testi kırıyor.

## [0.4.0] — 28.08.2026

### Değiştirildi (paket aynı numarayla yeniden yayımlandı)
- Arayüz paleti okulapp.org'un Sorumluluk Sınavı bölümüyle aynı kümeye
  (`ss`: bordo + sıcak kum) çevrildi. Renkler `arayuz/palet.py`'de tek yerde;
  önce iki ayrı sözlükte ve yirmiye yakın doğrudan yazılmış kodda dağınıktı.
- Logo da aynı paletten üretiliyor; dış kare bordo, başlık şeridi sıcak kum.

### Eklendi
- **Başvuru kapısı** (OKY md.58/2-d): okuldan mezun olamayan 12. sınıf
  öğrencileri ile devamsızlık tebligatı yapıldığı hâlde okula veya sınavlara
  katılımı sağlanamayan öğrenciler otomatik plana alınmıyor; yazılı
  başvuruları hâlinde dâhil ediliyor. Başvuru duyurusu ve plan dışı tutanağı
  belgeleri eklendi. Göç `007_basvuru_kapisi.sql`.
- Sürümü tek kaynakta tutan `cekirdek/surum.py`; `pyproject.toml`,
  `SorumlulukSinavi.spec`, Inno Setup betiği ve arayüz bu değeri okuyor.
- Üretilen `SorumlulukSinavi.exe` dosyasına Windows sürüm kaynağı gömülüyor;
  dosya özelliklerinin "Ayrıntılar" sekmesi artık dolu.
- Depoya gerçek kişi verisi girmesini engelleyen testler
  (`testler/test_gizlilik.py`): izlenen dosyaların uzantısı, kimlik ve
  telefon numarası kalıpları ve yoksayma kuralına takılan izlenen dosya
  denetleniyor.
- Proje düzeni: `CLAUDE.md`, bu günlük, `kararlar/` karar kayıtları,
  `PLAN.md`.

### Değiştirildi
- `.gitignore` biçim bazlı KVKK korumasına çevrildi: PDF, ODS/ODT, PPTX,
  RTF, arşivler, JSON dışa aktarımlar, `.env`, düzenleyici klasörleri ve
  **görseller** yoksayılıyor; izlenmesi gereken üç logo beyaz listede.
- Gerçek veriyle denemek için yoksayılan `/yerel/`, kuruma özel şablonlar
  için `/sablonlar/ozel/` ayrıldı.

### Düzeltildi
- `pyproject.toml` sürümü 0.2.0'da kalmıştı; arayüz ve kurulum betiği 0.3.0
  gösteriyordu. Önce değerler eşitlendi, sonra kaymanın kendisi ortadan
  kaldırıldı.

## [0.3.0] — 27.08.2026

Dağıtılan ilk paket.

### Eklendi
- Windows kurulum dosyası (Inno Setup 6): kullanıcı başına kurulum, yönetici
  hakkı istemez; kaldırma ve yükseltme veritabanına dokunmaz.
- Lisans sayfası; `LICENSE` ve `NOTICE` pakete giriyor.
- Evrak teslim çizelgesi: sınav sonrası komisyondan geri alınan evrak
  izleniyor.
- Komisyon bazlı görevlendirme çizelgesi ve KVKK uyumlu ilan çıktıları.
- Personel yönetimi, görev havuzu, logo ve yardım sayfası.
- Servis katmanı ve Tkinter arayüzü; uygulama çalışır hâle geldi.
- Windows paketi (PyInstaller).

### Değiştirildi
- İlan belgelerinden imzalayan kişinin adı kaldırıldı; ilan çıktıları kişi
  adı yerine "Okul Müdürlüğü" yazıyor.
- Belge seti sadeleştirildi; evraktan logo kaldırıldı, dönem adları
  aylandırıldı.
- Kapsam dışı kalıntılar söküldü.

### Düzeltildi
- Önceki sürümün veritabanıyla şema çakışması: yeni şema ayrı klasörde
  (`…\SorumlulukSinavi\plan`) duruyor, eski dosyaya dokunulmuyor.
- Branş adındaki eğik çizgi ve kaydedilen planın yeniden doğrulanması.
- İlk kurulumda alınan yedek.

## 0.3.0 öncesi — 26.08.2026

Dağıtılmadı; çekirdek katmanların kurulduğu ilk üç commit.

### Eklendi
- Taban şema, veritabanı katmanı ve e-Okul rapor ayrıştırıcıları
  (OOK01001R1 personel, OOK12001R010 sorumluluk).
- Kural katmanı: 16 kural tek dosyada, her biri olumsuz senaryosuyla test
  edildi.
- Planlama motoru: yerleştirme ve görevlendirme birlikte çözülüyor.
