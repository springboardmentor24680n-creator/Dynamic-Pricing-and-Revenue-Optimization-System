"""
Generate 180 days of realistic sales history for all products.
Creates ~200K sales rows with realistic daily patterns.
"""
import sys, random
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='ascii', errors='replace')
sys.path.insert(0, '.')

import psycopg2

CONN = 'postgresql://postgres:postgres@localhost:5432/dynamic_pricing'
DAYS = 180
CHANNELS = ["Online", "Retail", "Marketplace", "Wholesale"]
REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["Consumer", "SMB", "Enterprise", "Government"]

def main():
    conn = psycopg2.connect(CONN)
    conn.autocommit = True
    cur = conn.cursor()

    # Get all products
    cur.execute("SELECT id, current_price, stock_quantity, category FROM products ORDER BY id")
    products = cur.fetchall()
    print(f"Products to seed: {len(products)}")

    # Clear existing sales
    cur.execute("DELETE FROM sales")
    print("Cleared existing sales")

    total_sales = 0
    all_rows = []

    for pid, price, stock, category in products:
        random.seed(pid)
        if price and price < 50:
            base = random.randint(3, 8)
        elif price and price < 200:
            base = random.randint(2, 5)
        elif price and price < 1000:
            base = random.randint(1, 3)
        else:
            base = random.randint(1, 2)

        for day in range(DAYS):
            date = datetime.utcnow() - timedelta(days=DAYS - day)
            weekday_factor = 1.5 if date.weekday() >= 5 else 1.0
            trend = 1.0 + (day / DAYS) * 0.2
            month = date.month
            seasonal = {1: 0.7, 2: 0.75, 3: 0.9, 4: 1.0, 5: 1.05, 6: 1.1,
                       7: 1.15, 8: 1.1, 9: 1.0, 10: 1.05, 11: 1.2, 12: 1.3}.get(month, 1.0)
            daily_units = max(1, int(base * weekday_factor * trend * seasonal * random.uniform(0.5, 1.4)))
            for _ in range(daily_units):
                qty = random.randint(1, 3)
                unit_price = round(price * random.uniform(0.88, 1.12), 2)
                total = round(unit_price * qty, 2)
                dt = date.replace(hour=random.randint(8, 21), minute=random.randint(0, 59))
                all_rows.append((pid, qty, unit_price, total, dt,
                                 random.choice(CHANNELS), random.choice(REGIONS), random.choice(SEGMENTS)))

    # Bulk insert via COPY for speed
    import io, csv
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter='\t')
    for r in all_rows:
        writer.writerow(r)
    buf.seek(0)
    cur.copy_expert(
        "COPY sales (product_id, quantity, unit_price, total_amount, sale_date, sale_channel, region, customer_segment) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t')",
        buf
    )
    total_sales = len(all_rows)

    conn.commit()

    # Verify
    cur.execute("SELECT COUNT(*) FROM sales")
    final = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT product_id) FROM sales")
    prods = cur.fetchone()[0]
    cur.execute("SELECT MIN(sale_date), MAX(sale_date) FROM sales")
    date_range = cur.fetchone()

    print(f"\n=== SALES HISTORY ===")
    print(f"Total sales rows: {final}")
    print(f"Products with sales: {prods}")
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    conn.close()

if __name__ == "__main__":
    main()
