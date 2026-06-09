; MAKEVID Installer Script (Inno Setup)
; Baixar Inno Setup: https://jrsoftware.org/isdl.php
; Compilar: abrir este arquivo no Inno Setup Compiler e clicar Build

[Setup]
AppName=MAKEVID
AppVersion=1.0.0
AppPublisher=MAKEVID
DefaultDirName={autopf}\MAKEVID
DefaultGroupName=MAKEVID
OutputDir=installer\output
OutputBaseFilename=MAKEVID_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
; Tudo que o PyInstaller gerou em dist/MAKEVID/
Source: "dist\MAKEVID\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MAKEVID"; Filename: "{app}\MAKEVID.exe"
Name: "{commondesktop}\MAKEVID"; Filename: "{app}\MAKEVID.exe"

[Run]
Filename: "{app}\MAKEVID.exe"; Description: "Abrir MAKEVID"; Flags: nowait postinstall skipifsilent
