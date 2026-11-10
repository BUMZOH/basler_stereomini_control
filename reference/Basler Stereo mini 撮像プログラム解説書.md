# Basler Stereo mini 撮像プログラム解説書

対象コード：`capture_stereo_mini_with_bmp(2).py`  
作成日：2026-11-11

## 1. プログラムの目的

Basler Stereo miniから**1フレームの3Dデータ**を取得し、同じ撮像データから次の2ファイルを出力する。

| 出力 | ファイル名 | 内容 | 主な用途 |
|---|---|---|---|
| PLY | `pointcloud.ply` | XYZ座標を持つ3D点群 | CloudCompareなどでの3D確認 |
| BMP | `depth.bmp` | Z座標を濃淡にした8bit画像 | OpenCVでの画像処理 |

**今後の目的**：BMP画像から、重ならずにバラバラの位置・角度で置かれた製品を検出し、ロボットのピックアップ位置・角度を求める。製品のピックアップZ座標は固定する方針。現行コードには製品検出やロボット通信はまだない。

> 将来的にPLYファイルは不要になる予定だが、**添付された現行コードではPLYとBMPの両方を保存する**。この解説書は現行コードに準拠する。

## 2. プログラム全体の流れ

```text
main()
  │
  ├─ カメラデバイスを検索・生成
  ├─ camera.Open()
  ├─ RangeコンポーネントとPixelFormatを確認
  │
  ├─ capture_xyz(camera)
  │    ├─ 1フレーム撮像
  │    ├─ Rangeデータを探す
  │    └─ XYZ配列をコピーして返す
  │
  ├─ save_ply(OUTPUT_FILE, xyz)
  │    ├─ 無効点・範囲外の点を除去
  │    └─ バイナリPLY保存
  │
  ├─ save_depth_bmp(BMP_FILE, xyz)
  │    ├─ Z座標を取り出す
  │    ├─ 有効画素を判定
  │    ├─ Z座標を0～255に変換
  │    ├─ 無効画素を黒にする
  │    └─ BMP保存
  │
  └─ camera.Close()
```

1回の撮像結果 `xyz` を**PLYとBMPの両方に使い回す**。BMPを作るためにPLYを読み直すわけではない。

## 3. インポートとGenTLの設定

```python
import os
from pathlib import Path

GENTL_PATH = (
    r"C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini;"
    r"C:\Program Files\Basler\pylon\Runtime\x64"
)
os.environ["GENICAM_GENTL64_PATH"] = GENTL_PATH

import cv2
import numpy as np
from pypylon import pylon
```

- `os`：実行中のPythonプロセスの環境変数を設定する。
- `Path`：ファイル保存先を扱う。
- `cv2`：BMP画像の保存。
- `numpy`：XYZ配列と濃淡画像の数値処理。
- `pypylon`：Baslerカメラの制御・撮像。

### なぜ `GENICAM_GENTL64_PATH` が必要なのか

Stereo mini専用のGenTL Producerをpypylonが見つけるための**検索パス**である。専用Producerは以下の場所にある構成を想定している。

```text
C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini\ProducerBaslerStereoMini.cti
```

`;` はWindowsで複数の検索ディレクトリを区切る記号。`r"..."` はバックスラッシュをそのまま書けるraw文字列。

**重要**：`from pypylon import pylon` より前に環境変数を設定している。これにより、PowerShellで毎回 `$env:GENICAM_GENTL64_PATH` を指定する必要がなくなった。`os.environ` による変更は**そのPythonプロセス内の設定**であり、Windowsのユーザー環境変数を永続的に書き換えるものではない。

このパスはインストール先に依存するため、別PCでは確認が必要。

## 4. 設定セクション

