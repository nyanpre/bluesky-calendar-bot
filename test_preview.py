import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# --- 設定エリア ---
TIMETREE_EMAIL = os.environ.get('TIMETREE_EMAIL')
TIMETREE_PASSWORD = os.environ.get('TIMETREE_PASSWORD')
TIMETREE_CALENDAR_URL = os.environ.get('TIMETREE_CALENDAR_URL')

def test_preview():
    JST = timezone(timedelta(hours=+9))
    now = datetime.now(JST)
    print(f"=== 実行開始 ({now.strftime('%Y-%m-%d %H:%M:%S JST')}) ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            # 1. ログイン処理
            print("TimeTreeにログイン中...")
            page.goto("https://timetreeapp.com/signin")
            page.fill('input[type="email"]', TIMETREE_EMAIL)
            page.fill('input[type="password"]', TIMETREE_PASSWORD)
            page.keyboard.press("Enter")
            
            # ログイン後の遷移を待機
            page.wait_for_function("() => !window.location.href.includes('signin')", timeout=30000)
            print("ログインに成功しました。")

            # 2. カレンダーページへ移動（ここを強化）
            print(f"カレンダーへ移動中: {TIMETREE_CALENDAR_URL}")
            page.goto(TIMETREE_CALENDAR_URL, wait_until="networkidle")
            time.sleep(5) # ネットワークが落ち着いた後、さらに5秒待機

            # 現在のURLをログに出力（デバッグ用）
            print(f"現在のURL: {page.url}")

            # 3. カレンダー画面の要素（今日の日付ボタン）を待機
            print("カレンダー画面の読み込みを待機中...")
            try:
                # 画面が真っ白な場合を考慮し、再読み込みを試行
                page.wait_for_selector('button[aria-current="date"]', timeout=30000)
            except:
                print("⚠️ 要素が見つからないため、一度再読み込みします...")
                page.reload(wait_until="networkidle")
                page.wait_for_selector('button[aria-current="date"]', timeout=30000)

            # ポップアップがあればEscキーで消す
            page.keyboard.press("Escape")
            time.sleep(2)

            # 4. 予定の抽出
            today_button = page.locator('button[aria-current="date"]')
            if today_button.count() > 0:
                print("今日の予定を抽出しています...")
                today_button.click(force=True)
                time.sleep(3) # パネル展開待ち
                
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
                event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))

                if event_titles:
                    msg = f"【{now.strftime('%m/%d')}の予定】\n"
                    for title in event_titles:
                        msg += f"・{title}\n"
                    print("\n" + "="*30 + "\n" + msg + "="*30)
                else:
                    print("ℹ️ 今日の予定は見つかりませんでした。")
            else:
                print("❌ 今日の日付ボタンが見つかりません。")
                page.screenshot(path="debug_calendar.png")

        except Exception as e:
            print(f"❌ エラー発生: {e}")
            page.screenshot(path="error_fatal.png")
        finally:
            browser.close()
            print("=== 実行終了 ===")

if __name__ == "__main__":
    test_preview()
