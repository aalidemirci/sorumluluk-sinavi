; Sorumluluk Sınavı — Windows kurulum betiği (Inno Setup 6)
;
; Kurulum kullanıcı başınadır: yönetici hakkı istemez, Program Files'a
; yazmaz. Kullanıcı verisi kurulum klasöründe değil %LOCALAPPDATA% altında
; durduğu için kaldırma ve yükseltme veritabanına dokunmaz.
;
; Derlemek için:
;   iscc yapim\sorumluluk_sinavi.iss
; Öncesinde PyInstaller paketi üretilmiş olmalıdır:
;   python -m PyInstaller SorumlulukSinavi.spec --noconfirm

#define Ad          "Sorumluluk Sınavı"

; Sürüm tek kaynaktan okunur: cekirdek/surum.py içindeki
;   SURUM = "x.y.z"
; satırı ayrıştırılır. Burada elle sürüm yazmayın.
#define SurumDosyasi AddBackslash(SourcePath) + "..\cekirdek\surum.py"
#define public Surum ""
#define hSurum FileOpen(SurumDosyasi)
#sub SurumSatiriOku
  #define satir Trim(FileRead(hSurum))
  ; ISPP'de #sub icindeki #define yereldir; "public" olmadan disari cikmaz.
  #if Pos('SURUM = "', satir) == 1
    #define public Surum Copy(satir, 10, Len(satir) - 10)
  #endif
#endsub
#for {0; !FileEof(hSurum); 0} SurumSatiriOku
#expr FileClose(hSurum)
#if Surum == ""
  #error cekirdek/surum.py icinden SURUM okunamadi
#endif

#define Gelistirici "Ahmet Ali DEMİRCİ"
#define ExeAdi      "SorumlulukSinavi.exe"
#define Kaynak      "..\dist\SorumlulukSinavi"

[Setup]
AppId={{7C4F1B62-3E5A-4D18-9B7C-2A6E0F3D91C4}
AppName={#Ad}
AppVersion={#Surum}
AppVerName={#Ad} {#Surum}
AppPublisher={#Gelistirici}
VersionInfoVersion={#Surum}
VersionInfoDescription={#Ad} kurulumu

; Kullanıcı başına kurulum: yönetici hakkı gerekmez.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={localappdata}\SorumlulukSinavi\uygulama
DefaultGroupName={#Ad}
DisableProgramGroupPage=yes
AllowNoIcons=yes

OutputDir=..\dist-kurulum
OutputBaseFilename=SorumlulukSinavi-Kurulum-{#Surum}
SetupIconFile=..\varliklar\logo.ico
UninstallDisplayIcon={app}\{#ExeAdi}
UninstallDisplayName={#Ad} {#Surum}

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
LicenseFile=..\LICENSE
CloseApplications=yes
CloseApplicationsFilter=*.exe

[Languages]
Name: "turkce"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
turkce.KisayolOlustur=Masaüstü kısayolu oluştur
turkce.KurulumBitti={#Ad} kuruldu. Veritabanı ilk açılışta %LOCALAPPDATA%\SorumlulukSinavi\plan klasöründe oluşturulur; programı kaldırmak bu klasöre dokunmaz.

[Tasks]
Name: "masaustu"; Description: "{cm:KisayolOlustur}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller onedir çıktısının tamamı. _internal klasörü olmadan uygulama
; çalışmaz; recursesubdirs bunun için zorunludur.
Source: "{#Kaynak}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\BENIOKU.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\KURULUM.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#Ad}"; Filename: "{app}\{#ExeAdi}"
Name: "{group}\{cm:UninstallProgram,{#Ad}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#Ad}"; Filename: "{app}\{#ExeAdi}"; Tasks: masaustu

[Run]
Filename: "{app}\{#ExeAdi}"; Description: "{cm:LaunchProgram,{#Ad}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Yalnız uygulama klasöründeki kalıntılar silinir. Kullanıcı veritabanı
; %LOCALAPPDATA%\SorumlulukSinavi\plan altındadır ve kaldırılmaz.
Type: filesandordirs; Name: "{app}\_internal"
