# Sorumluluk Sınavı

Ortaöğretim kurumlarında sorumluluk sınavı planlaması ve görevlendirmesi için
çevrimdışı çalışan masaüstü uygulaması.

Uygulama **hiçbir ağ isteği yapmaz.** e-Okul, MEBBİS, DYS veya başka bir resmî
sisteme bağlanmaz, kullanıcı adı ya da şifre istemez. Yalnız sizin dışa
aktardığınız dosyaları okur; ürettiği planın e-Okul'a girişi kullanıcı
tarafından elle yapılır.

Windows ve Pardus için ayrı paketler yayımlanır (`.exe` ve `.deb`); ikisinde
de Python kurulu olması gerekmez. Kurulum yordamı KURULUM.md'dedir.

## Ne yapar

1. e-Okul **OOK01001R1** personel raporunu içe aktarır; branş havuzu bu
   rapordan kurulur.
2. e-Okul **OOK12001R010** sorumluluk raporunu içe aktarır.
3. Beklemeli ve devamsız öğrencilerin başvurularını toplar; başvurusu olmayanı
   plandan çıkarır (OKY md.58/2-d).
4. Dersleri branşlara eşler; iki aşamalı dersleri işaretler.
5. Sınav planını üretir: oturumları günlere ve saatlere yerleştirir,
   komisyon ve gözcüleri görevlendirir.
6. Planı sürükle-bırakla düzenletir, çakışmaları gösterir, müdür onayıyla
   kesinleştirir.
7. Sınav evrakını .docx olarak üretir ve sınav sonrası komisyondan geri
   alınan evrakı izler.

## Ne yapmaz

Sınav sonrası işlemler kapsam dışıdır: sonuç ve puan girişi, itiraz, telafi,
ek sınav, diploma tarihi ve disiplin işlemleri **e-Okul'da** yürütülür. Ek ders
ücreti hesaplanmaz; uygulama yalnız Karar md.12/2-a'daki 12 komisyon / 15
gözcülük sınırı için görev sayacı tutar, tutar hesabı MYS'de yapılır.

## Üretilen evrak

Belgeler şablon dosyasından değil koddan üretilir; sayfa düzeni tek yerde
tanımlıdır ve şablon ile kod birbirinden kopmaz. Sekiz belge vardır (ikisi başvuru kapısına aittir):

| Belge | İçerik |
|---|---|
| Sınav programı (öğrenci nüshası) | Tarih, saat, ders, süre, salon |
| Sınav programı (görevli nüshası) | + komisyon ve gözcüler |
| Görevlendirme çizelgesi | Komisyon bazlı: ders(ler), öğrenci sayısı, tarih, saat, salon, komisyon üyeleri, gözcüler + tebliğ-tebellüğ sayfası |
| Öğretmen görev sayacı | Üç dönemin dökümü, komisyon/gözcülük sayıları, 12/15 durumu |
| **İLAN:** sınav takvimi | Web sayfasında yayımlanmak üzere; kişisel veri içermez |
| **İLAN:** öğrenci çizelgesi | Hangi öğrencinin hangi derslerden sınava gireceği, ad maskeli |
| **İLAN:** başvuru duyurusu | Beklemeli/devamsız öğrencinin başvuru zorunluluğu ve son gün; kişi adı içermez |
| Plan dışı bırakılanlar tutanağı | Başvurusu bulunmadığı için plana alınmayanlar; okul içi kayıt, ilan edilmez |

Komisyon tutanağı, yoklama/salon listesi, kâğıt sarf tutanağı ve evrak teslim
tutanağı bu setten çıkarılmıştır. İlk üçü e-Okul'dan alınır; teslim takibi ise
ekrandaki çizelgeden yürütülür, ayrıca belge üretmeye gerek yoktur.

Belgelerde program logosu yer almaz: evrak okulun evrakıdır, yazılımın tanıtımı
değildir. İmza bloğu "Düzenleyen" ve müdür "OLUR" makamından oluşur.