```python
DEVICE_CLASS = "BaslerGTC/Basler/Stereo_mini"
OUTPUT_FILE = Path(__file__).resolve().parent / "pointcloud.ply"
BMP_FILE = Path(__file__).resolve().parent / "depth.bmp"
DEPTH_MIN = 180
DEPTH_MAX = 300
BMP_DEPTH_MIN = 221.9
BMP_DEPTH_MAX = 232.8
```

| 定数 | 意味 |
|---|---|
| `DEVICE_CLASS` | 使用するカメラのデバイスクラス |
| `OUTPUT_FILE` | PLY保存先 |
| `BMP_FILE` | BMP保存先 |
| `DEPTH_MIN` / `DEPTH_MAX` | PLYに残す点、およびBMPの有効画素を判定するZ範囲（180～300mm） |
| `BMP_DEPTH_MIN` / `BMP_DEPTH_MAX` | BMPの濃淡を割り当てるZ範囲（221.9～232.8mm） |

`Path(__file__).resolve().parent` は、**実行中のPythonファイルが置かれたフォルダ**を示す。作業ディレクトリが変わっても保存先を安定させられる。

### 2種類の深度範囲を混同しない

- **有効範囲：180～300mm** → この範囲外の点はBMPで黒（無効）にする。PLYからも除外する。
- **濃淡表示範囲：221.9～232.8mm** → 有効点の明るさを決めるための範囲。**この範囲外だからといって無効にはしない**。

今回の調整では、この区別が非常に重要だった。

## 5. `capture_xyz()`：3Dデータを1回撮像する

```python
camera.StartGrabbingMax(1)
grab_result = camera.RetrieveResult(
    10000, pylon.TimeoutHandling_ThrowException
)
```

- `StartGrabbingMax(1)`：最大1フレーム撮像する。
- `RetrieveResult(10000, ...)`：最大10,000ミリ秒（10秒）待って結果を取得。タイムアウト時は例外を発生させる。
- `GrabSucceeded()`：撮像成功を確認する。

撮像結果には複数のデータコンポーネントが含まれる可能性があるため、ループで `ComponentType_Range` を探す。

```python
container = grab_result.GetDataContainer()
for index in range(container.DataComponentCount):
    component = container.GetDataComponentByIndex(index)
    try:
        if component.ComponentType != pylon.ComponentType_Range:
            continue
        data = np.asarray(component.Array)
        height, width = component.Height, component.Width
        if data.size != height * width * 3:
            raise RuntimeError("XYZデータのサイズが想定と異なります。")
        return data.reshape(height, width, 3).copy()
    finally:
        component.Release()
```

- `GetDataComponentByIndex()`：インデックスでコンポーネントを取得（旧式の `GetDataComponent()` は使わない）。
- `np.asarray()`：データをNumPy配列として扱う。
- `reshape(height, width, 3)`：画像の各画素にX、Y、Zの3値を割り当てる。
- `.copy()`：元の取得バッファを解放しても安全に使える独立した配列にする。
- `component.Release()`：コンポーネントを解放する。

外側の `finally` では `grab_result.Release()` と、必要に応じた `camera.StopGrabbing()` を実行する。例外が発生しても後片付けするための構造。

### XYZ配列の構造

今回の撮像環境では、取得配列は次の形だった。

```python
xyz.shape  # (720, 1280, 3)
```

| 添字 | 意味 |
|---|---|
| `xyz[v, u, 0]` | 画素 `(u, v)` のX座標 |
| `xyz[v, u, 1]` | 画素 `(u, v)` のY座標 |
| `xyz[v, u, 2]` | 画素 `(u, v)` のZ座標 |

例えば、`xyz[100, 200, 2]` は**上から100行目、左から200列目のZ座標**（0始まり）を示す。

## 6. `save_ply()`：3D点群を保存する

```python
points = np.asarray(xyz, dtype=np.float32).reshape(-1, 3)
valid = (
    np.isfinite(points).all(axis=1)
    & (points[:, 2] >= DEPTH_MIN)
    & (points[:, 2] <= DEPTH_MAX)
)
points = points[valid]
```

