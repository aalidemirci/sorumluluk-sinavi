"""Yardım sayfasının içeriği.

Metin koddan ayrı tutulur: mevzuat değiştiğinde yalnız burası güncellenir.
Her bölüm (başlık, paragraflar) çiftidir; paragraflar arayüzde sırayla
yazılır ve "•" ile başlayanlar madde olarak girintilenir.
"""

from __future__ import annotations


E_OKUL_INDIRME = (
    "e-Okul raporunu doğru biçimde indirmek",
    [
        "e-Okul raporları tarayıcıda önce bir görüntüleyicide açılır. Rapor ekrandayken "
        "biçimlendirilmiş bir Excel dosyası indirirseniz satırlar birleşik hücreler ve "
        "başlık tekrarlarıyla gelir; program bu dosyayı okuyamaz.",
        "Doğru yol şudur:",
        "• Raporu e-Okul'da açın ve görüntüleyici seçeneklerinden HTML5 görüntüleyiciyi seçin.",
        "• Görüntüleyicinin dışa aktarma menüsünden Excel biçimini seçin.",
        "• Açılan seçeneklerde SADECE VERİ (yalnızca veri / data only) seçeneğini işaretleyin. "
        "Biçimlendirilmiş çıktı seçilmemelidir.",
        "• İnen .xls ya da .xlsx dosyasını hiç açıp kaydetmeden programa yükleyin.",
        "Dosya yanlış biçimde indirilmişse program sessizce yanlış okumaz; hangi başlığı "
        "bulamadığını söyleyerek durur.",
    ],
)