Görev sayacı raporu kesinleşmemiş plandan da üretilir; görev yükünü onaydan
önce görmek gerekir. Taslak dönem varsa belgeye uyarı düşülür.

Her belgenin altında dayanağı yazılıdır. Belgeler EBYS/DYS kayıt numarası ve
güvenli elektronik imza ibaresi üretmez; okulun kendi kayıtlarından hazırlanmış
çıktılardır.

Sürüm takibi belge *içeriğinin* özetine bağlıdır: aynı içerik yeniden
üretilirse yeni sürüm açılmaz, plan değişip belge farklılaşırsa sürüm numarası
artar ve hangi çıktının hangi içerikten geldiği izlenebilir.

## İlan çizelgeleri ve KVKK

Okul web sayfasında yayımlanmak üzere iki çıktı üretilir.

**Sınav takvimi** hiçbir kişisel veri içermez: ne öğrenci, ne görevli öğretmen,
ne de imzalayan müdürün adı geçer. Yalnız hangi dersin sınavının ne zaman ve
nerede yapılacağı yazar. Her iki ilan belgesi de kişi adı yerine "Okul
Müdürlüğü" makam satırıyla çıkarılır.

**Öğrenci sınav çizelgesi** öğrencinin kendi satırını bulabilmesi için okul
numarasını gösterir; ad ve soyadı hiçbir seçenekte açık yazılmaz. Gösterim
biçimi evrak ekranından seçilir:

| Seçenek | Görünüm |
|---|---|
| Okul numarası + maskeli ad *(varsayılan)* | `12820 — A**** A** D******` |
| Yalnız okul numarası | `12820` |
| Yalnız maskeli ad | `A**** A** D******` |

Maskeleme her sözcüğün ilk harfini bırakıp kalanını yıldızlar. İlk harf Türkçe
büyütmeden geçer.

Her iki belgede 6698 sayılı Kanuna atıf yapan bir not bulunur ve plan müdür
onayıyla kesinleşmeden üretilirse belge üzerinde TASLAK uyarısı yazar.

## Evrak teslim takibi

Sınav sonrası komisyondan geri alınması beklenen evrak — sınav kâğıtları,
komisyon tutanağı ve yoklama listesi — oturum başına izlenir. Teslim süresi
sınav tarihini izleyen ilk iş günüdür; süresinde gelmeyen evrak çizelgede
kırmızı görünür. Evrakı teslim eden komisyon üyesi ile teslim alan görevlinin
aynı kişi olması engellenir (TS-03).

## Öğretmen listesi

Liste e-Okul OOK01001R1 raporundan kurulur. Rapora henüz yansımamış bir kişiyi
**elle ekleyebilir**, ayrılan ya da görev alamayacak bir kişiyi **pasife
alabilirsiniz**. Pasif personel yeni görevlendirmeye girmez; geçmiş görevleri
ve sayaçları olduğu gibi kalır.

Görevi bulunan kişi listeden silinemez — silinirse üretilmiş evrak ile
veritabanı çelişir. Böyle bir kişi pasife alınır.

## Görev dengesi ve üç dönem

Bir öğretim yılında üç sınav dönemi vardır: **Eylül** (birinci dönemin ilk iki
haftası), **Şubat** (ikinci dönemin ilk iki haftası) ve **Haziran** (ikinci
dönemin son iki haftası). Görev sayaçları
dönemler arasında taşınır: ikinci dönem planlanırken birinci dönemde çok görev
almış öğretmen geri plana düşer. Görev sayacı raporu her dönemin dökümünü ayrı
sütunda gösterir.

Dengeleme branş arzının izin verdiği ölçüde çalışır. Bir branşta az öğretmen
varken o branşın çok sınavı olursa yük kaçınılmaz olarak birikir; rapor bunu
görünür kılar ve İlçe MEM'den öğretmen istenmesi gerekip gerekmediğini gösterir.