`reshape(-1, 3)` は画像状のXYZ配列を**点の一覧**に変える。`np.isfinite()` はNaNや無限大を除外する。`&` は条件のAND。

残った点のX・Y・Zを、バイナリlittle-endianの32bit浮動小数点でPLYに記録する。PLYヘッダーには点数とX/Y/Zのデータ形式を書く。

```python
with path.open("wb") as file:
    file.write(header.encode("ascii"))
    file.write(points.astype("<f4", copy=False).tobytes())
```

- `wb`：バイナリ書き込み。
- `<f4`：little-endianの4バイト浮動小数点。
- `tobytes()`：配列をバイト列に変換。

**注意**：無効点を削除して1次元の点群にするため、PLYだけから元画像の画素位置を正確に復元するのは難しい。これがBMPをXYZ配列から直接作る理由。

## 7. `save_depth_bmp()`：深度画像を保存する【重要】

### 7-1. Z座標だけを取り出す

```python
depth = xyz[:, :, 2]
```

`depth` は高さ×幅の2次元配列になる。各画素にZ座標が入っている。

### 7-2. 有効画素を判定する

```python
valid = (
    np.isfinite(xyz).all(axis=2)
    & (depth >= DEPTH_MIN)
    & (depth <= DEPTH_MAX)
)
```

X・Y・Zのすべてが有限値で、かつZが180～300mmの画素を有効とする。`valid` は画素ごとの `True` / `False` 配列。

### 7-3. NaNや無限大を一時的に置き換える

```python
safe_depth = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)
```

濃淡計算のため、特殊な値を一時的に0へ変換する。**これだけで有効点になるわけではない**。最後に `valid` を使って無効画素を黒くする。

### 7-4. Z座標を0～1へ正規化する

```python
gray = (safe_depth - BMP_DEPTH_MIN) / (BMP_DEPTH_MAX - BMP_DEPTH_MIN)
gray = np.clip(gray, 0, 1)
```

計算式：

```text
gray = (Z - 221.9) / (232.8 - 221.9)
```

| Z座標 | 正規化値（概算） | 8bit値（概算） |
|---|---:|---:|
| 221.9mm | 0.00 | 0（黒） |
| 227.35mm | 0.50 | 127（灰色） |
| 232.8mm | 1.00 | 255（白） |
| 240.0mm | 1.00に丸める | 255（白） |

この設定は**近いほど暗く、遠いほど明るい**。`np.clip(gray, 0, 1)` により表示範囲外の有効点も0か1へ丸める。

### 7-5. 8bit画像へ変換する

```python
image = (gray * 255).astype(np.uint8)
```

- `* 255`：0～1を0～255へ拡大。
- `np.uint8`：画素値0～255の8bit整数に変換。

### 7-6. 無効画素を黒にする

```python
image[~valid] = 0
```

`~valid` は `valid` の反転（無効画素を選ぶ）。**表示範囲外の有効点を黒にしない**ことが、今回の3D Viewerに近い画像を得るための重要ポイントだった。

なお、有効画素でもZが221.9mm以下なら黒（0）になるため、**BMPの黒画素が必ず無効点を意味するわけではない**。厳密な識別が必要なら、別途 `valid` マスクを保存する。

### 7-7. BMPファイルとして保存する

```python
if not cv2.imwrite(str(path), image):
    raise RuntimeError("BMP保存に失敗しました。")
```

`cv2.imwrite()` は保存成功時に `True` を返す。失敗した場合は例外を出す。`image` は2次元の `uint8` 配列なので、OpenCVで扱えるグレースケール画像になる。

## 8. `main()`：カメラ初期化から終了まで

```python
device_info = pylon.DeviceInfo()
device_info.SetDeviceClass(DEVICE_CLASS)
camera = pylon.InstantCamera(
    pylon.TlFactory.GetInstance().CreateFirstDevice(device_info)
)
```

