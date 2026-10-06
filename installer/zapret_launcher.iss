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
#define AppVersion "17.5"
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
russian.InfoLine=Установка в Program Files · ярлыки и служба обхода создаются автоматически
english.InfoLine=Installs to Program Files · shortcuts and the bypass service are created automatically
russian.FinishTitle=ВСЁ ГОТОВО!
english.FinishTitle=ALL DONE!
russian.FinishText=Обход включается большой кнопкой или хоткеем Ctrl+Shift+Z.
english.FinishText=Toggle the bypass with the big button or Ctrl+Shift+Z.
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
Source: "banner.bmp"; Flags: dontcopy
Source: "progress_track.bmp"; Flags: dontcopy
Source: "progress_fill.bmp"; Flags: dontcopy
Source: "finish_banner.bmp"; Flags: dontcopy

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
  CLOSE_SECONDS = 5;
  BM_CLICK = $00F5;

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

  InstallBanner: TBitmapImage;
  ProgressTrack: TBitmapImage;
  ProgressFill: TBitmapImage;
  PercentLabel: TNewStaticText;

  FinishBanner: TBitmapImage;
  FinishTitle: TNewStaticText;
  FinishText: TNewStaticText;

  CloseCountdown: Integer;
  CloseTimer: UINT;
  IntroLeft, IntroWidth: Integer;
  FinishLeft, FinishWidth: Integer;

function SetTimer(hWnd: HWND; nIDEvent: UINT; uElapse: UINT; uTimerFunc: LongWord): UINT;
  external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd: HWND; uIDEvent: UINT): BOOL; external 'KillTimer@user32.dll stdcall';
function SetFocus(hWnd: HWND): HWND; external 'SetFocus@user32.dll stdcall';
function SendMessage(hWnd: HWND; Msg: UINT; wParam: Longint; lParam: Longint): Longint;
  external 'SendMessageW@user32.dll stdcall';

{ Финальная страница закрывается сама через CLOSE_SECONDS секунд (как нажатие «ЗАКРЫТЬ») }
procedure CloseTick(hwnd: HWND; uMsg: UINT; idEvent: UINT; dwTime: DWORD);
begin
  CloseCountdown := CloseCountdown - 1;
  if CloseCountdown <= 0 then
  begin
    if CloseTimer <> 0 then
    begin
      KillTimer(0, CloseTimer);
      CloseTimer := 0;
    end;
    SendMessage(WizardForm.NextButton.Handle, BM_CLICK, 0, 0);
  end
  else
    WizardForm.NextButton.Caption := ExpandConstant('{cm:BtnClose}') + ' (' + IntToStr(CloseCountdown) + ')';
end;

function AddLabel(Parent: TWinControl; Left, Top, Width: Integer; Caption: String;
  Size: Integer; Bold: Boolean): TNewStaticText;
begin
  Result := TNewStaticText.Create(Parent);
  Result.Parent := Parent;
  Result.Left := Left;
  Result.Top := Top;
  Result.Width := Width;
  { AutoSize: иначе высота остаётся дефолтной и крупные шрифты обрезаются }
  Result.AutoSize := True;
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

{ Баннер по центру доступной ширины с сохранением пропорций картинки }
function AddBanner(Parent: TWinControl; Left, Top, MaxWidth, MaxHeight: Integer;
  FileName: String): TBitmapImage;
var
  bmpW, bmpH, w, h: Integer;
