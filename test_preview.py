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
    
    print("=== テスト実行開始 ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            # 1. ログイン処理
            print(f"[{now.strftime('%H:%M:%S')}] TimeTreeにログイン中...")
            page.goto("https://timetreeapp.com/signin")
            page.fill('input[type="email"]', TIMETREE_EMAIL)
            page.fill('input[type="password"]', TIMETREE_PASSWORD)
            page.click('button[type="submit"]')
            
            page.wait_for_url("**/calendars**", timeout=30000)
            
            # 2. カレンダーページへ移動
            print(f"[{now.strftime('%H:%M:%S')}] カレンダーへ移動中...")
            page.goto(TIMETREE_CALENDAR_URL)
            
            # ポップアップ対策
            time.sleep(5)
            page.keyboard.press("Escape")

            # 3. 今日の予定を取得
            print(f"[{now.strftime('%H:%M:%S')}] 今日の詳細パネルを開いています...")
            today_button = page.locator('button[aria-current="date"]')
            
            if today_button.count() > 0:
                today_button.click()
            else:
                print("❌ 今日の日付ボタンが見つかりませんでした。")
                return

            # 詳細パネル内の予定タイトルを待機
            try:
                page.wait_for_selector('[data-test-id="event-title"]', timeout=5000)
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
            except:
                print("ℹ️ 今日の予定は登録されていないようです。")
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
                print("✅ 文字数制限クリア（Blueskyに投稿可能です）")

        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
        finally:
            browser.close()
            print("\n=== テスト実行終了 ===")

if __name__ == "__main__":
    test_preview()
