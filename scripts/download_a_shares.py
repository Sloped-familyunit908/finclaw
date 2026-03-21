"""
Download ALL A-share historical data to local CSV files.
Uses BaoStock (no rate limit, free, reliable).
Saves to: data/a_shares/{code}.csv
"""
import baostock as bs
import os
import sys
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "a_shares")
os.makedirs(DATA_DIR, exist_ok=True)

def download_all():
    lg = bs.login()
    print(f"BaoStock login: {lg.error_code}")
    
    # Get all stock codes
    rs = bs.query_stock_basic()
    stocks = []
    while rs.error_code == '0' and rs.next():
        row = rs.get_row_data()
        code = row[0]  # e.g., sh.600000
        name = row[1]
        status = row[4]  # 1=listed
        if status == '1' and (code.startswith('sh.6') or code.startswith('sz.0') or code.startswith('sz.3') or code.startswith('sh.688')):
            stocks.append((code, name))
    
    print(f"Found {len(stocks)} active A-share stocks")
    
    downloaded = 0
    skipped = 0
    errors = 0
    
    for i, (code, name) in enumerate(stocks):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(stocks)} (downloaded={downloaded}, skipped={skipped})")
        
        # Skip if already downloaded today
        csv_code = code.replace('.', '_')
        csv_path = os.path.join(DATA_DIR, f"{csv_code}.csv")
        if os.path.exists(csv_path):
            # Check if file is recent (within 1 day)
            mtime = os.path.getmtime(csv_path)
            if time.time() - mtime < 86400:
                skipped += 1
                continue
        
        try:
            rs = bs.query_history_k_data_plus(
                code,
                "date,code,open,high,low,close,volume,amount,turn",
                start_date='2024-03-01',
                end_date='2026-03-20',
                frequency='d',
                adjustflag='2'  # Pre-adjusted
            )
            
            rows = []
            while rs.error_code == '0' and rs.next():
                rows.append(rs.get_row_data())
            
            if len(rows) > 30:
                # Save to CSV
                with open(csv_path, 'w', encoding='utf-8') as f:
                    f.write("date,code,open,high,low,close,volume,amount,turn\n")
                    for row in rows:
                        f.write(','.join(row) + '\n')
                downloaded += 1
            
        except Exception as e:
            errors += 1
            if errors > 50:
                print(f"Too many errors, stopping")
                break
    
    bs.logout()
    
    print(f"\n=== Download Complete ===")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped (already fresh): {skipped}")
    print(f"Errors: {errors}")
    print(f"Data directory: {DATA_DIR}")
    
    # Count total files
    total = len([f for f in os.listdir(DATA_DIR) if f.endswith('.csv')])
    print(f"Total CSV files: {total}")

if __name__ == "__main__":
    download_all()
