;
; Edit Videos — Windows インストーラー（Inno Setup 6）
;
; 同梱するのは uv.exe とソースコードだけ。Python 本体と依存パッケージは
; インストール時に uv が uv.lock のとおりに取得する（要インターネット接続）。
; ビルド: installer\build.ps1（uv.exe の取得 → ISCC）
;
#define AppName      "Edit Videos"
#define AppVersion   "0.1.0"
#define AppPublisher "lisso-hookah"
#define AppURL       "https://github.com/lisso-hookah/edit-videos-poc"

[Setup]
AppId={{7F3A9B2E-C1D4-4E8F-A562-0B1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
; ユーザー領域に入れる: アプリが自分のフォルダ（.venv / uploads / output / .env）に書き込むため
DefaultDirName={localappdata}\Programs\EditVideos
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist_installer
OutputBaseFilename=EditVideos_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName}

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加のショートカット:"

[Files]
Source: "uv\uv.exe";          DestDir: "{app}";     Flags: ignoreversion
Source: "..\start.bat";       DestDir: "{app}";     Flags: ignoreversion
Source: "..\pyproject.toml";  DestDir: "{app}";     Flags: ignoreversion
Source: "..\uv.lock";         DestDir: "{app}";     Flags: ignoreversion
Source: "..\README.md";       DestDir: "{app}";     Flags: ignoreversion
Source: "..\.env.example";    DestDir: "{app}";     Flags: ignoreversion
Source: "..\src\*";          DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"

[Icons]
; start.bat は同じフォルダの uv.exe を使って起動する
Name: "{group}\{#AppName}";                        Filename: "{app}\start.bat"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";                  Filename: "{app}\start.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; uv.lock どおりの環境を {app}\.venv に作る。失敗しても初回起動時に start.bat が再試行する
Filename: "{app}\uv.exe"; Parameters: "sync --frozen"; WorkingDir: "{app}"; StatusMsg: "Python と依存パッケージを取得中...（数分かかる場合があります）"; Flags: runhidden waituntilterminated

Filename: "{app}\start.bat"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\uploads"
Type: filesandordirs; Name: "{app}\output"
Type: filesandordirs; Name: "{app}\src"
Type: files;          Name: "{app}\.env"

[Code] (Pascal) ───────────────────────────────────────────────
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
  GeminiLabel.Caption := 'Gemini API キー（字幕のフィラー除去に使用・省略可）';
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
  // 再インストール時にキー欄を空のまま進めた場合は、既存の .env（入力済みのキー）を残す
  if FileExists(EnvPath) and (GeminiEdit.Text = '') and (OpenAiEdit.Text = '') then
    Exit;
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
