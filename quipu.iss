; Receta del instalador de Quipu (Inno Setup 6)

[Setup]
AppId={{7C3E2A91-4B5D-4F8E-9A21-6D0B3C8E5F14}
AppName=Quipu
AppVersion=1.1.0
AppPublisher=Eric
AppPublisherURL=https://quipu-app.github.io
AppSupportURL=https://quipu-app.github.io
VersionInfoVersion=1.1.0
VersionInfoCompany=Quipu
VersionInfoDescription=Instalador de Quipu
VersionInfoProductName=Quipu
VersionInfoCopyright=Copyright 2026 Eric
DefaultDirName={localappdata}\Programs\Quipu
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=instalador
OutputBaseFilename=Instalar-Quipu
SetupIconFile=quipu\assets\marca\q.ico
UninstallDisplayIcon={app}\Quipu.exe
UninstallDisplayName=Quipu
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "inicio"; Description: "Abrir Quipu al encender la compu"; GroupDescription: "Arranque:"; Flags: unchecked

[Files]
Source: "dist\Quipu\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Quipu"; Filename: "{app}\Quipu.exe"
Name: "{userdesktop}\Quipu"; Filename: "{app}\Quipu.exe"; Tasks: escritorio
Name: "{userstartup}\Quipu"; Filename: "{app}\Quipu.exe"; Tasks: inicio

[Run]
Filename: "{app}\Quipu.exe"; Description: "Abrir Quipu ahora"; Flags: nowait postinstall skipifsilent
Filename: "{app}\Quipu.exe"; Flags: nowait; Check: WizardSilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"