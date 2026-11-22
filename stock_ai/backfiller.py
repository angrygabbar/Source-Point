import time
from datetime import datetime, timedelta
# Import the tools you successfully built
from bse_downloader import download_with_fallback
from db_manager import save_bhavcopy_to_db

def backfill_data(days_to_go_back=6600):
    print(f"--- Starting Backfill for last {days_to_go_back} days ---")
    
    # Start from yesterday (since we already have today/Dec 27)
    current_date = datetime(2024, 12, 26) 
    
    success_count = 0
    
    for i in range(days_to_go_back):
        print(f"\n[>] Processing Date: {current_date.date()}")
        
        # 1. Download
        # We add a small delay to avoid getting blocked by BSE server
        time.sleep(1) 
        df = download_with_fallback(current_date)
        
        if df is not None:
            # 2. Save to DB
            # We save to a temporary CSV first (optional, but good for debugging)
            temp_filename = "temp_backfill.csv"
            df.to_csv(temp_filename, index=False)
            
            save_bhavcopy_to_db(temp_filename, current_date)
            success_count += 1
        else:
            print("    [!] No data found (Weekend/Holiday or Error).")
            
        # Move back one day
        current_date -= timedelta(days=1)

    print("\n" + "="*40)
    print(f"Backfill Complete. Successfully added {success_count} days of data.")
    print("="*40)

if __name__ == "__main__":
    # We will fetch roughly 2 months of data to ensure we have enough for 50-day Moving Average
    backfill_data(days_to_go_back=6600)