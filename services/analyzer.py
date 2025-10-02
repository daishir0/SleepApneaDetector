"""
解析パイプライン（軽量版）
音声処理のみを使用した無呼吸検出のメインロジック
メモリ効率を重視し、STFT・動画処理を削除
"""
from typing import Dict, List
from . import audio_simple
from . import video
from . import metrics


class AnalysisConfig:
    """解析設定"""
    def __init__(self):
        self.audio_cfg = audio_simple.SimpleAudioConfig()
        self.motion_fps = 1.0  # 動き量サンプリングFPS（未使用）
        self.motion_threshold_percentile = 20  # （未使用）
        self.version = "simple-v0.4.0"  # 軽量版バージョン


class AnalysisResults:
    """解析結果"""
    def __init__(self):
        self.duration_sec: float = 0.0
        self.sr: int = 0
        self.waveform_downsampled: Dict = {}
        self.rms_full: Dict = {}  # キャリブレーション用の全RMSデータ
        self.events: List[Dict] = []
        self.summary: Dict = {}
        self.version: str = ""

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "duration_sec": self.duration_sec,
            "sr": self.sr,
            "waveform_downsampled": self.waveform_downsampled,
            "rms_full": self.rms_full,  # キャリブレーション用の全RMSデータ
            "events": self.events,
            "summary": self.summary,
            "version": self.version
        }


def analyze(video_path: str, cfg: AnalysisConfig = None) -> AnalysisResults:
    """
    動画・音声ファイルを解析し、無呼吸検出結果を返す

    Args:
        video_path: 動画・音声ファイルパス
        cfg: 解析設定

    Returns:
        解析結果
    """
    if cfg is None:
        cfg = AnalysisConfig()

    results = AnalysisResults()
    results.version = cfg.version

    # ファイルタイプ判定
    import os
    file_ext = os.path.splitext(video_path)[1].lower().lstrip('.')

    video_extensions = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'm4v',
                       '3gp', 'mpg', 'mpeg', 'ogv']
    audio_extensions = ['wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'opus',
                       'aiff', 'aif']

    # 1. メタデータ取得（ファイルタイプで分岐）
    if file_ext in video_extensions:
        print("[解析開始] 動画メタデータを取得中...")
        metadata = video.get_video_metadata(video_path)
        results.duration_sec = metadata["duration"]
        print(f"  動画長: {results.duration_sec:.1f}秒 ({metadata['duration']/60:.1f}分)")
    elif file_ext in audio_extensions:
        print("[解析開始] 音声メタデータを取得中...")
        results.duration_sec = audio_simple.get_audio_duration(video_path)
        print(f"  音声長: {results.duration_sec:.1f}秒 ({results.duration_sec/60:.1f}分)")
    else:
        raise ValueError(f"非対応のファイル形式です: {file_ext}")

    # 2. 音声処理（軽量版：8kHz、ハイパスフィルタのみ）
    print("[音声処理] 音声抽出と前処理を実行中（軽量版）...")
    audio_data, sr = audio_simple.load_and_preprocess(video_path, cfg.audio_cfg.audio_sr)
    results.sr = sr
    print(f"  サンプリングレート: {sr} Hz")

    # 3. RMSエネルギー計算のみ（メモリ効率重視）
    print("[音声処理] RMS (音声エネルギー) を計算中...")
    rms_t, rms = audio_simple.compute_rms_energy(audio_data, sr, cfg.audio_cfg)
    print(f"  RMSフレーム数: {len(rms)}")

    # 4. シンプル無呼吸検出（無音→大音パターン）
    print("[無呼吸検出] シンプル検出アルゴリズムを実行中...")
    apnea_events = audio_simple.detect_apnea_simple(rms_t, rms, cfg.audio_cfg)
    print(f"  無呼吸イベント数: {len(apnea_events)}")

    # 5. イベント統合（無呼吸のみ、いびき検出は省略）
    all_events = []
    for event in apnea_events:
        all_events.append({
            "type": "apnea",
            "start": event["start"],
            "end": event["end"],
            "confidence": event.get("confidence", 0.8)  # デフォルト信頼度
        })

    results.events = sorted(all_events, key=lambda x: x["start"])

    # 6. サマリ計算（いびきは0件として扱う）
    print("[指標計算] 統計サマリを計算中...")
    snore_events = []  # いびき検出は省略
    summary = metrics.summarize(apnea_events, snore_events, results.duration_sec)
    results.summary = summary

    # 7. 全RMSデータを保存（キャリブレーション用）
    print("[データ保存] 全RMSデータを保存中...")
    results.rms_full = {
        "t": rms_t.tolist(),
        "y": rms.tolist()
    }

    # 8. 波形ダウンサンプリング (プロット用)
    print("[可視化準備] 波形データをダウンサンプリング中...")
    import numpy as np
    # シンプルなダウンサンプリング
    max_points = 5000
    if len(rms_t) > max_points:
        step = len(rms_t) // max_points
        down_t = rms_t[::step]
        down_y = rms[::step]
    else:
        down_t = rms_t
        down_y = rms

    results.waveform_downsampled = {
        "t": down_t.tolist(),
        "y": down_y.tolist()
    }

    print(f"[解析完了] 無呼吸 {summary['apnea_count']} 回")
    print(f"  AHI推定値: {summary['ahi_est']}")

    return results
