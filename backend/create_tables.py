from database.connection import engine
from models.user_model import Base

# Import models so SQLAlchemy registers their tables
from models.product_model import Product
from models.competitor_model import CompetitorPrice


print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully.")