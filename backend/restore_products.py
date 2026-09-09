import csv

from database.session import SessionLocal
from models.product_model import Product


CSV_FILE = "datasets/products_dataset.csv"


def restore_missing_products():

    db = SessionLocal()

    try:
        # Read products from CSV
        with open(
            CSV_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            csv_products = list(reader)

        # Existing database product names
        database_products = (
            db.query(Product).all()
        )

        existing_names = {
            product.product_name.strip().lower()
            for product in database_products
        }

        added_count = 0

        print(
            f"Products in CSV: {len(csv_products)}"
        )

        print(
            f"Products currently in database: "
            f"{len(database_products)}"
        )

        print("\nChecking for missing products...\n")

        for row in csv_products:

            product_name = row["product_name"].strip()

            name_key = product_name.lower()

            # Product already exists
            if name_key in existing_names:
                continue

            new_product = Product(
                product_name=product_name,
                category=row["category"].strip(),
                price=float(row["price"]),
                stock=int(row["stock"])
            )

            db.add(new_product)

            existing_names.add(name_key)

            added_count += 1

            print(
                f"Restoring: {product_name}"
            )

        db.commit()

        final_count = db.query(Product).count()

        print("\n-----------------------------")
        print(
            f"Products restored: {added_count}"
        )
        print(
            f"Final database count: {final_count}"
        )
        print("-----------------------------")

    except Exception as error:

        db.rollback()

        print("\nRestore failed:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    restore_missing_products()