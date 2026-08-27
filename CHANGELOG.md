# Değişiklik günlüğü

Biçim [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) esaslıdır,
sürümleme [Semantic Versioning](https://semver.org/lang/tr/) uyarınca yapılır.
Tarihler `gg.aa.yyyy`.

Sürüm numarası `cekirdek/surum.py` içindedir; yeni sürüm çıkarırken önce
oradaki `SURUM` güncellenir, sonra buraya başlık açılır, sonra paket
derlenir.

> **Not.** Bu günlük geriye dönük, git geçmişinden yazıldı. Depoda sürüm
> etiketi (`git tag`) yok. `pyproject.toml` ilk commit'ten beri 0.2.0
> diyordu ama o numarayla hiçbir paket dağıtılmadı; dağıtılan ilk paket
> 27.08.2026 tarihli 0.3.0'dır. Bu yüzden 0.3.0 öncesi tek başlık altında
> toplandı.

> **Dikkat.** Aşağıda "Yayımlanmamış" altındaki işler 0.3.0 numarasıyla
> derlendi; yani 27.08.2026'da dağıtılan 0.3.0 paketi ile bugün yeniden
> derlenen 0.3.0 paketi **aynı değil**. Bir sonraki dağıtımdan önce sürüm
> numarası yükseltilmelidir.

## [Yayımlanmamış]

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
