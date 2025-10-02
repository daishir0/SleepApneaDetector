# SleepApneaDetector

## Overview
SleepApneaDetector is a memory-optimized sleep apnea syndrome (SAS) detection and analysis system that analyzes audio from sleep recordings (video or audio files) to detect apnea events. It provides an intuitive 4-step workflow with calibration tools, statistical candidate extraction, and AHI (Apnea-Hypopnea Index) calculation for medical diagnosis support.

### Key Highlights
- **98.6% Memory Optimization**: Reduced from 11GB to 150MB through 8kHz sampling and lightweight audio processing
- **Dual Format Support**: Supports both video (MP4, MOV, AVI, etc.) and audio files (M4A, MP3, WAV, etc.)
- **4-Step Guided Workflow**: Intuitive UI with progress indicators for step-by-step analysis
- **Low-Spec Server Compatible**: Optimized for resource-constrained environments

## Installation

### Prerequisites
- Python 3.11
- FFmpeg
- conda environment
- Minimum 512MB RAM (previously required 8GB+)

### Step-by-step Installation

1. Clone the repository
```bash
git clone https://github.com/daishir0/SleepApneaDetector
cd SleepApneaDetector
```

2. Activate conda environment
```bash
conda activate 311
```
If you don't have Python 3.11 environment, create one:
```bash
conda create -n 311 python=3.11
conda activate 311
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Install FFmpeg (if not already installed)
```bash
# Amazon Linux 2023
sudo yum install ffmpeg -y

# Ubuntu/Debian
sudo apt-get install ffmpeg -y

# macOS
brew install ffmpeg
```

## Usage

### Starting the Server

```bash
# Start server
./sleep-apnea.sh start

# Stop server
./sleep-apnea.sh stop

# Restart server
./sleep-apnea.sh restart

