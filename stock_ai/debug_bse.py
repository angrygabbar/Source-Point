import requests
from datetime import datetime

def test_bse_access():
    print("--- 🔍 STARTING BSE CONNECTIVITY TEST ---")
    
    # 1. Setup Session (Mimic a Real Browser)
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    session.headers.update(headers)

    # 2. Visit Homepage first (To get Cookies)
    try:
        print("[*] Visiting BSE Homepage to get cookies...")
        r_home = session.get("https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx", timeout=10)
        print(f"    Status: {r_home.status_code} | Cookies: {list(session.cookies.get_dict().keys())}")
    except Exception as e:
        print(f"    ❌ Connection Error: {e}")
        return

    # 3. Try to Download Specific File (Jan 14, 2026 - Today)
    # Note: Adjust date if today is a holiday/weekend
    date_str = "140126" # 14th Jan 2026
    date_full = "20260114"
    
    urls = [
        f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{date_full}_F_0000.CSV",
        f"https://www.bseindia.com/download/BhavCopy/Equity/EQ{date_str}_CSV.ZIP"
    ]

    print(f"\n[*] Attempting Downloads for {date_full}...")
    for url in urls:
        print(f"    TARGET: {url}")
        try:
            r = session.get(url, timeout=10)
            print(f"    RESULT: Status {r.status_code}")
            if r.status_code == 200:
                print("    ✅ SUCCESS! File found.")
                print(f"    Size: {len(r.content)} bytes")
                break
            elif r.status_code == 403:
                print("    ⛔ ACCESS DENIED (403). Firewall is blocking Python.")
            elif r.status_code == 404:
                print("    ❌ NOT FOUND (404). File doesn't exist.")
        except Exception as e:
            print(f"    ⚠️ Error: {e}")

if __name__ == "__main__":
    test_bse_access()