begin
  Result := TBitmapImage.Create(Parent);
  Result.Parent := Parent;
  Result.Stretch := True;
  Result.Bitmap.LoadFromFile(ExpandConstant('{tmp}\') + FileName);
  bmpW := Result.Bitmap.Width;
  bmpH := Result.Bitmap.Height;
  if (bmpW <= 0) or (bmpH <= 0) then
  begin
    w := MaxWidth;
    h := MaxHeight;
  end
  else
  begin
    w := MaxWidth;
    h := (MaxWidth * bmpH) div bmpW;
    if h > MaxHeight then
    begin
      h := MaxHeight;
      w := (MaxHeight * bmpW) div bmpH;
    end;
  end;
  Result.Left := Left + (MaxWidth - w) div 2;
  Result.Top := Top;
  Result.Width := w;
  Result.Height := h;
end;

{ Кастомные страницы (вступление/установка) большую картинку мастера НЕ показывают —
  им нужна полная ширина; финальная страница картинку показывает — резервируем её. }
procedure ComputeLayout();
begin
  IntroLeft := ScaleX(18);
  IntroWidth := WizardForm.ClientWidth - ScaleX(36);

  if WizardForm.WizardBitmapImage.Visible then
  begin
    if WizardForm.WizardBitmapImage.Left < (WizardForm.ClientWidth div 2) then
    begin
      FinishLeft := WizardForm.WizardBitmapImage.Left + WizardForm.WizardBitmapImage.Width + ScaleX(18);
      FinishWidth := WizardForm.ClientWidth - FinishLeft - ScaleX(18);
    end
    else
    begin
      FinishLeft := ScaleX(18);
      FinishWidth := WizardForm.WizardBitmapImage.Left - FinishLeft - ScaleX(18);
    end;
  end
  else
  begin
    FinishLeft := ScaleX(18);
    FinishWidth := WizardForm.ClientWidth - ScaleX(36);
  end;

  if FinishWidth < ScaleX(260) then
  begin
    FinishLeft := ScaleX(18);
    FinishWidth := WizardForm.ClientWidth - ScaleX(36);
  end;
end;

procedure ExtractAssets();
begin
  ExtractTemporaryFile('banner.bmp');
  ExtractTemporaryFile('progress_track.bmp');
  ExtractTemporaryFile('progress_fill.bmp');
  ExtractTemporaryFile('finish_banner.bmp');
end;

procedure InitializeWizard();
var
  y: Integer;
begin
  ExtractAssets();
  ComputeLayout();

  { прячем стандартную шапку Inno }
  WizardForm.PageNameLabel.Visible := False;
  WizardForm.PageDescriptionLabel.Visible := False;
  WizardForm.Bevel.Visible := False;

  { --- страница 1: вступление (статичный баннер, без звука) --- }
  IntroPage := CreateCustomPage(wpWelcome, '', '');
  IntroBanner := AddBanner(IntroPage.Surface, IntroLeft, ScaleY(8), IntroWidth, ScaleY(100), 'banner.bmp');
  IntroTitle := AddLabel(IntroPage.Surface, IntroLeft, IntroBanner.Top + IntroBanner.Height + ScaleY(12),
    IntroWidth, 'ZAPRET LAUNCHER', 16, True);
  IntroSub := AddLabel(IntroPage.Surface, IntroLeft, IntroTitle.Top + IntroTitle.Height + ScaleY(4),
    IntroWidth, ExpandConstant('{cm:IntroSub}'), 9, False);
  y := IntroSub.Top + IntroSub.Height + ScaleY(14);
  Feat1 := AddLabel(IntroPage.Surface, IntroLeft, y, IntroWidth, ExpandConstant('{cm:Feat1}'), 9, False);
  y := Feat1.Top + Feat1.Height + ScaleY(5);
  Feat2 := AddLabel(IntroPage.Surface, IntroLeft, y, IntroWidth, ExpandConstant('{cm:Feat2}'), 9, False);
  y := Feat2.Top + Feat2.Height + ScaleY(5);
  Feat3 := AddLabel(IntroPage.Surface, IntroLeft, y, IntroWidth, ExpandConstant('{cm:Feat3}'), 9, False);
  y := Feat3.Top + Feat3.Height + ScaleY(5);
  Feat4 := AddLabel(IntroPage.Surface, IntroLeft, y, IntroWidth, ExpandConstant('{cm:Feat4}'), 9, False);
  InfoLine := AddLabel(IntroPage.Surface, IntroLeft, Feat4.Top + Feat4.Height + ScaleY(16),
    IntroWidth, ExpandConstant('{cm:InfoLine}'), 8, False);

  { --- страница 2: установка (статичный баннер, без звука) --- }
  InstallBanner := AddBanner(WizardForm.InstallingPage, IntroLeft, ScaleY(8), IntroWidth, ScaleY(100), 'banner.bmp');
  WizardForm.ProgressGauge.Visible := False;
  WizardForm.FilenameLabel.Visible := False;
  WizardForm.StatusLabel.Left := IntroLeft;
  WizardForm.StatusLabel.Top := InstallBanner.Top + InstallBanner.Height + ScaleY(16);
  WizardForm.StatusLabel.Width := IntroWidth;
  WizardForm.StatusLabel.AutoSize := False;
  WizardForm.StatusLabel.Font.Name := 'Segoe UI';
  WizardForm.StatusLabel.Font.Size := 9;
  ProgressTrack := AddImage(WizardForm.InstallingPage, IntroLeft,
    WizardForm.StatusLabel.Top + WizardForm.StatusLabel.Height + ScaleY(14),
    IntroWidth, ScaleY(16), 'progress_track.bmp');
  ProgressFill := AddImage(WizardForm.InstallingPage, IntroLeft, ProgressTrack.Top, 1, ScaleY(16), 'progress_fill.bmp');
  PercentLabel := AddLabel(WizardForm.InstallingPage, IntroLeft,
    ProgressTrack.Top + ProgressTrack.Height + ScaleY(8), IntroWidth, '0%', 8, True);

  { --- страница 3: финал (большая картинка слева — учитываем) --- }
  FinishBanner := AddBanner(WizardForm.FinishedPage, FinishLeft, ScaleY(6), FinishWidth, ScaleY(96), 'finish_banner.bmp');
  WizardForm.FinishedHeadingLabel.Visible := False;
  WizardForm.FinishedLabel.Visible := False;
  FinishTitle := AddLabel(WizardForm.FinishedPage, FinishLeft,
    FinishBanner.Top + FinishBanner.Height + ScaleY(10), FinishWidth, ExpandConstant('{cm:FinishTitle}'), 15, True);
  FinishText := AddLabel(WizardForm.FinishedPage, FinishLeft,
    FinishTitle.Top + FinishTitle.Height + ScaleY(4), FinishWidth, ExpandConstant('{cm:FinishText}'), 9, False);
  WizardForm.RunList.Left := FinishLeft;
  WizardForm.RunList.Top := FinishText.Top + FinishText.Height + ScaleY(10);
  WizardForm.RunList.Width := FinishWidth;
  WizardForm.RunList.Height := WizardForm.FinishedPage.Height - WizardForm.RunList.Top - ScaleY(12);
  if WizardForm.RunList.Height < ScaleY(40) then
    WizardForm.RunList.Height := ScaleY(40);
  WizardForm.RunList.Font.Name := 'Segoe UI';
  WizardForm.RunList.Font.Size := 9;

  { --- кнопки: размеры НЕ трогаем (Inno позиционирует по правому краю — иначе наезжают) --- }
  WizardForm.NextButton.Font.Name := 'Segoe UI';
  WizardForm.NextButton.Font.Size := 10;
  WizardForm.NextButton.Font.Style := [fsBold];
  WizardForm.CancelButton.Font.Name := 'Segoe UI';
  WizardForm.CancelButton.Font.Size := 9;
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
    SetFocus(WizardForm.NextButton.Handle);
  end
  else if CurPageID = wpInstalling then
  begin
    WizardForm.BackButton.Visible := False;
  end
  else if CurPageID = wpFinished then
  begin
    { не висим в ожидании: закрываемся сами через CLOSE_SECONDS секунд }
    CloseCountdown := CLOSE_SECONDS;
    WizardForm.NextButton.Caption := ExpandConstant('{cm:BtnClose}') + ' (' + IntToStr(CloseCountdown) + ')';
    WizardForm.BackButton.Visible := False;
    WizardForm.CancelButton.Visible := False;
    SetFocus(WizardForm.NextButton.Handle);
    CloseTimer := SetTimer(0, 0, 1000, CreateCallback(@CloseTick));
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
  if CloseTimer <> 0 then
    KillTimer(0, CloseTimer);
end;

{ Запущенное приложение держит Zapret.exe (DeleteFile: код 32) — закрываем перед
  заменой файлов. Работает и в silent-режиме (обновление через апдейтер). }
procedure CurStepChanged(CurStep: TSetupStep);
var
  KillCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill.exe', '/F /IM Zapret.exe /T', '', SW_HIDE, ewWaitUntilTerminated, KillCode);
    Exec('taskkill.exe', '/F /IM ZapretWeb.exe /T', '', SW_HIDE, ewWaitUntilTerminated, KillCode);
    Sleep(600);
  end;
end;