# Check status
./sleep-apnea.sh status
```

### Access the Application
- **Top Page (Quick Analysis)**: http://localhost:8000
- **Calibration UI (Detailed Analysis)**: http://localhost:8000/calibration
- **API Documentation**: http://localhost:8000/docs

### 4-Step Workflow

The system guides you through a clear 4-step process:

#### Step 1: Upload & Analysis
1. **Top Page**: Upload video or audio file
   - Supported formats: MP4, MOV, AVI, M4A, MP3, WAV, etc.
   - Automatic audio extraction and analysis
2. **Navigate to Calibration Page** for detailed analysis

#### Step 2: Candidate Extraction
1. **Extract Candidates**: Click "Extract Candidates" → Top 50 RMS energy peaks automatically extracted
2. **Visual Progress**: Progress indicator shows current step

#### Step 3: Apnea Judgment
1. **Play Audio**: Listen to each candidate point
2. **Binary Judgment**: Mark as "Apnea" or "Skip"
3. **Auto-Save**: Judgments automatically saved to database
4. **View Summary**: Check judgment statistics (mean RMS, std dev, recommended range)

#### Step 4: Parameter Calculation
1. **Auto-Calculate**: Click "Calculate Parameters"
2. **Compute Thresholds**:
   - Silence threshold (based on mean RMS of apnea events)
   - Breathing resume multiplier (ratio of peak to silence)

#### Step 5: SAS Determination
1. **Execute SAS Judgment**: Click "Execute SAS Judgment"
2. **Results Display**:
   - Overall AHI (Apnea-Hypopnea Index)
   - Severity classification (Normal/Mild/Moderate/Severe)
   - Maximum AHI and worst symptomatic period
   - AHI timeline graph (Plotly visualization)

### Key Features

#### 1. Memory Optimization (v0.4.0)
- **98.6% memory reduction**: 11GB → 150MB
- **8kHz sampling rate**: Optimized for speech analysis
- **Lightweight audio processing**: RMS energy calculation only
- **No STFT computation**: Removed to reduce memory footprint
- **Compatible with low-spec servers**: Runs on 512MB RAM environments

#### 2. Dual Format Support
- **Video files**: MP4, MOV, AVI, MKV, FLV, WMV, WebM, M4V, 3GP, MPG, MPEG, OGV
- **Audio files**: WAV, MP3, M4A, AAC, FLAC, OGG, WMA, Opus, AIFF, AIF
- **Unified processing**: All files processed through optimized audio pipeline

#### 3. 4-Step Workflow UI
- **Progress Indicator**: Visual step-by-step progress tracking
- **Auto Step Transition**: Automatic progression between steps
- **Step Cards**: Collapsible cards with color-coded headers
- **Smooth Navigation**: Scroll-to-view functionality for better UX

#### 4. Calibration Function
- Video/audio file upload and analysis
- RMS energy-based candidate point extraction
- User-guided apnea interval marking
- Automatic parameter calculation (silence threshold, breathing resume multiplier)

#### 5. Candidate Judgment Mode
- Automatic extraction of top 50 RMS energy peaks
- Audio playback for verification
- Binary judgment (apnea/skip)
- Database persistence of judgment results

#### 6. Statistical-based Additional Candidate Extraction
- Statistical calculation from judged data (mean, standard deviation)
- Automatic extraction of similar candidates within μ±2σ range
- Confidence score-based incremental addition

#### 7. Recording Start DateTime Function
- Set video/audio recording start date/time
- Toggle between relative time ⇔ absolute time display
- Time display support for candidate list and waveform graph

#### 8. SAS Judgment Function (AHI Calculation)
- Sliding window method (5-minute intervals, 1-hour window)
- Overall AHI and severity determination (normal/mild/moderate/severe)
- Identification of maximum AHI and most symptomatic period
- AHI timeline graph visualization (Plotly)
- SAS diagnostic baseline (AHI=5) display

## Notes

### Medical Disclaimer
This system is for research and educational purposes only. It is NOT a substitute for professional medical diagnosis. Always consult with qualified healthcare professionals for sleep apnea diagnosis and treatment.

### SAS Diagnostic Criteria
- **AHI < 5**: Normal
- **5 ≤ AHI < 15**: Mild
- **15 ≤ AHI < 30**: Moderate
- **AHI ≥ 30**: Severe

### Data Privacy
- All video/audio and analysis data is stored locally
- No data is transmitted to external servers
- Database file: `data/sleep_analysis.db`

### System Requirements
- **Minimum**: 512MB RAM (after optimization)
- **Recommended**: 1GB+ RAM for smoother analysis
- **Storage**: Sufficient space for video/audio files
- **CPU**: Single-core processor sufficient (multi-core recommended for faster analysis)

### Technology Stack
- **Backend**: FastAPI 0.116.1, librosa 0.10.2, scipy 1.13.0, Plotly 2.27.0
- **Frontend**: HTML5/JavaScript, Plotly 2.27.0
- **Database**: SQLite
- **Audio Processing**: FFmpeg, FFprobe
- **Version**: simple-v0.4.0 (lightweight optimized version)

### Performance Metrics
- **Memory Usage**: 150MB (was 11GB)
- **Sampling Rate**: 8kHz (optimized for speech)
- **Processing Time**: ~30 seconds for 1-hour audio (on typical server)
- **Supported File Size**: Up to 2GB video/audio files

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

# SleepApneaDetector

## 概要
SleepApneaDetectorは、睡眠中の録音データ（動画または音声ファイル）から音声を解析し、無呼吸イベントを検出するメモリ最適化された睡眠時無呼吸症候群（SAS）検出・解析システムです。直感的な4ステップワークフローにより、キャリブレーションツール、統計ベース候補抽出、AHI（無呼吸低呼吸指数）計算による医学的診断支援機能を提供します。

### 主な特徴
- **98.6%のメモリ最適化**: 11GBから150MBへ削減（8kHzサンプリング、軽量音声処理）
- **動画・音声両対応**: MP4、MOV、M4A、MP3など幅広いフォーマットに対応
- **4ステップガイド付きワークフロー**: プログレスインジケーター付きの直感的UI
- **低スペックサーバー対応**: リソース制約環境向けに最適化

## インストール方法

### 必要環境
- Python 3.11
- FFmpeg
- conda環境
- 最小512MB RAM（従来は8GB以上必要でした）

### Step by stepのインストール方法

1. リポジトリをクローン
```bash
git clone https://github.com/daishir0/SleepApneaDetector
cd SleepApneaDetector
```

2. conda環境をアクティベート
```bash
conda activate 311
```
Python 3.11環境がない場合は作成します：
```bash
conda create -n 311 python=3.11
conda activate 311
```

3. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

4. FFmpegをインストール（未インストールの場合）
```bash
# Amazon Linux 2023
sudo yum install ffmpeg -y

# Ubuntu/Debian
sudo apt-get install ffmpeg -y

# macOS
brew install ffmpeg
```

## 使い方

### サーバー起動

```bash
# サーバー起動
./sleep-apnea.sh start

# サーバー停止
./sleep-apnea.sh stop

# サーバー再起動
./sleep-apnea.sh restart

