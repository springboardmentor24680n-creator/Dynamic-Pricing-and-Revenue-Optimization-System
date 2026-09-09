from database.session import SessionLocal
from models.product_model import Product


def remove_duplicate_products():

    db = SessionLocal()

    try:
        products = (
            db.query(Product)
            .order_by(Product.id.asc())
            .all()
        )

        seen_products = set()
        duplicates = []

        for product in products:

            name = product.product_name.strip().lower()

            if name in seen_products:
                duplicates.append(product)
            else:
                seen_products.add(name)

        print(f"Total products before cleanup: {len(products)}")

        for product in duplicates:

            print(
                f"Removing duplicate: "
                f"{product.product_name} "
                f"(ID: {product.id})"
            )

            db.delete(product)

        db.commit()

        remaining_count = (
            db.query(Product).count()
        )

        print(
            f"Duplicates removed: {len(duplicates)}"
        )

        print(
            f"Total products after cleanup: "
            f"{remaining_count}"
        )

    except Exception as error:

        db.rollback()

        print("Cleanup failed:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    remove_duplicate_products()