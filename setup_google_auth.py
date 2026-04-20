"""
執行此腳本來完成 Google OAuth 授權
第一次執行會開啟瀏覽器讓你登入 Google 帳號
授權完成後會輸出 token JSON，把它複製到 .env 的 GOOGLE_TOKEN_JSON
"""
import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly"
]

def main():
    print("🔐 開始 Google OAuth 授權流程...")
    print("請確認 credentials.json 在同一個資料夾\n")
    
    if not os.path.exists("credentials.json"):
        print("❌ 找不到 credentials.json，請先下載並放到專案根目錄")
        return
    
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes)
    }
    
    token_json = json.dumps(token_data)
    
    print("\n✅ 授權成功！")
    print("\n請將以下內容複製到 .env 檔案的 GOOGLE_TOKEN_JSON=")
    print("（同時也要加入 Railway 的環境變數）\n")
    print("=" * 60)
    print(token_json)
    print("=" * 60)
    
    # 同時存成本地檔案備用
    with open("token.json", "w") as f:
        json.dump(token_data, f)
    print("\n✅ 也已存成 token.json 備用")

if __name__ == "__main__":
    main()
