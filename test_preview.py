import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# --- 設定エリア ---
TIMETREE_EMAIL = os.environ.get('TIMETREE_EMAIL')
TIMETREE_PASSWORD = os.environ.get('TIMETREE_PASSWORD')
TIMETREE_CALENDAR_URL = os.environ.get('TIMETREE_CALENDAR_URL')

def test_preview():
    """TimeTreeから取得した内容をログに表示してテストする"""
    JST = timezone(timedelta(hours=+9))
    now = datetime.now(JST)
    
    print(f"=== テスト実行開始 ({now.strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    with sync_playwright() as p:
        # ブラウザの起動
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            # 1. ログイン処理
            print("TimeTreeにアクセス中...")
            page.goto("https://timetreeapp.com/signin")
            
            # 入力を少しゆっくりにする（1文字ごとに50ms休む）
            page.type('input[type="email"]', TIMETREE_EMAIL, delay=50)
            page.type('input[type="password"]', TIMETREE_PASSWORD, delay=50)
            
            # ボタンをクリックする代わりに、パスワード欄で「Enter」キーを押す
            # これにより、ボタンの配置変更や重なりを無視して送信できます
            print("ログイン情報を送信中...")
            page.keyboard.press("Enter")
            
            # ログイン後の読み込み（ネットワークが落ち着くまで）を最大30秒待つ
            # ここでURLが /calendars に変わるのをじっくり待ちます
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
                print("ログイン完了。カレンダーへ移動します...")
            except:
                print("読み込みに時間がかかっていますが、強行します。")

            # 直接カレンダーURLへ
            page.goto(TIMETREE_CALENDAR_URL)
            
            # 2. カレンダーの読み込み待機
            print("画面の読み込みを待機中（最大60秒）...")
            try:
                # 今日の日付ボタンが出るまで粘り強く待つ
                page.wait_for_selector('button[aria-current="date"]', timeout=60000)
            except:
                print("⚠️ カレンダーの読み込みに時間がかかっています。現在の状態を確認します。")
            
            # 案内ポップアップなどが出ている可能性を考慮してEscape
            page.keyboard.press("Escape")
            time.sleep(2)

            # 3. 今日の予定を取得
            print("今日の詳細パネルを開いています...")
            today_button = page.locator('button[aria-current="date"]')
            
            if today_button.count() > 0:
                # 確実にクリックするために force=True を追加
                today_button.click(force=True)
                time.sleep(2) # パネルが開くのを少し待つ
            else:
                print("❌ 今日の日付ボタンが見つかりませんでした。")
                # デバッグ用に現在のURLを表示
                print(f"現在のURL: {page.url}")
                return

            # 詳細パネル内の予定タイトルを待機
            try:
                # 画像で見つけた最強の目印 data-test-id を使用
                page.wait_for_selector('[data-test-id="event-title"]', timeout=10000)
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
            except:
                print("ℹ️ 今日の予定は登録されていないか、詳細パネルが開きませんでした。")
                return

            # 4. 整形とプレビュー表示
            event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))

            msg = f"【{now.strftime('%m/%d')}の予定】\n"
            for title in event_titles:
                msg += f"・{title}\n"
            
            print("\n" + "="*30)
            print("📣 ポスト予定のプレビュー")
            print("="*30)
            print(msg)
            print("="*30)
            
            # 文字数チェック
            char_count = len(msg)
            print(f"現在の文字数: {char_count} / 300文字")
            
            if char_count > 300:
                print("⚠️ 警告: 300文字を超えています！本番では切り捨てられます。")
            else:
                print("✅ 文字数制限クリア")

        except Exception as e:
            print(f"❌ 予期せぬエラーが発生しました: {e}")
        finally:
            browser.close()
            print("\n=== テスト実行終了 ===")

if __name__ == "__main__":
    test_preview()
