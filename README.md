# Basler Stereo mini Control

Basler Stereo miniで3Dデータを1フレーム撮像し、深度画像（BMP）と点群データ（PLY）を保存するPythonプログラムです。

将来的には、深度画像から製品の位置・角度を検出し、ロボットによるピックアップに利用する予定です。

## 動作環境

- Windows / Python
- Basler pylon Software Suite
- Basler Stereo mini用 Supplementary Package（GenTL Producer）
- Pythonライブラリ：`numpy`、`opencv-python`、`pypylon`

## セットアップ

プロジェクトフォルダで仮想環境を作成し、ライブラリをインストールします。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

BaslerのソフトウェアとStereo mini用Supplementary Packageは別途インストールしてください。GenTLの検索パスはPythonコード内で設定しています（Baslerのインストール先が既定の場所であることが前提です）。

## 実行方法

`activate_venv.bat` をダブルクリックして仮想環境を有効化するか、ターミナルで有効化した後、次を実行します。

```powershell
python capture_stereo_mini_with_bmp.py
```

※ 実際のPythonファイル名が異なる場合は読み替えてください。

## 出力ファイル

撮像結果は自動作成される `output/` フォルダに保存されます。

| ファイル | 内容 |
|---|---|
| `output/depth.bmp` | 8bitグレースケール深度画像 |
| `output/pointcloud.ply` | XYZ点群データ |

PLYの保存対象Z範囲は180〜300mm、BMPの濃淡表示範囲は221.9〜232.8mmです。値はソースコード冒頭の設定セクションで変更できます。

`output/` と `.venv/` は `.gitignore` によりGit管理対象から除外します。
