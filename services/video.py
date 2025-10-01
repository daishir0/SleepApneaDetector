"""
動画処理モジュール
睡眠時無呼吸症候群の検出のための動画解析機能
"""
import cv2
import numpy as np
from typing import Tuple, Optional
import subprocess
import json


def get_video_metadata(video_path: str) -> dict:
    """
    動画のメタデータを取得

    Args:
        video_path: 動画ファイルパス

    Returns:
        {"duration": 総秒数, "fps": フレームレート, "width": 幅, "height": 高さ}
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = frame_count / fps if fps > 0 else 0

    cap.release()

    return {
        "duration": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": frame_count
    }


def extract_frame_at_time(video_path: str, time_sec: float) -> Optional[np.ndarray]:
    """
    指定時刻のフレームを抽出

    Args:
        video_path: 動画ファイルパス
        time_sec: 抽出する時刻 (秒)

    Returns:
        フレーム画像 (BGR形式のnumpy配列)、失敗時はNone
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return None

    # 指定時刻にシーク
    cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)

    ret, frame = cap.read()
    cap.release()

    if ret:
        return frame
    else:
        return None


def extract_frame_by_index(video_path: str, frame_index: int) -> Optional[np.ndarray]:
    """
    フレームインデックスでフレームを抽出

    Args:
        video_path: 動画ファイルパス
        frame_index: フレームインデックス (0始まり)

    Returns:
        フレーム画像 (BGR形式のnumpy配列)、失敗時はNone
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return None

    # 指定フレームにシーク
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

    ret, frame = cap.read()
    cap.release()

    if ret:
        return frame
    else:
        return None


def motion_series(video_path: str, fps: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    動画から動き量の時系列データを抽出

    Args:
        video_path: 動画ファイルパス
        fps: サンプリングFPS (デフォルト1.0 = 1秒ごと)

    Returns:
        (時刻配列, 動き量配列)
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps)  # サンプリング間隔

    times = []
    motions = []

    prev_gray = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # サンプリングFPSに従って処理
        if frame_idx % frame_interval == 0:
            # グレースケール変換
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None:
                # オプティカルフロー (Farneback法)
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray,
                    None,
                    pyr_scale=0.5,
                    levels=3,
                    winsize=15,
                    iterations=3,
                    poly_n=5,
                    poly_sigma=1.2,
                    flags=0
                )

                # フロー magnitude (動き量)
                mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                motion_value = np.mean(mag)

                time_sec = frame_idx / video_fps
                times.append(time_sec)
                motions.append(motion_value)

            prev_gray = gray.copy()

        frame_idx += 1

    cap.release()

    return np.array(times), np.array(motions)


def calculate_chest_motion(video_path: str, roi: Optional[Tuple[int, int, int, int]] = None, fps: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    胸郭領域の動き量を計算 (ROI指定可能)

    Args:
        video_path: 動画ファイルパス
        roi: (x, y, width, height) の形式でROIを指定。Noneの場合は画像中央部を使用
        fps: サンプリングFPS

    Returns:
        (時刻配列, 動き量配列)
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps)

    # ROIのデフォルト設定 (画像中央50%領域)
    if roi is None:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        roi = (
            int(width * 0.25),
            int(height * 0.25),
            int(width * 0.5),
            int(height * 0.5)
        )

    x, y, w, h = roi

    times = []
    motions = []

    prev_gray_roi = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            # ROI切り出し
            roi_frame = frame[y:y+h, x:x+w]
            gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)

            if prev_gray_roi is not None:
                # フレーム差分 (簡易的な動き検出)
                diff = cv2.absdiff(prev_gray_roi, gray_roi)
                motion_value = np.mean(diff)

                time_sec = frame_idx / video_fps
                times.append(time_sec)
                motions.append(motion_value)

            prev_gray_roi = gray_roi.copy()

        frame_idx += 1

    cap.release()

    return np.array(times), np.array(motions)


def encode_frame_to_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
    """
    フレームをJPEGバイト列にエンコード

    Args:
        frame: フレーム画像 (BGR形式のnumpy配列)
        quality: JPEG品質 (1-100)

    Returns:
        JPEGバイト列
    """
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    result, encoded_img = cv2.imencode('.jpg', frame, encode_param)

    if result:
        return encoded_img.tobytes()
    else:
        raise ValueError("Failed to encode frame to JPEG")