# 状態確認
./sleep-apnea.sh status
```

### アプリケーションへのアクセス
- **トップページ（簡易解析）**: http://localhost:8000
- **キャリブレーションUI（詳細解析）**: http://localhost:8000/calibration
- **API仕様書**: http://localhost:8000/docs

### 4ステップワークフロー

システムが明確な4ステップでガイドします：

#### ステップ1: アップロード＆解析
1. **トップページ**: 動画または音声ファイルをアップロード
   - 対応形式: MP4, MOV, AVI, M4A, MP3, WAVなど
   - 自動的に音声抽出と解析を実行
2. **キャリブレーションページへ移動** 詳細解析を実施

#### ステップ2: 候補ポイント抽出
1. **候補抽出**: 「候補ポイントを抽出」ボタンをクリック → RMSエネルギー上位50件を自動抽出
2. **進捗表示**: プログレスインジケーターで現在のステップを表示

#### ステップ3: 無呼吸判定
1. **音声再生**: 各候補ポイントの音声を聴く
2. **2択判定**: 「無呼吸」または「違う」を判定
3. **自動保存**: 判定結果は自動的にデータベースに保存
4. **サマリ確認**: 判定統計（平均RMS、標準偏差、推奨範囲）を確認

#### ステップ4: パラメーター計算
1. **自動計算**: 「パラメータを計算」ボタンをクリック
2. **閾値計算**:
   - 無音閾値（無呼吸イベントの平均RMSベース）
   - 呼吸再開倍率（ピークと無音の比率）

#### ステップ5: SAS判定
1. **SAS判定実行**: 「SAS判定を実行」ボタンをクリック
2. **結果表示**:
   - 全体AHI（無呼吸低呼吸指数）
   - 重症度分類（正常/軽度/中等度/重度）
   - 最大AHIと最悪症状時間帯
   - AHI推移グラフ（Plotly可視化）

### 主な機能

#### 1. メモリ最適化（v0.4.0）
- **98.6%のメモリ削減**: 11GB → 150MB
- **8kHzサンプリングレート**: 音声解析に最適化
- **軽量音声処理**: RMSエネルギー計算のみ
- **STFT計算の削除**: メモリフットプリント削減のため除外
- **低スペックサーバー対応**: 512MB RAM環境で動作

#### 2. 動画・音声両対応
- **動画ファイル**: MP4, MOV, AVI, MKV, FLV, WMV, WebM, M4V, 3GP, MPG, MPEG, OGV
- **音声ファイル**: WAV, MP3, M4A, AAC, FLAC, OGG, WMA, Opus, AIFF, AIF
- **統一処理**: すべてのファイルを最適化された音声パイプラインで処理

#### 3. 4ステップワークフローUI
- **プログレスインジケーター**: ステップバイステップの進捗を視覚的に追跡
- **自動ステップ遷移**: ステップ間の自動進行
- **ステップカード**: 色分けされたヘッダー付きの折りたたみ可能カード
- **スムーズナビゲーション**: UX向上のためのスクロール機能

#### 4. キャリブレーション機能
- 動画・音声ファイルのアップロードと解析
- RMSエネルギーベースの候補ポイント抽出
- ユーザー主導の無呼吸区間マーキング
- パラメータ（無音閾値、呼吸再開倍率）の自動計算

#### 5. 候補判定モード
- RMSエネルギー上位50件の自動抽出
- 音声再生による確認
- 無呼吸/違うの2択判定
- 判定結果のデータベース永続化

#### 6. 統計ベース追加候補抽出
- 判定済みデータから統計計算（平均、標準偏差）
- μ±2σ範囲での類似候補の自動抽出
- 信頼度スコア付き段階的追加

#### 7. 撮影開始日時機能
- 動画・音声撮影開始日時の設定
- 相対時間⇔実時刻の表示切り替え
- 候補リスト・波形グラフの時刻表示対応

#### 8. SAS判定機能（AHI計算）
- スライディングウィンドウ方式（5分刻み、1時間窓）
- 全体AHI・重症度判定（正常/軽度/中等度/重度）
- 最大AHIと最も症状が強い時間帯の特定
- AHI推移グラフ（Plotly）による視覚化
- SAS診断基準線（AHI=5）の表示

## 注意点

### 医療免責事項
このシステムは研究・教育目的のみです。専門的な医学的診断の代わりにはなりません。睡眠時無呼吸症候群の診断・治療については、必ず資格を持つ医療専門家にご相談ください。

### SAS診断基準
- **AHI < 5**: 正常
- **5 ≤ AHI < 15**: 軽度
- **15 ≤ AHI < 30**: 中等度
- **AHI ≥ 30**: 重度

### データプライバシー
- すべての動画・音声・解析データはローカルに保存されます
- 外部サーバーへのデータ送信はありません
- データベースファイル: `data/sleep_analysis.db`

### システム要件
- **最小**: 512MB RAM（最適化後）
- **推奨**: 1GB以上のRAM（よりスムーズな解析のため）
- **ストレージ**: 動画・音声ファイル用の十分な空き容量
- **CPU**: シングルコアプロセッサで十分（高速解析にはマルチコア推奨）

### 技術スタック
- **バックエンド**: FastAPI 0.116.1, librosa 0.10.2, scipy 1.13.0, Plotly 2.27.0
- **フロントエンド**: HTML5/JavaScript, Plotly 2.27.0
- **データベース**: SQLite
- **音声処理**: FFmpeg, FFprobe
- **バージョン**: simple-v0.4.0（軽量最適化版）

### パフォーマンス指標
- **メモリ使用量**: 150MB（従来11GB）
- **サンプリングレート**: 8kHz（音声向けに最適化）
- **処理時間**: 1時間音声で約30秒（一般的なサーバー）
- **対応ファイルサイズ**: 最大2GBの動画・音声ファイル

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。詳細はLICENSEファイルを参照してください。