## Planlama motoru

Yerleştirme ve görevlendirme tek problem olarak çözülür: bir oturumun nereye
konabileceği, o saatte komisyonun kurulup kurulamayacağına bağlıdır. Bu sayede
aynı saatte birden fazla sınav yapılabilir ve program az sayıda güne sığar.

Plan üretmeden önce üç şey sorulur:

- **Hafta sonu kullanılsın mı?** Kullanılabilir seçilse bile hafta içi
  tükenmeden hafta sonuna geçilmez (OKY md.58/2-ç).
- **Öğrenci günlük sınav sınırı** (varsayılan 2).
- **Yazılı + uygulama tek mi ayrı mı sayılsın?** Tek sayılırsa iki aşamalı
  dersin iki oturumu öğrencinin günlük sayacına bir sınav olarak girer.

Gün sayısı otomatik seçilir: öğrencilerin çoğunluğunun sığdığı en kısa program
denenir (bir hafta → iki hafta → gereken kadar). Bu pencereye sığmayan tek tük
öğrencinin günlük sınırı, gereken **en düşük** değere çıkarılır ve raporlanır.
"Yükü çözümle" düğmesi her seçeneğin sonucunu plan üretilmeden önce gösterir.

Plan üretilemezse hangi kısıtın bağladığı yazılır: salon sayısı, görevli
kapasitesi, branş arzı ya da bir öğrencinin günlük oturum tavanı.

## Uygulanan kurallar

18 kural tek dosyada (`cekirdek/kurallar.py`) tanımlanır ve tek yerde
uygulanır. Motorun ürettiği plan da elle düzenlenen plan da aynı doğrulayıcıdan
geçer.

| Kural | Dayanak |
|---|---|
| SP-01 sınav penceresi | OKY md.58/2-a |
| SP-02 komisyon ve gözcü | OKY md.58/2-a |
| SP-03 gözcü sayısı = salon sayısı | OKY md.58/2-b + okul kararı |
| SP-04 düzey birleştirme (30 sınırı) | OKY md.58/2-c |
| SP-05 hafta sonu ve müdür onayı | OKY md.58/2-ç |
| SP-06 iki aşamalı dersler | OKY md.58/2-e |
| SP-07 beklemeli/devamsız öğrencinin başvurusu | OKY md.58/2-d |
| SP-10 sınav süresi | ÖDY md.5/1-l |
| SP-11 günlük sınav sayısı | ÖDY md.5/1-k |
| SP-15 Şubat/Haziran için güncel liste | Okul uygulaması |
| EK-03 aynı sınavda çifte rol yok | Karar md.12/2-b |
| EK-04 yönetici görevi ücretsizdir | Karar md.12/2-c |
| EK-05 yıllık görev sayacı | Karar md.12/2-a |
| SG-05, SG-06 sorumluluk kaynağı | OKY md.58/1 |
| TS-01…03 evrak teslim takibi | Okul uygulaması |

Bazı kurallar mevzuat değil **okul kararıdır** ve kod içinde böyle
etiketlenmiştir: salon başına bir gözcü sayılması, gözcünün sınav branşından
farklı seçilmesi, müdür ve rehber öğretmene sınav görevi verilmemesi.

## Veri ve gizlilik

Veritabanı Windows'ta `%LOCALAPPDATA%\SorumlulukSinavi\plan`, Pardus/Linux'ta
`~/.local/share/sorumluluk-sinavi/plan` altındadır. T.C. kimlik numarası okunmaz ve
saklanmaz. Denetim izi yalnız tablo adı, kayıt kimliği ve işlem türü tutar;
öğrenci adı veya numarası yazılmaz. Günlük dosyası kişisel veri içermez.

Veritabanını e-posta, kişisel bulut veya herkese açık depoya koymayın.

## Bilinmesi gerekenler

