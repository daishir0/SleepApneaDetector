"""
無音区間のパターン分析
無音区間とその後の音レベルを統計的に分析してパラメータを決定
"""
import sys
sys.path.append('.')

from services import audio_simple, video
import numpy as np


def analyze_silence_patterns(video_path: str):
    """無音区間パターンの詳細分析"""

    print('='*60)
    print('無音区間パターン分析')
    print('='*60)
    print()

    # 1. 音声抽出
    print('[1/4] 音声抽出中...')
    cfg = audio_simple.SimpleAudioConfig()
    audio_data, sr = audio_simple.load_and_preprocess(video_path, cfg.audio_sr)
    print(f'  完了')
    print()

    # 2. RMS計算
    print('[2/4] RMSエネルギー計算中...')
    times, rms = audio_simple.compute_rms_energy(audio_data, sr, cfg)
    print(f'  RMSフレーム数: {len(rms):,}')
    print()

    # 3. RMS統計
    stats = audio_simple.analyze_audio_statistics(rms)
    print('[3/4] RMS統計:')
    for key, value in stats.items():
        print(f'  {key}: {value:.6f}')
    print()

    # 4. 無音区間の全パターン分析
    print('[4/4] 無音区間パターン分析中...')
    print()

    # 様々な閾値で無音区間を抽出
    test_percentiles = [20, 25, 30, 35, 40, 45, 50]

    for percentile in test_percentiles:
        silence_threshold = np.percentile(rms, percentile)

        # 無音区間を抽出（最小持続時間なし）
        is_silence = rms < silence_threshold

        silence_segments = []
        in_silence = False
        silence_start_idx = 0

        for i in range(len(is_silence)):
            if is_silence[i] and not in_silence:
                in_silence = True
                silence_start_idx = i
            elif not is_silence[i] and in_silence:
                in_silence = False
                duration = times[i] - times[silence_start_idx]

                # 無音区間の後の音レベルを取得
                check_frames = min(20, len(rms) - i)  # 後続1秒間をチェック
                if check_frames > 0:
                    resume_peak = np.max(rms[i:i+check_frames])
                    resume_mean = np.mean(rms[i:i+check_frames])

                    silence_segments.append({
                        'start': times[silence_start_idx],
                        'end': times[i],
                        'duration': duration,
                        'resume_peak': resume_peak,
                        'resume_mean': resume_mean,
                        'ratio_peak': resume_peak / silence_threshold if silence_threshold > 0 else 0,
                        'ratio_mean': resume_mean / silence_threshold if silence_threshold > 0 else 0
                    })

        # 統計分析
        if len(silence_segments) > 0:
            durations = [s['duration'] for s in silence_segments]
            resume_peaks = [s['resume_peak'] for s in silence_segments]
            ratios_peak = [s['ratio_peak'] for s in silence_segments]
            ratios_mean = [s['ratio_mean'] for s in silence_segments]

            # 長い無音区間（10秒以上）の抽出
            long_silence = [s for s in silence_segments if s['duration'] >= 10.0]

            print(f'--- 無音閾値 {percentile}%tile (RMS={silence_threshold:.6f}) ---')
            print(f'  全無音区間数: {len(silence_segments)}')
            print(f'  無音持続時間: min={min(durations):.1f}s, max={max(durations):.1f}s, mean={np.mean(durations):.1f}s')
            print(f'  10秒以上の無音: {len(long_silence)}個')

            if len(long_silence) > 0:
                long_ratios_peak = [s['ratio_peak'] for s in long_silence]
                long_ratios_mean = [s['ratio_mean'] for s in long_silence]

                print(f'  → 10秒以上無音の後の音レベル比率（ピーク）:')
                print(f'     min={min(long_ratios_peak):.2f}x, max={max(long_ratios_peak):.2f}x, ')
                print(f'     mean={np.mean(long_ratios_peak):.2f}x, median={np.median(long_ratios_peak):.2f}x')
                print(f'     p25={np.percentile(long_ratios_peak, 25):.2f}x, p75={np.percentile(long_ratios_peak, 75):.2f}x')

                print(f'  → 10秒以上無音の詳細（最初の5件）:')
                for i, s in enumerate(long_silence[:5], 1):
                    print(f'     {i}. {s["start"]:.1f}s-{s["end"]:.1f}s (持続:{s["duration"]:.1f}s, 後の音:{s["ratio_peak"]:.2f}x)')

                # 推奨パラメータ
                if len(long_ratios_peak) >= 3:
                    # 75%点を推奨値とする（上位25%を無呼吸とみなす）
                    recommended_ratio = np.percentile(long_ratios_peak, 75)
                    print(f'  ★ 推奨パラメータ: 無音閾値={percentile}%tile, 呼吸再開倍率={recommended_ratio:.1f}x')

            print()

    print('='*60)
    print('分析完了')
    print('='*60)


if __name__ == "__main__":
    # 3つのサンプルで分析
    samples = [
        'tests/test_data/sleep_sample_5min.mp4',
        'tests/test_data/sleep_sample_1h.mp4',
        'tests/test_data/sleep_sample_2h.mp4',
        'tests/test_data/sleep_sample_3h.mp4'
    ]

    for sample in samples:
        print(f'\n\n{"#"*60}')
        print(f'# サンプル: {sample}')
        print(f'{"#"*60}\n')

        try:
            analyze_silence_patterns(sample)
        except Exception as e:
            print(f'エラー: {e}')
            continue
