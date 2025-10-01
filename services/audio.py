"""
音声処理モジュール
睡眠時無呼吸症候群の検出のための音声解析機能
"""
import numpy as np
import librosa
import soundfile as sf
from scipy import signal
from scipy.fft import fft
from typing import Tuple, Dict, List
import tempfile
import subprocess


class AudioConfig:
    """音声処理の設定パラメータ"""
    def __init__(self):
        self.audio_sr = 16000  # サンプリングレート
        self.rms_win = 0.05  # RMS窓サイズ (秒)
        self.rms_hop = 0.01  # RMSホップサイズ (秒)
        self.apnea_min_duration = 10.0  # 無呼吸最小持続時間 (秒)
        self.rms_threshold_percentile = 15  # RMS閾値パーセンタイル
        self.breath_band = (200, 800)  # 呼吸帯域 (Hz)
        self.snore_band = (800, 2000)  # いびき帯域 (Hz)
        self.highpass_cutoff = 80  # ハイパスフィルタカットオフ (Hz)


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
    cutoff = 80 / nyquist
    b, a = signal.butter(4, cutoff, btype='high')
    audio = signal.filtfilt(b, a, audio)

    # 振幅正規化
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val

    return audio, sr


def short_time_rms(audio: np.ndarray, sr: int, cfg: AudioConfig) -> Tuple[np.ndarray, np.ndarray]:
    """
    短時間RMS (Root Mean Square) エネルギーを計算

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


def band_energy(audio: np.ndarray, sr: int, bands: List[Tuple[int, int]], cfg: AudioConfig) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    特定の周波数帯域のエネルギーを計算

    Args:
        audio: 音声データ
        sr: サンプリングレート
        bands: [(低域Hz, 高域Hz), ...] のリスト
        cfg: 設定

    Returns:
        {"帯域名": (時刻配列, エネルギー配列), ...}
    """
    hop_length = int(cfg.rms_hop * sr)
    n_fft = 2048

    # STFT (短時間フーリエ変換)
    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(stft)

    # 周波数配列
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # 時刻配列
    times = librosa.frames_to_time(
        np.arange(magnitude.shape[1]),
        sr=sr,
        hop_length=hop_length
    )

    result = {}
    for low, high in bands:
        # 帯域内の周波数インデックスを取得
        band_indices = np.where((freqs >= low) & (freqs <= high))[0]

        # 帯域エネルギー (帯域内の周波数成分の合計)
        band_power = np.sum(magnitude[band_indices, :], axis=0)

        band_name = f"{low}-{high}"
        result[band_name] = (times, band_power)

    return result


def breath_cycle_strength(audio: np.ndarray, sr: int, cfg: AudioConfig) -> Tuple[np.ndarray, np.ndarray]:
    """
    呼吸周期の強度を計算 (簡略版 - パフォーマンス改善)

    Args:
        audio: 音声データ
        sr: サンプリングレート
        cfg: 設定

    Returns:
        (時刻配列, 周期強度配列)
    """
    hop_length = int(cfg.rms_hop * sr)

    # 呼吸帯域のフィルタリング
    nyquist = sr / 2
    low_cut = cfg.breath_band[0] / nyquist
    high_cut = cfg.breath_band[1] / nyquist
    b, a = signal.butter(4, [low_cut, high_cut], btype='band')
    breath_audio = signal.filtfilt(b, a, audio)

    # 短時間エネルギーの変動を周期強度として使用（軽量版）
    rms = librosa.feature.rms(
        y=breath_audio,
        frame_length=int(1.0 * sr),  # 1秒窓
        hop_length=hop_length
    )[0]

    times = librosa.frames_to_time(
        np.arange(len(rms)),
        sr=sr,
        hop_length=hop_length
    )

    # RMSの標準偏差を周期強度として使用（変動が少ない=無呼吸の可能性）
    # 移動窓で標準偏差を計算
    window_size = 30  # 約3秒分のフレーム
    cycle_strength = np.zeros_like(rms)

    for i in range(len(rms)):
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(rms), i + window_size // 2)
        cycle_strength[i] = np.std(rms[start_idx:end_idx])

    return times, cycle_strength


