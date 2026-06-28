; LDKLauncher — Script do Inno Setup 6
; https://jrsoftware.org/isinfo.php
;
; Pré-requisito: compilar o PyInstaller primeiro (dist\LDKLauncher\ deve existir)
; Para compilar: abrir no Inno Setup e pressionar F9
; Saída: LDKLauncher-Setup.exe (na raiz do projeto)

#define AppName      "LDKLauncher"
#define AppVersion   "1.3.0"
#define AppExeName   "LDKLauncher.exe"
#define AppPublisher "LDK"
#define SourceDir    "..\dist\LDKLauncher"

[Setup]
; GUID único do app — NÃO alterar entre versões (seria tratado como app diferente pelo Windows)
AppId={{7E4A3B2C-9D1F-4E8A-B5C3-6F2D0E8A1B4C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppSupportURL=https://github.com/juliocmmo/LDKLauncher
DefaultDirName={commonpf32}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..
OutputBaseFilename=LDKLauncher-Setup
SetupIconFile=..\launcher\assets\ldkf.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Admin necessário para adicionar exclusão no Windows Defender
PrivilegesRequired=admin
UsedUserAreasWarning=no
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon";   Description: "Criar ícone na Área de Trabalho"; GroupDescription: "Ícones adicionais:"
Name: "startmenuicon"; Description: "Criar atalho no Menu Iniciar";    GroupDescription: "Ícones adicionais:"

[Files]
; Copia todo o conteúdo de dist\LDKLauncher\ para a pasta de instalação
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#AppName}";                                  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{autoprograms}\{#AppName}\{#AppName}";                      Filename: "{app}\{#AppExeName}"; Tasks: startmenuicon
Name: "{autoprograms}\{#AppName}\Desinstalar {#AppName}";          Filename: "{uninstallexe}";      Tasks: startmenuicon

[Run]
; Oferece abrir o launcher ao final da instalação
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName} agora"; Flags: nowait postinstall skipifsilent

[Code]
procedure AdicionarExclusaoDefender(Pasta: String);
var
  ResultCode: Integer;
begin
  Exec(
    'powershell.exe',
    '-NoProfile -WindowStyle Hidden -Command "Add-MpPreference -ExclusionPath ''' + Pasta + '''"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode
  );
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    AdicionarExclusaoDefender(ExpandConstant('{app}'));
    AdicionarExclusaoDefender('C:\LDKLauncher');
  end;
end;

function ObterPastaJogos(): String;
var
  ConfigFile: String;
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
begin
  Result := 'C:\LDKLauncher';

  ConfigFile := ExpandConstant('{localappdata}\LDKLauncher\config.json');
  TempFile   := ExpandConstant('{tmp}\ldk_install_dir.txt');

  if FileExists(ConfigFile) then
  begin
    Exec('powershell.exe',
      '-NoProfile -WindowStyle Hidden -Command ' +
      '"(Get-Content ''' + ConfigFile + ''' | ConvertFrom-Json).install_dir | ' +
      'Out-File -FilePath ''' + TempFile + ''' -Encoding utf8 -NoNewline"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    if LoadStringsFromFile(TempFile, Lines) and (GetArrayLength(Lines) > 0) then
      Result := Trim(Lines[0]);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DirDados: String;
  DirJogos: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DirJogos := ObterPastaJogos();

    DirDados := ExpandConstant('{localappdata}\LDKLauncher');
    if DirExists(DirDados) then
      DelTree(DirDados, True, True, True);

    if DirExists(DirJogos) then
    begin
      if MsgBox(
        'Deseja remover também a pasta de jogos?' + #13#10 +
        DirJogos + #13#10#13#10 +
        'Isso apagará todos os jogos instalados.',
        mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DirJogos, True, True, True);
    end;
  end;
end;