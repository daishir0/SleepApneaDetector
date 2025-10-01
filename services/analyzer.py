"""
解析パイプライン
音声・動画処理を統合した無呼吸検出のメインロジック
"""
from typing import Dict, List
from . import audio
from . import video
from . import fusion
from . import metrics


class AnalysisConfig:
    """解析設定"""
    def __init__(self):
        self.audio_cfg = audio.AudioConfig()
        self.motion_fps = 1.0  # 動き量サンプリングFPS
        self.motion_threshold_percentile = 20
        self.version = "rule-v0.3.1"


class AnalysisResults:
    """解析結果"""
    def __init__(self):
        self.duration_sec: float = 0.0
        self.sr: int = 0
        self.waveform_downsampled: Dict = {}
        self.events: List[Dict] = []
        self.summary: Dict = {}
        self.version: str = ""

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "duration_sec": self.duration_sec,
            "sr": self.sr,
            "waveform_downsampled": self.waveform_downsampled,
            "events": self.events,
            "summary": self.summary,
            "version": self.version
        }


def analyze(video_path: str, cfg: AnalysisConfig = None) -> AnalysisResults:
    """
    動画ファイルを解析し、無呼吸検出結果を返す

    Args:
        video_path: 動画ファイルパス
        cfg: 解析設定

    Returns:
        解析結果
    """
    if cfg is None:
        cfg = AnalysisConfig()

    results = AnalysisResults()
    results.version = cfg.version

    # 1. 動画メタデータ取得
    print("[解析開始] 動画メタデータを取得中...")
    metadata = video.get_video_metadata(video_path)
    results.duration_sec = metadata["duration"]
    print(f"  動画長: {results.duration_sec:.1f}秒 ({metadata['duration']/60:.1f}分)")

    # 2. 音声処理
    print("[音声処理] 音声抽出と前処理を実行中...")
    audio_data, sr = audio.load_and_preprocess(video_path, cfg.audio_cfg.audio_sr)
    results.sr = sr
    print(f"  サンプリングレート: {sr} Hz")

    # 3. RMS計算
    print("[音声処理] RMS (音声エネルギー) を計算中...")
    rms_t, rms = audio.short_time_rms(audio_data, sr, cfg.audio_cfg)
    print(f"  RMSフレーム数: {len(rms)}")

    # 4. 帯域エネルギー計算
    print("[音声処理] 周波数帯域エネルギーを計算中...")
    bands = audio.band_energy(
        audio_data, sr,
        [cfg.audio_cfg.breath_band, cfg.audio_cfg.snore_band],
        cfg.audio_cfg
    )
    breath_t, breath_energy = bands[f"{cfg.audio_cfg.breath_band[0]}-{cfg.audio_cfg.breath_band[1]}"]
    snore_t, snore_energy = bands[f"{cfg.audio_cfg.snore_band[0]}-{cfg.audio_cfg.snore_band[1]}"]
    print(f"  呼吸帯域フレーム数: {len(breath_energy)}")

    # 5. 呼吸周期強度計算
    print("[音声処理] 呼吸周期強度を計算中...")
    cycle_t, cycle_strength = audio.breath_cycle_strength(audio_data, sr, cfg.audio_cfg)
    print(f"  周期強度フレーム数: {len(cycle_strength)}")

    # 6. 無呼吸候補検出 (音声ベース)
    print("[無呼吸検出] 音声ベースの無呼吸候補を検出中...")
    apnea_candidates = audio.detect_apnea_candidates(
        rms_t, rms,
        breath_t, breath_energy,
        cycle_t, cycle_strength,
        cfg.audio_cfg
    )
    print(f"  初期無呼吸候補数: {len(apnea_candidates)}")

    # 7. 動き量解析
    print("[動画処理] 動き量を解析中...")
    try:
        motion_t, motion = video.motion_series(video_path, fps=cfg.motion_fps)
        print(f"  動き量フレーム数: {len(motion)}")
    except Exception as e:
        print(f"  警告: 動き量解析に失敗しました ({e})")
        motion_t, motion = [], []

    # 8. 融合判定 (音声 + 動画)
    print("[融合判定] 音声と動画情報を統合して無呼吸を精緻化中...")
    if len(motion_t) > 0:
        apnea_events_refined = fusion.refine_with_motion(
            apnea_candidates, motion_t, motion,
            cfg.motion_threshold_percentile
        )
    else:
        apnea_events_refined = apnea_candidates

    # 近接イベントを統合
    apnea_events_final = fusion.merge_nearby_events(apnea_events_refined, max_gap=2.0)
    print(f"  最終無呼吸イベント数: {len(apnea_events_final)}")

    # 9. いびき検出
    print("[いびき検出] いびきイベントを検出中...")
    snore_events = audio.detect_snore(snore_t, snore_energy, cfg.audio_cfg)
    print(f"  いびきイベント数: {len(snore_events)}")

    # 10. イベント統合
    all_events = []
    for event in apnea_events_final:
        all_events.append({
            "type": "apnea",
            "start": event["start"],
            "end": event["end"],
            "confidence": event["confidence"]
        })

    for event in snore_events:
        all_events.append({
            "type": "snore",
            "start": event["start"],
            "end": event["end"],
            "level": event["level"]
        })

    results.events = sorted(all_events, key=lambda x: x["start"])

    # 11. サマリ計算
    print("[指標計算] 統計サマリを計算中...")
    summary = metrics.summarize(apnea_events_final, snore_events, results.duration_sec)
    results.summary = summary

    # 12. 波形ダウンサンプリング (プロット用)
    print("[可視化準備] 波形データをダウンサンプリング中...")
    down_t, down_y = audio.downsample_for_plot(rms_t, rms, max_points=5000)
    results.waveform_downsampled = {
        "t": down_t.tolist(),
        "y": down_y.tolist()
    }

    print(f"[解析完了] 無呼吸 {summary['apnea_count']} 回、いびき {summary['snore_count']} 回")
    print(f"  AHI推定値: {summary['ahi_est']}")

    return results
