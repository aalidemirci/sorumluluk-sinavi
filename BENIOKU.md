# Sorumluluk Sınavı

Ortaöğretim kurumlarında sorumluluk sınavı planlaması ve görevlendirmesi için
çevrimdışı çalışan masaüstü uygulaması.

Uygulama **hiçbir ağ isteği yapmaz.** e-Okul, MEBBİS, DYS veya başka bir resmî
sisteme bağlanmaz, kullanıcı adı ya da şifre istemez. Yalnız sizin dışa
aktardığınız dosyaları okur; ürettiği planın e-Okul'a girişi kullanıcı
tarafından elle yapılır.

## Ne yapar

1. e-Okul **OOK01001R1** personel raporunu içe aktarır; branş havuzu bu
   rapordan kurulur.
2. e-Okul **OOK12001R010** sorumluluk raporunu içe aktarır.
3. Dersleri branşlara eşler; iki aşamalı dersleri işaretler.
4. Sınav planını üretir: oturumları günlere ve saatlere yerleştirir,
   komisyon ve gözcüleri görevlendirir.
5. Planı sürükle-bırakla düzenletir, çakışmaları gösterir, müdür onayıyla
   kesinleştirir.

## Ne yapmaz

Sınav sonrası işlemler kapsam dışıdır: sonuç ve puan girişi, itiraz, telafi,
ek sınav, diploma tarihi ve disiplin işlemleri **e-Okul'da** yürütülür. Ek ders
ücreti hesaplanmaz; uygulama yalnız Karar md.12/2-a'daki 12 komisyon / 15
gözcülük sınırı için görev sayacı tutar, tutar hesabı MYS'de yapılır.

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

16 kural tek dosyada (`cekirdek/kurallar.py`) tanımlanır ve tek yerde
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
| SP-07 yazılı talep süresi | OKY md.58/2-d |
| SP-10 sınav süresi | ÖDY md.5/1-l |
| SP-11 günlük sınav sayısı | ÖDY md.5/1-k |
| SP-12 yazılı yoklama biçimi | ÖDY md.5/1-g |
| SP-14 BEP değerlendirme notu | ÖDY md.5/1-n |
| EK-03 aynı sınavda çifte rol yok | Karar md.12/2-b |
| EK-04 yönetici görevi ücretsizdir | Karar md.12/2-c |
| EK-05 yıllık görev sayacı | Karar md.12/2-a |
| SG-05, SG-06 sorumluluk kaynağı | OKY md.58/1 |
| TS-01…03 evrak teslim takibi | Okul uygulaması |

Bazı kurallar mevzuat değil **okul kararıdır** ve kod içinde böyle
etiketlenmiştir: salon başına bir gözcü sayılması, gözcünün sınav branşından
farklı seçilmesi, müdür ve rehber öğretmene sınav görevi verilmemesi.

## Veri ve gizlilik

Veritabanı Windows'ta `%LOCALAPPDATA%\SorumlulukSinavi\veri`, Linux'ta
`~/.local/share/sorumluluk-sinavi` altındadır. T.C. kimlik numarası okunmaz ve
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

## Geliştirme

```bash
python -m venv .venv
.venv/Scripts/pip install -e .[test]
.venv/Scripts/python -m pytest
.venv/Scripts/python sorumluluk_sinavi.py
```