BOLUMLER = [
    (
        "Bu program ne yapar, ne yapmaz",
        [
            "Program şunları yapar:",
            "• e-Okul OOK01001R1 personel ve OOK12001R010 sorumluluk raporlarını okur,",
            "• sınav takvimini kurar; oturumları güne, saate ve salona yerleştirir, tatil "
            "günlerine sınav koymaz,",
            "• komisyon üyelerini ve gözcüleri görevlendirir; öğretmenin dersi, izni ya da "
            "başka görevi olan saatlere görev vermez, yükü üç dönem boyunca dengeler,",
            "• tek dersten başarısız kalan son sınıf öğrencisinin takip eden haftadaki "
            "sınavını planlar (OKY md.58/6),",
            "• sınav programı, görevlendirme çizelgesi, kişi bazlı görev çizelgesi, görev "
            "sayacı raporu ve web sayfasında yayımlanacak iki ilan çizelgesi üretir,",
            "• sınav sonrası komisyondan geri alınan evrakın teslim alınıp alınmadığını "
            "izler.",
            "Program şunları YAPMAZ; bunlar e-Okul'da ve okul müdürlüğünce yürütülür:",
            "• sınav sonucu ve puan girişi (tek ders sınavı dâhil), sorumluluğun kalkması,",
            "• sonuç itirazı ve telafi,",
            "• diploma tarihi hesabı, disiplin ve kopya işlemleri,",
            "• ek ders ücreti tutarının hesaplanması ve tahakkuku. Program yalnız görev "
            "sayacı tutar; tutar hesabı yetkili sistemde yapılır.",
            "• komisyon tutanağı, yoklama/salon listesi ve kâğıt sarf tutanağı üretimi — "
            "bunlar e-Okul'dan alınır.",
            "Program hiçbir ağ isteği yapmaz. e-Okul, MEBBİS ya da başka bir sisteme "
            "bağlanmaz, kullanıcı adı veya şifre istemez. Yalnız sizin dışa aktardığınız "
            "dosyaları okur.",
        ],
    ),
    (
        "Kısaltmalar ve dayanaklar",
        [
            "• OKY — Millî Eğitim Bakanlığı Ortaöğretim Kurumları Yönetmeliği "
            "(RG 07.09.2013/28758; son değişiklik RG 22.02.2025/32821).",
            "• ÖDY — Millî Eğitim Bakanlığı Ölçme ve Değerlendirme Yönetmeliği "
            "(RG 09.09.2023/32304).",
            "• Karar — Millî Eğitim Bakanlığı Yönetici ve Öğretmenlerinin Ders ve Ek Ders "
            "Saatlerine İlişkin Karar (01.12.2006 tarihli ve 2006/11350 sayılı BKK).",
            "• Toplu Sözleşme — 8. Dönem (2026–2027) Toplu Sözleşme, Eğitim, Öğretim ve Bilim "
            "Hizmet Kolu (RG 27.08.2025).",
            "• Resmî Yazışma Yönetmeliği — Resmî Yazışmalarda Uygulanacak Usul ve Esaslar "
            "Hakkında Yönetmelik (RG 10.06.2020/31151).",
            "Program kuralı mevzuattan değil okulun kendi kararından geliyorsa bunu "
            "\"okul kararı\" ya da \"okul uygulaması\" diye ayrıca yazar.",
        ],
    ),
    (
        "Sorumluluk nasıl doğar",
        [
            "Ders yılı sonunda her dersten iki dönem puanı bulunmak kaydıyla doğrudan "
            "sınıfını geçemeyen öğrencilerden yılsonu başarı puanı en az 50 olanlar, "
            "bulunduğu sınıfta başarısız oldukları en fazla 3 dersten sorumlu olarak "
            "sınıflarını geçer. Alt sınıflar dâhil toplam 6 dersten fazla başarısız dersi "
            "bulunanlar sınıf tekrar eder. (OKY md.58/1)",
            "Nakil ve geçişler nedeniyle ortaya çıkan sorumlu dersler bu sayıya dâhil "
            "edilmez. (OKY md.58/1 son cümle) Program 3/6 sayacını hesaplamaz; e-Okul "
            "raporundan okunan kayıtlar bu ayrımı taşımadığı için \"başarısızlık\" kaynağıyla "
            "alınır.",
            "İçe aktarılan veride 3/6 tavanını aşan öğrenci bulunabilir; mezun olamayan "
            "12. sınıf öğrencisi bunun tipik örneğidir. Bu, içe aktarmada hata sayılmaz.",
        ],
    ),
    (
        "Sınav ne zaman yapılır",
        [
            "Sorumluluk sınavları birinci dönemin ilk iki haftası, ikinci dönemin ilk iki "
            "haftası ile son iki haftası içinde yapılır. Program bu üç dönemi girdiğiniz "
            "dönem tarihlerinden hesaplar ve düştükleri aya göre Eylül, Şubat ve Haziran "
            "diye adlandırır; tarihler koda gömülü değildir. (OKY md.58/2-a)",
            "Sınavlar dersleri aksatmayacak şekilde hafta içinde planlanır; gerektiğinde "
            "cumartesi ve pazar günleri de kullanılabilir. Program hafta sonunu ancak hafta "
            "içi yetmediğinde kullanır ve gerekçesini belgeye yazar; gerekçe yazılması okul "
            "uygulamasıdır. (OKY md.58/2-ç)",
            "\"Dersleri aksatmayacak şekilde\" için öğretmenin dersi, izni ya da başka görevi "
            "olan saatleri Öğretmen Listesi ekranındaki \"Müsaitlik\" penceresine girin; "
            "planlayıcı bu saatlere görev vermez.",
            "Resmî tatil ve idari izin günlerini Kurum Ayarları ekranına girin. Program bu "
            "günlere sınav koymaz; başvurudaki 5 iş günü ile evrak teslim süresini "
            "hesaplarken bu günleri iş günü saymaz.",
            "Zorunlu hâller dışında yazılı sınav süresi bir ders saatini aşamaz (ÖDY md.5/1-l). "
            "Uygulamalı sınavın süresini zümre belirler (OKY md.45/1-f); plan ekranında ayrıca "
            "girilir.",
            "Bir günde yapılacak yazılı ve uygulamalı sınavların sayısının ikiyi geçmemesi "
            "esastır; zorunlu hâllerde bir sınav daha yapılabilir (ÖDY md.5/1-k). Program "
            "bu sınırı öğrenci başına uygular: ikiyi aşan gün uyarı, üçü aşan gün engel olarak "
            "görünür. Kısa takvim için çok dersi olan öğrencinin sınırı en çok üçe yükseltilir; "
            "üç de yetmiyorsa program daha uzun takvime geçer ya da hafta sonunu açmanızı ister.",
        ],
    ),
    (
        "Komisyon ve gözcü",
        [
            "Sınavlar iki alan öğretmeni, bulunmaması hâlinde biri alan öğretmeni olmak "
            "üzere iki öğretmen ve bir gözcü öğretmen tarafından yapılır. İkinci alan "
            "öğretmeni bulunamıyorsa program bunu gerekçe olarak belgeye yazar. "
            "(OKY md.58/2-a)",
            "Sınava girecek öğrenci sayısının otuzu aşması ve/veya birden fazla salonda "
            "sınav yapılması hâlinde her sınav salonu için ayrıca bir gözcü öğretmen daha "
            "görevlendirilir (OKY md.58/2-b). Program bir salona en çok 30 öğrenci koyar ve "
            "salon başına bir gözcü sayar; ikisi de okul kararıdır. Hangi gözcünün hangi "
            "salonda olduğu evrakta yazılır.",
            "Bir sınavda aynı kişiye hem komisyon üyeliği hem gözcülük verilmez; sınav iki "
            "öğretmen ve bir gözcü öğretmenle yapılır (OKY md.58/2-a), aynı sınavdaki iki rol "
            "için ücret de ödenmez (Karar md.12/2-b). Yöneticilere sınav görevi için ücret "
            "ödenmez (Karar md.12/2-c).",
            "Bir öğretim yılında bir kişiye 12'den fazla komisyon üyeliği ve 15'ten fazla "
            "gözcülük için ücret ödenmez (Karar md.12/2-a). Toplu sözleşme gereği "
            "01.01.2024 – 31.12.2027 tarihleri arasındaki sınav görevlerinde bu sınırlar "
            "uygulanmaz (8. Dönem Toplu Sözleşme, eğitim hizmet kolu md.4; 7. Dönemde de aynı "
            "hüküm vardı). Program sınırı görev tarihine göre uygular: askıdaki görevler yıl "
            "içi sayaca girer ama kendileri sınıra takılmaz, askı dışındaki görev yıl içi "
            "sırası 12'yi ya da 15'i aşıyorsa uyarı verir. Bu, iki hükmün birlikte "
            "okunmasında programın yorumudur.",
            "Müdüre ve rehber öğretmene sınav görevi verilmemesi, gözcünün sınav branşından "
            "farklı seçilmesi mevzuat hükmü değil okul kararıdır; program bunları böyle "
            "etiketler.",
            "Görevli plan ekranında değiştirilebilir: sınav kartına tıklayıp \"Görevliyi "
            "değiştir\"i seçin. Kesinleşmiş planda değişiklik müdür onay numarası ve "
            "gerekçeyle yapılır, görevlendirme çizelgesinde listelenir.",
        ],
    ),
    (
        "Birleştirme ve iki aşamalı dersler",
        [
            "Farklı sınıflardaki aynı dersin öğrenci sayısının toplamda otuzu aşmaması "
            "hâlinde bu öğrencilerin sınavları birleştirilerek tek komisyonla yapılabilir. "
            "Aynı öğrenci aynı dersin iki düzeyinden sorumluysa birleştirilemez, ayrı ayrı "
            "sınava alınır. (OKY md.58/2-c)",
            "Türk dili ve edebiyatı ile yabancı dil derslerinin sorumluluk sınavları yazılı "
            "ve uygulamalı olarak iki aşamada yapılır; yazılı ve uygulama için ayrı komisyon "
            "kurulur, komisyonların aynı üyelerden oluşturulması esastır. Yazılı ve uygulama "
            "sınavları sorumluluk sınavları dönemi içinde farklı günlerde de yapılabilir. "
            "(OKY md.58/2-e)",
            "Program iki aşamayı aynı günün ardışık iki saatine yerleştirir ve komisyonu "
            "korur. Plan ekranında yazılı kartını taşırsanız uygulama da birlikte gelir; "
            "uygulama kartını ise tek başına başka bir güne taşıyabilirsiniz.",
            "Hangi dersin iki aşamalı olduğuna Ders / Branş ekranında siz karar verirsiniz. "
            "Program ders adına bakarak öneri getirir ama kararı size bırakır.",
        ],
    ),
    (
        "Beklemeli ve devamsız öğrencinin başvurusu",
        [
            "Okuldan mezun olamayan 12. sınıf öğrencileri ile devamsızlık tebligatı "
            "yapıldığı hâlde okula veya sınavlara katılımları sağlanamayan öğrenciler "
            "otomatik olarak plana ALINMAZ; sınav tarihinden 5 iş günü öncesine kadar "
            "yazılı başvurmaları hâlinde dâhil edilir. (OKY md.58/2-d)",
            "Akış şudur: önce duyuru yayımlanır, sonra başvurular toplanır, en son plan "
            "üretilir ve takvim ilan edilir. Başvuru bu yüzden bir oturuma değil pencereye "
            "bağlanır — mevzuat başvuruyu plandan önce ister.",
            "e-Okul sorumluluk raporu bu iki grubu ayırt etmez; öğrencileri Başvuru "
            "adımında elle işaretlersiniz. İşaret konduğu öğretim yılına aittir: yeni yılda "
            "program önceki yıldan kalan işaretleri gözden geçirmenizi ister. Başvuru her "
            "dönemde yenilenir: Eylülde başvuran öğrenci Şubata başvurmuş sayılmaz.",
            "Mevzuattaki süre sınav tarihine bağlıdır. Okul tek bir başvuru son günü ilan "
            "ettiğinde program bu günün, pencerenin en erken gününden en az 5 iş günü önce "
            "olmasını arar; böylece son güne kadar başvuran herkes kendi sınav tarihinden "
            "5 iş günü önce başvurmuş olur. Tatil günleri iş günü sayılmaz.",
            "Son günü kaçıran başvuru reddedilemez. Mevzuat “bildirmeleri hâlinde plana "
            "dâhil edilir” der; okulun ilan ettiği son gün iç düzenlemedir ve bu hakkı "
            "ortadan kaldırmaz. Böyle bir başvuru, fiilî sınav tarihinden en az 5 iş günü "
            "önce yapılmışsa müdür onayıyla plana eklenir.",
            "Duyurunun pencereden 15 gün önce yayımlanması okul uygulamasıdır; mevzuatta "
            "duyuru süresi yoktur. Program geç duyuruda uyarır ama engellemez.",
            "Başvuru adımından iki belge üretilir: web sayfasında yayımlanacak başvuru "
            "duyurusu (kişi adı taşımaz) ve plan dışı bırakılanların tutanağı (okul içi "
            "kayıttır, ilan edilmez).",
        ],
    ),
    (
        "Tek ders sınavı (OKY md.58/6)",
        [
            "Sorumluluk sınavı sonunda tek dersten başarısızlığı bulunan son sınıf "
            "öğrencileri için aynı usulle takip eden hafta içinde bir sınav daha yapılır. "
            "(OKY md.58/6)",
            "Sınav Planı ekranında dönem kutusundan \"… — tek ders (58/6)\" seçeneğini seçin. "
            "\"Tek ders öğrencileri\" penceresi o dönemin planındaki 12. sınıf öğrencilerini "
            "ve derslerini listeler; e-Okul'daki sonuçlara bakarak öğrencinin başarısız "
            "kaldığı tek dersi seçin. Program sonuçları bilmez.",
            "Takip eden hafta, olağan plandaki son sınavın haftasından sonraki "
            "pazartesi–pazar aralığıdır. Plan aynı usulle kurulur: komisyon, gözcü, iki "
            "aşamalı dersler ve günlük sınır aynen uygulanır. Görevler yıllık görev sayacına "
            "bağlı olduğu dönemin sütununda girer. Gerekçe: kararlar/0010.",
        ],
    ),
    (
        "Program dışında kalan hükümler",
        [
            "Aşağıdaki hükümler sorumluluk sınavlarıyla ilgilidir ama programın işlemediği "
            "konulardır; burada başvuru kolaylığı için yer alır. Bu işleri e-Okul'da ya da "
            "okul müdürlüğü kayıtlarında yürütürsünüz.",
            "• Bir dersin sorumluluğu, o dersin sorumluluk sınavından en az 50 puan "
            "alınması hâlinde kalkar. (OKY md.58/4)",
            "• Sorumluluk sınavlarına itiraz edilmesi durumunda OKY md.49 uygulanır. "
            "(OKY md.58/5)",
            "• Sorumluluk sınavlarına girenler için diploma tarihi, sınavların bitimini "
            "takip eden ilk iş günüdür. (OKY md.69/2-b)",
            "• Okulda yapılan sınavlar, cevaplarını öğrencilerin oluşturduğu yazılı yoklama "
            "biçimindedir. (ÖDY md.5/1-g)",
            "• Kaynaştırma/bütünleştirme yoluyla eğitim gören öğrencinin başarısı BEP'teki "
            "amaçlara göre değerlendirilir. (ÖDY md.5/1-n)",
        ],
    ),
    E_OKUL_INDIRME,
    (
        "Adım adım kullanım",
        [
            "Soldaki adımlar sırayla tamamlanır; her adım bir sonrakinin girdisidir.",
            "• 01 Kurum Ayarları — okul bilgileri, üç dönem tarihi (gg.aa.yyyy), evrak "
            "anteti ve düzenleyen bilgisi; tatil ve idari izin günleri; yedek alma.",
            "• 02 Öğretmen Listesi — OOK01001R1 personel raporunu yükleyin. Branş havuzu "
            "bu rapordan kurulur. Rapora yansımamış kişiyi elle ekleyebilir, ayrılan "
            "kişiyi pasife alabilir, dolu saatlerini \"Müsaitlik\" penceresine girebilirsiniz.",
            "• 03 Salonlar — salon sayısı ve kapasitesi, aynı saatte kaç sınav "
            "yapılabileceğini belirler.",
            "• 04 e-Okul Sorumluluk — OOK12001R010 raporunu yükleyin. Rapor okulun "
            "tamamını kapsıyorsa 'tam listedir' işaretli kalsın.",
            "• 05 Başvuru — beklemeli ve devamsız öğrencileri işaretleyin, duyuruyu "
            "kaydedin ve başvuru kararlarını girin. Bu adım atlanırsa bu öğrenciler "
            "plana alınmaz; diğer öğrenciler etkilenmez. (OKY md.58/2-d)",
            "• 06 Ders / Branş — her dersi bir branşa eşleyin, iki aşamalı dersleri "
            "işaretleyin. Eşlenmemiş ders varken plan üretilmez.",
            "• 07 Sınav Planı — dönemi ve parametreleri seçin, isterseniz önce 'Yükü "
            "çözümle' ile sonucu görün, sonra planı üretin. Sürükle-bırakla ve görevli "
            "değişikliğiyle düzeltip kaydedin, müdür onayıyla kesinleştirin. Kesinleşmiş "
            "planın yerine yeni plan kaydedilmez.",
            "• 08 Evrak ve Teslim — plan belgelerini üretin; sınavlardan sonra komisyondan "
            "geri alınan evrakı çizelgeye işleyin. Başvuru duyurusu ve plan dışı tutanağı "
            "05 Başvuru adımından üretilir, çünkü ikisi de plandan önce doğar.",
            "• 09 Yardım, 10 Lisans — bu sayfa ve program bilgisi.",
        ],
    ),
    (
        "Planlama motoru nasıl çalışır",
        [
            "Yerleştirme ve görevlendirme tek problem olarak çözülür: bir oturumun nereye "
            "konabileceği, o saatte komisyonun kurulup kurulamayacağına bağlıdır. Bu sayede "
            "aynı saatte birden fazla sınav yapılabilir ve program az sayıda güne sığar. "
            "Öğretmen müsaitliği de bu hesaba girer: bir saatte müsait öğretmen yoksa o "
            "saate o branşın sınavı konmaz.",
            "Plan üretmeden önce şunlar sorulur: hafta sonu kullanılsın mı, bir öğrenci "
            "günde en çok kaç sınava girsin (1–3), iki aşamalı derste yazılı ve uygulama tek "
            "sınav mı yoksa ayrı ayrı mı sayılsın, uygulama sınavı kaç dakika sürsün.",
            "Gün sayısı otomatik seçilir. Öğrencilerin çoğunluğunun sığdığı en kısa program "
            "denenir: önce bir hafta, sığmazsa iki hafta, o da yetmezse gereken kadar gün. "
            "Bu pencereye sığmayan tek tük öğrencinin günlük sınırı gereken en düşük değere, "
            "en çok üçe çıkarılır ve adıyla raporlanır.",
            "Arama her adımda yerleştirilecek yeri en az kalan sınavı önce yerleştirir ve "
            "bir sınavı koyunca o günün diğer sınavlar için kalan yerlerini hemen günceller; "
            "çıkmaza giren yol erkenden bırakılır. Arama bütçesi süreyle değil adım sayısıyla "
            "tutulur: aynı girdi her bilgisayarda aynı programı üretir.",
            "Plan üretilemezse program hangi kısıtın bağladığını söyler: salon sayısı, "
            "görevli kapasitesi, branş arzı, müsaitlik ya da bir öğrencinin günlük sınav "
            "tavanı.",
            "Motorun ürettiği plan da elle düzenlenen plan da aynı doğrulayıcıdan geçer. "
            "Doğrulayıcı çözücüden bağımsızdır; kurallar tek yerde tanımlanır.",
        ],
    ),
    (
        "Evrak biçimi",
        [
            "Evrak Resmî Yazışma Yönetmeliği'ne göre düzenlenir: A4, Times New Roman 12 "
            "punto (tablolarda gerektiğinde 9 puntoya kadar), üst, sol ve sağda 1,5 cm boşluk, "
            "\"T.C. / İDARE ADI / Birim adı\" başlığı (md.6, 7, 8, 10). Renk kullanılmaz; "
            "evrak siyah-beyaz yazıcıdan çıkar.",
            "Başlığın ikinci satırı ilçe okulunda \"… KAYMAKAMLIĞI\", merkez ilçede "
            "\"… VALİLİĞİ\"dir; Kurum Ayarları'ndan değiştirilebilir. İmza bloğunda "
            "düzenleyenin adı ve unvanı ile müdürün OLUR'u (tarih satırı ve \"Okul Müdürü\" "
            "unvanıyla) yer alır.",
            "Evrak EBYS/DYS kayıt numarası ve güvenli elektronik imza ibaresi üretmez; okulun "
            "kendi kayıtlarından hazırlanmış çıktılardır.",
        ],
    ),
    (
        "Veri, gizlilik ve yedekleme",
        [
            "Veritabanı yalnız bu bilgisayardadır. T.C. kimlik numarası okunmaz ve "
            "saklanmaz. Denetim izi yalnız tablo adı, kayıt kimliği ve işlem türü tutar; "
            "öğrenci adı veya numarası yazılmaz.",
            "Okul web sayfasında yayımlanmak üzere üretilen iki çizelgede öğrencinin açık "
            "adı hiçbir seçenekte yazılmaz; öğrenci kendi satırını okul numarasından bulur. "
            "Sınav takviminde ise hiçbir kişi adı geçmez.",
            "Müsaitlik ve görevli değişikliği açıklamalarına sağlık bilgisi yazmayın "
            "(KVKK özel nitelikli kişisel veri); \"izinli\", \"derste\" gibi yazmak yeter.",
            "Kurum Ayarları'ndaki \"Yedek al\" düğmesi veritabanının tam yedeğini seçtiğiniz "
            "klasöre alır. Şema yükseltmelerinde program göç öncesi otomatik yedek alır. "
            "Gerçek veriyi e-posta, kişisel bulut veya herkese açık depoya koymayın.",
        ],
    ),
]


