"""
指標計算モジュール
無呼吸やいびきの統計指標を計算
"""
from typing import List, Dict


def summarize(apnea_events: List[Dict], snore_events: List[Dict], duration_sec: float) -> Dict:
    """
    解析結果のサマリを計算

    Args:
        apnea_events: 無呼吸イベントリスト
        snore_events: いびきイベントリスト
        duration_sec: 総録画時間 (秒)

    Returns:
        統計サマリ辞書
    """
    # 無呼吸関連の指標
    apnea_count = len(apnea_events)

    if apnea_count > 0:
        durations = [e["end"] - e["start"] for e in apnea_events]
        apnea_avg_duration = sum(durations) / len(durations)
        apnea_max_duration = max(durations)
        apnea_total_duration = sum(durations)
    else:
        apnea_avg_duration = 0.0
        apnea_max_duration = 0.0
        apnea_total_duration = 0.0

    # AHI (Apnea-Hypopnea Index) 相当の計算
    recording_hours = duration_sec / 3600.0
    ahi_est = apnea_count / recording_hours if recording_hours > 0 else 0.0

    # いびき関連の指標
    snore_count = len(snore_events)

    if snore_count > 0:
        snore_durations = [e["end"] - e["start"] for e in snore_events]
        snore_total_duration = sum(snore_durations)
        snore_index = snore_total_duration / duration_sec if duration_sec > 0 else 0.0
    else:
        snore_total_duration = 0.0
        snore_index = 0.0

    return {
        "apnea_count": apnea_count,
        "apnea_avg_duration": round(apnea_avg_duration, 2),
        "apnea_max_duration": round(apnea_max_duration, 2),
        "apnea_total_duration": round(apnea_total_duration, 2),
        "recording_hours": round(recording_hours, 2),
        "ahi_est": round(ahi_est, 2),
        "snore_count": snore_count,
        "snore_total_duration": round(snore_total_duration, 2),
        "snore_index": round(snore_index, 4),
        "説明": {
            "apnea_count": "検出された無呼吸の回数",
            "apnea_avg_duration": "無呼吸の平均持続時間（秒）",
            "apnea_max_duration": "無呼吸の最大持続時間（秒）",
            "apnea_total_duration": "無呼吸の合計時間（秒）",
            "recording_hours": "録画時間（時間）",
            "ahi_est": "推定AHI（1時間あたりの無呼吸回数、5未満が正常、5-15が軽度、15-30が中等度、30以上が重度）",
            "snore_count": "いびきイベントの回数",
            "snore_total_duration": "いびきの合計時間（秒）",
            "snore_index": "いびき指数（いびき時間/録画時間）"
        }
    }