def detect_apnea_candidates(
    rms_t: np.ndarray,
    rms: np.ndarray,
    breath_energy_t: np.ndarray,
    breath_energy: np.ndarray,
    cycle_t: np.ndarray,
    cycle_strength: np.ndarray,
    cfg: AudioConfig
) -> List[Dict]:
    """
    無呼吸候補を検出

    Args:
        rms_t: RMS時刻配列
        rms: RMS配列
        breath_energy_t: 呼吸帯域エネルギー時刻配列
        breath_energy: 呼吸帯域エネルギー配列
        cycle_t: 呼吸周期強度時刻配列
        cycle_strength: 呼吸周期強度配列
        cfg: 設定

    Returns:
        [{"start": 開始時刻, "end": 終了時刻, "confidence": 信頼度}, ...]
    """
    # RMS閾値を自動計算
    rms_threshold = np.percentile(rms, cfg.rms_threshold_percentile)

    # 呼吸エネルギー閾値
    breath_threshold = np.percentile(breath_energy, cfg.rms_threshold_percentile)

    # 周期強度閾値
    cycle_threshold = np.percentile(cycle_strength, 30)

    # RMSを時系列でスキャンし、低エネルギー区間を検出
    is_low_energy = (rms < rms_threshold)

    # 呼吸エネルギーも低い区間
    # 時刻を合わせるため、補間
    breath_interp = np.interp(rms_t, breath_energy_t, breath_energy)
    is_low_breath = (breath_interp < breath_threshold)

    # 周期強度も低い区間
    cycle_interp = np.interp(rms_t, cycle_t, cycle_strength)
    is_low_cycle = (cycle_interp < cycle_threshold)

    # 3つの条件を組み合わせて無呼吸候補を判定
    is_apnea = is_low_energy & is_low_breath & is_low_cycle

    # 連続区間を検出
    candidates = []
    in_apnea = False
    start_idx = 0

    for i in range(len(is_apnea)):
        if is_apnea[i] and not in_apnea:
            # 無呼吸開始
            in_apnea = True
            start_idx = i
        elif not is_apnea[i] and in_apnea:
            # 無呼吸終了
            in_apnea = False
            start_t = rms_t[start_idx]
            end_t = rms_t[i]
            duration = end_t - start_t

            # 最小持続時間チェック
            if duration >= cfg.apnea_min_duration:
                confidence = 0.5  # 基本信頼度
                candidates.append({
                    "start": float(start_t),
                    "end": float(end_t),
                    "confidence": confidence
                })

    # 最後まで無呼吸状態の場合
    if in_apnea:
        start_t = rms_t[start_idx]
        end_t = rms_t[-1]
        duration = end_t - start_t
        if duration >= cfg.apnea_min_duration:
            candidates.append({
                "start": float(start_t),
                "end": float(end_t),
                "confidence": 0.5
            })

    return candidates


def detect_snore(rms_t: np.ndarray, snore_energy: np.ndarray, cfg: AudioConfig) -> List[Dict]:
    """
    いびきイベントを検出

    Args:
        rms_t: 時刻配列
        snore_energy: いびき帯域エネルギー配列
        cfg: 設定

    Returns:
        [{"start": 開始時刻, "end": 終了時刻, "level": 強度}, ...]
    """
    # いびき帯域の高エネルギー区間を検出
    threshold = np.percentile(snore_energy, 75)

    is_snore = (snore_energy > threshold)

    # 連続区間を検出
    snore_events = []
    in_snore = False
    start_idx = 0

    for i in range(len(is_snore)):
        if is_snore[i] and not in_snore:
            in_snore = True
            start_idx = i
        elif not is_snore[i] and in_snore:
            in_snore = False
            start_t = rms_t[start_idx]
            end_t = rms_t[i]

            # 0.5秒以上のいびきのみ記録
            if (end_t - start_t) >= 0.5:
                level = float(np.mean(snore_energy[start_idx:i]) / (np.max(snore_energy) + 1e-10))
                snore_events.append({
                    "start": float(start_t),
                    "end": float(end_t),
                    "level": level
                })

    if in_snore:
        start_t = rms_t[start_idx]
        end_t = rms_t[-1]
        if (end_t - start_t) >= 0.5:
            level = float(np.mean(snore_energy[start_idx:]) / (np.max(snore_energy) + 1e-10))
            snore_events.append({
                "start": float(start_t),
                "end": float(end_t),
                "level": level
            })

    return snore_events


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