- **8. Dönem Toplu Sözleşme md.4** gereği 2025-2026 ve 2026-2027 öğretim
  yıllarında 12/15 sınırları uygulanmaz. Bu iki yıl `cekirdek/kurallar.py`
  içindeki `SINIRSIZ_OGRETIM_YILLARI` sabitindedir; 2027-2028'de yeni toplu
  sözleşmeye göre güncellenmelidir.
- e-Okul rapor biçimi değişirse sorumluluk raporu ayrıştırıcısı güncellenmelidir.
  Ayrıştırıcı sessizce yanlış okumaz, anlaşılır hata verir.
- Personel raporunda kurum sicil numarası sütunu yoksa aynı adlı iki öğretmen
  ayırt edilemez; bu durumda içe aktarma hata vererek durur.

## Yardım sayfası

Uygulamanın son adımı yardım sayfasıdır: sorumluluk sınavlarına ilişkin mevzuat
hükümleri (dayanak maddeleriyle), adım adım kullanım, planlama motorunun çalışma
mantığı ve e-Okul raporlarının doğru biçimde nasıl indirileceği burada yazılıdır.

## e-Okul raporlarını indirme

Rapor tarayıcıda bir görüntüleyicide açılır. Biçimlendirilmiş Excel çıktısı
birleşik hücreler ve tekrarlanan başlıklar içerdiği için okunamaz. Doğru yol:

1. Raporu **HTML5 görüntüleyici** ile açın.
2. Dışa aktarma menüsünden **Excel** biçimini seçin.
3. **SADECE VERİ** seçeneğini işaretleyin.
4. İnen dosyayı açıp kaydetmeden programa yükleyin.

Bu uyarı ilgili içe aktarma ekranlarının üstünde de yazılıdır. Dosya yanlış
biçimdeyse program sessizce yanlış okumaz; hangi başlığı bulamadığını söyleyerek
durur.

## Logo

Logo `araclar/logo_uret.py` betiğiyle koddan üretilir ve `varliklar/` altına
yazılır. Uygulama penceresinde, kenar çubuğunda, evrak antetinde ve Windows
uygulama simgesinde görünür. Renk ya da biçim değişirse betik yeniden
çalıştırılır; depoda elle güncellenen bir ikili dosya yoktur.

```bash
python araclar/logo_uret.py
```

## Lisans

Sorumluluk Sınavı, [PolyForm Noncommercial License 1.0.0](LICENSE) ile
yayımlanır. Eğitim kurumları, kamu kurumları, kâr amacı gütmeyen kuruluşlar ve
bireyler programı ticari olmayan amaçlarla kullanabilir. Bağlayıcı koşullar
`LICENSE`, telif bildirimi `NOTICE` dosyasındadır. Aynı bilgiler uygulamanın
Lisans sayfasında da yer alır.

Geliştirici: Ahmet Ali DEMİRCİ — aalidemirci@gmail.com

## Geliştirme

```bash
python -m venv .venv
.venv/Scripts/pip install -e .[test]
.venv/Scripts/python -m pytest
.venv/Scripts/python sorumluluk_sinavi.py
```

Kurulum ve paketleme KURULUM.md'de anlatılır.

Testler GitHub Actions'ta da koşar: her itmede Windows (Python 3.11 ve 3.12)
ve Pardus 23'ün tabanı olan Debian 12 kabı denenir, Pardus paketi de orada
üretilip kurularak açılıp açılmadığına bakılır.

### Proje belgeleri

| Dosya | İçerik |
|---|---|
| `CLAUDE.md` | Projede çalışırken uyulacak kurallar, değişmezler, katman düzeni |
| `CHANGELOG.md` | Sürüm sürüm değişiklik günlüğü |
| `PLAN.md` | Açık işler, takvime bağlı zorunluluklar, kapsam dışı konular |
| `kararlar/` | Mimari karar kayıtları: neyin neden öyle olduğu |
