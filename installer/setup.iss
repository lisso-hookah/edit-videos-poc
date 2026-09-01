; ============================================================
; EditVideos_Setup.exe — Inno Setup 6.x スクリプト
;
; ビルド前の準備 (BUILD.md 参照):
;   installer\
;     dist\EditVideos.exe   ← PyInstaller でビルド済みランチャー
;     python-embed\         ← Python 3.11 embeddable を展開したフォルダ
;     ffmpeg-bin\
;       ffmpeg.exe
;       ffprobe.exe
;     get-pip.py            ← https://bootstrap.pypa.io/get-pip.py
;     icon.ico              ← create_icon.py で生成
; ============================================================

#define AppName      "Edit Videos"
#define AppVersion   "1.0.0"
#define AppPublisher "lisso-hookah"
#define AppURL       "https://github.com/lisso-hookah/edit-videos-poc"
#define AppExeName   "EditVideos.exe"

; ── [Setup] ──────────────────────────────────────────────────────
[Setup]
AppId={{7F3A9B2E-C1D4-4E8F-A562-0B1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\EditVideos
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist_installer
OutputBaseFilename=EditVideos_Setup_{#AppVersion}
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
DisableWelcomePage=no
PrivilegesRequired=admin
MinVersion=10.0
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
; インストール後に自動起動するかを選択させる
CloseApplications=yes

; ── [Languages] ───────────────────────────────────────────────────
[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

; ── [Tasks] ───────────────────────────────────────────────────────
[Tasks]
Name: "desktopicon";    Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加のショートカット:"
Name: "startupicon";   Description: "Windows 起動時に自動スタートする（システムトレイ常駐）"; GroupDescription: "スタートアップ:"

; ── [Files] ───────────────────────────────────────────────────────
[Files]
; ─ ランチャー EXE ─
Source: "dist\EditVideos.exe";         DestDir: "{app}";          Flags: ignoreversion

; ─ Python 3.11 embeddable ─
Source: "python-embed\*";              DestDir: "{app}\python";   Flags: ignoreversion recursesubdirs createallsubdirs

; ─ pip インストーラー ─
Source: "get-pip.py";                  DestDir: "{app}\python";   Flags: ignoreversion

; ─ ffmpeg バイナリ ─
Source: "ffmpeg-bin\ffmpeg.exe";       DestDir: "{app}\bin";      Flags: ignoreversion
Source: "ffmpeg-bin\ffprobe.exe";      DestDir: "{app}\bin";      Flags: ignoreversion

; ─ プロジェクト ソース ─
Source: "..\src\*";                    DestDir: "{app}\src";      Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\*";               DestDir: "{app}\scripts";  Flags: ignoreversion recursesubdirs
Source: "..\pyproject.toml";           DestDir: "{app}";          Flags: ignoreversion

; ─ セットアップスクリプト ─
Source: "setup_env.py";                DestDir: "{app}";          Flags: ignoreversion

; ── [Icons] ───────────────────────────────────────────────────────
[Icons]
Name: "{group}\{#AppName}";                        Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";                  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}";                  Filename: "{app}\{#AppExeName}"; Tasks: startupicon

; ── [Run] ─────────────────────────────────────────────────────────
[Run]
; Python 環境をセットアップ（インターネット接続が必要、数分かかる）
Filename: "{app}\python\python.exe";
  Parameters: "{app}\setup_env.py ""{app}""";
  StatusMsg: "Python パッケージをインストール中... (数分かかる場合があります)";
  Flags: runhidden waituntilterminated

; インストール後にアプリを起動するか選択
Filename: "{app}\{#AppExeName}";
  Description: "{cm:LaunchProgram,{#AppName}}";
  Flags: nowait postinstall skipifsilent

; ── [UninstallDelete] ─────────────────────────────────────────────
[UninstallDelete]
; インストール後に生成されるファイル類を削除
Type: filesandordirs; Name: "{app}\python\Lib"
Type: filesandordirs; Name: "{app}\uploads"
Type: filesandordirs; Name: "{app}\output"
Type: files;          Name: "{app}\.env"

; ── [Code] (Pascal) ───────────────────────────────────────────────
[Code]

// ─── カスタム API キーページの変数 ─────────────────────────────
var
  ApiKeyPage:   TWizardPage;
  GeminiLabel:  TLabel;
  GeminiEdit:   TEdit;
  GeminiNote:   TLabel;
  OpenAiLabel:  TLabel;
  OpenAiEdit:   TEdit;
  ModelLabel:   TLabel;
  ModelCombo:   TComboBox;
  InfoLabel:    TLabel;

// ─── ウィザード初期化 ────────────────────────────────────────────
procedure InitializeWizard;
var
  W: Integer;
begin
  ApiKeyPage := CreateCustomPage(
    wpSelectDir,
    'API キーの設定',
    '使用する AI サービスの API キーを入力してください。後で .env ファイルで変更できます。'
  );
  W := ApiKeyPage.SurfaceWidth;

  // ── Gemini ──
  GeminiLabel := TLabel.Create(WizardForm);
  GeminiLabel.Parent  := ApiKeyPage.Surface;
  GeminiLabel.Caption := 'Gemini API キー（Video / Short パイプラインの字幕生成に必須）';
  GeminiLabel.Top     := 10;
  GeminiLabel.Left    := 0;
  GeminiLabel.Width   := W;

  GeminiEdit := TEdit.Create(WizardForm);
  GeminiEdit.Parent      := ApiKeyPage.Surface;
  GeminiEdit.Top         := 30;
  GeminiEdit.Left        := 0;
  GeminiEdit.Width       := W;
  GeminiEdit.Text        := '';
  GeminiEdit.PasswordChar := '*';

  GeminiNote := TLabel.Create(WizardForm);
  GeminiNote.Parent  := ApiKeyPage.Surface;
  GeminiNote.Caption := '取得先: https://aistudio.google.com/apikey  （無料枠あり）';
  GeminiNote.Top     := 54;
  GeminiNote.Left    := 0;
  GeminiNote.Width   := W;
  GeminiNote.Font.Color := clGray;
  GeminiNote.Font.Size  := 8;

  // ── OpenAI ──
  OpenAiLabel := TLabel.Create(WizardForm);
  OpenAiLabel.Parent  := ApiKeyPage.Surface;
  OpenAiLabel.Caption := 'OpenAI API キー（サムネイル自動生成に使用・省略可）';
  OpenAiLabel.Top     := 82;
  OpenAiLabel.Left    := 0;
  OpenAiLabel.Width   := W;

  OpenAiEdit := TEdit.Create(WizardForm);
  OpenAiEdit.Parent      := ApiKeyPage.Surface;
  OpenAiEdit.Top         := 102;
  OpenAiEdit.Left        := 0;
  OpenAiEdit.Width       := W;
  OpenAiEdit.Text        := '';
  OpenAiEdit.PasswordChar := '*';

  // ── Whisper モデル ──
  ModelLabel := TLabel.Create(WizardForm);
  ModelLabel.Parent  := ApiKeyPage.Surface;
  ModelLabel.Caption := 'Whisper 文字起こしモデル（精度と速度のバランスを選択）';
  ModelLabel.Top     := 142;
  ModelLabel.Left    := 0;
  ModelLabel.Width   := W;

  ModelCombo := TComboBox.Create(WizardForm);
  ModelCombo.Parent  := ApiKeyPage.Surface;
  ModelCombo.Top     := 162;
  ModelCombo.Left    := 0;
  ModelCombo.Width   := W div 2;
  ModelCombo.Style   := csDropDownList;
  ModelCombo.Items.Add('medium  （推奨・バランス型）');
  ModelCombo.Items.Add('small   （高速・精度やや低）');
  ModelCombo.Items.Add('large-v3（最高精度・低速）');
  ModelCombo.Items.Add('base    （最速・精度低）');
  ModelCombo.Items.Add('tiny    （超高速・精度最低）');
  ModelCombo.ItemIndex := 0;

  // ── 注意書き ──
  InfoLabel := TLabel.Create(WizardForm);
  InfoLabel.Parent  := ApiKeyPage.Surface;
  InfoLabel.Caption :=
    '※ API キーは暗号化されずに {インストール先}\.env に保存されます。' + #13#10 +
    '※ Whisper モデルは初回使用時に自動ダウンロードされます（medium: 約 1.5 GB）。';
  InfoLabel.Top   := 202;
  InfoLabel.Left  := 0;
  InfoLabel.Width := W;
  InfoLabel.Font.Color := clGray;
  InfoLabel.Font.Size  := 8;
  InfoLabel.WordWrap   := True;
end;

// ─── Whisper モデル名を文字列で取得 ─────────────────────────────
function GetWhisperModel: String;
begin
  case ModelCombo.ItemIndex of
    0: Result := 'medium';
    1: Result := 'small';
    2: Result := 'large-v3';
    3: Result := 'base';
    4: Result := 'tiny';
  else
    Result := 'medium';
  end;
end;

// ─── .env ファイルを書き出す ─────────────────────────────────────
procedure WriteEnvFile;
var
  EnvPath: String;
  Lines: TStringList;
begin
  EnvPath := ExpandConstant('{app}\.env');
  Lines   := TStringList.Create;
  try
    Lines.Add('# Edit Videos 設定ファイル');
    Lines.Add('# このファイルを直接編集して API キーを変更できます。');
    Lines.Add('');
    Lines.Add('# Gemini API キー（字幕フィラー除去に使用）');
    Lines.Add('GEMINI_API_KEY=' + GeminiEdit.Text);
    Lines.Add('');
    Lines.Add('# OpenAI API キー（サムネイル生成時のみ）');
    Lines.Add('OPENAI_API_KEY=' + OpenAiEdit.Text);
    Lines.Add('');
    Lines.Add('# Whisper 文字起こしモデル');
    Lines.Add('WHISPER_MODEL=' + GetWhisperModel);
    Lines.Add('');
    Lines.Add('# 出力先ディレクトリ（変更する場合のみコメントアウトを外す）');
    Lines.Add('# WORK_DIR=D:\Videos\output');
    Lines.SaveToFile(EnvPath);
  finally
    Lines.Free;
  end;
end;

// ─── インストール後に .env を書き出す ───────────────────────────
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteEnvFile;
end;

// ─── Gemini キーが空のときに警告を出す ──────────────────────────
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ApiKeyPage.ID then
  begin
    if Trim(GeminiEdit.Text) = '' then
    begin
      if MsgBox(
        'Gemini API キーが入力されていません。' + #13#10 +
        'Video / Short パイプラインを使う場合は必要です。' + #13#10 + #13#10 +
        'このまま続けますか？（後で .env ファイルに記入できます）',
        mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end;
  end;
end;
