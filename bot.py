import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
from atproto import Client

# --- 設定エリア ---
# GitHub Secretsから環境変数を読み込みます
TIMETREE_EMAIL = os.environ.get('TIMETREE_EMAIL')
TIMETREE_PASSWORD = os.environ.get('TIMETREE_PASSWORD')
TIMETREE_CALENDAR_URL = os.environ.get('TIMETREE_CALENDAR_URL')
BSKY_HANDLE = os.environ.get('BSKY_HANDLE')
BSKY_PASSWORD = os.environ.get('BSKY_PASSWORD')

def scrape_timetree():
    """TimeTreeから今日の予定をスクレイピングする"""
    JST = timezone(timedelta(hours=+9))
    now = datetime.now(JST)
    
    with sync_playwright() as p:
        # ブラウザの起動 (GitHub Actions上で動くようヘッドレスモード)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
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
            page.click('button[type="submit"]')
            
            # ログイン後の遷移を待機
            page.wait_for_url("**/calendars**", timeout=30000)
            
            # 2. カレンダーページへ移動
            print(f"カレンダーにアクセス中: {TIMETREE_CALENDAR_URL}")
            page.goto(TIMETREE_CALENDAR_URL)
            
            # ポップアップが出た場合に備えてEscapeキーを押す
            time.sleep(5)
            page.keyboard.press("Escape")

            # 3. 今日の予定を取得
            # 今日のボタン（aria-current="date"）を探してクリック
            print("今日の詳細パネルを開いています...")
            today_button = page.locator('button[aria-current="date"]')
            if today_button.count() > 0:
                today_button.click()
            else:
                print("今日のボタンが見つかりませんでした。")
                return None

            # 詳細パネル内のタイトル要素(data-test-id)を待機
            # 予定がない場合はタイムアウトするので、try-exceptで囲みます
            try:
                page.wait_for_selector('[data-test-id="event-title"]', timeout=5000)
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
            except:
                print("今日の予定は空のようです。")
                return None

            # 4. 取得したテキストの整形
            event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))

            if not event_titles:
                return None

            msg = f"【{now.strftime('%m/%d')}の予定】\n"
            for title in event_titles:
                msg += f"・{title}\n"
            
            # Blueskyの300文字制限対策
            if len(msg) > 300:
                msg = msg[:297] + "..."
                
            return msg

        except Exception as e:
            print(f"エラー発生: {e}")
            return None
        finally:
            browser.close()

def post_to_bluesky(text):
    """Blueskyに投稿する"""
    try:
        print("Blueskyに投稿中...")
        client = Client()
        client.login(BSKY_HANDLE, BSKY_PASSWORD)
        client.send_post(text)
        print("投稿に成功しました！")
    except Exception as e:
        print(f"Bluesky投稿エラー: {e}")

if __name__ == "__main__":
    # 実行
    content = scrape_timetree()
    if content:
        print(f"--- 投稿内容 ---\n{content}")
        post_to_bluesky(content)
    else:
        print("投稿する内容がないため、終了します。")
