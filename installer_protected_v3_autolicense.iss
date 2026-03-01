; installer_protected_v3_autolicense.iss
; Inno Setup script for ZondEditor with auto-license initialization on install
; Requires app supports: ZondEditor.exe --init-license

#define AppName "ZondEditor"
#define AppExeName "ZondEditor.exe"
#define AppPublisher "ZondEditor"
#define AppVersion "3.0.1"
#define AppId "{{9B4F6D71-7B6F-4E1B-9B1A-7E4D8A2D4F11}}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist_installer
OutputBaseFilename={#AppName}_protected_setup_v3_autolicense
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"; Flags: unchecked

[Files]
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "SZ_icon_transparent_bg_only_adaptive.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
Name: "{commonappdata}\{#AppName}"; Permissions: everyone-full
Name: "{commonappdata}\{#AppName}\logs"; Permissions: everyone-full

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; 1) init license silently
Filename: "{app}\{#AppExeName}"; Parameters: "--init-license"; Flags: runhidden waituntilterminated
; 2) launch app for user
Filename: "{app}\{#AppExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
