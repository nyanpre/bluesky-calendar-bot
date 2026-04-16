import os
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
from atproto import Client

def scrape_timetree():
    email = os.environ['TIMETREE_EMAIL']
    password = os.environ['TIMETREE_PASSWORD']
    calendar_url = os.environ['TIMETREE_CALENDAR_URL'] # 例: https://timetreeapp.com/calendars/XXXXX
    
    JST = timezone(timedelta(hours=+9))
    now = datetime.now(JST)
    
    with sync_playwright() as p:
        # ヘッドレスモード（画面を表示しない）で起動
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale='ja-JP', timezone_id='Asia/Tokyo')
        page = context.new_page()

        try:
            # 1. ログイン画面へアクセス
            print("ログインしています...")
            page.goto("https://timetreeapp.com/signin")
            
            # メールアドレスとパスワードを入力してログイン
            # ※セレクタ(inputのname属性など)は現在のTimeTree Web版に合わせてください
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)
            page.click('button[type="submit"]') # ログインボタン
            
            # ログイン完了を待機（カレンダー一覧ページ等に飛ぶまで）
            page.wait_for_url("**/calendars**", timeout=15000)
            
            # 2. 対象のカレンダーURL（オタクカレンダー等）へ直接移動
            print("カレンダーを取得中...")
            page.goto(calendar_url)
            
            # カレンダーの描画を少し待つ
            time.sleep(5)
            
            # 3. 今日の予定を抽出するロジック
            # TODO: ここから下はTimeTreeのHTML構造をブラウザの検証ツール(F12)で確認し、
            # 今日の予定のタイトルが格納されている要素のセレクタを指定します。
            
            # 例: 今日の日付の枠の中にある予定要素をすべて取得するイメージ
            # elements = page.query_selector_all('.today-event-title-class') 
            
            event_titles = []
            # for el in elements:
            #     event_titles.append(el.inner_text())

            # --- 仮の抽出データ（ローカルテスト用） ---
            event_titles = ["ハスノソラ聖地巡礼", "19:00 真剣飲み"]
            # ----------------------------------------

            if not event_titles:
                return None

            msg = f"【{now.strftime('%m/%d')}の予定】\n"
            for title in event_titles:
                msg += f"・{title}\n"
            
            return msg

        except Exception as e:
            print(f"スクレイピング中にエラーが発生しました: {e}")
            return None
        finally:
            browser.close()

def post_to_bluesky(text):
    client = Client()
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])
    client.send_post(text)

if __name__ == "__main__":
    content = scrape_timetree()
    if content:
        print("投稿内容:\n", content)
        # テストが完了するまでは投稿処理をコメントアウトしておくのが安全です
        # post_to_bluesky(content)
    else:
        print("今日の予定はありませんでした。")
