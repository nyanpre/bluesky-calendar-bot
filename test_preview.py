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
        # 一般的なWindows Chromeのふりをして検知を回避
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            # 直接ログイン画面へ
            print("TimeTreeにログイン中...")
            page.goto("https://timetreeapp.com/signin")
            
            # メールアドレスとパスワードを入力
            page.fill('input[type="email"]', TIMETREE_EMAIL)
            page.fill('input[type="password"]', TIMETREE_PASSWORD)
            
            # Enterキーで送信し、遷移を待つ
            page.keyboard.press("Enter")
            
            # ログインが完了してURLから 'signin' が消えるのを待つ
            try:
                page.wait_for_function("() => !window.location.href.includes('signin')", timeout=30000)
                print("ログインに成功しました。")
            except:
                print(f"ログイン後の遷移に失敗しました。現在のURL: {page.url}")
                page.screenshot(path="error_login.png")
                return

            # カレンダーページへ移動
            print("カレンダーを読み込み中...")
            page.goto(TIMETREE_CALENDAR_URL)
            
            # 「今日」のボタンが出るまで待機
            page.wait_for_selector('button[aria-current="date"]', timeout=30000)
            
            # ポップアップを閉じる
            page.keyboard.press("Escape")
            time.sleep(2)

            # 今日の予定パネルを展開
            today_button = page.locator('button[aria-current="date"]')
            if today_button.count() > 0:
                print("今日の予定を抽出しています...")
                today_button.click(force=True)
                time.sleep(3) # 展開待ち
                
                # イベントタイトルを取得
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
                event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))

                if event_titles:
                    msg = f"【{now.strftime('%m/%d')}の予定】\n"
                    for title in event_titles:
                        msg += f"・{title}\n"
                    
                    print("\n" + "="*30)
                    print(msg)
                    print("="*30)
                else:
                    print("ℹ️ 今日の予定は見つかりませんでした。")
            else:
                print("❌ 今日の日付ボタンが見つかりません。")

        except Exception as e:
            print(f"❌ エラー発生: {e}")
            page.screenshot(path="error_fatal.png")
        finally:
            browser.close()
            print("=== 実行終了 ===")

if __name__ == "__main__":
    test_preview()
