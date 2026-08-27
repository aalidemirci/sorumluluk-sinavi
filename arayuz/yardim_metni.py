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
            "Program, e-Okul'dan aldığınız iki raporu okuyup sorumluluk sınavlarının "
            "takvimini kurar, komisyon ve gözcüleri görevlendirir, evrakı üretir ve sınav "
            "sonrası geri alınan evrakı izler.",
            "Sınav sonrası işlemler kapsam dışıdır: sonuç ve puan girişi, itiraz, telafi, "
            "ek sınav, diploma tarihi ve disiplin işlemleri e-Okul'da yürütülür. Ek ders "
            "ücreti tutarı hesaplanmaz; yalnız görev sayacı tutulur, tahakkuk yetkili "
            "sistemde yapılır.",
            "Program hiçbir ağ isteği yapmaz. e-Okul, MEBBİS ya da başka bir sisteme "
            "bağlanmaz, kullanıcı adı veya şifre istemez. Yalnız sizin dışa aktardığınız "
            "dosyaları okur.",
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
            "edilmez. Program kayıt kaynağını ayrı tutar. (OKY md.58/1 son cümle)",
            "İçe aktarılan veride 3/6 tavanını aşan öğrenci bulunabilir; mezun olamayan "
            "12. sınıf öğrencisi bunun tipik örneğidir. Bu, içe aktarmada hata sayılmaz.",
        ],
    ),
    (
        "Sınav ne zaman yapılır",
        [
            "Sorumluluk sınavları birinci dönemin ilk iki haftası, ikinci dönemin ilk iki "
            "haftası ile son iki haftası içinde yapılır. Program bu üç pencereyi girdiğiniz "
            "dönem tarihlerinden hesaplar; pencereler koda gömülü değildir. (OKY md.58/2-a)",
            "Sınavlar dersleri aksatmayacak biçimde hafta içinde planlanır; gerektiğinde "
            "cumartesi ve pazar günleri de kullanılabilir. Program hafta sonunu ancak hafta "
            "içi yetmediğinde kullanır ve gerekçesini belgeye yazar. (OKY md.58/2-ç)",
            "Zorunlu hâller dışında yazılı sınav süresi bir ders saatini aşamaz. "
            "(ÖDY md.5/1-l)",
            "Bir günde yapılacak yazılı ve uygulamalı sınavların sayısının ikiyi geçmemesi "
            "esastır; zorunlu hâllerde bir sınav daha yapılabilir. Program bu sınırı öğrenci "
            "başına uygular. (ÖDY md.5/1-k)",
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
            "görevlendirilir. Program salon başına bir gözcü sayar; bu bir okul kararıdır. "
            "(OKY md.58/2-b)",
            "Bir sınavda aynı kişiye hem komisyon üyeliği hem gözcülük verilemez ve "
            "yöneticilere sınav görevi için ücret ödenmez. (Karar md.12/2-b, 2-c)",
            "Bir öğretim yılında bir kişiye 12'den fazla komisyon üyeliği ve 15'ten fazla "
            "gözcülük için ücret ödenmez. 8. Dönem Toplu Sözleşme md.4 gereği 2025-2026 ve "
            "2026-2027 öğretim yıllarında bu sınırlar uygulanmaz; sayaç yine tutulur. "
            "(Karar md.12/2-a)",
            "Müdüre ve rehber öğretmene sınav görevi verilmemesi, gözcünün sınav branşından "
            "farklı seçilmesi mevzuat hükmü değil okul kararıdır; program bunları böyle "
            "etiketler.",
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
            "ve uygulamalı olarak iki aşamada yapılır; komisyonların aynı üyelerden "
            "oluşturulması esastır. Program bu dersleri aynı günün ardışık iki saatine "
            "yerleştirir ve komisyonu korur. (OKY md.58/2-e)",
            "Hangi dersin iki aşamalı olduğuna Ders / Branş ekranında siz karar verirsiniz. "
            "Program ders adına bakarak öneri getirir ama kararı size bırakır.",
        ],
    ),
    (
        "Diğer hükümler",
        [
            "Okuldan mezun olamayan 12. sınıf öğrencileri ile devamsızlık tebligatı "
            "yapıldığı hâlde okula veya sınavlara katılımları sağlanamayan öğrenciler, "
            "sınav tarihinden 5 iş günü öncesine kadar yazılı talepte bulunmaları hâlinde "
            "plana dâhil edilir. (OKY md.58/2-d)",
            "Bir dersin sorumluluğu, o dersin sorumluluk sınavından en az 50 puan alınması "
            "hâlinde kalkar. Bu işlem e-Okul'da yapılır. (OKY md.58/4)",
            "Sorumluluk sınavlarına girenler için diploma tarihi, sınavların bitimini takip "
            "eden ilk iş günüdür. (OKY md.43/2-b)",
            "Okulda yapılan sınavlar, cevaplarını öğrencilerin oluşturduğu yazılı yoklama "
            "biçimindedir. (ÖDY md.5/1-g)",
        ],
    ),
    E_OKUL_INDIRME,
    (
        "Adım adım kullanım",
        [
            "Soldaki adımlar sırayla tamamlanır; her adım bir sonrakinin girdisidir.",
            "• 01 Kurum Ayarları — okul bilgileri ve üç dönem tarihi. Sınav pencereleri "
            "bu tarihlerden hesaplanır ve ekranın altında gösterilir.",
            "• 02 Öğretmen Listesi — OOK01001R1 personel raporunu yükleyin. Branş havuzu "
            "bu rapordan kurulur. Rapora yansımamış kişiyi elle ekleyebilir, ayrılan "
            "kişiyi pasife alabilirsiniz.",
            "• 03 Salonlar — salon sayısı ve kapasitesi, aynı saatte kaç sınav "
            "yapılabileceğini belirler.",
            "• 04 e-Okul Sorumluluk — OOK12001R010 raporunu yükleyin. Rapor okulun "
            "tamamını kapsıyorsa 'tam listedir' işaretli kalsın.",
            "• 05 Ders / Branş — her dersi bir branşa eşleyin, iki aşamalı dersleri "
            "işaretleyin. Eşlenmemiş ders varken plan üretilmez.",
            "• 06 Sınav Planı — parametreleri seçin, isterseniz önce 'Yükü çözümle' ile "
            "sonucu görün, sonra planı üretin. Sürükle-bırakla düzeltip kaydedin, müdür "
            "onayıyla kesinleştirin.",
            "• 07 Evrak ve Teslim — belgeleri üretin; sınavlardan sonra geri alınan evrakı "
            "çizelgeye işleyin.",
        ],
    ),
    (
        "Planlama motoru nasıl çalışır",
        [
            "Yerleştirme ve görevlendirme tek problem olarak çözülür: bir oturumun nereye "
            "konabileceği, o saatte komisyonun kurulup kurulamayacağına bağlıdır. Bu sayede "
            "aynı saatte birden fazla sınav yapılabilir ve program az sayıda güne sığar.",
            "Plan üretmeden önce üç şey sorulur: hafta sonu kullanılsın mı, bir öğrenci "
            "günde en çok kaç sınava girsin, iki aşamalı derste yazılı ve uygulama tek "
            "sınav mı yoksa ayrı ayrı mı sayılsın.",
            "Gün sayısı otomatik seçilir. Öğrencilerin çoğunluğunun sığdığı en kısa program "
            "denenir: önce bir hafta, sığmazsa iki hafta, o da yetmezse gereken kadar gün. "
            "Bu pencereye sığmayan tek tük öğrencinin günlük sınırı gereken en düşük değere "
            "çıkarılır ve adıyla raporlanır.",
            "Görev yükü kişiler arasında dengelenir. Bir öğretim yılında üç sınav dönemi "
            "olduğu için sayaçlar dönemler arasında taşınır: ikinci dönem planlanırken "
            "birinci dönemde çok görev almış öğretmen geri plana düşer.",
            "Aynı girdi her zaman aynı programı üretir. Plan üretilemezse program hangi "
            "kısıtın bağladığını söyler: salon sayısı, görevli kapasitesi, branş arzı ya da "
            "bir öğrencinin günlük oturum tavanı.",
            "Motorun ürettiği plan da elle düzenlenen plan da aynı doğrulayıcıdan geçer. "
            "Doğrulayıcı çözücüden bağımsızdır; kurallar tek yerde tanımlanır.",
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
            "Uygulamayı kapatıp veri klasöründeki veritabanı dosyasını kurumun yedek "
            "ortamına kopyalayın. Şema yükseltmelerinde program göç öncesi otomatik yedek "
            "alır. Gerçek veriyi e-posta, kişisel bulut veya herkese açık depoya koymayın.",
        ],
    ),
]
