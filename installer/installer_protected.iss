; installer/installer_protected.iss
; Installs built ZondEditor and initializes ProgramData license data.

#define AppName "ZondEditor"
#define AppExeName "ZondEditor.exe"
#define AppPublisher "ZondEditor"
#define AppVersion "0.1.0"
#define AppId "{{D942DBCC-A143-4E01-9CB8-3687B91FA6D6}}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist_installer
OutputBaseFilename={#AppName}_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\ZondEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{commonappdata}\{#AppName}"; Permissions: everyone-full
Name: "{commonappdata}\{#AppName}\logs"; Permissions: everyone-full

[Icons]
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
; Initialize ProgramData\ZondEditor\license.dat and logs folder
Filename: "{app}\{#AppExeName}"; Parameters: "--init-license"; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
