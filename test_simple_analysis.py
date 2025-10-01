"""
シンプルな音声解析のテスト
実データでパラメータを調整
"""
import sys
sys.path.append('.')

from services import audio_simple, video


def test_audio_analysis(video_path: str):
    """音声解析テスト"""

    print('='*60)
    print('音声解析テスト')
    print('='*60)
    print()

    # 1. 動画メタデータ
    print('[1/5] 動画メタデータ取得中...')
    metadata = video.get_video_metadata(video_path)
    print(f'  動画長: {metadata["duration"]:.1f}秒 ({metadata["duration"]/60:.1f}分)')
    print()

    # 2. 音声抽出と前処理
    print('[2/5] 音声抽出と前処理中...')
    cfg = audio_simple.SimpleAudioConfig()
    audio_data, sr = audio_simple.load_and_preprocess(video_path, cfg.audio_sr)
    print(f'  サンプル数: {len(audio_data):,}')
    print(f'  サンプリングレート: {sr} Hz')
    print()

    # 3. RMSエネルギー計算
    print('[3/5] RMSエネルギー計算中...')
    times, rms = audio_simple.compute_rms_energy(audio_data, sr, cfg)
    print(f'  RMSフレーム数: {len(rms):,}')
    print()

    # 4. 音声統計分析
    print('[4/5] 音声統計分析中...')
    stats = audio_simple.analyze_audio_statistics(rms)
    print('  RMS統計:')
    for key, value in stats.items():
        print(f'    {key}: {value:.6f}')
    print()

    # 5. パラメータ推奨値を提案
    print('[5/5] パラメータ推奨値:')
    print(f'  無音閾値候補 (p25): {stats["p25"]:.6f}')
    print(f'  無音閾値候補 (p30): {stats["p30"]:.6f}')
    print(f'  呼吸再開閾値候補 (p75): {stats["p75"]:.6f}')
    print(f'  呼吸再開閾値候補 (p90): {stats["p90"]:.6f}')
    print()

    # 6. 無呼吸検出テスト（複数パラメータで試行）
    print('='*60)
    print('無呼吸検出テスト（パラメータ調整）')
    print('='*60)
    print()

    test_params = [
        {"percentile": 25, "multiplier": 2.0, "min_duration": 10.0},
        {"percentile": 30, "multiplier": 2.5, "min_duration": 10.0},
        {"percentile": 30, "multiplier": 3.0, "min_duration": 10.0},
        {"percentile": 35, "multiplier": 3.0, "min_duration": 10.0},
    ]

    best_result = None
    best_count = 0

    for i, params in enumerate(test_params, 1):
        print(f'--- テスト {i} ---')
        print(f'  パラメータ: 無音={params["percentile"]}%tile, 倍率={params["multiplier"]}x, 最小={params["min_duration"]}秒')

        cfg_test = audio_simple.SimpleAudioConfig()
        cfg_test.silence_threshold_percentile = params["percentile"]
        cfg_test.resume_threshold_multiplier = params["multiplier"]
        cfg_test.silence_min_duration = params["min_duration"]

        apnea_events = audio_simple.detect_apnea_simple(times, rms, cfg_test)

        print(f'  検出数: {len(apnea_events)} 回')

        if len(apnea_events) > 0:
            durations = [e["duration"] for e in apnea_events]
            avg_dur = sum(durations) / len(durations)
            max_dur = max(durations)
            print(f'  平均持続: {avg_dur:.1f}秒, 最大持続: {max_dur:.1f}秒')

            # 最初の3件を表示
            print(f'  検出イベント（最初の3件）:')
            for j, event in enumerate(apnea_events[:3], 1):
                print(f'    {j}. {event["start"]:.1f}s - {event["end"]:.1f}s (持続:{event["duration"]:.1f}s, 再開音:{event["resume_peak"]:.4f}, 信頼度:{event["confidence"]:.2f})')

            # AHI計算
            recording_hours = metadata["duration"] / 3600.0
            ahi = len(apnea_events) / recording_hours if recording_hours > 0 else 0
            print(f'  推定AHI: {ahi:.1f}')

            if len(apnea_events) > best_count:
                best_count = len(apnea_events)
                best_result = (params, apnea_events, ahi)

        print()

    # ベスト結果の表示
    if best_result:
        params, events, ahi = best_result
        print('='*60)
        print('推奨パラメータ:')
        print('='*60)
        print(f'  無音閾値パーセンタイル: {params["percentile"]}')
        print(f'  呼吸再開閾値倍率: {params["multiplier"]}')
        print(f'  無音最小持続時間: {params["min_duration"]}秒')
        print(f'  → 検出数: {len(events)}回, 推定AHI: {ahi:.1f}')
        print('='*60)


if __name__ == "__main__":
    video_path = 'tests/test_data/sleep_sample_5min.mp4'
    test_audio_analysis(video_path)
