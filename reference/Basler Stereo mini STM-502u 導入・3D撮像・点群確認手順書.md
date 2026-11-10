# Basler Stereo mini STM-502u 導入・3D撮像・点群確認手順書

作成日：2026-11-10  
対象：Windows 11 / Basler Stereo mini STM-502u / Python / CloudCompare  
目的：次回、カメラの接続からPLY保存・3D表示まで迷わず再現する

> この手順書は実際に動作確認した操作と、添付の `capture_stereo_mini(4).py` を基に作成したものです。バージョンやインストール先は使用PCに応じて確認してください。

## 1. 最短起動手順（次回はここから）

1. **Stereo miniをPC本体のUSBポートへ直接接続する。** USBハブ経由では撮像開始後に切断された。
2. 必要に応じて **pylon 3D Viewer** を起動し、カメラを開いて3D画像が映るか確認する。Pythonで撮像する前にはViewerを閉じる。
3. VS Codeで `basler_stereomini_control` フォルダを開く。
4. PowerShellで仮想環境を有効化し、GenTL Producerの検索パスを設定する。
5. `python capture_stereo_mini.py` を実行し、`pointcloud.ply` が作成されたことを確認する。
6. **CloudCompare** で `pointcloud.ply` を開き、必要ならZ座標で色分けする。

```powershell
cd C:\Users\fumih\Desktop\basler_stereomini_control
.\.venv\Scripts\Activate.ps1
$env:GENICAM_GENTL64_PATH = "C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini;C:\Program Files\Basler\pylon\Runtime\x64"
python capture_stereo_mini.py
```

> **重要：** 環境変数の設定は、このPowerShellセッションにだけ有効。新しいターミナルで実行する場合は再設定する。VS CodeのF5実行も成功した実績があるが、環境変数を引き継がない場合は、まず上記のPowerShellから実行する。

## 2. 使用機器・ソフトウェア

| 項目 | 今回確認した内容 |
|---|---|
| 3Dカメラ | Basler Stereo mini STM-502u |
| カメラ識別情報 | AUSW36D00041（今回の実機） |
| OS | Windows（今回の操作画面はWindows環境） |
| pylon Software Suite | 26.10系へアップグレードする画面を確認（最終インストール版は必要に応じて確認） |
| Stereo mini Supplementary Package | 1.1.2 |
| pypylon | 26.10 |
| Python | `.venv` 内のPython（バージョン番号は未記録） |
| 3D撮像確認 | pylon 3D Viewer |
| PLY確認 | CloudCompare 2.13.2（64-bit） |
| Pythonライブラリ | `pypylon`、`numpy` |

## 3. 初回セットアップ

### 3.1 pylon Software Suite

1. Basler公式サイトのソフトウェアダウンロードページを開く。
2. Windows向け **pylon Software Suite** のフルインストーラーを入手する。
3. インストール時は **GigE Camera Support** と **GenTL Consumer Support** を含める（Stereo miniパッケージの案内に記載されたWindows向け要件）。
4. 既存pylonからアップグレードする場合、既存のBaslerアプリに影響する可能性があるので注意する。

公式サイト：<https://www.baslerweb.com/>

### 3.2 Stereo mini専用パッケージ

1. **pylon Supplementary Package for Basler Stereo mini 1.1.2**（または対応する後継版）をダウンロードする。
2. インストーラーを実行する。
3. **pylon 3D Viewer** が利用できることを確認する。
4. GenTL Producerが次の場所に存在するか確認する。

```text
C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini\ProducerBaslerStereoMini.cti
```

PowerShellでの確認：

```powershell
Get-ChildItem "C:\Program Files\Basler" -Recurse -Filter *.cti -ErrorAction SilentlyContinue |
    Select-Object FullName
```

今回確認できたファイル：

```text
C:\Program Files\Basler\pylon\Runtime\Win32\ProducerU3V.cti
C:\Program Files\Basler\pylon\Runtime\x64\ProducerU3V.cti
C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini\ProducerBaslerStereoMini.cti
```

### 3.3 Python仮想環境

