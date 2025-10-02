"""
シンプルな音声ベース無呼吸検出
雑音を除外し、無音→大きな音のパターンで無呼吸を検出
"""
import numpy as np
import librosa
import soundfile as sf
from scipy import signal
from typing import Tuple, List, Dict
import tempfile
import subprocess


class SimpleAudioConfig:
    """シンプル音声処理の設定パラメータ"""
    def __init__(self):
        self.audio_sr = 16000  # サンプリングレート
        self.rms_win = 0.1  # RMS窓サイズ (秒)
        self.rms_hop = 0.05  # RMSホップサイズ (秒)

        # 無音検出パラメータ（実データで調整）
        self.silence_threshold_percentile = 30  # 無音判定の閾値パーセンタイル
        self.silence_min_duration = 10.0  # 無音最小持続時間 (秒)

        # 呼吸再開検出パラメータ
        self.resume_threshold_multiplier = 3.0  # 無音閾値の何倍で呼吸再開とするか

        # ノイズ除去
        self.highpass_cutoff = 100  # ハイパスフィルタカットオフ (Hz)
        self.noise_floor_percentile = 10  # ノイズフロア推定


def load_and_preprocess(video_path: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """
    動画から音声を抽出し、前処理を実行

    Args:
        video_path: 動画ファイルパス
        target_sr: 目標サンプリングレート

    Returns:
        (音声データ, サンプリングレート)
    """
    # FFmpegで動画から音声を抽出
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
        tmp_path = tmp_audio.name

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn',  # ビデオなし
        '-acodec', 'pcm_s16le',
        '-ar', str(target_sr),
        '-ac', '1',  # モノラル
        '-y',
        tmp_path
    ]

    subprocess.run(cmd, capture_output=True, check=True)

    # 音声読み込み
    audio, sr = librosa.load(tmp_path, sr=target_sr, mono=True)

    # ハイパスフィルタ (低周波ノイズ除去)
    nyquist = sr / 2
    cutoff = 100 / nyquist
    b, a = signal.butter(4, cutoff, btype='high')
    audio = signal.filtfilt(b, a, audio)

    # 振幅正規化
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val

    return audio, sr


def compute_rms_energy(audio: np.ndarray, sr: int, cfg: SimpleAudioConfig) -> Tuple[np.ndarray, np.ndarray]:
    """
    RMSエネルギーを計算

    Args:
        audio: 音声データ
        sr: サンプリングレート
        cfg: 設定

    Returns:
        (時刻配列, RMS配列)
    """
    win_length = int(cfg.rms_win * sr)
    hop_length = int(cfg.rms_hop * sr)

    # RMS計算
    rms = librosa.feature.rms(
        y=audio,
        frame_length=win_length,
        hop_length=hop_length
    )[0]

    # 時刻配列
    times = librosa.frames_to_time(
        np.arange(len(rms)),
        sr=sr,
        hop_length=hop_length
    )

    return times, rms


def analyze_audio_statistics(rms: np.ndarray) -> Dict:
    """
    音声統計を分析してパラメータ推定

    Args:
        rms: RMS配列

    Returns:
        統計情報辞書
    """
    stats = {
        "min": float(np.min(rms)),
        "max": float(np.max(rms)),
        "mean": float(np.mean(rms)),
        "median": float(np.median(rms)),
        "std": float(np.std(rms)),
        "p10": float(np.percentile(rms, 10)),
        "p25": float(np.percentile(rms, 25)),
        "p30": float(np.percentile(rms, 30)),
        "p50": float(np.percentile(rms, 50)),
        "p75": float(np.percentile(rms, 75)),
        "p90": float(np.percentile(rms, 90)),
    }
    return stats


def detect_apnea_simple(
    times: np.ndarray,
    rms: np.ndarray,
    cfg: SimpleAudioConfig
) -> List[Dict]:
    """
    シンプルな無呼吸検出

    パターン: 無音が一定時間続く → 大きな音（呼吸再開）

    Args:
        times: 時刻配列
        rms: RMS配列
        cfg: 設定

    Returns:
        無呼吸イベントリスト
    """
    # 無音閾値を決定（パーセンタイル基準）
    silence_threshold = np.percentile(rms, cfg.silence_threshold_percentile)

    # 呼吸再開閾値（無音閾値の数倍）
    resume_threshold = silence_threshold * cfg.resume_threshold_multiplier

    print(f"  無音閾値: {silence_threshold:.6f}")
    print(f"  呼吸再開閾値: {resume_threshold:.6f}")

    # 無音区間を検出
    is_silence = rms < silence_threshold

    # 連続する無音区間を検出
    apnea_events = []
    in_silence = False
    silence_start_idx = 0

    for i in range(len(is_silence)):
        if is_silence[i] and not in_silence:
            # 無音開始
            in_silence = True
            silence_start_idx = i

        elif not is_silence[i] and in_silence:
            # 無音終了
            in_silence = False
            silence_start_time = times[silence_start_idx]
            silence_end_time = times[i]
            silence_duration = silence_end_time - silence_start_time

            # 最小持続時間チェック
            if silence_duration >= cfg.silence_min_duration:
                # 呼吸再開の大きな音をチェック（無音終了後の数フレーム）
                check_frames = min(10, len(rms) - i)
                if check_frames > 0:
                    resume_peak = np.max(rms[i:i+check_frames])

                    # 呼吸再開の音が十分大きいかチェック
                    if resume_peak > resume_threshold:
                        confidence = min(1.0, resume_peak / resume_threshold)

                        apnea_events.append({
                            "start": float(silence_start_time),
                            "end": float(silence_end_time),
                            "duration": float(silence_duration),
                            "resume_peak": float(resume_peak),
                            "confidence": float(confidence)
                        })

    # 最後まで無音の場合
    if in_silence:
        silence_start_time = times[silence_start_idx]
        silence_end_time = times[-1]
        silence_duration = silence_end_time - silence_start_time

        if silence_duration >= cfg.silence_min_duration:
            apnea_events.append({
                "start": float(silence_start_time),
                "end": float(silence_end_time),
                "duration": float(silence_duration),
                "resume_peak": 0.0,
                "confidence": 0.5  # 終端なので低めの信頼度
            })

    return apnea_events


def downsample_for_plot(times: np.ndarray, values: np.ndarray, max_points: int = 5000) -> Tuple[np.ndarray, np.ndarray]:
    """
    プロット用にデータをダウンサンプリング

    Args:
        times: 時刻配列
        values: 値配列
        max_points: 最大ポイント数

    Returns:
        (ダウンサンプリング後時刻配列, ダウンサンプリング後値配列)
    """
    if len(times) <= max_points:
        return times, values

    # 等間隔でサンプリング
    indices = np.linspace(0, len(times) - 1, max_points, dtype=int)
    return times[indices], values[indices]


def get_audio_duration(audio_path: str) -> float:
    """
    音声ファイルの継続時間を取得（動画対応なし、音声専用）

    Args:
        audio_path: 音声ファイルパス

    Returns:
        継続時間（秒）
    """
    # librosaで音声読み込み（サンプリングレートは元のまま）
    y, sr = librosa.load(audio_path, sr=None)
    duration = len(y) / sr
    return float(duration)
