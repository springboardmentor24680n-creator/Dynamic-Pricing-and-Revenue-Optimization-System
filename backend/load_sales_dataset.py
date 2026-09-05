import csv
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import SalesRecord, Base

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'pricepilot.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

CSV_PATH = BASE_DIR / 'database' / 'sample_sales_dataset.csv'

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            records = []
            for row in reader:
                if not row.get('product_name') or row.get('price') == '0':
                    continue
                try:
                    price = float(row['price'])
                    quantity = int(row['quantity_sold'])
                except (TypeError, ValueError):
                    continue
                sales_record = SalesRecord(
                    product_name=row['product_name'],
                    units_sold=quantity,
                    revenue=float(row.get('revenue', price * quantity)),
                    price=price,
                )
                records.append(sales_record)

        db.add_all(records)
        db.commit()
        print('Loaded rows:', len(records))
    finally:
        db.close()
