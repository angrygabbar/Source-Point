import requests
import zipfile
import io
import pandas as pd
from datetime import datetime

def download_with_fallback(date_obj):
    # 1. Setup Dates
    # Classic format: 271224 (ddmmyy)
    d_str_classic = date_obj.strftime("%d%m%y") 
    # New format: 20241227 (yyyymmdd)
    d_str_new = date_obj.strftime("%Y%m%d")
    
    # 2. Define URL Patterns to try
    urls_to_try = [
        # Pattern A: Classic ZIP (Most common)
        f"https://www.bseindia.com/download/BhavCopy/Equity/EQ{d_str_classic}_CSV.ZIP",
        
        # Pattern B: New CSV format (Sometimes used for new archives)
        f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{d_str_new}_F_0000.CSV"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx'
    }

    print(f"--- Attempting Download for {date_obj.date()} ---")

    for url in urls_to_try:
        print(f"[*] Trying: {url} ...")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print("    [+] Success! File found.")
                
                # Check if it's a ZIP or a raw CSV
                content_type = response.headers.get('Content-Type', '')
                
                if 'zip' in content_type or url.endswith('.ZIP'):
                    print("    [+] Extracting ZIP...")
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        csv_filename = z.namelist()[0]
                        with z.open(csv_filename) as f:
                            df = pd.read_csv(f)
                else:
                    print("    [+] Reading CSV directly...")
                    df = pd.read_csv(io.BytesIO(response.content))
                    
                return df
            else:
                print(f"    [-] Failed (Status: {response.status_code})")
                
        except Exception as e:
            print(f"    [-] Error: {e}")

    return None

if __name__ == "__main__":
    # FORCE a known past date: Dec 27, 2024 (Friday)
    # This bypasses your system clock issue
    test_date = datetime(2024, 12, 27)
    
    df = download_with_fallback(test_date)

    if df is not None:
        print("\n" + "="*30)
        print("SUCCESS: CONNECTION ESTABLISHED")
        print("="*30)
        print(f"Rows fetched: {len(df)}")
        print("Columns:", list(df.columns[:5]), "...")
        df.to_csv("bse_final_test.csv", index=False)
        print("[+] Saved 'bse_final_test.csv'")
    else:
        print("\n[-] All methods failed. BSE might be blocking this IP or the archive moved.")