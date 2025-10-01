# SleepApneaDetector

## Overview
SleepApneaDetector is a sleep apnea syndrome (SAS) detection and analysis system that analyzes audio from sleep videos to detect apnea events. It provides calibration tools, statistical candidate extraction, and AHI (Apnea-Hypopnea Index) calculation for medical diagnosis support.

## Installation

### Prerequisites
- Python 3.11
- FFmpeg
- conda environment

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
- **Calibration UI**: http://localhost:8000/calibration
- **API Documentation**: http://localhost:8000/docs

### Basic Workflow

1. **Upload Video**
   - Upload a video file of your sleep
   - Audio analysis runs automatically

2. **Candidate Judgment Mode**
   - Click "Extract Candidates" → Top 50 candidates extracted
   - Play each candidate audio
   - Judge as "Apnea" or "Skip"

3. **View Judgment Summary**
   - Click "Show Judgment Summary" → View statistics
   - Mean RMS, standard deviation, recommended range displayed

4. **Extract Additional Candidates** (Optional)
   - Extract similar candidates based on statistics
   - Select range (μ±2σ or μ±1σ)
   - Specify maximum number of candidates

5. **Calculate Parameters**
   - Click "Calculate Parameters" → Calculate silence threshold and breathing resume multiplier

6. **Execute SAS Judgment**
   - Click "Execute SAS Judgment" → AHI calculation and severity determination
   - Overall AHI, severity, worst period displayed
   - Click "Show AHI Timeline Graph" → View symptom trends over time

### Key Features

#### 1. Calibration Function
- Video file upload and audio analysis
- RMS energy-based candidate point extraction
- User-guided apnea interval marking
- Automatic parameter calculation (silence threshold, breathing resume multiplier)

#### 2. Candidate Judgment Mode
- Automatic extraction of top 50 RMS energy peaks
- Audio playback for verification
- Binary judgment (apnea/skip)
- Database persistence of judgment results

#### 3. Statistical-based Additional Candidate Extraction
- Statistical calculation from judged data (mean, standard deviation)
- Automatic extraction of similar candidates within μ±2σ range
- Confidence score-based incremental addition

#### 4. Recording Start DateTime Function
- Set video recording start date/time
- Toggle between relative time ⇔ absolute time display
- Time display support for candidate list and waveform graph

#### 5. SAS Judgment Function (AHI Calculation)
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
- All video and analysis data is stored locally
- No data is transmitted to external servers
- Database file: `data/sleep_analysis.db`

### System Requirements
- Recommended: 8GB RAM or more
- Storage: Sufficient space for video files
- CPU: Multi-core processor recommended for faster analysis

### Technology Stack
- **Backend**: FastAPI 0.116.1, librosa 0.10.2, scipy 1.13.0
- **Frontend**: HTML5/JavaScript, Plotly 2.27.0
- **Database**: SQLite
- **Audio Processing**: FFmpeg

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

# SleepApneaDetector

## 概要
SleepApneaDetectorは、睡眠中の動画から音声を解析し、無呼吸イベントを検出するための睡眠時無呼吸症候群（SAS）検出・解析システムです。キャリブレーションツール、統計ベース候補抽出、AHI（無呼吸低呼吸指数）計算による医学的診断支援機能を提供します。

## インストール方法

### 必要環境
- Python 3.11
- FFmpeg
- conda環境

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
- **キャリブレーションUI**: http://localhost:8000/calibration
- **API仕様書**: http://localhost:8000/docs

### 基本ワークフロー

1. **動画アップロード**
   - 睡眠中の動画ファイルをアップロード
   - 自動的に音声解析が実行される

2. **候補判定モード**
   - 「候補ポイントを抽出」→ 上位50件を自動抽出
   - 各候補を再生して確認
   - 無呼吸 or 違う を判定

3. **判定サマリ確認**
   - 「判定サマリを表示」→ 統計情報を確認
   - 平均RMS、標準偏差、推奨範囲を表示

4. **追加候補抽出**（任意）
   - 統計ベースで類似候補を追加抽出
   - 範囲（μ±2σ or μ±1σ）を選択
   - 最大件数を指定して実行

5. **パラメータ計算**
   - 「パラメータを計算」→ 無音閾値と呼吸再開倍率を算出

6. **SAS判定実行**
   - 「SAS判定を実行」→ AHI計算と重症度判定
   - 全体AHI、重症度、最悪時間帯を表示
   - 「AHI推移グラフを表示」→ 時系列での症状推移を確認

### 主な機能

#### 1. キャリブレーション機能
- 動画ファイルのアップロードと音声解析
- RMSエネルギーベースの候補ポイント抽出
- ユーザー主導の無呼吸区間マーキング
- パラメータ（無音閾値、呼吸再開倍率）の自動計算

#### 2. 候補判定モード
- RMSエネルギー上位50件の自動抽出
- 音声再生による確認
- 無呼吸/違うの2択判定
- 判定結果のデータベース永続化

#### 3. 統計ベース追加候補抽出
- 判定済みデータから統計計算（平均、標準偏差）
- μ±2σ範囲での類似候補の自動抽出
- 信頼度スコア付き段階的追加

#### 4. 撮影開始日時機能
- 動画撮影開始日時の設定
- 相対時間⇔実時刻の表示切り替え
- 候補リスト・波形グラフの時刻表示対応

#### 5. SAS判定機能（AHI計算）
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
- すべての動画・解析データはローカルに保存されます
- 外部サーバーへのデータ送信はありません
- データベースファイル: `data/sleep_analysis.db`

### システム要件
- 推奨: 8GB以上のRAM
- ストレージ: 動画ファイル用の十分な空き容量
- CPU: マルチコアプロセッサ推奨（高速解析のため）

### 技術スタック
- **バックエンド**: FastAPI 0.116.1, librosa 0.10.2, scipy 1.13.0
- **フロントエンド**: HTML5/JavaScript, Plotly 2.27.0
- **データベース**: SQLite
- **音声処理**: FFmpeg

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。詳細はLICENSEファイルを参照してください。
