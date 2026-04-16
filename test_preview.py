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
    print(f"=== テスト実行開始 ({now.strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    with sync_playwright() as p:
        # ボット検知を避けるため、一般的なWindowsのChromeとして振る舞う
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            # 直接カレンダーURLへアクセス（未ログインならsigninに飛ばされる）
            print(f"カレンダーページにアクセス中...")
            page.goto(TIMETREE_CALENDAR_URL)
            time.sleep(5)

            # ログイン画面にリダイレクトされた場合の処理
            if "signin" in page.url:
                print("未ログイン状態です。ログイン情報を入力します...")
                page.type('input[type="email"]', TIMETREE_EMAIL, delay=100)
                page.type('input[type="password"]', TIMETREE_PASSWORD, delay=100)
                
                print("ログイン情報を送信中（Enterキー）...")
                page.keyboard.press("Enter")
                
                # URLに 'signin' という文字列が含まれなくなるまで最大60秒待つ
                print("ログイン完了とカレンダーへの遷移を待機しています...")
                try:
                    page.wait_for_function("() => !window.location.href.includes('signin')", timeout=60000)
                    print("ログインに成功しました。")
                except:
                    print(f"⚠️ ログイン後の遷移がタイムアウトしました。現在のURL: {page.url}")
                    page.screenshot(path="error_login_timeout.png")
            
            # 再度カレンダーURLへ（確実に予定ページを表示するため）
            page.goto(TIMETREE_CALENDAR_URL)
            
            print("カレンダー画面の読み込みを待機中...")
            try:
                # 今日の日付ボタンが表示されるのを待つ
                page.wait_for_selector('button[aria-current="date"]', timeout=30000)
            except:
                print("❌ 予定画面を表示できませんでした。")
                page.screenshot(path="error_calendar_not_found.png")
                return

            # ポップアップがあれば消す
            page.keyboard.press("Escape")
            time.sleep(2)

            # 予定の抽出
            print("今日の予定をパネルから取得中...")
            today_button = page.locator('button[aria-current="date"]')
            if today_button.count() > 0:
                today_button.click(force=True)
                time.sleep(3) # パネルが開くのを待つ
                
                # スクリーンショットで確認した data-test-id を使用
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
                event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))

                if event_titles:
                    msg = f"【{now.strftime('%m/%d')}の予定】\n"
                    for title in event_titles:
                        msg += f"・{title}\n"
                    
                    print("\n" + "="*30)
                    print("📣 ポスト予定のプレビュー")
                    print("="*30)
                    print(msg)
                    print("="*30)
                else:
                    print("ℹ️ 今日の予定は登録されていないようです。")
            else:
                print("❌ 今日の日付ボタンが見つかりませんでした。")

        except Exception as e:
            print(f"❌ 実行中にエラーが発生しました: {e}")
            page.screenshot(path="error_fatal.png")
        finally:
            browser.close()
            print("=== テスト実行終了 ===")

if __name__ == "__main__":
    test_preview()
