import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
from atproto import Client

# --- 設定エリア ---
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
            page.fill('input[type="email"]', TIMETREE_EMAIL)
            page.fill('input[type="password"]', TIMETREE_PASSWORD)
            
            # ログインボタンを確実にクリック
            page.click('button[type="submit"]', force=True)
            
            # URL監視を避け、3秒待機後に直接カレンダーURLへ移動
            print("ログイン処理を実行しました。カレンダーページへ移動します...")
            time.sleep(3) 
            page.goto(TIMETREE_CALENDAR_URL)
            
            # 2. カレンダーの読み込みを待機
            print("画面の読み込みを待機中（最大60秒）...")
            try:
                # 「今日」のボタンが出るまで待つ
                page.wait_for_selector('button[aria-current="date"]', timeout=60000)
            except:
                print("カレンダーの読み込みが遅れていますが、処理を続行します。")
            
            # ポップアップ対策
            page.keyboard.press("Escape")
            time.sleep(2)

            # 3. 今日の予定を取得
            print("今日の詳細パネルを開いています...")
            today_button = page.locator('button[aria-current="date"]')
            
            if today_button.count() > 0:
                today_button.click(force=True)
                time.sleep(2) # パネル展開を待つ
            else:
                print("今日のボタンが見つかりませんでした。")
                return None

            # 詳細パネル内の予定タイトルを待機
            try:
                # [data-test-id="event-title"] を使用
                page.wait_for_selector('[data-test-id="event-title"]', timeout=10000)
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
            except:
                print("今日の予定は見つかりませんでした。")
                return None

            # 4. 整形
            event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))
            if not event_titles:
                return None

            msg = f"【{now.strftime('%m/%d')}の予定】\n"
            for title in event_titles:
                msg += f"・{title}\n"
            
            # Bluesky 300文字制限対策
            if len(msg) > 300:
                msg = msg[:297] + "..."
                
            return msg

        except Exception as e:
            print(f"スクレイピングエラー: {e}")
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
    content = scrape_timetree()
    if content:
        print(f"--- 投稿内容 ---\n{content}")
        post_to_bluesky(content)
    else:
        print("投稿する内容がないため、終了します。")
