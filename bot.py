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
    JST = timezone(timedelta(hours=+9))
    now = datetime.now(JST)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale='ja-JP',
            timezone_id='Asia/Tokyo'
        )
        page = context.new_page()

        try:
            # ログイン
            page.goto("https://timetreeapp.com/signin")
            page.fill('input[type="email"]', TIMETREE_EMAIL)
            page.fill('input[type="password"]', TIMETREE_PASSWORD)
            page.keyboard.press("Enter")
            
            # 遷移待ち
            page.wait_for_function("() => !window.location.href.includes('signin')", timeout=30000)
            
            # カレンダーへ
            page.goto(TIMETREE_CALENDAR_URL)
            page.wait_for_selector('button[aria-current="date"]', timeout=30000)
            page.keyboard.press("Escape")
            time.sleep(2)

            # パネル展開
            today_button = page.locator('button[aria-current="date"]')
            if today_button.count() > 0:
                today_button.click(force=True)
                time.sleep(3)
                
                # 抽出
                titles = page.locator('[data-test-id="event-title"]').all_text_contents()
                event_titles = sorted(list(set([t.strip() for t in titles if t.strip()])))

                if not event_titles:
                    return None

                msg = f"【{now.strftime('%m/%d')}の予定】\n"
                for title in event_titles:
                    msg += f"・{title}\n"
                
                # 文字数制限対策
                return msg[:300]
            return None

        except Exception as e:
            print(f"Scraping Error: {e}")
            return None
        finally:
            browser.close()

def post_to_bluesky(text):
    try:
        client = Client()
        client.login(BSKY_HANDLE, BSKY_PASSWORD)
        client.send_post(text)
        print("Successfully posted to Bluesky.")
    except Exception as e:
        print(f"Bluesky Error: {e}")

if __name__ == "__main__":
    content = scrape_timetree()
    if content:
        post_to_bluesky(content)
    else:
        print("No content to post.")