LISANS_BOLUMLERI = [
    (
        "Geliştirici",
        [
            "Ahmet Ali DEMİRCİ — aalidemirci@gmail.com",
            "Bir ortaöğretim kurumunda çalışıyorum. Bu program, okulda karşılaştığım "
            "sorumluluk sınavı planlama ve görevlendirme işini elle yürütmenin zorluğundan "
            "doğdu; mevzuata bağlı kalarak, kurum verisini dışarı çıkarmadan çalışacak "
            "biçimde geliştirildi.",
        ],
    ),
    (
        "Lisans",
        [
            "Sorumluluk Sınavı, PolyForm Noncommercial License 1.0.0 ile yayımlanır. "
            "Tam metin uygulama klasöründeki LICENSE dosyasındadır; telif bildirimi "
            "NOTICE dosyasındadır.",
            "Bu lisans kapsamında programı ticari olmayan amaçlarla kullanabilecekler:",
            "• eğitim kurumları ve kamu kurumları,",
            "• kâr amacı gütmeyen kuruluşlar,",
            "• kişisel kullanım için bireyler.",
            "Ticari kullanım lisans kapsamı dışındadır. Programı değiştirebilir ve "
            "dağıtabilirsiniz; bu durumda telif bildirimi ile lisans metnini birlikte "
            "iletmeniz gerekir.",
            "Program olduğu gibi, herhangi bir garanti verilmeksizin sunulur. Ürettiği "
            "plan, görevlendirme ve evrakın mevzuata ve kurum uygulamasına uygunluğunu "
            "onaylamak kullanıcının sorumluluğundadır.",
        ],
    ),
    (
        "Üçüncü taraf bileşenler",
        [
            "Uygulama şu açık kaynaklı paketleri kullanır:",
            "• openpyxl (MIT) — .xlsx okuma",
            "• xlrd (BSD) — .xls okuma",
            "• python-docx (MIT) — .docx üretimi",
            "• tzdata (Apache-2.0) — IANA saat dilimi verisi",
            "Uygulama simgesi ve evrak düzeni bu projeye aittir; üçüncü taraf görsel "
            "varlık içermez.",
        ],
    ),
    (
        "Veri sorumluluğu",
        [
            "Program hiçbir ağ isteği yapmaz; veri yalnız bu bilgisayarda kalır. "
            "Öğrenci, veli ve personel verisi 6698 sayılı Kanun kapsamındadır. "
            "Veritabanını e-posta, kişisel bulut veya herkese açık depoya koymayın.",
            "Sorun bildiriminde günlük dosyası paylaşılabilir; günlük kişisel veri "
            "içermeyecek biçimde yazılır. Yine de kurum dışına çıkarmadan önce gözle "
            "kontrol edin.",
        ],
    ),
]