既存の `.venv` がある場合は作り直さない。新規構築時の例：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install numpy pypylon
python -m pip show pypylon
```

今回の動作確認済み `pypylon` は **26.10**。新規構築時に同一環境を再現するなら、インストールするバージョンを合わせる。

## 4. Windowsでのカメラ認識確認

**デバイスマネージャー → カメラ** に以下が表示された。

- `Basler Stereo mini STM-502u Depth Camera`
- `Basler Stereo mini STM-502u RGB Camera`

この表示はUSBデバイスの認識確認に有効。ただし、3D撮像ができるかはpylon 3D Viewerでも確認する。

## 5. pylon 3D Viewerで撮像確認

1. pylon 3D Viewerを起動する。
2. 上部のカメラ選択欄で `Stereo mini STM-502u` を選ぶ。
3. **Open Camera** を押す。
4. `Point Cloud View`、`Depth Map View`、`Intensity Image View` を確認する。
5. 必要に応じて `Depth Camera` タブの設定を調整する。

今回使用した設定・表示例：

| 項目 | 値・内容 |
|---|---|
| DepthMin | 200 mm |
| DepthMax | 1000 mm |
| Viewerで表示された解像度 | 848 × 480 |
| Viewerでのフレームレート | 約30 FPS |
| 撮像対象 | カメラから約30cm付近の物体 |

**注意：** ViewerのDepth Map上部のカラーレンジ表示と、カメラ設定のDepthMin/DepthMaxは別の設定。黒い表示になったときは、距離範囲の設定や表示範囲を確認する。

## 6. Pythonで3D撮像・PLY保存

使用するプログラム：`capture_stereo_mini.py`  
今回の添付版：`capture_stereo_mini(4).py`

### 6.1 重要な定数

```python
DEVICE_CLASS = "BaslerGTC/Basler/Stereo_mini"
OUTPUT_FILE = Path(__file__).resolve().parent / "pointcloud.ply"
DEPTH_MIN = 200
DEPTH_MAX = 1000
```

`DEPTH_MIN` と `DEPTH_MAX` は**保存時のZ座標フィルター**であり、現行コードではカメラ本体のDepthMin/DepthMaxを変更していない。

### 6.2 プログラム構成

| 関数 | 処理 |
|---|---|
| `capture_xyz(camera)` | 1フレーム撮像し、RangeコンポーネントからXYZ配列を取得 |
| `save_ply(path, xyz)` | NaN/InfとZ範囲外を除外して、バイナリPLY形式で保存 |
| `main()` | カメラ接続、設定確認、撮像、保存、切断 |

カメラ側では `ComponentSelector = "Range"` を選択し、`ComponentEnable == True`、`PixelFormat == "Coord3D_ABC32f"` を確認する。**書き込み不可だった `ComponentEnable` にTrueを代入しない。**

### 6.3 保存形式

- ファイル：`pointcloud.ply`（プログラムと同じフォルダ）
- 形式：binary little-endian PLY
- 属性：`x`、`y`、`z`（それぞれ32bit浮動小数点）
- RGB色情報：**保存していない**
- フィルター：有限値、かつ **200 ≤ Z ≤ 1000**
- Z座標の単位：**mmを想定**。正式な単位設定は実機の仕様・設定で最終確認すること

### 6.4 実行結果の実績

```text
Camera: Basler Stereo mini STM-502u (AUSW36D00041)
ComponentEnable: True
PixelFormat: Coord3D_ABC32f
Captured XYZ shape: (720, 1280, 3)
Saved 688,233 points: ...\pointcloud.ply
```

上記は整理前コードで取得した実績。整理後コードでは日本語のログ表示に変わっている。

全画素数は `1280 × 720 = 921,600`。Z範囲でフィルターした結果、ある撮像では **688,233点** を保存できた。点数は撮像対象や環境によって変わる。

> Viewerの表示解像度848×480とPython取得配列1280×720は異なっていた。両者の設定・データ構成が完全に一致するとは限らないため、同じものとして扱わない。

## 7. CloudCompareでPLYを確認

### 7.1 インストール

1. 公式サイト <https://www.cloudcompare.org/> を開く。
2. Windows 64-bitのインストーラー版をダウンロードする。
3. 今回使用したバージョンは **2.13.2**。
4. インストール時の追加タスクは以下で十分だった。

| 追加タスク | 今回の選択 |
|---|---|
| Create a desktop shortcut | ON |
| Install Faro I/O plugin | OFF |
| Install the Python and 3DFin plugins | OFF |

CloudCompareのPythonプラグインは、外部Pythonで作成したPLYを閲覧するだけなら不要。

### 7.2 PLYを開く

1. CloudCompareを起動する。
2. **File → Open** で `pointcloud.ply` を選択する。
3. `Ply File Open` ダイアログでは以下を確認する。

| 項目 | 対応付け |
|---|---|
| Point X | `vertex - x [PLY_FLOAT]` |
| Point Y | `vertex - y [PLY_FLOAT]` |
| Point Z | `vertex - z [PLY_FLOAT]` |
| Red / Green / Blue | `None` |
| その他 | `None` |

4. **Apply** をクリックする。
5. 左上のDB Treeで点群を選択し、必要に応じてズーム・回転する。

### 7.3 Z座標による色分け

1. DB Treeで `pointcloud.ply - Cloud` を選択する。
2. **Edit → Scalar fields → Export coordinates to SF(s)** を実行する。
3. Propertiesパネルで表示するScalar Fieldを **Coord. Z** にする。
4. 好みのカラースケールを選択する。

これで白一色だった点群をZ座標の値に応じて色分けでき、形状の違いが見やすくなった。

> 色と距離の対応は選択したカラースケールによる。赤が近い／青が遠いとは決めつけない。

## 8. 実際に発生したトラブルと解決方法

### 8.1 PythonでTransport Layer生成エラー

```text
The transport layer for device class
'BaslerGTC/Basler/Stereo_mini' could not be created.
```

**原因候補：** Stereo mini専用のGenTL ProducerをPython側が検索できていなかった。

**今回の解決方法：** `ProducerBaslerStereoMini.cti` がある `stereo-mini` フォルダを `GENICAM_GENTL64_PATH` に追加した。

```powershell
$env:GENICAM_GENTL64_PATH = "C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini;C:\Program Files\Basler\pylon\Runtime\x64"
```

変更後、Pythonからカメラ名を取得できるようになった。

### 8.2 `ComponentEnable` が書き込み不可

```text
Node is not writable.
```

`camera.ComponentEnable.Value = True` の代入で発生。実際の値はすでに `True` だった。

**対処：** 書き込まず、読み取り確認のみ実施する。

```python
camera.ComponentSelector.Value = "Range"
if not camera.ComponentEnable.Value:
    raise RuntimeError("Rangeコンポーネントが無効です。")
