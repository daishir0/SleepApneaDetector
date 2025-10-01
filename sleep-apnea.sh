#!/bin/bash
# Sleep Apnea Detection API - 管理スクリプト
# 使い方: ./sleep-apnea.sh {start|stop|restart|status}

APP_DIR="/home/ec2-user/hirashimallc/21_pj-sleep/outputs/app"
PORT=8000
LOG_FILE="/tmp/sleep_server.log"
PID_FILE="/tmp/sleep_server.pid"

start() {
    echo "サーバーを起動しています..."

    # 既に起動しているか確認
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo "❌ サーバーは既に起動しています (ポート $PORT が使用中)"
        echo "先に停止してください: $0 stop"
        exit 1
    fi

    cd $APP_DIR

    # conda環境をアクティベート
    source /home/ec2-user/anaconda3/bin/activate
    conda activate 311

    # サーバー起動
    nohup python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT > $LOG_FILE 2>&1 &

    # プロセスIDを保存
    echo $! > $PID_FILE

    sleep 3

    # 起動確認
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo "✅ サーバーが起動しました (PID: $(cat $PID_FILE))"
        echo "📍 URL: http://localhost:$PORT"
        echo "📍 キャリブレーション: http://localhost:$PORT/calibration"
        echo "📋 ログ: tail -f $LOG_FILE"
    else
        echo "❌ サーバーの起動に失敗しました"
        echo "ログを確認してください: cat $LOG_FILE"
        exit 1
    fi
}

stop() {
    echo "サーバーを停止しています..."

    # ポートを使用しているプロセスを強制終了
    if lsof -i :$PORT > /dev/null 2>&1; then
        lsof -ti :$PORT | xargs kill -9 2>/dev/null
        sleep 1

        if lsof -i :$PORT > /dev/null 2>&1; then
            echo "❌ サーバーの停止に失敗しました"
            exit 1
        else
            echo "✅ サーバーを停止しました"
            rm -f $PID_FILE
        fi
    else
        echo "ℹ️  サーバーは既に停止しています"
    fi
}

restart() {
    echo "🔄 サーバーを再起動します..."
    echo ""
    stop
    echo ""
    start
}

status() {
    echo "=== サーバー状態 ==="
    echo ""

    if lsof -i :$PORT > /dev/null 2>&1; then
        PID=$(lsof -ti :$PORT)
        echo "✅ サーバーは起動中です"
        echo "📍 PID: $PID"
        echo "📍 URL: http://localhost:$PORT"
        echo "📍 キャリブレーション: http://localhost:$PORT/calibration"
        echo ""
        echo "プロセス情報:"
        ps aux | grep $PID | grep -v grep
        echo ""
        echo "最新ログ (最後の10行):"
        tail -10 $LOG_FILE
    else
        echo "❌ サーバーは停止しています"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "使い方: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
