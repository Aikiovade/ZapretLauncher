; A9/I3: Inno Setup 6 — кастомный установщик ZapretLauncher (только Tk-версия).
;
; Сборка:
;   pyinstaller --noconfirm Zapret.spec
;   iscc installer\zapret_launcher.iss
; Результат: dist\ZapretLauncher-<версия>-setup.exe
;
; Выбор интерфейса (WebView2/Tk) убран — вернём, когда будет готов интересный web-функционал.
; Кастомный UI: свои страницы (вступление/установка/финал), анимированный баннер
; (SetTimer + кадры), свой прогресс-бар, тёмный стиль, звуки.

#define AppName "ZapretLauncher"
#define AppVersion "17.4"
#define AppPublisher "Aikiovade"
#define AppURL "https://github.com/Aikiovade/ZapretLauncher"

[Setup]
AppId={{A1B6A0F4-8C2E-4E9B-9B3B-1F5C7D2A9E10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=ZapretLauncher-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\icon.ico
UninstallDisplayIcon={uninstallexe}
WizardStyle=modern dark includetitlebar
WizardSizePercent=115
WizardImageFile=wizard_image.bmp
WizardSmallImageFile=wizard_small.bmp
WizardImageBackColor=#0a0b1e
WizardBackImageFile=wizard_back.bmp
WizardBackImageOpacity=90
CloseApplications=yes
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoCopyright=MIT License
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
russian.SoundCaption=Звуковое сопровождение установки
english.SoundCaption=Installer sound effects
russian.IntroSub=Установка лаунчера обхода блокировок
english.IntroSub=DPI bypass launcher installation
russian.Feat1=• Обход YouTube и Discord (служба zapret, движок winws)
english.Feat1=• Bypass for YouTube and Discord (zapret service, winws engine)
russian.Feat2=• Ускорение Telegram (TgWsProxy)
english.Feat2=• Telegram acceleration (TgWsProxy)
russian.Feat3=• Авто-подбор стратегии, мониторинг сервисов, профили сети
english.Feat3=• Auto strategy pick, service monitoring, network profiles
russian.Feat4=• Автообновление, portable-режим, Discord Rich Presence
english.Feat4=• Auto-update, portable mode, Discord Rich Presence
russian.InfoLine=Установка в Program Files · ярлык на рабочем столе · служба обхода ставится автоматически
english.InfoLine=Installs to Program Files · desktop shortcut · bypass service is set up automatically
russian.FinishTitle=ВСЁ ГОТОВО!
english.FinishTitle=ALL DONE!
russian.FinishText={#AppName} {#AppVersion} установлен. Включайте обход большой кнопкой или хоткеем Ctrl+Shift+Z.
english.FinishText={#AppName} {#AppVersion} is installed. Enable the bypass with the big button or Ctrl+Shift+Z.
russian.BtnInstall=УСТАНОВИТЬ
english.BtnInstall=INSTALL
russian.BtnCancel=Отмена
english.BtnCancel=Cancel
russian.BtnClose=ЗАКРЫТЬ
english.BtnClose=CLOSE

[Dirs]
; E2: общий каталог данных с DACL (Administrators: Full, Users: Read & Execute)
Name: "{commonappdata}\ZapretLauncher"; Permissions: admins-full users-readexec

[InstallDelete]
; Чистим exe прошлой установки (в т.ч. ZapretWeb.exe, если он остался от старых сборок)
Type: files; Name: "{app}\Zapret.exe"
Type: files; Name: "{app}\ZapretWeb.exe"

[Files]
Source: "..\dist\Zapret.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\tools\uninstall.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "frames\anim_*.bmp"; Flags: dontcopy
Source: "progress_track.bmp"; Flags: dontcopy
Source: "progress_fill.bmp"; Flags: dontcopy
Source: "finish_banner.bmp"; Flags: dontcopy
Source: "sound_intro.wav"; Flags: dontcopy
Source: "sound_done.wav"; Flags: dontcopy

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Zapret.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Zapret.exe"

[Run]
; Служба обхода ставится один раз установщиком (повторные запуски — no-op). Elevated, как и Setup.
Filename: "{app}\Zapret.exe"; Parameters: "--install-service"; Flags: runhidden runascurrentuser; StatusMsg: "Установка службы обхода..."
; postinstall по умолчанию запускается БЕЗ прав админа (runasoriginaluser) — для exe с манифестом
; requireAdministrator это даёт CreateProcess 740, поэтому явно просим runascurrentuser.
Filename: "{app}\Zapret.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallRun]
; Чистим службу zapret/WinDivert, процессы, автозапуск, ярлыки и каталог данных.
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall.ps1"""; RunOnceId: "CleanupZapretComponents"; Flags: runhidden

[Code]
const
  FRAME_COUNT = 16;
  FRAME_MS = 120;

var
  IntroPage: TWizardPage;
  IntroBanner: TBitmapImage;
  IntroTitle: TNewStaticText;
  IntroSub: TNewStaticText;
  Feat1: TNewStaticText;
  Feat2: TNewStaticText;
  Feat3: TNewStaticText;
  Feat4: TNewStaticText;
  InfoLine: TNewStaticText;
  SoundCheck: TNewCheckBox;
  SoundEnabled: Boolean;

  InstallBanner: TBitmapImage;
  ProgressTrack: TBitmapImage;
  ProgressFill: TBitmapImage;
  PercentLabel: TNewStaticText;

  FinishBanner: TBitmapImage;
  FinishTitle: TNewStaticText;
  FinishText: TNewStaticText;

  FrameIdx: Integer;
  AnimTimer: UINT;
  ContentLeft, ContentWidth: Integer;

function mciSendString(lpszCommand: String; lpszReturnString: String; uReturnLen: Integer;
  hwndCallback: Integer): Integer; external 'mciSendStringW@winmm.dll stdcall';
function SetTimer(hWnd: HWND; nIDEvent: UINT; uElapse: UINT; uTimerFunc: LongWord): UINT;
  external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd: HWND; uIDEvent: UINT): BOOL; external 'KillTimer@user32.dll stdcall';

procedure PlaySoundFile(FileName: String; Alias: String);
begin
  if WizardSilent or (not SoundEnabled) then
    exit;
  try
    ExtractTemporaryFile(FileName);
  except
  end;
  mciSendString('close ' + Alias, '', 0, 0);
  mciSendString('open "' + ExpandConstant('{tmp}\') + FileName + '" type waveaudio alias ' + Alias, '', 0, 0);
  mciSendString('play ' + Alias, '', 0, 0);
end;

procedure SoundCheckClick(Sender: TObject);
begin
  SoundEnabled := SoundCheck.Checked;
  if SoundEnabled then
    PlaySoundFile('sound_intro.wav', 'zlaunch_intro')
  else
    mciSendString('close zlaunch_intro', '', 0, 0);
end;

function AddLabel(Parent: TWinControl; Left, Top, Width: Integer; Caption: String;
  Size: Integer; Bold: Boolean): TNewStaticText;
begin
  Result := TNewStaticText.Create(Parent);
  Result.Parent := Parent;
  Result.Left := Left;
  Result.Top := Top;
  Result.Width := Width;
  Result.AutoSize := False;
  Result.Caption := Caption;
  Result.Font.Name := 'Segoe UI';
  Result.Font.Size := Size;
  if Bold then
    Result.Font.Style := [fsBold];
end;

function AddImage(Parent: TWinControl; Left, Top, Width, Height: Integer;
  FileName: String): TBitmapImage;
begin
  Result := TBitmapImage.Create(Parent);
  Result.Parent := Parent;
  Result.Left := Left;
  Result.Top := Top;
  Result.Width := Width;
  Result.Height := Height;
  Result.Stretch := True;
  Result.Bitmap.LoadFromFile(ExpandConstant('{tmp}\') + FileName);
end;

function FrameName(Idx: Integer): String;
begin
  Result := 'anim_';
  if Idx < 10 then
    Result := Result + '0';
  Result := Result + IntToStr(Idx) + '.bmp';
end;

procedure LoadFrame(Img: TBitmapImage; Idx: Integer);
begin
  if Img = nil then
    exit;
  Img.Bitmap.LoadFromFile(ExpandConstant('{tmp}\') + FrameName(Idx));
end;

procedure AnimTick(hwnd: HWND; uMsg: UINT; idEvent: UINT; dwTime: DWORD);
begin
  FrameIdx := (FrameIdx + 1) mod FRAME_COUNT;
  LoadFrame(IntroBanner, FrameIdx);
  LoadFrame(InstallBanner, FrameIdx);
end;

procedure ExtractAssets();
var
  i: Integer;
begin
  for i := 0 to FRAME_COUNT - 1 do
    ExtractTemporaryFile(FrameName(i));
  ExtractTemporaryFile('progress_track.bmp');
  ExtractTemporaryFile('progress_fill.bmp');
  ExtractTemporaryFile('finish_banner.bmp');
  ExtractTemporaryFile('sound_intro.wav');
  ExtractTemporaryFile('sound_done.wav');
end;

procedure InitializeWizard();
var
  y: Integer;
begin
  ExtractAssets();
  SoundEnabled := True;

  { область контента: с учётом позиции большой картинки мастера (слева/справа/скрыта) }
  if not WizardForm.WizardBitmapImage.Visible then
  begin
    ContentLeft := ScaleX(18);
    ContentWidth := WizardForm.ClientWidth - ScaleX(34);
  end
  else if WizardForm.WizardBitmapImage.Left < (WizardForm.ClientWidth div 2) then
  begin
    ContentLeft := WizardForm.WizardBitmapImage.Left + WizardForm.WizardBitmapImage.Width + ScaleX(16);
    ContentWidth := WizardForm.ClientWidth - ContentLeft - ScaleX(16);
  end
  else
  begin
    ContentLeft := ScaleX(18);
    ContentWidth := WizardForm.WizardBitmapImage.Left - ContentLeft - ScaleX(16);
  end;
  if ContentWidth < ScaleX(300) then
  begin
    ContentLeft := ScaleX(18);
    ContentWidth := WizardForm.ClientWidth - ScaleX(34);
  end;

  { прячем стандартную шапку Inno }
  WizardForm.PageNameLabel.Visible := False;
  WizardForm.PageDescriptionLabel.Visible := False;
  WizardForm.Bevel.Visible := False;

  { --- страница 1: вступление --- }
  IntroPage := CreateCustomPage(wpWelcome, '', '');
  IntroBanner := AddImage(IntroPage.Surface, ContentLeft, ScaleY(8), ContentWidth, ScaleY(96), 'anim_00.bmp');
  IntroTitle := AddLabel(IntroPage.Surface, ContentLeft, IntroBanner.Top + IntroBanner.Height + ScaleY(6),
    ContentWidth, 'ZAPRET LAUNCHER', 16, True);
  IntroSub := AddLabel(IntroPage.Surface, ContentLeft, IntroTitle.Top + IntroTitle.Height + ScaleY(2),
    ContentWidth, ExpandConstant('{cm:IntroSub}'), 9, False);
  y := IntroSub.Top + IntroSub.Height + ScaleY(12);
  Feat1 := AddLabel(IntroPage.Surface, ContentLeft, y, ContentWidth, ExpandConstant('{cm:Feat1}'), 9, False);
  y := Feat1.Top + Feat1.Height + ScaleY(3);
  Feat2 := AddLabel(IntroPage.Surface, ContentLeft, y, ContentWidth, ExpandConstant('{cm:Feat2}'), 9, False);
  y := Feat2.Top + Feat2.Height + ScaleY(3);
  Feat3 := AddLabel(IntroPage.Surface, ContentLeft, y, ContentWidth, ExpandConstant('{cm:Feat3}'), 9, False);
  y := Feat3.Top + Feat3.Height + ScaleY(3);
  Feat4 := AddLabel(IntroPage.Surface, ContentLeft, y, ContentWidth, ExpandConstant('{cm:Feat4}'), 9, False);
  InfoLine := AddLabel(IntroPage.Surface, ContentLeft, Feat4.Top + Feat4.Height + ScaleY(12),
    ContentWidth, ExpandConstant('{cm:InfoLine}'), 8, False);
  SoundCheck := TNewCheckBox.Create(IntroPage.Surface);
  SoundCheck.Parent := IntroPage.Surface;
  SoundCheck.Left := ContentLeft;
  SoundCheck.Top := InfoLine.Top + InfoLine.Height + ScaleY(12);
  SoundCheck.Width := ContentWidth;
  SoundCheck.Caption := ExpandConstant('{cm:SoundCaption}');
  SoundCheck.Checked := True;
  SoundCheck.OnClick := @SoundCheckClick;
  SoundCheck.Font.Name := 'Segoe UI';
  SoundCheck.Font.Size := 8;

  { --- страница 2: установка --- }
  InstallBanner := AddImage(WizardForm.InstallingPage, ContentLeft, ScaleY(8), ContentWidth, ScaleY(96), 'anim_00.bmp');
  WizardForm.ProgressGauge.Visible := False;
  WizardForm.FilenameLabel.Visible := False;
  WizardForm.StatusLabel.Left := ContentLeft;
  WizardForm.StatusLabel.Top := InstallBanner.Top + InstallBanner.Height + ScaleY(14);
  WizardForm.StatusLabel.Width := ContentWidth;
  WizardForm.StatusLabel.AutoSize := False;
  WizardForm.StatusLabel.Font.Name := 'Segoe UI';
  WizardForm.StatusLabel.Font.Size := 9;
  ProgressTrack := AddImage(WizardForm.InstallingPage, ContentLeft,
    WizardForm.StatusLabel.Top + WizardForm.StatusLabel.Height + ScaleY(12),
    ContentWidth, ScaleY(16), 'progress_track.bmp');
  ProgressFill := AddImage(WizardForm.InstallingPage, ContentLeft, ProgressTrack.Top, 1, ScaleY(16), 'progress_fill.bmp');
  PercentLabel := AddLabel(WizardForm.InstallingPage, ContentLeft,
    ProgressTrack.Top + ProgressTrack.Height + ScaleY(6), ContentWidth, '0%', 8, True);

  { --- страница 3: финал --- }
  FinishBanner := AddImage(WizardForm.FinishedPage, ContentLeft, ScaleY(8), ContentWidth, ScaleY(96), 'finish_banner.bmp');
  WizardForm.FinishedHeadingLabel.Visible := False;
  WizardForm.FinishedLabel.Visible := False;
  FinishTitle := AddLabel(WizardForm.FinishedPage, ContentLeft,
    FinishBanner.Top + FinishBanner.Height + ScaleY(8), ContentWidth, ExpandConstant('{cm:FinishTitle}'), 15, True);
  FinishText := AddLabel(WizardForm.FinishedPage, ContentLeft,
    FinishTitle.Top + FinishTitle.Height + ScaleY(4), ContentWidth, ExpandConstant('{cm:FinishText}'), 9, False);
  WizardForm.RunList.Left := ContentLeft;
  WizardForm.RunList.Top := FinishText.Top + FinishText.Height + ScaleY(10);
  WizardForm.RunList.Width := ContentWidth;
  WizardForm.RunList.Font.Name := 'Segoe UI';
  WizardForm.RunList.Font.Size := 9;

  { --- кнопки: размеры НЕ трогаем (Inno позиционирует по правому краю — иначе наезжают) --- }
  WizardForm.NextButton.Font.Name := 'Segoe UI';
  WizardForm.NextButton.Font.Size := 10;
  WizardForm.NextButton.Font.Style := [fsBold];
  WizardForm.CancelButton.Font.Name := 'Segoe UI';
  WizardForm.CancelButton.Font.Size := 9;

  FrameIdx := 0;
  AnimTimer := SetTimer(0, 0, FRAME_MS, CreateCallback(@AnimTick));
  PlaySoundFile('sound_intro.wav', 'zlaunch_intro');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpWelcome) or (PageID = wpInfoBefore) or (PageID = wpSelectComponents)
    or (PageID = wpSelectDir) or (PageID = wpSelectTasks) or (PageID = wpReady);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = IntroPage.ID then
  begin
    WizardForm.NextButton.Caption := ExpandConstant('{cm:BtnInstall}');
    WizardForm.CancelButton.Caption := ExpandConstant('{cm:BtnCancel}');
    WizardForm.BackButton.Visible := False;
  end
  else if CurPageID = wpInstalling then
  begin
    WizardForm.BackButton.Visible := False;
  end
  else if CurPageID = wpFinished then
  begin
    mciSendString('close zlaunch_intro', '', 0, 0);
    PlaySoundFile('sound_done.wav', 'zlaunch_done');
    WizardForm.NextButton.Caption := ExpandConstant('{cm:BtnClose}');
    WizardForm.BackButton.Visible := False;
    WizardForm.CancelButton.Visible := False;
  end;
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
var
  w: Integer;
begin
  if MaxProgress > 0 then
    w := (ProgressTrack.Width * CurProgress) div MaxProgress
  else
    w := 0;
  if w < 1 then
    w := 1;
  ProgressFill.Width := w;
  if MaxProgress > 0 then
    PercentLabel.Caption := IntToStr((CurProgress * 100) div MaxProgress) + '%'
  else
    PercentLabel.Caption := '0%';
end;

procedure DeinitializeSetup();
begin
  if AnimTimer <> 0 then
    KillTimer(0, AnimTimer);
  mciSendString('close zlaunch_intro', '', 0, 0);
  mciSendString('close zlaunch_done', '', 0, 0);
end;