```

### 8.3 Viewerが数十秒で勝手にクローズする

Viewerのログに `Camera has been removed.` が表示された。

**今回の解決方法：** USBハブから抜き、PC本体のUSBポートへ直接接続したところ改善した。

### 8.4 30cm付近が真っ黒になる

当初の深度範囲は `DepthMin=353mm`、`DepthMax=3526mm` だった。約300mmの対象は範囲外になり得る。

**対処：** Viewer側で `DepthMin=200mm`、`DepthMax=1000mm` に調整したところ3D表示に成功した。

### 8.5 CloudCompareで点群が小さく、離れて見える

当初は全921,600画素をPLYに保存しており、Z=0や4m超の点も含まれていた。`np.isfinite()` だけではZ=0を除外できない。

**対処：** PLY保存時に `200 ≤ Z ≤ 1000` を適用。ある撮像では688,233点に減少し、CloudCompareの表示が大きく改善した。

### 8.6 PLYが白一色で分かりにくい

**対処：** CloudCompareで `Export coordinates to SF(s)` を実行し、`Coord. Z` を選択して色分けした。

## 9. 次回の確認チェックリスト

- [ ] USBハブを使わず、PC本体へ接続した
- [ ] デバイスマネージャーでDepth/RGB Cameraを確認した
- [ ] 必要ならpylon 3D Viewerで3D撮像を確認した
- [ ] Python撮像前にpylon 3D Viewerを終了した
- [ ] VS Codeで正しいプロジェクトと `.venv` を開いた
- [ ] `GENICAM_GENTL64_PATH` を設定した
- [ ] `DEPTH_MIN` / `DEPTH_MAX` を確認した
- [ ] `python capture_stereo_mini.py` を実行した
- [ ] `pointcloud.ply` の更新日時と保存点数を確認した
- [ ] CloudCompareで新しいPLYを開き直した
- [ ] 必要に応じて `Coord. Z` で色分けした

## 10. 今後の改良候補（未実装）

- XYZ座標の単位・座標系の正式確認
- カメラ側DepthMin/DepthMax設定とPython保存フィルターの整理
- カラー画像とXYZの対応確認、およびRGB付きPLYの保存
- 無効点の判定条件や保存点数の追加検証
- 保存ファイル名への撮像日時付与（現在は同名PLYを上書き）

---

**まとめ：** Stereo mini専用GenTL Producerの検索パス設定、USB直結、適切な深度範囲での保存、CloudCompareのZ色分けが、今回の動作確認で特に重要だった。
