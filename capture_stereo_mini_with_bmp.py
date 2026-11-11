"""Basler Stereo miniで3D点群を1回撮像し、PLY形式と深度BMP形式で保存する。"""

import os
from pathlib import Path

# ================================================
# 設定
# ================================================
GENTL_PATH = (
    r"C:\Program Files\Basler\pylon\Runtime\x64\stereo-mini;"
    r"C:\Program Files\Basler\pylon\Runtime\x64"
)

# GenTL Producerの検索パスを設定
os.environ["GENICAM_GENTL64_PATH"] = GENTL_PATH

import cv2
import numpy as np
from pypylon import pylon

DEVICE_CLASS = "BaslerGTC/Basler/Stereo_mini"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "pointcloud.ply"
BMP_FILE = OUTPUT_DIR / "depth.bmp"
DEPTH_MIN = 180  # PLY保存範囲（mm）
DEPTH_MAX = 300
# BMP濃淡表示範囲（mm）(3D Viewerで決定すること)
BMP_DEPTH_MIN = 224
BMP_DEPTH_MAX = 234


# ================================================
# 3D撮像
# ================================================
def capture_xyz(camera: pylon.InstantCamera) -> np.ndarray:
    """1フレーム撮像し、XYZ座標の配列を取得する。"""
    camera.StartGrabbingMax(1)
    grab_result = None

    try:
        grab_result = camera.RetrieveResult(
            10000, pylon.TimeoutHandling_ThrowException
        )
        if not grab_result.GrabSucceeded():
            raise RuntimeError(grab_result.GetErrorDescription())

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

                # Release後も使えるようにコピーする
                return data.reshape(height, width, 3).copy()
            finally:
                component.Release()

        raise RuntimeError("XYZデータ（Range）が見つかりません。")
    finally:
        if grab_result is not None:
            grab_result.Release()
        if camera.IsGrabbing():
            camera.StopGrabbing()


# ================================================
# PLY保存
# ================================================
def save_ply(path: Path, xyz: np.ndarray) -> int:
    """無効点と範囲外の点を除き、XYZ点群をバイナリPLYで保存する。"""
    points = np.asarray(xyz, dtype=np.float32).reshape(-1, 3)

    # NaN・Infと、指定したZ座標範囲外の点を除外する
    valid = (
        np.isfinite(points).all(axis=1)
        & (points[:, 2] >= DEPTH_MIN)
        & (points[:, 2] <= DEPTH_MAX)
    )
    points = points[valid]
    if len(points) == 0:
        raise RuntimeError("保存できる3D点群がありません。")

    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {len(points)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "end_header\n"
    )

    # 各点のXYZを32bit浮動小数点・リトルエンディアンで記録
    with path.open("wb") as file:
        file.write(header.encode("ascii"))
        file.write(points.astype("<f4", copy=False).tobytes())

    return len(points)


# ================================================
# 深度BMP保存
# ================================================
def save_depth_bmp(path: Path, xyz: np.ndarray) -> None:
    """XYZ配列のZ座標を8bitグレースケールBMPで保存する。"""
    depth = xyz[:, :, 2]

    # 測定データとして有効な画素を判定
    valid = (
        np.isfinite(xyz).all(axis=2)
        & (depth >= DEPTH_MIN)
        & (depth <= DEPTH_MAX)
    )

    # 濃淡表示範囲でグレースケールに変換
    safe_depth = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)

    gray = (safe_depth - BMP_DEPTH_MIN) / (BMP_DEPTH_MAX - BMP_DEPTH_MIN)
    gray = np.clip(gray, 0, 1)

    # 0～255に変換
    image = (gray * 255).astype(np.uint8)

    # 無効な測定点だけ黒にする
    image[~valid] = 0

    # BMP保存
    if not cv2.imwrite(str(path), image):
        raise RuntimeError("BMP保存に失敗しました。")


# ================================================
# メイン処理
# ================================================
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    device_info = pylon.DeviceInfo()
    device_info.SetDeviceClass(DEVICE_CLASS)
    camera = pylon.InstantCamera(
        pylon.TlFactory.GetInstance().CreateFirstDevice(device_info)
    )

    try:
        camera.Open()
        print(f"カメラ: {camera.GetDeviceInfo().GetFriendlyName()}")

        # 既に有効な設定は書き換えず、Rangeを選択する
        camera.ComponentSelector.Value = "Range"
        if not camera.ComponentEnable.Value:
            raise RuntimeError("Rangeコンポーネントが無効です。")
        if camera.PixelFormat.Value != "Coord3D_ABC32f":
            raise RuntimeError("PixelFormatがCoord3D_ABC32fではありません。")

        xyz = capture_xyz(camera)
        count = save_ply(OUTPUT_FILE, xyz)
        save_depth_bmp(BMP_FILE, xyz)
        print(f"撮像サイズ: {xyz.shape}")
        print(f"保存点数: {count:,}")
        print(f"PLY保存先: {OUTPUT_FILE}")
        print(f"BMP保存先: {BMP_FILE}")
    finally:
        if camera.IsOpen():
            camera.Close()


if __name__ == "__main__":
    main()
