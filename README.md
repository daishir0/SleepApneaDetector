# Sleep Apnea Detection System

睡眠時無呼吸症候群（SAS）の検出・解析システム

## 🎯 概要

このシステムは、睡眠中の動画から音声を解析し、無呼吸イベントを検出するためのキャリブレーション・解析ツールです。

## ✨ 主な機能

### 1. キャリブレーション機能
- 動画ファイルのアップロードと音声解析
- RMSエネルギーベースの候補ポイント抽出
- ユーザー主導の無呼吸区間マーキング
- パラメータ（無音閾値、呼吸再開倍率）の自動計算

### 2. 候補判定モード
- RMSエネルギー上位50件の自動抽出
- 音声再生による確認
- 無呼吸/違うの2択判定
- 判定結果のデータベース永続化

### 3. 統計ベース追加候補抽出
- 判定済みデータから統計計算（平均、標準偏差）
- μ±2σ範囲での類似候補の自動抽出
- 信頼度スコア付き段階的追加

### 4. 撮影開始日時機能
- 動画撮影開始日時の設定
- 相対時間⇔実時刻の表示切り替え
- 候補リスト・波形グラフの時刻表示対応

### 5. 判定結果の永続化
- 候補判定結果のデータベース保存
- 再判定可能（無呼吸⇔違う）
- ページリロード後も設定・判定を復元

### 6. SAS判定機能（AHI計算）
- スライディングウィンドウ方式（5分刻み、1時間窓）
- 全体AHI・重症度判定（正常/軽度/中等度/重度）
- 最大AHIと最も症状が強い時間帯の特定
- AHI推移グラフ（Plotly）による視覚化
- SAS診断基準線（AHI=5）の表示

## 🏗️ アーキテクチャ

```
app/
├── api/                    # FastAPI バックエンド
│   ├── main.py            # メインアプリケーション
│   └── calibration.py     # キャリブレーションAPI
├── services/              # ビジネスロジック
│   ├── audio_simple.py    # 音声処理
│   ├── video.py           # 動画処理
│   └── storage.py         # データ永続化
├── web/                   # フロントエンド
│   └── calibration.html   # キャリブレーションUI
├── data/                  # データ保存先
│   ├── uploads/           # アップロードファイル
│   ├── results/           # 解析結果JSON
│   └── sleep_analysis.db  # SQLiteデータベース
└── sleep-apnea.sh         # サーバー管理スクリプト
```

## 🚀 セットアップ

### 必要環境
- Python 3.11
- FFmpeg
- conda環境（311）

### インストール

```bash
# conda環境アクティベート
conda activate 311

# 依存パッケージインストール
pip install -r requirements.txt

# FFmpegインストール（未インストールの場合）
# Amazon Linux 2023
sudo yum install ffmpeg -y
```

## 📦 使い方

### サーバー起動

```bash
# 起動
./sleep-apnea.sh start

# 停止
./sleep-apnea.sh stop

# 再起動
./sleep-apnea.sh restart

# 状態確認
./sleep-apnea.sh status
```

### アクセス

- **キャリブレーションUI**: http://localhost:8000/calibration
- **API仕様**: http://localhost:8000/docs

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

4. **追加候補抽出（任意）**
   - 統計ベースで類似候補を追加抽出
   - 範囲（μ±2σ or μ±1σ）を選択
   - 最大件数を指定して実行

5. **パラメータ計算**
   - 「パラメータを計算」→ 無音閾値と呼吸再開倍率を算出

6. **SAS判定実行**
   - 「SAS判定を実行」→ AHI計算と重症度判定
   - 全体AHI、重症度、最悪時間帯を表示
   - 「AHI推移グラフを表示」→ 時系列での症状推移を確認

## 📊 データベーススキーマ

### jobs テーブル
- ジョブ管理（動画ファイル情報）
- 撮影開始日時、表示モード

### candidate_judgments テーブル
- 候補判定結果の保存
- job_id, candidate_id, status

### events テーブル
- 検出された無呼吸イベント

### summary テーブル
- 解析結果サマリ

## 🛠️ 技術スタック

### バックエンド
- **FastAPI** 0.116.1 - REST API フレームワーク
- **numpy** 1.26.4 - 数値計算
- **librosa** 0.10.2 - 音声処理
- **scipy** 1.13.0 - 信号処理（ピーク検出）
- **SQLite** - データ永続化

### フロントエンド
- **HTML5/JavaScript**
- **Plotly** 2.27.0 - インタラクティブグラフ
- **HTML5 Audio API** - 音声再生

### その他
- **FFmpeg** - 動画からの音声抽出
- **uvicorn** - ASGIサーバー

## 📝 API エンドポイント

### キャリブレーション
- `POST /calibrate/analyze` - 動画解析
- `POST /calibrate/extract-candidates` - 候補抽出
- `POST /calibrate/extract-additional-candidates` - 追加候補抽出
- `POST /calibrate/judgment-summary` - 判定サマリ計算
- `POST /calibrate/calculate` - パラメータ計算

### ジョブ管理
- `GET /calibrate/jobs` - ジョブ一覧
- `GET /calibrate/load?job_id=xxx` - ジョブ読み込み
- `PUT /calibrate/job/{job_id}/name` - ジョブ名更新
- `PUT /calibrate/job/{job_id}/recording-time` - 撮影日時設定
- `PUT /calibrate/job/{job_id}/display-mode` - 表示モード切替
- `DELETE /calibrate/job/{job_id}` - ジョブ削除

### 判定管理
- `POST /calibrate/save-judgment` - 判定保存
- `GET /calibrate/judgments?job_id=xxx` - 判定取得

### SAS判定
- `POST /calibrate/calculate-ahi` - AHI計算と重症度判定

## 🔧 開発

### テスト実行

```bash
pytest tests/
```

### ログ確認

```bash
tail -f /tmp/sleep_server.log
```

## 📈 今後の開発予定

- [x] SAS判定ロジック（AHI計算） ✅
- [x] スライディングウィンドウ方式のAHI推移グラフ ✅
- [x] 重症度判定（正常/軽度/中等度/重度） ✅
- [x] 最大AHI・最悪時間帯の特定 ✅
- [ ] レポート出力機能（PDF/Excel）
- [ ] 無呼吸イベントの詳細分析（継続時間分布）
- [ ] 複数日にまたがる解析の比較機能

## 📄 ライセンス

Private Project

## 👤 作者

Hirashima LLC
