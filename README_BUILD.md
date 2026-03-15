# STS2 Tracker — ビルド手順

local-agent を Windows 向け単一 exe にパッケージングする手順です。

## 前提条件

- Python 3.11 以上（3.13 推奨）
- Windows 10/11 x64
- `local-agent/venv` が構築済みであること

venv が未構築の場合：

```bat
cd local-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## アイコンの準備

`local-agent/assets/icon.ico` を用意してください（必須）。

```
local-agent/
└── assets/
    └── icon.ico   ← 256x256 推奨（マルチサイズ ICO）
```

PNG から変換する場合：

```python
from PIL import Image
img = Image.open("icon.png")
img.save("assets/icon.ico", sizes=[(16,16),(32,32),(48,48),(256,256)])
```

## ビルド

```bat
cd local-agent
build.bat
```

成功すると `local-agent/dist/STS2Tracker.exe` が生成されます。

## 手動ビルドコマンド

```bat
cd local-agent
venv\Scripts\activate
pip install pyinstaller
python -m pyinstaller sts2tracker.spec --clean
```

## 出力

| パス | 内容 |
|------|------|
| `dist/STS2Tracker.exe` | 配布用単一 exe（依存込み） |
| `build/` | PyInstaller 中間ファイル（削除可） |

## 配布

`dist/STS2Tracker.exe` 単体をユーザーに配布します。
初回起動時に `%USERPROFILE%\.sts2tracker\config.json` が自動生成され、
UUID の生成とサーバーへのユーザー登録が行われます。

## トラブルシューティング

### `pystray` 関連のエラー

```
ModuleNotFoundError: No module named 'pystray._win32'
```

spec ファイルの `hiddenimports` に `pystray._win32` が含まれていることを確認してください。

### `watchdog` 関連のエラー

```
No module named 'watchdog.observers.winapi'
```

spec ファイルの `hiddenimports` に `watchdog.observers.winapi` が含まれていることを確認してください。

### exe 起動時に即終了する

`console=False` の場合エラーが見えません。デバッグ時は spec の `console=True` に変更して再ビルドし、
ログを `%USERPROFILE%\.sts2tracker\sts2tracker.log` で確認してください。

### UPX 圧縮エラー

UPX がインストールされていない場合は spec の `upx=True` を `upx=False` に変更してください。

```bat
pip install pyinstaller
:: UPX なしでビルド
python -m pyinstaller sts2tracker.spec --clean --noupx
```
