; Inno Setup Script for Screen Time Tracker
; Requires Inno Setup 6.0 or later

#define MyAppName "Screen Time Tracker"
#define MyAppNameNoSpace "ScreenTimeTracker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher ""
#define MyAppURL ""
#define MyAppExeName "ScreenTimeTracker.exe"
#define MyAppCopyright "Copyright (c) 2026"

[Setup]
AppId={{8A3F5B2C-9D1E-4F7A-8B6C-3E2D1A9F5B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoBeforeFile=
InfoAfterFile=
OutputDir=..\dist
OutputBaseFilename={#MyAppNameNoSpace}_Setup
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch at Windows startup"; GroupDescription: "Options:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start registry entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppNameNoSpace}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Check if application is running before uninstall
function InitializeUninstall(): Boolean;
begin
  if CheckForMutexes('Global\ScreenTimeTrackerMutex') then
  begin
    if MsgBox('Screen Time Tracker is currently running. Please close it before uninstalling.', mbError, MB_OK) = IDOK then
    begin
      Result := False;
      Exit;
    end;
  end;
  Result := True;
end;