指定したデバイスクラスからカメラを検索して生成する。以前の `The transport layer ... could not be created` エラーは、Stereo mini専用GenTLの検索パス不足が原因だった。

```python
camera.Open()
camera.ComponentSelector.Value = "Range"
if not camera.ComponentEnable.Value:
    raise RuntimeError("Rangeコンポーネントが無効です。")
if camera.PixelFormat.Value != "Coord3D_ABC32f":
    raise RuntimeError("PixelFormatがCoord3D_ABC32fではありません。")
```

`ComponentEnable` は**読み取りだけ**行う。以前、これを変更しようとしてread-onlyの例外が発生したため、現行コードでは書き換えない。

```python
xyz = capture_xyz(camera)
count = save_ply(OUTPUT_FILE, xyz)
save_depth_bmp(BMP_FILE, xyz)
```

撮像は1回。保存はPLYとBMPの2回。最後に撮像サイズ、PLY点数、保存先を表示する。`finally` 内の `camera.Close()` でカメラを閉じる。

## 9. 実行方法と必要なライブラリ

仮想環境が用意されているプロジェクトのPowerShell例：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install numpy opencv-python pypylon
python capture_stereo_mini_with_bmp.py
```

`pypylon` のバージョンは、インストールしたBasler pylonとの対応を確認すること。実際のファイル名に合わせて実行コマンドを変更する。

正常終了するとPythonファイルと同じフォルダに `pointcloud.ply` と `depth.bmp` が保存される。既存の同名ファイルは上書きされる。

## 10. よくあるトラブルと確認ポイント

| 現象 | 確認ポイント |
|---|---|
| Transport Layerを生成できない | `GENTL_PATH`、専用`.cti`の存在、`pypylon`より前の環境変数設定 |
| カメラが途中で切断される | USBハブではなくPC本体への直接接続を試す（以前の実機で改善） |
| `ComponentEnable` の書き込みで例外 | read-onlyなので書き換えない |
| BMPの背景が白くなる | `image[~valid] = 0` と有効範囲判定を確認 |
| BMPが黒い部分だらけになる | `BMP_DEPTH_MIN/MAX` で有効判定していないか確認 |
| BMPの濃淡が逆 | `safe_depth - BMP_DEPTH_MIN` と引き算の向きを確認 |
| 保存できない | 保存先、アクセス権、ファイル使用状況を確認 |

## 11. 今後の開発方針（現行コードには未実装）

製品は**同一平面上で、互いに重ならず、位置と角度がばらばら**という前提。

1. PLY保存処理を外し、BMP保存のみに簡略化する。
2. OpenCVでBMPを二値化し、製品の輪郭を検出する。
3. 各製品の中心画素座標 `(u, v)` と角度 `θ` を求める。
4. カメラ座標とロボット座標の対応を校正する。
5. 校正結果からロボットの `(X, Y, θ)` を求める。ピックアップZは固定値を使用する。
6. ロボットへ指令する前に、検出精度、把持位置、干渉、安全条件を検証する。

**注意**：製品が同一平面にあっても、画像の画素座標がそのままロボット座標になるわけではない。座標変換のための校正が必要。BMPは8bit表示画像なので、実測Z値の精度を保持する用途には適さない。

## 12. まとめ

- `capture_xyz()` は**XYZの2次元画素配置を保ったまま**3Dデータを取得する。
- `save_ply()` はXYZ点群を保存する（将来は削除予定）。
- `save_depth_bmp()` は**Z座標を直接8bit画像へ変換**する。
- `DEPTH_MIN/MAX` は**有効範囲**、`BMP_DEPTH_MIN/MAX` は**濃淡表示範囲**。
- `image[~valid] = 0` により無効画素を黒にする。
- 現段階では3D Viewerに近いBMPの保存まで動作確認済み。製品検出とロボット連携は次の開発段階。
