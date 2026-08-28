"""
Replace all products with a realistic e-commerce catalog.
Keeps the same product IDs so sales_history remains linked.
"""
import sys, random
sys.stdout.reconfigure(encoding='ascii', errors='replace')
sys.path.insert(0, '.')

import psycopg2
from app.utils import hash_password

CONN = 'postgresql://postgres:postgres@localhost:5432/dynamic_pricing'

# ─── Realistic product catalog ───────────────────────────────────────────────
# Each tuple: (name, sku, description, category, base_price, current_price, cost_price, stock_quantity, image_url)
# base_price = MSRP, current_price = selling price, cost_price = wholesale

CATALOG = [
    # ═══ LAPTOPS (40) ═══
    ("Apple MacBook Air 13-inch M3", "LAP-001", "Apple MacBook Air with M3 chip, 8GB RAM, 256GB SSD, Liquid Retina display, 18-hour battery life", "Laptops", 1099, 1049, 780, 45, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
    ("Apple MacBook Pro 14-inch M3 Pro", "LAP-002", "Apple MacBook Pro 14-inch with M3 Pro chip, 18GB RAM, 512GB SSD, ProMotion display", "Laptops", 1999, 1899, 1450, 30, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
    ("Apple MacBook Pro 16-inch M3 Max", "LAP-003", "Apple MacBook Pro 16-inch with M3 Max chip, 36GB RAM, 1TB SSD, Liquid Retina XDR", "Laptops", 3499, 3299, 2500, 15, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
    ("Dell XPS 15", "LAP-004", "Dell XPS 15 with Intel Core i7-13700H, 16GB RAM, 512GB SSD, 15.6-inch OLED display", "Laptops", 1499, 1399, 1000, 40, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("Dell XPS 13 Plus", "LAP-005", "Dell XPS 13 Plus with Intel Core i7-1360P, 16GB RAM, 512GB SSD, InfinityEdge display", "Laptops", 1299, 1199, 850, 35, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("Dell Inspiron 16", "LAP-006", "Dell Inspiron 16 laptop, Intel Core i5-1335U, 8GB RAM, 512GB SSD, 16-inch FHD+ display", "Laptops", 799, 729, 500, 60, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("HP Spectre x360 14", "LAP-007", "HP Spectre x360 14-inch 2-in-1 convertible, Intel Core i7, 16GB RAM, 1TB SSD, OLED touch", "Laptops", 1649, 1549, 1100, 25, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("HP Envy 16", "LAP-008", "HP Envy 16-inch creative laptop, Intel Core i9, 32GB RAM, 1TB SSD, RTX 4060", "Laptops", 1799, 1699, 1200, 20, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("HP Pavilion 15", "LAP-009", "HP Pavilion 15-inch everyday laptop, AMD Ryzen 7, 16GB RAM, 512GB SSD", "Laptops", 749, 679, 450, 70, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("Lenovo ThinkPad X1 Carbon Gen 11", "LAP-010", "Lenovo ThinkPad X1 Carbon Gen 11, Intel Core i7-1365U, 16GB RAM, 512GB SSD, 14-inch 2.8K OLED", "Laptops", 1849, 1749, 1250, 30, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("Lenovo ThinkPad X1 Yoga Gen 8", "LAP-011", "Lenovo ThinkPad X1 Yoga 2-in-1, Intel Core i7, 16GB RAM, 512GB SSD, 14-inch WUXGA touch", "Laptops", 1949, 1849, 1350, 20, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("Lenovo IdeaPad 5", "LAP-012", "Lenovo IdeaPad 5 15-inch, AMD Ryzen 5 7530U, 8GB RAM, 512GB SSD, FHD IPS", "Laptops", 549, 499, 320, 80, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("Lenovo Legion Pro 5 16", "LAP-013", "Lenovo Legion Pro 5 gaming laptop, Intel Core i9-13900HX, 32GB RAM, RTX 4070, 16-inch WQXGA", "Laptops", 2099, 1999, 1500, 18, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("ASUS ROG Zephyrus G14", "LAP-014", "ASUS ROG Zephyrus G14 gaming laptop, AMD Ryzen 9, 16GB RAM, RTX 4070, 14-inch QHD 165Hz", "Laptops", 1649, 1549, 1100, 22, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("ASUS Zenbook 14 OLED", "LAP-015", "ASUS Zenbook 14 OLED, Intel Core Ultra 7, 16GB RAM, 1TB SSD, 14-inch 2.8K OLED", "Laptops", 1299, 1199, 850, 35, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("ASUS Vivobook 15", "LAP-016", "ASUS Vivobook 15 everyday laptop, Intel Core i5-1335U, 8GB RAM, 512GB SSD", "Laptops", 599, 549, 360, 65, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Apple MacBook Air 15-inch M3", "LAP-017", "Apple MacBook Air 15-inch with M3 chip, 8GB RAM, 256GB SSD, Liquid Retina display", "Laptops", 1299, 1249, 900, 35, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
    ("MSI Raider GE78 HX", "LAP-018", "MSI Raider GE78 HX gaming laptop, Intel Core i9-14900HX, 32GB RAM, RTX 4080, 17-inch QHD+ 240Hz", "Laptops", 2999, 2799, 2100, 12, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("MSI Prestige 16 AI Evo", "LAP-019", "MSI Prestige 16 AI Evo, Intel Core Ultra 7, 32GB RAM, 1TB SSD, 16-inch QHD+ 240Hz", "Laptops", 1599, 1499, 1050, 20, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Dell Alienware m18 R2", "LAP-020", "Dell Alienware m18 R2 gaming laptop, Intel Core i9, 32GB RAM, RTX 4090, 18-inch QHD+ 165Hz", "Laptops", 3499, 3199, 2400, 10, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("HP Omen 16", "LAP-021", "HP Omen 16 gaming laptop, AMD Ryzen 9, 16GB RAM, RTX 4070, 16.1-inch QHD 240Hz", "Laptops", 1599, 1449, 1050, 25, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("Lenovo Yoga 9i 14", "LAP-022", "Lenovo Yoga 9i 14-inch 2-in-1, Intel Core i7, 16GB RAM, 512GB SSD, 2.8K OLED touch", "Laptops", 1549, 1449, 1000, 22, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("ASUS TUF Gaming A15", "LAP-023", "ASUS TUF Gaming A15, AMD Ryzen 7 7735HS, 16GB RAM, RTX 4060, 15.6-inch FHD 144Hz", "Laptops", 1199, 1099, 780, 35, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Dell G16 Gaming", "LAP-024", "Dell G16 gaming laptop, Intel Core i7-13650HX, 16GB RAM, RTX 4060, 16-inch QHD 165Hz", "Laptops", 1399, 1299, 900, 30, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("HP Chromebook Plus", "LAP-025", "HP Chromebook Plus, Intel Core i3, 8GB RAM, 256GB SSD, 14-inch FHD IPS", "Laptops", 499, 449, 280, 55, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("Lenovo Chromebook Duet 5", "LAP-026", "Lenovo Chromebook Duet 5 detachable 2-in-1, Qualcomm Snapdragon 7c Gen 2, 8GB RAM, 128GB eMMC", "Laptops", 429, 399, 240, 40, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("MacBook Pro 14-inch M3 Pro 36GB", "LAP-027", "Apple MacBook Pro 14-inch M3 Pro, 36GB RAM, 1TB SSD, ProMotion XDR display", "Laptops", 2399, 2299, 1700, 15, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
    ("Dell Latitude 5540", "LAP-028", "Dell Latitude 5540 business laptop, Intel Core i5-1345U, 16GB RAM, 512GB SSD", "Laptops", 1149, 1049, 720, 40, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("HP EliteBook 860 G10", "LAP-029", "HP EliteBook 860 G10 business laptop, Intel Core i7, 16GB RAM, 512GB SSD, 16-inch WUXGA", "Laptops", 1749, 1649, 1150, 20, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("Lenovo ThinkPad T14s Gen 4", "LAP-030", "Lenovo ThinkPad T14s Gen 4, AMD Ryzen 7 PRO, 16GB RAM, 512GB SSD, 14-inch WUXGA", "Laptops", 1649, 1549, 1050, 28, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("ASUS ProArt Studiobook 16", "LAP-031", "ASUS ProArt Studiobook 16, Intel Core i9-13980HX, 32GB RAM, RTX 4070, 16-inch 3.2K OLED", "Laptops", 2499, 2299, 1750, 12, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("MSI Creator Z17 HX Studio", "LAP-032", "MSI Creator Z17 HX Studio, Intel Core i9, 32GB RAM, RTX 4070, 17-inch QHD+ touch", "Laptops", 2799, 2599, 1900, 10, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Acer Nitro 5", "LAP-033", "Acer Nitro 5 gaming laptop, Intel Core i5-12500H, 8GB RAM, RTX 4050, 15.6-inch FHD 144Hz", "Laptops", 899, 799, 550, 45, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Acer Aspire 5", "LAP-034", "Acer Aspire 5 15-inch, AMD Ryzen 5 7520U, 8GB RAM, 512GB SSD, FHD IPS", "Laptops", 549, 499, 320, 60, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("LG Gram 17", "LAP-035", "LG Gram 17 ultralight laptop, Intel Core i7-1360P, 16GB RAM, 512GB SSD, 17-inch WQXGA", "Laptops", 1799, 1699, 1200, 18, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Book 4 Pro", "LAP-036", "Samsung Galaxy Book 4 Pro 14-inch, Intel Core Ultra 7, 16GB RAM, 512GB SSD, AMOLED", "Laptops", 1449, 1349, 950, 28, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Book 3 Ultra", "LAP-037", "Samsung Galaxy Book 3 Ultra 16-inch, Intel Core i9-13900H, 32GB RAM, RTX 4070, 3K AMOLED", "Laptops", 2399, 2199, 1650, 14, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Razer Blade 16", "LAP-038", "Razer Blade 16 gaming laptop, Intel Core i9-14900HX, 32GB RAM, RTX 4080, 16-inch Dual-Mode Mini LED", "Laptops", 3199, 2999, 2300, 8, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Framework Laptop 16", "LAP-039", "Framework Laptop 16 modular laptop, AMD Ryzen 7 7840HS, 32GB RAM, 1TB SSD, 16-inch 2560x1600", "Laptops", 1699, 1599, 1100, 15, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Surface Laptop 5", "LAP-040", "Microsoft Surface Laptop 5, Intel Core i7-1255U, 16GB RAM, 512GB SSD, 13.5-inch PixelSense", "Laptops", 1299, 1199, 850, 30, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),

    # ═══ SMARTPHONES (30) ═══
    ("Apple iPhone 15 Pro Max 256GB", "PHN-001", "Apple iPhone 15 Pro Max, 256GB, A17 Pro chip, 6.7-inch Super Retina XDR, titanium design", "Smartphones", 1199, 1149, 850, 60, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Apple iPhone 15 Pro 128GB", "PHN-002", "Apple iPhone 15 Pro, 128GB, A17 Pro chip, 6.1-inch Super Retina XDR, titanium design", "Smartphones", 999, 949, 680, 75, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Apple iPhone 15 128GB", "PHN-003", "Apple iPhone 15, 128GB, A16 Bionic, 6.1-inch Super Retina XDR, Dynamic Island", "Smartphones", 799, 749, 520, 90, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Apple iPhone 15 Plus 128GB", "PHN-004", "Apple iPhone 15 Plus, 128GB, A16 Bionic, 6.7-inch Super Retina XDR", "Smartphones", 899, 849, 580, 55, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Apple iPhone 14 128GB", "PHN-005", "Apple iPhone 14, 128GB, A15 Bionic, 6.1-inch Super Retina XDR", "Smartphones", 699, 649, 450, 80, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Samsung Galaxy S24 Ultra 256GB", "PHN-006", "Samsung Galaxy S24 Ultra, 256GB, Snapdragon 8 Gen 3, 6.8-inch QHD+ AMOLED, S Pen, titanium frame", "Smartphones", 1299, 1249, 900, 50, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Samsung Galaxy S24+ 256GB", "PHN-007", "Samsung Galaxy S24+, 256GB, Snapdragon 8 Gen 3, 6.7-inch QHD+ AMOLED, 4900mAh", "Smartphones", 999, 949, 680, 55, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Samsung Galaxy S24 128GB", "PHN-008", "Samsung Galaxy S24, 128GB, Snapdragon 8 Gen 3, 6.2-inch FHD+ AMOLED, Galaxy AI", "Smartphones", 799, 749, 520, 65, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Z Fold5 256GB", "PHN-009", "Samsung Galaxy Z Fold5, 256GB, Snapdragon 8 Gen 2, 7.6-inch foldable AMOLED", "Smartphones", 1799, 1699, 1250, 20, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Z Flip5 256GB", "PHN-010", "Samsung Galaxy Z Flip5, 256GB, Snapdragon 8 Gen 2, 6.7-inch foldable AMOLED", "Smartphones", 999, 949, 680, 35, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Samsung Galaxy A55 5G 128GB", "PHN-011", "Samsung Galaxy A55 5G, 128GB, Exynos 1480, 6.6-inch FHD+ AMOLED, IP67, 5000mAh", "Smartphones", 449, 399, 260, 100, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Google Pixel 8 Pro 128GB", "PHN-012", "Google Pixel 8 Pro, 128GB, Tensor G3, 6.7-inch QHD+ LTPO OLED, AI-powered camera", "Smartphones", 999, 949, 680, 40, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Google Pixel 8 128GB", "PHN-013", "Google Pixel 8, 128GB, Tensor G3, 6.2-inch FHD+ OLED, 7 years of updates", "Smartphones", 699, 649, 450, 55, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Google Pixel 7a 128GB", "PHN-014", "Google Pixel 7a, 128GB, Tensor G2, 6.1-inch FHD+ OLED, 64MP camera, wireless charging", "Smartphones", 499, 449, 300, 60, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("OnePlus 12 256GB", "PHN-015", "OnePlus 12, 256GB, Snapdragon 8 Gen 3, 6.82-inch QHD+ LTPO AMOLED, 5400mAh, 100W charging", "Smartphones", 799, 749, 520, 35, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("OnePlus 11 256GB", "PHN-016", "OnePlus 11, 256GB, Snapdragon 8 Gen 2, 6.7-inch QHD+ LTPO AMOLED, 100W SUPERVOOC", "Smartphones", 699, 649, 450, 45, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("OnePlus Nord N30 5G 128GB", "PHN-017", "OnePlus Nord N30 5G, 128GB, Snapdragon 695, 6.72-inch FHD+ IPS LCD, 5000mAh", "Smartphones", 299, 269, 170, 80, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Sony Xperia 1 V 256GB", "PHN-018", "Sony Xperia 1 V, 256GB, Snapdragon 8 Gen 2, 6.5-inch 4K OLED, dedicated camera shutter button", "Smartphones", 1399, 1299, 950, 15, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Samsung Galaxy S23 FE 128GB", "PHN-019", "Samsung Galaxy S23 FE, 128GB, Exynos 2200, 6.4-inch FHD+ AMOLED, IP68", "Smartphones", 599, 549, 380, 50, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Motorola Edge 40 Pro 256GB", "PHN-020", "Motorola Edge 40 Pro, 256GB, Snapdragon 8 Gen 2, 6.67-inch pOLED, 125W TurboPower", "Smartphones", 799, 729, 500, 30, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("iPhone SE 2022 64GB", "PHN-021", "Apple iPhone SE (2022), 64GB, A15 Bionic, 4.7-inch Retina HD, Touch ID", "Smartphones", 429, 399, 260, 70, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Samsung Galaxy A35 5G 128GB", "PHN-022", "Samsung Galaxy A35 5G, 128GB, Exynos 1380, 6.6-inch FHD+ AMOLED, IP67, 5000mAh", "Smartphones", 399, 349, 220, 90, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Nothing Phone 2 256GB", "PHN-023", "Nothing Phone 2, 256GB, Snapdragon 8+ Gen 1, 6.7-inch LTPO OLED, unique Glyph interface", "Smartphones", 599, 549, 380, 40, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Google Pixel Fold 256GB", "PHN-024", "Google Pixel Fold, 256GB, Tensor G2, 7.6-inch foldable OLED, triple camera", "Smartphones", 1799, 1699, 1250, 10, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Samsung Galaxy S24 FE 128GB", "PHN-025", "Samsung Galaxy S24 FE, 128GB, Exynos 2400e, 6.7-inch FHD+ AMOLED, Galaxy AI", "Smartphones", 649, 599, 410, 55, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Xiaomi 14 Ultra 512GB", "PHN-026", "Xiaomi 14 Ultra, 512GB, Snapdragon 8 Gen 3, 6.73-inch QHD+ AMOLED, Leica quad camera", "Smartphones", 1099, 999, 720, 20, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("OnePlus Nord CE4 128GB", "PHN-027", "OnePlus Nord CE4, 128GB, Snapdragon 7 Gen 3, 6.7-inch FHD+ AMOLED, 5500mAh, 100W", "Smartphones", 349, 319, 200, 70, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("iPhone 13 128GB", "PHN-028", "Apple iPhone 13, 128GB, A15 Bionic, 6.1-inch Super Retina XDR, Ceramic Shield", "Smartphones", 599, 549, 380, 75, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Z Flip4 256GB", "PHN-029", "Samsung Galaxy Z Flip4, 256GB, Snapdragon 8+ Gen 1, 6.7-inch foldable AMOLED, Flex mode", "Smartphones", 899, 829, 600, 25, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Google Pixel 8a 128GB", "PHN-030", "Google Pixel 8a, 128GB, Tensor G3, 6.1-inch FHD+ OLED, 7 years updates, IP67", "Smartphones", 499, 469, 310, 60, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),

    # ═══ HEADPHONES (25) ═══
    ("Sony WH-1000XM5", "AUD-001", "Sony WH-1000XM5 wireless noise-cancelling headphones, 30-hour battery, multipoint, LDAC, Hi-Res Audio", "Headphones", 399, 349, 220, 50, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Sony WF-1000XM5", "AUD-002", "Sony WF-1000XM5 true wireless earbuds, industry-leading noise cancellation, 24-hour battery with case", "Headphones", 299, 279, 185, 45, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Sony WH-1000XM4", "AUD-003", "Sony WH-1000XM4 wireless noise-cancelling headphones, 30-hour battery, Speak-to-Chat", "Headphones", 349, 299, 200, 40, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Apple AirPods Pro 2nd Gen USB-C", "AUD-004", "Apple AirPods Pro 2nd generation with USB-C, active noise cancellation, adaptive transparency, spatial audio", "Headphones", 249, 229, 155, 70, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Apple AirPods Max", "AUD-005", "Apple AirPods Max over-ear headphones, active noise cancellation, spatial audio, 20-hour battery", "Headphones", 549, 519, 370, 20, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Apple AirPods 3rd Gen", "AUD-006", "Apple AirPods 3rd generation, spatial audio, adaptive EQ, sweat and water resistant, 6-hour battery", "Headphones", 169, 159, 100, 80, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Bose QuietComfort Ultra Headphones", "AUD-007", "Bose QC Ultra wireless noise-cancelling headphones, spatial audio, custom튠, 24-hour battery", "Headphones", 429, 399, 260, 30, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Bose QuietComfort Ultra Earbuds", "AUD-008", "Bose QC Ultra true wireless earbuds, spatial audio, world-class noise cancellation, 6-hour battery", "AUD-008", 299, 279, 185, 35, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Bose QuietComfort 45", "AUD-009", "Bose QC45 wireless noise-cancelling headphones, 24-hour battery, TriPort acoustic architecture", "Headphones", 329, 279, 185, 40, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Sennheiser Momentum 4 Wireless", "AUD-010", "Sennheiser Momentum 4 wireless headphones, adaptive noise cancellation, 60-hour battery, aptX Adaptive", "Headphones", 349, 329, 220, 25, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Sennheiser Momentum True Wireless 4", "AUD-011", "Sennheiser MTW4 true wireless earbuds, adaptive ANC, 30-hour total battery, aptX Lossless", "Headphones", 299, 279, 185, 30, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Sennheiser HD 660S2", "AUD-012", "Sennheiser HD 660S2 open-back reference headphones, 38-ohm impedance, audiophile-grade", "Headphones", 499, 469, 330, 15, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Jabra Elite 85t", "AUD-013", "Jabra Elite 85t true wireless earbuds, advanced ANC, 6-mic call technology, 25-hour battery", "Headphones", 229, 199, 130, 40, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Jabra Elite 85h", "AUD-014", "Jabra Elite 85h wireless headphones, smart ANC, 8 microphones, 36-hour battery, MySound AI", "Headphones", 249, 219, 145, 30, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Beats Studio Pro", "AUD-015", "Beats Studio Pro wireless headphones, ANC, personalized spatial audio, 40-hour battery", "Headphones", 349, 299, 200, 35, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Beats Fit Pro", "AUD-016", "Beats Fit Pro true wireless earbuds, active noise cancellation, spatial audio, Apple H1 chip", "Headphones", 199, 179, 115, 50, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Beats Solo 4", "AUD-017", "Beats Solo 4 on-ear wireless headphones, 50-hour battery, personalized spatial audio, USB-C", "Headphones", 199, 189, 120, 40, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("JBL Tour One M2", "AUD-018", "JBL Tour One M2 wireless headphones, True Adaptive ANC, Hi-Res certified, 50-hour battery", "Headphones", 299, 269, 175, 30, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("JBL Tune 770NC", "AUD-019", "JBL Tune 770NC wireless headphones, adaptive noise cancellation, 44-hour battery, JBL Pure Bass", "Headphones", 99, 79, 48, 70, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Beyerdynamic DT 900 Pro X", "AUD-020", "Beyerdynamic DT 900 Pro X open-back studio reference headphones, STELLAR.45 driver", "Headphones", 269, 249, 170, 15, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Audio-Technica ATH-M50xBT2", "AUD-021", "Audio-Technica ATH-M50xBT2 wireless headphones, 50mm drivers, LDAC, 50-hour battery", "Headphones", 199, 179, 115, 35, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Shure AONIC 50 Gen 2", "AUD-022", "Shure AONIC 50 Gen 2 wireless headphones, adjustable ANC, studio-quality audio, 45-hour battery", "Headphones", 399, 369, 250, 20, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Shure SE846", "AUD-023", "Shure SE846 sound isolating earbuds, quad high-definition drivers, true bass response", "Headphones", 999, 899, 650, 8, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Skullcandy Crusher ANC 2", "AUD-024", "Skullcandy Crusher ANC 2 headphones, adjustable sensory bass, ANC, 50-hour battery", "Headphones", 229, 199, 130, 40, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Buds2 Pro", "AUD-025", "Samsung Galaxy Buds2 Pro, 24-bit Hi-Fi, intelligent ANC, 360 Audio, IPX7", "Headphones", 229, 199, 130, 50, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),

    # ═══ TVs & MONITORS (25) ═══
    ("Samsung 65-inch QN90C Neo QLED 4K", "TV-001", "Samsung 65-inch QN90C Neo QLED 4K TV, Quantum Matrix, Anti-Glare, 120Hz, Dolby Atmos", "TVs", 1799, 1599, 1150, 20, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Samsung 55-inch S95C OLED 4K", "TV-002", "Samsung 55-inch S95C OLED 4K TV, Neural Quantum Processor, 144Hz, OTS+", "TVs", 1599, 1399, 1000, 15, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Samsung 75-inch QN85C Neo QLED 4K", "TV-003", "Samsung 75-inch QN85C Neo QLED 4K TV, Neural Quantum Processor 4K, 120Hz, Anti-Glare", "TVs", 2199, 1999, 1450, 12, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("LG 65-inch C3 OLED evo 4K", "TV-004", "LG 65-inch C3 OLED evo 4K TV, a9 Gen6 AI Processor, Dolby Vision, 120Hz, 4 HDMI 2.1", "TVs", 1799, 1499, 1050, 18, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("LG 55-inch B3 OLED 4K", "TV-005", "LG 55-inch B3 OLED 4K TV, a7 Gen6 AI Processor, Dolby Vision, 120Hz", "TVs", 1299, 1099, 780, 22, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("LG 77-inch G3 OLED evo 4K", "TV-006", "LG 77-inch G3 OLED evo 4K TV, a9 Gen6 AI Processor, Brightness Booster Max, Gallery design", "TVs", 3299, 2999, 2200, 8, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Sony 65-inch A95L QD-OLED 4K", "TV-007", "Sony 65-inch A95L QD-OLED 4K TV, Cognitive Processor XR, Dolby Vision, Acoustic Surface Audio+", "TVs", 2799, 2499, 1800, 10, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Sony 55-inch X90L LED 4K", "TV-008", "Sony 55-inch X90L LED 4K TV, Cognitive Processor XR, 120Hz, XR Motion Clarity", "TVs", 1199, 1049, 740, 20, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("TCL 65-inch QM8 Mini LED 4K", "TV-009", "TCL 65-inch QM8 Mini LED 4K TV, 2000 nits, 120Hz, Game Accelerator 240, Dolby Vision", "TVs", 1099, 949, 650, 25, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("TCL 55-inch S4 4K TV", "TV-010", "TCL 55-inch S4 4K TV, HDR PRO, Game Mode, Roku TV built-in", "TVs", 349, 299, 190, 40, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Samsung 50-inch CU7000 4K UHD", "TV-011", "Samsung 50-inch CU7000 4K UHD TV, Crystal Processor 4K, HDR, Smart TV", "TVs", 449, 379, 250, 35, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Hisense 65-inch U8K Mini LED 4K", "TV-012", "Hisense 65-inch U8K Mini LED 4K TV, 1500 nits, 144Hz, Game Mode Pro, Dolby Vision", "TVs", 999, 849, 580, 20, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
    ("Dell UltraSharp 27 4K USB-C Hub Monitor U2723QE", "MON-001", "Dell 27-inch 4K USB-C Hub monitor, IPS Black, 98% DCI-P3, USB-C 90W, HDMI, DP", "Monitors", 619, 549, 380, 25, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("Dell 27 Gaming Monitor S2722DGM", "MON-002", "Dell 27-inch curved gaming monitor, 2560x1440, 165Hz, 2ms, AMD FreeSync Premium", "Monitors", 299, 249, 165, 35, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("LG 27GP950-B 4K Gaming Monitor", "MON-003", "LG 27-inch 4K UHD Nano IPS gaming monitor, 160Hz, 1ms, HDMI 2.1, G-Sync Compatible", "Monitors", 799, 699, 490, 15, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("ASUS ProArt PA279CRV 4K Monitor", "MON-004", "ASUS ProArt 27-inch 4K UHD monitor, IPS, 99% DCI-P3, Calman Verified, USB-C 96W", "Monitors", 549, 489, 340, 20, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("Samsung 34-inch Odyssey G5 Ultra-Wide", "MON-005", "Samsung 34-inch Ultra-Wide curved gaming monitor, 3440x1440, 165Hz, 1ms, HDR10", "Monitors", 449, 389, 265, 18, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("Apple Studio Display", "MON-006", "Apple Studio Display 27-inch 5K Retina, A13 Bionic, 600 nits, 12MP camera, 6 speakers", "Monitors", 1599, 1499, 1050, 10, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("LG 34-inch UltraWide WQHD Monitor 34WP85C-B", "MON-007", "LG 34-inch UltraWide WQHD curved monitor, IPS, USB-C 96W, HDR10, 3440x1440", "Monitors", 599, 529, 370, 15, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("BenQ EW3280U 4K Monitor", "MON-008", "BenQ 32-inch 4K UHD monitor, HDRi, treVolo speakers, USB-C, 95% DCI-P3", "Monitors", 699, 629, 440, 12, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("LG 27-inch UltraGear OLED Gaming Monitor", "MON-009", "LG 27-inch UltraGear OLED, 2560x1440, 240Hz, 0.03ms, G-Sync, Anti-Glare", "Monitors", 999, 899, 650, 10, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("ASUS ROG Swift PG27AQN 360Hz", "MON-010", "ASUS ROG Swift 27-inch gaming monitor, 360Hz, 1440p, G-Sync, 1ms, NVIDIA Reflex", "Monitors", 849, 749, 530, 8, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("Samsung 32-inch ViewFinity S9 5K Monitor", "MON-011", "Samsung 32-inch ViewFinity S9 5K monitor, 5120x2880, matte display, Thunderbolt 4, 99% DCI-P3", "Monitors", 1599, 1399, 1000, 8, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("HP U32 4K HDR Monitor", "MON-012", "HP U32 32-inch 4K UHD monitor, IPS, 99% sRGB, HDR400, USB-C, built-in KVM", "Monitors", 449, 399, 275, 20, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("Dell 32 Plus 4K USB-C Hub Monitor S3221QS", "MON-013", "Dell 32-inch 4K curved monitor, USB-C, 90% DCI-P3, built-in KVM, VESA DisplayHDR 400", "Monitors", 499, 439, 305, 22, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ("Acer Predator X27U 27 OLED", "MON-014", "Acer Predator 27-inch OLED gaming monitor, 2560x1440, 240Hz, 0.03ms, DCI-P3 99%", "Monitors", 899, 799, 560, 10, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),

    # ═══ TABLETS (12) ═══
    ("Apple iPad Pro 12.9-inch M2 256GB", "TAB-001", "Apple iPad Pro 12.9-inch, M2 chip, 256GB, Liquid Retina XDR, Face ID, Thunderbolt", "Tablets", 1099, 999, 740, 25, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Apple iPad Air M1 64GB", "TAB-002", "Apple iPad Air, M1 chip, 64GB, 10.9-inch Liquid Retina, Touch ID, USB-C", "Tablets", 599, 559, 380, 40, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Apple iPad 10th Gen 64GB", "TAB-003", "Apple iPad 10th generation, A14 Bionic, 64GB, 10.9-inch Liquid Retina, USB-C", "Tablets", 449, 419, 280, 50, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Apple iPad Mini 6th Gen 64GB", "TAB-004", "Apple iPad mini 6th generation, A15 Bionic, 64GB, 8.3-inch Liquid Retina, USB-C", "Tablets", 499, 469, 310, 30, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Tab S9 Ultra 256GB", "TAB-005", "Samsung Galaxy Tab S9 Ultra, 256GB, Snapdragon 8 Gen 2, 14.6-inch Dynamic AMOLED 2X, S Pen", "Tablets", 1199, 1099, 780, 18, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Tab S9 FE 128GB", "TAB-006", "Samsung Galaxy Tab S9 FE, 128GB, Exynos 1380, 10.9-inch LCD, S Pen included, IP68", "Tablets", 449, 399, 265, 35, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Microsoft Surface Pro 9 i7 256GB", "TAB-007", "Microsoft Surface Pro 9, Intel Core i7, 12GB RAM, 256GB SSD, 13-inch PixelSense Flow", "Tablets", 1599, 1449, 1050, 15, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Lenovo Tab P12 Pro 256GB", "TAB-008", "Lenovo Tab P12 Pro, 256GB, Snapdragon 870, 12.6-inch AMOLED, 120Hz, JBL speakers", "Tablets", 609, 549, 380, 20, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Amazon Fire HD 10 64GB", "TAB-009", "Amazon Fire HD 10 tablet, 64GB, octa-core, 10.1-inch FHD, 13-hour battery", "Tablets", 149, 119, 65, 60, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Google Pixel Tablet 128GB", "TAB-010", "Google Pixel Tablet, 128GB, Tensor G2, 10.95-inch LCD, Charging Speaker Dock", "Tablets", 499, 449, 300, 28, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("iPad Pro 11-inch M2 128GB", "TAB-011", "Apple iPad Pro 11-inch, M2 chip, 128GB, Liquid Retina, Face ID, Thunderbolt", "Tablets", 799, 749, 530, 30, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Tab A9+ 64GB", "TAB-012", "Samsung Galaxy Tab A9+, 64GB, Snapdragon 695, 11-inch TFT, quad speakers", "Tablets", 229, 199, 120, 55, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),

    # ═══ SMARTWATCHES (15) ═══
    ("Apple Watch Series 9 45mm GPS", "WAT-001", "Apple Watch Series 9, 45mm, GPS, Always-On Retina, S9 chip, double tap gesture, carbon neutral", "Smartwatches", 429, 399, 270, 45, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Apple Watch Series 9 41mm GPS", "WAT-002", "Apple Watch Series 9, 41mm, GPS, Always-On Retina, S9 chip, double tap gesture", "Smartwatches", 399, 369, 250, 50, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Apple Watch Ultra 2 Titanium 49mm", "WAT-003", "Apple Watch Ultra 2, 49mm, GPS+Cellular, precision dual-frequency GPS, depth gauge, 36hr battery", "Smartwatches", 799, 769, 540, 15, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Watch 6 Classic 47mm", "WAT-004", "Samsung Galaxy Watch 6 Classic, 47mm, rotating bezel, Wear OS, BioActive Sensor, sapphire crystal", "Smartwatches", 399, 349, 230, 30, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Watch 6 44mm", "WAT-005", "Samsung Galaxy Watch 6, 44mm, Wear OS, sapphire crystal, sleep coaching, body composition", "Smartwatches", 329, 299, 195, 40, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Garmin Fenix 7X Solar", "WAT-006", "Garmin Fenix 7X Solar multisport GPS watch, solar charging, 28-day battery, topographic maps", "Smartwatches", 899, 799, 570, 12, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Garmin Venu 3", "WAT-007", "Garmin Venu 3 AMOLED smartwatch, advanced sleep monitoring, Body Battery, wheelchair mode", "Smartwatches", 449, 399, 270, 22, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Google Pixel Watch 2 LTE", "WAT-008", "Google Pixel Watch 2, LTE, Wear OS, Fitbit health tracking, 3D curved glass, all-day battery", "Smartwatches", 399, 349, 230, 25, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Fitbit Sense 2", "WAT-009", "Fitbit Sense 2 health smartwatch, continuous EDA, cEDA, SpO2, ECG, built-in GPS", "Smartwatches", 299, 249, 160, 35, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Watch 5 Pro 45mm", "WAT-010", "Samsung Galaxy Watch 5 Pro, 45mm, titanium, sapphire crystal, GPX route tracking, 80hr battery", "Smartwatches", 449, 379, 250, 20, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Garmin Forerunner 265", "WAT-011", "Garmin Forerunner 265 GPS running watch, AMOLED display, training readiness, morning report", "Smartwatches", 449, 399, 270, 18, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Apple Watch SE 2nd Gen 40mm", "WAT-012", "Apple Watch SE 2nd generation, 40mm, GPS, S8 chip, crash detection, swimproof", "Smartwatches", 249, 229, 145, 55, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Amazfit GTR 4", "WAT-013", "Amazfit GTR 4 smartwatch, 1.43-inch AMOLED, 14-day battery, GPS, bio tracker 3.0 PPG", "Smartwatches", 199, 169, 95, 30, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Withings ScanWatch 2", "WAT-014", "Withings ScanWatch 2 hybrid smartwatch, ECG, SpO2, temperature, 30-day battery, swim-proof", "Smartwatches", 349, 299, 200, 15, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ("Whoop 4.0 Band", "WAT-015", "Whoop 4.0 wearable health monitor, strain, recovery, sleep coaching, water-resistant, 5-day battery", "Smartwatches", 299, 239, 140, 40, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),

    # ═══ SHIRTS & TOPS (30) ═══
    ("Nike Dri-FIT Classic Polo", "SHR-001", "Nike Dri-FIT Classic polo shirt, moisture-wicking fabric, flat knit collar, three-button placket", "Shirts", 55, 45, 18, 120, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Nike Dri-FIT UV Miler Short-Sleeve", "SHR-002", "Nike Dri-FIT UV Miler running shirt, lightweight, sun protection, breathable mesh", "Shirts", 40, 35, 14, 100, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Adidas Originals Trefoil Tee", "SHR-003", "Adidas Originals Trefoil logo t-shirt, cotton jersey, relaxed fit, classic trefoil print", "Shirts", 35, 28, 10, 150, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Adidas Climalite Soccer Jersey", "SHR-004", "Adidas Climalite soccer jersey, moisture management, mesh panels, team wear style", "Shirts", 65, 55, 22, 80, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Under Armour Tech 2.0 T-Shirt", "SHR-005", "Under Armour Tech 2.0 short-sleeve, 4-way stretch, anti-odor, ultra-soft fabric", "Shirts", 30, 25, 9, 140, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Levi's 511 Slim Fit Oxford Shirt", "SHR-006", "Levi's 511 slim fit button-down oxford shirt, stretch cotton, spread collar, chest pocket", "Shirts", 50, 42, 17, 90, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Ralph Lauren Classic Fit Polo", "SHR-007", "Ralph Lauren classic fit polo, cotton mesh, signature embroidered pony, ribbed collar", "Shirts", 98, 85, 35, 60, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Tommy Hilfiger Classic Crew Neck Tee", "SHR-008", "Tommy Hilfiger classic crew neck t-shirt, soft cotton jersey, signature flag logo", "Shirts", 40, 32, 12, 110, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Calvin Klein Modern Cotton V-Neck Tee", "SHR-009", "Calvin Klein Modern Cotton V-neck t-shirt, cotton-modal blend, minimal CK logo", "Shirts", 35, 28, 10, 130, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("H&M Regular Fit Oxford Shirt", "SHR-010", "H&M regular fit oxford shirt, cotton, button-down collar, long sleeves with button cuffs", "Shirts", 25, 20, 7, 160, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Uniqlo Supima Cotton T-Shirt", "SHR-011", "Uniqlo Supima cotton crew neck t-shirt, premium Supima cotton, soft, smooth, slim fit", "Shirts", 20, 15, 5, 200, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Polo Ralph Lauren Mesh Polo", "SHR-012", "Polo Ralph Lauren mesh polo, cotton mesh, pony logo, classic fit, ribbed cuffs", "Shirts", 110, 95, 40, 45, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Nike Sportswear Club T-Shirt", "SHR-013", "Nike Sportswear Club tee, cotton jersey, standard fit, Nike Futura logo", "Shirts", 30, 25, 9, 170, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Lululemon Metal Vent Tech Short Sleeve", "SHR-014", "Lululemon Metal Vent Tech 2.0, Silverescent technology, mesh ventilation, anti-odor", "Shirts", 68, 58, 23, 50, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Zara Slim Fit Printed Shirt", "SHR-015", "Zara slim fit printed shirt, lightweight viscose, all-over print, relaxed spread collar", "Shirts", 50, 40, 15, 70, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Brooks Brothers Non-Iron Dress Shirt", "SHR-016", "Brooks Brothers non-iron dress shirt, 100% cotton, wrinkle-free, fitted, classic collar", "Shirts", 128, 108, 45, 35, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Columbia PFG Terminal Tackle Shirt", "SHR-017", "Columbia PFG fishing shirt, Omni-Shade sun protection, vented, utility pockets", "Shirts", 55, 45, 18, 40, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Patagonia Capilene Cool Daily Graphic Tee", "SHR-018", "Patagonia Capilene Cool Daily tee, recycled polyester, HeiQ Fresh odor control, Fair Trade", "Shirts", 45, 38, 15, 65, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("The North Face Drew Peak Polo", "SHR-019", "The North Face Drew Peak polo, FlashDry-XD technology, collar, split hem", "Shirts", 55, 48, 19, 50, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Gildan Heavy Cotton T-Shirt", "SHR-020", "Gildan heavy cotton t-shirt, preshrunk 100% cotton, classic fit, seamless double-needle collar", "Shirts", 10, 8, 3, 500, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Carhartt Midweight Short-Sleeve Pocket Tee", "SHR-021", "Carhartt midweight pocket t-shirt, cotton, rib-knit neckline, left-chest pocket with pen slot", "Shirts", 30, 24, 9, 120, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Zara Linen Blend Shirt", "SHR-022", "Zara linen blend relaxed fit shirt, short sleeve, camp collar, textured weave", "Shirts", 40, 32, 11, 85, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Amazon Essentials Slim-Fit Oxford Shirt", "SHR-023", "Amazon Essentials slim-fit oxford, cotton, button-down collar, chest pocket", "Shirts", 22, 18, 6, 200, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Mango Slim Fit Linen Shirt", "SHR-024", "Mango slim fit linen shirt, pure linen, regular collar, long sleeves, button placket", "Shirts", 60, 50, 20, 40, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("GAP Classic Chambray Shirt", "SHR-025", "GAP classic chambray button-down shirt, soft chambray fabric, chest pockets, adjustable cuffs", "Shirts", 45, 35, 13, 75, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Banana Republic Italian Wool Dress Shirt", "SHR-026", "Banana Republic Italian wool stretch dress shirt, wrinkle-resistant, fitted, spread collar", "Shirts", 148, 118, 48, 25, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("J.Crew Ludlow Classic-Fit Dress Shirt", "SHR-027", "J.Crew Ludlow dress shirt, Japanese cotton, wrinkle-resistant, classic fit, Japanese selvedge", "Shirts", 98, 78, 32, 35, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Vintage Polo Sport Windbreaker Shirt", "SHR-028", "Vintage-inspired Polo Sport windbreaker pullover, lightweight nylon, half-zip, mesh lining", "Shirts", 145, 125, 50, 20, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Columbia Silver Ridge Utility Shirt", "SHR-029", "Columbia Silver Ridge utility shirt, Omni-Shade UPF 40, vented back, dual chest pockets", "Shirts", 50, 42, 16, 55, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Todd Snyder Japanese Seersucker Camp Shirt", "SHR-030", "Todd Snyder seersucker camp collar shirt, Japanese fabric, relaxed fit, tropical print", "Shirts", 168, 148, 60, 15, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),

    # ═══ SHOES (30) ═══
    ("Nike Air Max 90", "SHO-001", "Nike Air Max 90 men's running shoes, visible Air unit, rubber Waffle outsole, classic design", "Shoes", 130, 120, 52, 80, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Nike Air Force 1 Low", "SHO-002", "Nike Air Force 1 Low men's sneakers, full-grain leather upper, Air-Sole unit, pivot-circle outsole", "Shoes", 115, 105, 44, 90, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Nike Pegasus 40", "SHO-003", "Nike Air Zoom Pegasus 40 running shoes, React foam, Zoom Air units, breathable mesh", "Shoes", 130, 120, 52, 70, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Adidas Ultraboost 23", "SHO-004", "Adidas Ultraboost 23 running shoes, BOOST midsole, Continental rubber outsole, Primeknit+", "Shoes", 190, 170, 75, 55, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Adidas Stan Smith", "SHO-005", "Adidas Stan Smith sneakers, smooth leather upper, perforated 3-Stripes, rubber cupsole", "Shoes", 100, 90, 38, 75, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Adidas Samba OG", "SHO-006", "Adidas Samba OG sneakers, suede upper, T-toe overlay, rubber outsole, gum sole", "Shoes", 100, 90, 38, 65, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("New Balance 990v6", "SHO-007", "New Balance 990v6 made-in-USA running shoes, ENCAP midsole, pigskin suede, mesh upper", "Shoes", 200, 180, 80, 30, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("New Balance Fresh Foam X 1080v13", "SHO-008", "New Balance Fresh Foam X 1080v13 running shoes, Hypoknit upper, Fresh Foam X midsole", "Shoes", 165, 150, 62, 45, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Converse Chuck Taylor All Star", "SHO-009", "Converse Chuck Taylor All Star high-top sneakers, canvas upper, rubber toe cap, classic design", "Shoes", 60, 55, 18, 120, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Vans Old Skool", "SHO-010", "Vans Old Skool skate shoes, suede and canvas upper, waffle outsole, side stripe", "Shoes", 70, 65, 22, 100, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("ASICS Gel-Kayano 30", "SHO-011", "ASICS Gel-Kayano 30 stability running shoes, FF Blast Plus cushion, 4D Guidance System", "Shoes", 160, 145, 58, 40, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Brooks Ghost 15", "SHO-012", "Brooks Ghost 15 neutral running shoes, DNA LOFT v2 cushion, 3D Fit Print upper", "Shoes", 140, 130, 52, 50, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Puma Suede Classic XXI", "SHO-013", "Puma Suede Classic XXI sneakers, suede upper, rubber cupsole, Formstrip overlay", "Shoes", 75, 65, 24, 80, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Reebok Classic Leather", "SHO-014", "Reebok Classic Leather sneakers, smooth leather upper, EVA midsole, rubber outsole", "Shoes", 85, 75, 28, 60, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Salomon XT-6", "SHO-015", "Salomon XT-6 trail running shoes, Contagrip MA outsole, Advanced Chassis, quick-lace", "Shoes", 180, 165, 68, 25, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("On Cloud 5", "SHO-016", "On Cloud 5 running shoes, CloudTec sole, Helion superfoam, speed-lacing system", "Shoes", 150, 140, 55, 40, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Hoka Clifton 9", "SHO-017", "Hoka Clifton 9 running shoes, compression-molded EVA, breathable mesh, meta-rocker geometry", "Shoes", 145, 135, 54, 45, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Timberland Premium 6-Inch Boot", "SHO-018", "Timberland Premium 6-inch waterproof boots, full-grain leather, seam-sealed, PrimaLoft insulation", "Shoes", 198, 180, 78, 35, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Dr. Martens 1460 Boot", "SHO-019", "Dr. Martens 1460 8-eye boots, smooth leather, AirWair sole, Goodyear welted construction", "Shoes", 170, 155, 65, 30, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Cole Haan Zerogrand Stitchlite", "SHO-010", "Cole Haan Zerogrand Stitchlite oxford, knit upper, Grand.OS cushion, leather sole", "Shoes", 150, 130, 52, 40, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Birkenstock Arizona", "SHO-021", "Birkenstock Arizona sandals, suede leather, cork-latex footbed, EVA sole, two adjustable straps", "Shoes", 110, 100, 40, 60, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Jordan 1 Retro High OG", "SHO-022", "Air Jordan 1 Retro High OG sneakers, leather upper, Air-Sole unit, rubber cupsole, iconic silhouette", "Shoes", 180, 170, 72, 25, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Merrell Moab 3 Hiking Boot", "SHO-023", "Merrell Moab 3 hiking boots, Vibram TC5+ outsole, bellows tongue, protective toe cap, waterproof", "Shoes", 145, 130, 52, 35, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Nike Dunk Low Retro", "SHO-024", "Nike Dunk Low Retro sneakers, leather and synthetic upper, foam midsole, rubber outsole", "Shoes", 115, 105, 44, 70, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Red Wing Iron Ranger", "SHO-025", "Red Wing Iron Ranger boots, premium leather, Vibram mini-lug sole, Goodyear welt, speed hooks", "Shoes", 350, 320, 160, 15, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Saucony Kinvara 14", "SHO-026", "Saucony Kinvara 14 lightweight running shoes, PWRRUN cushion, FORMFIT upper, 4mm drop", "Shoes", 110, 100, 38, 50, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Keen Newport H2 Sandal", "SHO-027", "Keen Newport H2 water sandals, washable polyester upper, EVA footbed, multi-directional lugs", "Shoes", 130, 120, 48, 40, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Allbirds Tree Dasher 2", "SHO-028", "Allbirds Tree Dasher 2 running shoes, eucalyptus tree fiber upper, SweetFoam midsole, carbon negative", "Shoes", 125, 115, 45, 35, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Under Armour HOVR Phantom 3", "SHO-029", "Under Armour HOVR Phantom 3 running shoes, UA HOVR cushion, knit upper, MapMyRun connected", "Shoes", 140, 130, 52, 30, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ("Clarks Desert Boot", "SHO-030", "Clarks Desert Boot, beeswax leather, crepe sole, ankle height, classic minimalist design", "Shoes", 130, 115, 48, 45, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),

    # ═══ WATCHES & JEWELRY (20) ═══
    ("Casio G-Shock GA-2100", "JWL-001", "Casio G-Shock GA-2100 analog-digital watch, carbon core guard, 200m water resistant, world time", "Accessories", 99, 89, 35, 60, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Citizen Eco-Drive Promaster Diver", "JWL-002", "Citizen Eco-Drive Promaster diver watch, solar powered, 200m, stainless steel, luminous hands", "Accessories", 375, 325, 180, 25, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Seiko Presage Cocktail Time", "JWL-003", "Seiko Presage Cocktail Time automatic, 40.5mm, sunburst dial, 4R35 movement, leather strap", "Accessories", 425, 385, 200, 18, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Fossil Gen 6 Hybrid Smartwatch", "JWL-004", "Fossil Gen 6 Hybrid smartwatch, automatic wrist heart rate, smartphone notifications, sleep tracking", "Accessories", 229, 199, 95, 30, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Tissot PRX Powermatic 80", "JWL-005", "Tissot PRX Powermatic 80 automatic watch, 40mm, integrated bracelet, 80hr power reserve", "Accessories", 695, 625, 380, 12, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Michael Kors Bradshaw Gold-Tone Watch", "JWL-006", "Michael Kors Bradshaw gold-tone stainless steel watch, crystal-accented bezel, quartz movement", "Accessories", 295, 245, 110, 35, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Fitbit Versa 4", "JWL-007", "Fitbit Versa 4 fitness smartwatch, GPS, 6+ day battery, Daily Readiness Score, 40+ exercise modes", "Accessories", 229, 199, 95, 40, "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ("Ray-Ban Aviator Classic", "JWL-008", "Ray-Ban Aviator classic sunglasses, crystal green lenses, gold metal frame, UV protection", "Accessories", 171, 150, 55, 45, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
    ("Ray-Ban Wayfarer Classic", "JWL-009", "Ray-Ban Wayfarer classic sunglasses, green G-15 lenses, acetate frame, iconic design", "Accessories", 171, 150, 55, 50, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
    ("Oakley Holbrook", "JWL-010", "Oakley Holbrook sunglasses, Prizm lenses, lightweight O Matter frame, three-point fit", "Accessories", 181, 160, 60, 35, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
    ("Maui Jim Peahi Sunglasses", "JWL-011", "Maui Jim Peahi sunglasses, PolarizedPlus2 lenses, acetate frame, superior clarity", "Accessories", 249, 219, 90, 20, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
    ("Fjallraven Kanken Classic Backpack", "JWL-012", "Fjallraven Kanken Classic backpack, Vinylon F fabric, 16L, zip opening, front pocket", "Accessories", 80, 69, 28, 60, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
    ("North Face Borealis Backpack", "JWL-013", "The North Face Borealis backpack, 28L, FlexVent suspension, padded laptop sleeve, reflective", "Accessories", 99, 89, 36, 45, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
    ("Samsonite Freeform 21-Inch Carry-On", "JWL-014", "Samsonite Freeform 21-inch carry-on spinner, lightweight ABS, TSA lock, 4 spinner wheels", "Accessories", 249, 219, 95, 25, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
    ("Coach Crossbody Bag", "JWL-015", "Coach crossbody bag, crossgrain leather, adjustable strap, multiple card slots, zip closure", "Accessories", 195, 165, 65, 35, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
    ("Lululemon Everywhere Belt Bag", "JWL-016", "Lululemon Everywhere Belt Bag, water-repellent fabric, zippered pockets, adjustable strap", "Accessories", 42, 38, 13, 100, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
    ("Bellroy Classic Wallet", "JWL-017", "Bellroy Classic bifold wallet, premium leather, RFID protection, slim profile, 12 card slots", "Accessories", 89, 79, 30, 40, "https://images.unsplash.com/photo-1627123424574-724758594e93?w=400&h=400&fit=crop"),
    ("Fossil RFID Bifold Wallet", "JWL-018", "Fossil RFID-blocking bifold wallet, genuine leather, 8 card slots, clear ID window", "Accessories", 55, 45, 16, 60, "https://images.unsplash.com/photo-1627123424574-724758594e93?w=400&h=400&fit=crop"),
    ("Lodge Cast Iron Skillet 12-inch", "JWL-019", "Lodge 12-inch pre-seasoned cast iron skillet, even heat distribution, oven-safe to 500F", "Accessories", 30, 25, 9, 80, "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop"),
    ("YETI Rambler 20oz Tumbler", "JWL-020", "YETI Rambler 20oz tumbler, double-wall vacuum insulation, shatter-resistant, dishwasher safe", "Accessories", 35, 30, 12, 90, "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop"),

    # ═══ KITCHEN APPLIANCES (25) ═══
    ("KitchenAid Artisan Stand Mixer 5qt", "KIT-001", "KitchenAid Artisan 5-quart tilt-head stand mixer, 10 speeds, 325-watt motor, stainless steel bowl", "Home & Kitchen", 449, 399, 260, 25, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Ninja Professional Plus Blender", "KIT-002", "Ninja Professional Plus blender, 1100 watts, 72-oz total crushing pitcher, 3 speeds", "Home & Kitchen", 90, 79, 38, 50, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Breville Barista Express Espresso Machine", "KIT-003", "Breville Barista Express, built-in conical burr grinder, steam wand, 15-bar Italian pump", "Home & Kitchen", 699, 599, 400, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Keurig K-Supreme Plus Coffee Maker", "KIT-004", "Keurig K-Supreme Plus single-serve coffee maker, MultiStream technology, 78oz reservoir, customizable", "Home & Kitchen", 190, 170, 80, 40, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Vitamix A3500 Ascent Series Blender", "KIT-005", "Vitamix A3500 Ascent Series blender, touchscreen, wireless connectivity, self-detect containers", "Home & Kitchen", 649, 549, 380, 12, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Instant Pot Duo 7-in-1 6qt", "KIT-006", "Instant Pot Duo 7-in-1 pressure cooker, 6 quart, 13 customizable Smart Programs, stainless steel", "Home & Kitchen", 100, 89, 42, 60, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Cuisinart Chef's Classic 11-Piece Cookware Set", "KIT-007", "Cuisinart Chef's Classic 11-piece stainless steel cookware set, encapsulated aluminum base", "Home & Kitchen", 230, 199, 100, 20, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Dyson V15 Detect Absolute Vacuum", "KIT-008", "Dyson V15 Detect cordless vacuum, laser dust detection, piezo sensor, 60min runtime, HEPA", "Home & Kitchen", 749, 649, 460, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("iRobot Roomba j7+ Self-Emptying Robot Vacuum", "KIT-009", "iRobot Roomba j7+ robot vacuum, PrecisionVision Navigation, self-emptying, 75-day capacity", "Home & Kitchen", 799, 599, 420, 18, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Cuisinart TOA-70 Air Fryer Toaster Oven", "KIT-010", "Cuisinart TOA-70 air fryer toaster oven, 1800 watts, 7 functions, large capacity", "Home & Kitchen", 230, 199, 100, 30, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Le Creuset Dutch Oven 5.5qt", "KIT-011", "Le Creuset Signature round Dutch oven, 5.5 quart, enameled cast iron, superior heat distribution", "Home & Kitchen", 410, 370, 220, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Nespresso Vertuo Next Coffee & Espresso Maker", "KIT-012", "Nespresso Vertuo Next, 5 cup sizes, Centrifusion technology, Bluetooth connected, 30sec heat-up", "Home & Kitchen", 200, 179, 85, 35, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("All-Clad D3 Stainless 10-Piece Cookware Set", "KIT-013", "All-Clad D3 stainless steel 10-piece set, tri-ply bonded, induction compatible, dishwasher safe", "Home & Kitchen", 699, 599, 380, 10, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("De'Longhi Magnifica Super Automatic Espresso", "KIT-014", "De'Longhi Magnifica Evo super-automatic espresso, built-in grinder, lattecrema system", "Home & Kitchen", 899, 799, 540, 10, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Black+Decker 12-Cup Programmable Coffeemaker", "KIT-015", "Black+Decker 12-cup programmable coffeemaker, Vortex technology, auto-brew, easy-clean carafe", "Home & Kitchen", 40, 32, 12, 70, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Thermapen ONE Instant-Read Thermometer", "KIT-016", "Thermapen ONE instant-read thermometer, 1-second readings, IP67 waterproof, auto-rotating display", "Home & Kitchen", 105, 95, 40, 30, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Vitamix FoodCycler FC-50", "KIT-017", "Vitamix FoodCycler food waste recycler, 2L capacity, carbon filter, odor-free, compact design", "Home & Kitchen", 499, 449, 310, 8, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Ninja Creami Ice Cream Maker", "KIT-018", "Ninja Creami 7-in-1 ice cream maker, 7 programs, CREAMi technology, pint containers included", "Home & Kitchen", 200, 179, 90, 40, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Ooni Koda 12 Gas Pizza Oven", "KIT-019", "Ooni Koda 12 gas-powered pizza oven, reaches 932F in 15min, cooks pizza in 60 seconds", "Home & Kitchen", 399, 349, 210, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Hamilton Beach FlexBrew Trio Coffee Maker", "KIT-020", "Hamilton Beach FlexBrew Trio, single-serve and 12-cup carafe, WiFi connected, programmable", "Home & Kitchen", 120, 105, 48, 35, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Wusthof Classic 8-Inch Chef's Knife", "KIT-021", "Wusthof Classic 8-inch chef's knife, high-carbon stainless steel, precision edge technology", "Home & Kitchen", 170, 150, 72, 25, "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=400&h=400&fit=crop"),
    ("Lodge Cast Iron Skillet 10-Inch", "KIT-022", "Lodge 10-inch pre-seasoned cast iron skillet, oven-safe to 500F, even heat retention", "Home & Kitchen", 20, 17, 6, 100, "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=400&h=400&fit=crop"),
    ("Pyrex 18-Piece Storage Set", "KIT-023", "Pyrex 18-piece glass food storage set, BPA-free lids, oven-safe glass, freezer, microwave, dishwasher", "Home & Kitchen", 50, 42, 16, 45, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Ninja Air Fryer Max XL", "KIT-024", "Ninja Air Fryer Max XL, 5.5 quart, Max Crisp technology, 7 functions, dishwasher safe basket", "Home & Kitchen", 130, 115, 52, 40, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Anova Precision Cooker Nano", "KIT-025", "Anova Precision Cooker Nano sous vide, 12L/min, WiFi + Bluetooth, 1000 watts, compact design", "Home & Kitchen", 130, 115, 52, 25, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),

    # ═══ HOME FURNITURE (25) ═══
    ("IKEA MALM 6-Drawer Dresser", "FRN-001", "IKEA MALM 6-drawer dresser, white, 63x30.75 inches, smooth-running drawers, safety anchored", "Furniture", 229, 199, 95, 30, "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=400&fit=crop"),
    ("Herman Miller Aeron Chair Size B", "FRN-002", "Herman Miller Aeron office chair, size B medium, PostureFit SL, adjustable arms, breathable mesh", "Furniture", 1645, 1495, 1050, 8, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA KALLAX Shelf Unit 4x4", "FRN-003", "IKEA KALLAX shelf unit 4x4, white, 57.75x57.75 inches, 16 storage compartments", "Furniture", 179, 159, 68, 25, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("West Elm Mid-Century Modern Desk", "FRN-004", "West Elm mid-century modern desk, 48 inches, solid wood/acacia, 2 drawers, cable management", "Furniture", 799, 699, 400, 12, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA HEMNES 8-Drawer Dresser", "FRN-005", "IKEA HEMNES 8-drawer dresser, white stain, 63x37.75 inches, dovetail joints", "Furniture", 299, 269, 115, 20, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Pottery Barn Comfort Roll Arm Upholstered Sofa", "FRN-006", "Pottery Barn Comfort Roll Arm sofa, 81 inches, down-blend fill, slipcover-friendly, solid wood frame", "Furniture", 2299, 1999, 1200, 6, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA BEKANT Sit/Stand Desk", "FRN-007", "IKEA BEKANT sit/stand desk, electric height adjustable 27.5-47.25 inches, 63x31.5 inches", "Furniture", 499, 449, 220, 15, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Wayfair Andover Mills Platform Bed Queen", "FRN-008", "Wayfair Andover Mills queen platform bed, steel frame, no box spring needed, wood slat support", "Furniture", 199, 169, 75, 20, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA ALEX Drawer Unit on Casters", "FRN-009", "IKEA ALEX drawer unit, white, 27.5x27.5 inches, 9 drawers, integrated casters", "Furniture", 219, 189, 80, 30, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Ashley Furniture Realyn Dining Table", "FRN-010", "Ashley Realyn two-tone dining table, 36x72 inches, chipped edges, trestle style, seats 6-8", "Furniture", 699, 599, 340, 10, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA POANG Armchair", "FRN-011", "IKEA POANG armchair, birch veneer frame, Layermark cushion, high resilience foam", "Furniture", 129, 109, 45, 35, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("CB2 Avec Sofa", "FRN-012", "CB2 Avec sofa, 82 inches, feather-down fill, solid wood frame, performance velvet upholstery", "Furniture", 1599, 1399, 850, 8, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA LACK Coffee Table", "FRN-013", "IKEA LACK coffee table, black-brown, 47.25x21.625 inches, lightweight, easy to assemble", "Furniture", 30, 25, 8, 60, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Upholstered Accent Chair with Gold Frame", "FRN-014", "Modern accent chair, 100% linen upholstery, gold-finished metal frame, 44 inches high", "Furniture", 399, 349, 180, 15, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA BILLY Bookcase", "FRN-015", "IKEA BILLY bookcase, white, 31.5x11.75x79.5 inches, adjustable shelves, height-extension unit available", "Furniture", 79, 69, 25, 50, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("West Elm Lucas Swivel Chair", "FRN-016", "West Elm Lucas swivel chair, 30 inches, brushed brass swivel base, foam fill, multiple fabrics", "Furniture", 699, 599, 340, 10, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("CB2 Dondra Metal Dining Table 60-Inch", "FRN-017", "CB2 Drona 60-inch round dining table, matte white marble top, black metal base, seats 4-6", "Furniture", 899, 799, 480, 8, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA HEMNES Nightstand", "FRN-018", "IKEA HEMNES nightstand, white stain, 2 drawers, 23.25x18.125 inches", "Furniture", 99, 89, 35, 40, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA NORDLI Dresser with 6 Drawers", "FRN-019", "IKEA NORDLI chest of 6 drawers, white, 27.5x52.75 inches, integrated drawer stops", "Furniture", 299, 269, 115, 18, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Wayfair Ophelia & Co. Upholstered Bed Queen", "FRN-020", "Wayfair Ophelia & Co. queen upholstered bed, diamond tufted headboard, linen fabric, solid wood legs", "Furniture", 449, 399, 210, 12, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("CB2 Sven Charme Tan Leather Sofa", "FRN-021", "CB2 Sven 88-inch sofa, top-grain leather, solid wood frame, tufted back, mid-century legs", "Furniture", 2099, 1899, 1200, 5, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA ALEX Desk", "FRN-022", "IKEA ALEX desk, white, 51.625x23.625 inches, deep drawer, cable management, adjustable feet", "Furniture", 229, 199, 85, 25, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("IKEA KALLAX Shelf Unit 2x4", "FRN-023", "IKEA KALLAX shelf unit 2x4, white, 30.375x57.75 inches, 8 storage compartments", "Furniture", 109, 95, 38, 35, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Restoration Hardware Cloud Bed King", "FRN-024", "RH Cloud bed, king, engineered wood frame, fully upholstered, floating platform design", "Furniture", 3195, 2895, 2000, 3, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ("Article Sven Charme Tan Sofa", "FRN-025", "Article Sven mid-century modern sofa, top-grain aniline leather, solid wood frame, tufted back", "Furniture", 1799, 1599, 1000, 7, "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),

    # ═══ HOME DECOR & BEDDING (20) ═══
    ("Casper Original Hybrid Mattress Queen", "DEC-001", "Casper Original Hybrid mattress, queen, zoned support, AirScape perforated foam, pocketed coils", "Home Decor", 1595, 1395, 850, 15, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Brooklinen Luxe Core Sheet Set Queen", "DEC-002", "Brooklinen Luxe Core 4-piece sheet set, queen, long-staple cotton, 480 thread count, sateen weave", "Home Decor", 169, 149, 55, 40, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Parachute Home Cloud Cotton Robe", "DEC-003", "Parachute Home Cloud Cotton robe, 100% organic Turkish cotton, waffle weave, oversized pockets", "Home Decor", 120, 105, 38, 30, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Ruggable Washable Rug 5x7", "DEC-004", "Ruggable 5x7 washable rug, machine-washable 2-piece system, stain-resistant, water-repellent", "Home Decor", 449, 399, 180, 20, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Restoration Hardware Belgian Linen Duvet", "DEC-005", "RH Belgian linen duvet cover, queen, washed linen, stonewashed, 100% European flax", "Home Decor", 349, 299, 140, 15, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("IKEA BERGPALM Duvet Cover Set Queen", "DEC-006", "IKEA BERGPALM queen duvet cover set, cotton, 155 thread count, reversible floral pattern", "Home Decor", 30, 25, 8, 60, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("West Elm Chunky Wool Throw", "DEC-007", "West Elm chunky wool throw, 50x60 inches, hand-knitted, pure wool, neutral tones", "Home Decor", 199, 169, 68, 20, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Crate & Barrel Swerve Square Arm Sofa Slipcover", "DEC-008", "Crate & Barrel Swerve slipcover, polyester blend, machine washable, multiple colors", "Home Decor", 169, 149, 55, 18, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Pottery Barn Belgian Flax Linen Duvet Cover", "DEC-009", "Pottery Barn Belgian flax linen duvet cover, queen, OEKO-TEX certified, stonewashed softness", "Home Decor", 259, 219, 95, 22, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Frette Linen Bath Towel Set", "DEC-010", "Frette linen bath towel set, 100% linen, 4-piece, quick-drying, softens with each wash", "Home Decor", 290, 259, 115, 12, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Threshold Designed with Studio McGee Throw Pillow", "DEC-011", "Threshold throw pillow with Studio McGee, 18x18, polyester cover, down-alternative fill", "Home Decor", 20, 17, 5, 80, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Boll & Branch Signature Hemmed Sheet Set", "DEC-012", "Boll & Branch Signature hemmed sheet set, queen, 300TC organic cotton, Fair Trade certified", "Home Decor", 239, 199, 85, 20, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Threshold Woven Outdoor Lumbar Pillow", "DEC-013", "Threshold woven outdoor lumbar pillow, weather-resistant, decorative outdoor use", "Home Decor", 15, 12, 4, 100, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("West Elm Stonewashed Velvet Duvet Cover", "DEC-014", "West Elm stonewashed velvet duvet cover, queen, 100% cotton, rich texture, zip closure", "Home Decor", 249, 219, 90, 16, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Opalhouse Designed with Jungalow Ceramic Vase", "DEC-015", "Opalhouse ceramic vase, handcrafted, artisan glaze, decorative, 11 inches tall", "Home Decor", 30, 25, 8, 50, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Kate Spade New York Melrose Place Candle", "DEC-016", "Kate Spade Melrose Place 3-wick candle, 15.5 oz, jasmine and peony notes, decorative glass vessel", "Home Decor", 40, 35, 12, 40, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("IKEA STOCKHOLM Cushion Cover", "DEC-017", "IKEA STOCKHOLM cushion cover, 20x20, wool jacquard weave, Scandinavian design", "Home Decor", 25, 20, 7, 45, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Pottery Barn Shag Tonal Rug 5x8", "DEC-018", "Pottery Barn Shag Tonal rug, 5x8 feet, 100% wool, hand-tufted, plush pile", "Home Decor", 499, 439, 210, 10, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Crate & Barrel Autumn Throw Blanket", "DEC-019", "Crate & Barrel Autumn throw blanket, 50x60, acrylic, fringed edges, soft knit", "Home Decor", 70, 59, 22, 30, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ("Serena & Lily Coastal Stripe Duvet Cover", "DEC-020", "Serena & Lily Coastal stripe duvet cover, queen, 100% linen, casual elegance", "Home Decor", 348, 298, 135, 12, "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),

    # ═══ SPORTS & FITNESS (25) ═══
    ("Peloton Bike+ Indoor Cycling", "SPT-001", "Peloton Bike+, 23.8-inch rotating HD touchscreen, Apple GymKit, auto-follow resistance, speakers", "Sports & Fitness", 2495, 2245, 1600, 5, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("TRX All-in-One Suspension Training System", "SPT-002", "TRX All-in-One suspension trainer, door anchor, indoor/outdoor, full body workout system", "Sports & Fitness", 170, 150, 60, 30, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Bowflex SelectTech 552 Adjustable Dumbbells", "SPT-003", "Bowflex SelectTech 552 adjustable dumbbells, 5-52.5 lbs each, replaces 15 sets of weights", "Sports & Fitness", 549, 479, 280, 12, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Theragun Pro Massage Gun", "SPT-004", "Theragun Pro smart percussive therapy device, OLED screen, 6 attachments, Bluetooth app", "Sports & Fitness", 449, 399, 230, 18, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Garmin Edge 540 Solar GPS Cycling Computer", "SPT-005", "Garmin Edge 540 Solar cycling computer, touchscreen, solar charging, 26hr battery, climb pro", "Sports & Fitness", 450, 400, 240, 10, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Hydro Flask 32oz Wide Mouth", "SPT-006", "Hydro Flask 32oz wide mouth water bottle, TempShield double-wall vacuum, stainless steel", "Sports & Fitness", 45, 38, 14, 80, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Manduka PRO Yoga Mat 6mm", "SPT-007", "Manduka PRO yoga mat, 71 inches, 6mm dense cushion, closed-cell surface, lifetime guarantee", "Sports & Fitness", 140, 120, 48, 25, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Rogue Fitness Ohio Barbell", "SPT-008", "Rogue Ohio barbell, 20kg, 190K PSI tensile strength steel, composite bushings, lifetime warranty", "Sports & Fitness", 395, 350, 200, 10, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("NordicTrack Commercial 1750 Treadmill", "SPT-009", "NordicTrack 1750 treadmill, 14-inch HD touchscreen, -3% to 15% incline, iFIT coach", "Sports & Fitness", 1799, 1599, 1050, 8, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Hyperice Hypervolt 2 Pro Massage Gun", "SPT-010", "Hyperice Hypervolt 2 Pro, 5 speed settings, QuietGlide technology, Bluetooth app, 5 attachments", "Sports & Fitness", 399, 349, 200, 15, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Under Armour Project Rock 6 Training Shoes", "SPT-011", "Under Armour Project Rock 6 training shoes, TriBase outsole, UA HOVR cushion, flat stable base", "Sports & Fitness", 160, 145, 58, 25, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Concept2 RowErg Indoor Rower", "SPT-012", "Concept2 RowErg indoor rower, PM5 monitor, nickel-plated chain, air resistance, adjustable footrests", "Sports & Fitness", 990, 890, 580, 10, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Garmin Forerunner 965 GPS Running Watch", "SPT-013", "Garmin Forerunner 965 running watch, AMOLED, 31-day battery, training readiness, morning report", "Sports & Fitness", 599, 549, 380, 12, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Lululemon Align High-Rise Pant 25-Inch", "SPT-014", "Lululemon Align high-rise pant, 25-inch, Nulu fabric, barely-there feel, hidden pocket", "Sports & Fitness", 98, 88, 32, 60, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("REI Co-op Half Dome SL 2 Plus Tent", "SPT-015", "REI Co-op Half Dome SL 2 Plus tent, 2-person, full mesh canopy, two vestibules, 4lb 7oz", "Sports & Fitness", 229, 199, 95, 15, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Osprey Atmos AG 65 Backpack", "SPT-016", "Osprey Atmos AG 65 hiking backpack, Anti-Gravity suspension, sleeping bag compartment, 65L", "Sports & Fitness", 300, 270, 120, 12, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("The North Face Apex Bionic 3 Jacket", "SPT-017", "The North Face Apex Bionic 3 softshell jacket, WindWall fabric, DWR finish, warm fleece backing", "Sports & Fitness", 199, 179, 72, 20, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Wilson US Open Extra Duty Tennis Balls (4-Pack)", "SPT-018", "Wilson US Open Extra Duty tennis balls, pressurized, natural rubber core, extra duty felt", "Sports & Fitness", 5, 4, 1.5, 200, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Callaway Paradym X Driver", "SPT-019", "Callaway Paradym X driver, jailbreak AI, forged carbon chassis, 460cc, adjustable loft", "Sports & Fitness", 599, 549, 330, 8, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("YETI Hopper Flip 12 Soft Cooler", "SPT-020", "YETI Hopper Flip 12 portable soft cooler, DryHide Shell, 20 cans, cold-cell insulation", "Sports & Fitness", 250, 225, 100, 18, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Black Diamond Spot 400 Headlamp", "SPT-021", "Black Diamond Spot 400 headlamp, 400 lumens, waterproof, red night-vision mode, 3 AAA batteries", "Sports & Fitness", 50, 42, 16, 35, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Columbia Silver Ridge Cargo Shorts", "SPT-022", "Columbia Silver Ridge cargo shorts, Omni-Shade UPF 50, Omni-Shield water repellent, 10-inch inseam", "Sports & Fitness", 45, 38, 14, 50, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Garmin inReach Mini 2 Satellite Communicator", "SPT-023", "Garmin inReach Mini 2, two-way messaging, SOS, GPS tracking, weather, 14-day battery", "Sports & Fitness", 400, 360, 210, 10, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Aftershokz OpenRun Pro Bone Conduction Headphones", "SPT-024", "Shokz OpenRun Pro bone conduction headphones, 10hr battery, IP55, TurboPitch, Bluetooth 5.1", "Sports & Fitness", 180, 160, 65, 25, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Scarpa Zodiac Plus GTX Hiking Boots", "SPT-025", "Scarpa Zodiac Plus GTX hiking boots, Gore-Tex, Vibram Drumlin sole, suede leather, crampon compatible", "Sports & Fitness", 349, 310, 170, 8, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),

    # ═══ BEAUTY & PERSONAL CARE (20) ═══
    ("Dyson Airwrap Multi-Styler Complete", "BTY-001", "Dyson Airwrap multi-styler, Coanda airflow, curling, waving, smoothing, drying with no extreme heat", "Beauty & Personal Care", 599, 549, 380, 15, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Olaplex No. 3 Hair Perfector Treatment", "BTY-002", "Olaplex No. 3 hair perfector, bond repair treatment, reduces breakage, restores damaged hair", "Beauty & Personal Care", 30, 28, 8, 80, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("La Mer Creme de la Mer Moisturizer 2oz", "BTY-003", "La Mer Creme de la Mer moisturizer, 2oz, Miracle Broth, hydrates, soothes, minimizes pores", "Beauty & Personal Care", 380, 340, 190, 10, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Drunk Elephant Protini Polypeptide Cream", "BTY-004", "Drunk Elephant Protini moisturizer, signal peptides, growth factors, supportive amino acids", "Beauty & Personal Care", 68, 62, 22, 35, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Dyson Corrale Straightener", "BTY-005", "Dyson Corrale hair straightener, flexing plates, cordless, 45min runtime, heat control", "Beauty & Personal Care", 499, 449, 300, 12, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("CeraVe Moisturizing Cream 16oz", "BTY-006", "CeraVe moisturizing cream, 16oz, hyaluronic acid, ceramides, MVE technology, 24hr hydration", "Beauty & Personal Care", 19, 16, 5, 120, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("The Ordinary Hyaluronic Acid 2% + B5", "BTY-007", "The Ordinary Hyaluronic Acid 2% + B5 serum, multi-depth hydration, vegan, cruelty-free", "Beauty & Personal Care", 10, 8, 2.5, 150, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Charlotte Tilbury Pillow Talk Lipstick", "BTY-008", "Charlotte Tilbury Pillow Talk matte lipstick, nude-pink, hydrating, buildable, iconic shade", "Beauty & Personal Care", 36, 32, 10, 45, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Tatcha The Dewy Skin Cream", "BTY-009", "Tatcha The Dewy Skin Cream, Japanese purple rice, anti-aging, plumping, dewy glow", "Beauty & Personal Care", 69, 62, 24, 25, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Paula's Choice 2% BHA Liquid Exfoliant", "BTY-010", "Paula's Choice BHA exfoliant, salicylic acid, unclogs pores, reduces redness, smooths texture", "Beauty & Personal Care", 34, 30, 10, 40, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Revlon One-Step Hair Dryer and Volumizer", "BTY-011", "Revlon One-Step hair dryer and volumizer, oval brush design, ionic technology, 2 heat settings", "Beauty & Personal Care", 42, 35, 12, 60, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("SK-II Facial Treatment Essence", "BTY-012", "SK-II Facial Treatment Essence, Pitera, 90%+, crystal clear skin, anti-aging, hydrating", "Beauty & Personal Care", 235, 210, 110, 12, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Estee Lauder Advanced Night Repair Serum", "BTY-013", "Estee Lauder Advanced Night Repair serum, chronolux power signal technology, anti-aging, 1.7oz", "Beauty & Personal Care", 82, 74, 30, 30, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Bioderma Sensibio H2O Micellar Water", "BTY-014", "Bioderma Sensibio H2O micellar water, 500ml, gentle cleansing, sensitive skin, no-rinse", "Beauty & Personal Care", 18, 15, 5, 80, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Lancome La Vie Est Belle Eau de Parfum", "BTY-015", "Lancome La Vie Est Belle EDP, 3.3oz, iris, praline, vanilla, patchouli, long-lasting", "Beauty & Personal Care", 130, 115, 50, 20, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Clinique Moisture Surge 100H Moisturizer", "BTY-016", "Clinique Moisture Surge 100H auto-replenishing hydrator, 72-hour moisture, aloe water", "Beauty & Personal Care", 52, 46, 18, 35, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("T3 AireLuxe Hair Dryer", "BTY-017", "T3 AireLuxe hair dryer, IonAir technology, volume booster switch, auto-pulse digital motor", "Beauty & Personal Care", 235, 210, 105, 15, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Shiseido Ultimate Sun Protector Lotion SPF 60", "BTY-018", "Shiseido Ultimate Sun Protector Lotion, SPF 60, invisible, reef-safe, heat-force technology", "Beauty & Personal Care", 48, 44, 15, 50, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("First Aid Beauty Ultra Repair Cream", "BTY-019", "First Aid Beauty Ultra Repair Cream, shea butter, colloidal oatmeal, safe for eczema, 6oz", "Beauty & Personal Care", 38, 34, 12, 45, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Tom Ford Noir Extreme Eau de Parfum", "BTY-020", "Tom Ford Noir Extreme EDP, 3.3oz, cardamom, nutmeg, vanilla, amber, woody, masculine", "Beauty & Personal Care", 145, 130, 60, 15, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),

    # ═══ ELECTRONICS & GADGETS (remaining to fill up to 585) ═══
    ("Dell XPS 17 Laptop", "ELC-001", "Dell XPS 17 laptop, Intel Core i9-13900H, 32GB RAM, 1TB SSD, 17-inch 4K display", "Electronics", 2299, 2099, 1550, 15, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("Apple TV 4K 128GB", "ELC-002", "Apple TV 4K 128GB, A15 Bionic, Thread and Matter support, Dolby Atmos, HDR10+", "Electronics", 149, 139, 88, 40, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("WD My Cloud Home 8TB NAS", "ELC-003", "WD My Cloud Home 8TB personal cloud storage, gigabit ethernet, auto backup, remote access", "Electronics", 299, 269, 165, 20, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Anker PowerCore III 10000mAh Wireless", "ELC-004", "Anker PowerCore III 10000mAh wireless power bank, Qi-certified, USB-C, PowerIQ", "Electronics", 36, 29, 10, 90, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Logitech MX Master 3S Mouse", "ELC-005", "Logitech MX Master 3S wireless mouse, 8K DPI, quiet clicks, MagSpeed scroll, USB-C", "Electronics", 99, 89, 40, 55, "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400&h=400&fit=crop"),
    ("Logitech MX Keys S Keyboard", "ELC-006", "Logitech MX Keys S wireless keyboard, smart illumination, perfect stroke keys, multi-device", "Electronics", 109, 99, 45, 40, "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
    ("Samsung T7 2TB Portable SSD", "ELC-007", "Samsung T7 2TB portable SSD, 1050MB/s read, 1000MB/s write, USB 3.2, hardware encryption", "Electronics", 189, 159, 95, 45, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Western Digital My Passport 5TB", "ELC-008", "WD My Passport 5TB external hard drive, USB 3.0, password protection, 256-bit AES", "Electronics", 149, 129, 70, 30, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Ring Video Doorbell Pro 2", "ELC-009", "Ring Video Doorbell Pro 2, 3D motion detection, Head-to-Toe HD+ Video, Alexa", "Electronics", 249, 199, 115, 25, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Sonos Era 300 Speaker", "ELC-010", "Sonos Era 300 speaker, spatial audio, Dolby Atmos, Trueplay tuning, voice control", "Electronics", 449, 399, 250, 18, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Canon EOS R6 Mark II Body", "ELC-011", "Canon EOS R6 Mark II mirrorless camera body, 24.2MP, 40fps, 4K 60p, 10-bit video", "Electronics", 2499, 2299, 1650, 8, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
    ("Sony a7 IV Mirrorless Camera Body", "ELC-012", "Sony a7 IV mirrorless camera, 33MP, 10fps, 4K 60p, real-time tracking, 10-bit 4:2:2", "Electronics", 2498, 2298, 1650, 7, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
    ("GoPro HERO12 Black", "ELC-013", "GoPro HERO12 Black, 5.3K60 video, HyperSmooth 6.0, waterproof 33ft, Bluetooth audio", "Electronics", 399, 349, 220, 30, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
    ("DJI Mini 4 Pro Drone", "ELC-014", "DJI Mini 4 Pro drone, 4K HDR video, omnidirectional sensing, 34-min flight time, under 249g", "Electronics", 999, 899, 620, 10, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
    ("JBL Flip 6 Portable Speaker", "ELC-015", "JBL Flip 6 portable Bluetooth speaker, IP67, 12hr battery, PartyBoost, JBL Pro Sound", "Electronics", 129, 109, 48, 60, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
    ("Amazon Fire TV Stick 4K Max", "ELC-016", "Amazon Fire TV Stick 4K Max, Wi-Fi 6E, ambient experience, Alexa voice remote, Dolby Atmos", "Electronics", 59, 39, 18, 100, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Roku Streaming Stick 4K+", "ELC-017", "Roku Streaming Stick 4K+, long-range Wi-Fi, voice remote with lost remote finder, 4K HDR", "Electronics", 49, 39, 15, 80, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Chromecast with Google TV 4K", "ELC-018", "Chromecast with Google TV 4K, voice remote, Dolby Vision, HDR10+, 32GB storage", "Electronics", 49, 44, 18, 75, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("NVIDIA Shield TV Pro", "ELC-019", "NVIDIA Shield TV Pro, 4K HDR, Dolby Vision Atmos, AI upscaling, Plex Media Server", "Electronics", 199, 179, 95, 20, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Apple iPad Pro 11-inch M2 128GB", "ELC-020", "Apple iPad Pro 11-inch, M2, 128GB, Liquid Retina, Thunderbolt, Face ID", "Electronics", 799, 749, 530, 22, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ("Logitech C920s HD Pro Webcam", "ELC-021", "Logitech C920s HD Pro webcam, 1080p, privacy shutter, stereo mics, autofocus", "Electronics", 79, 69, 28, 50, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Elgato Stream Deck MK.2", "ELC-022", "Elgato Stream Deck MK.2, 15 LCD keys, customizable, scenes, media, chat, upload", "Electronics", 149, 139, 65, 25, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Razer DeathAdder V3 Gaming Mouse", "ELC-023", "Razer DeathAdder V3, 30K DPI Focus Pro sensor, 90hr battery, optical switches Gen-3", "Electronics", 99, 89, 40, 35, "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400&h=400&fit=crop"),
    ("Corsair K100 RGB Mechanical Keyboard", "ELC-024", "Corsair K100 RGB mechanical keyboard, OPX switches, iCUE control wheel, PBT keycaps", "Electronics", 229, 199, 100, 15, "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
    ("Beats Studio Buds Plus", "ELC-025", "Beats Studio Buds Plus true wireless earbuds, ANC, transparency mode, up to 36hr battery", "Electronics", 169, 149, 75, 45, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Bose SoundLink Flex Speaker", "ELC-026", "Bose SoundLink Flex portable speaker, IP67, PositionIQ, 12hr battery, USB-C", "Electronics", 149, 129, 55, 40, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
    ("TP-Link Deco XE75 Mesh Wi-Fi 6E System", "ELC-027", "TP-Link Deco XE75 Wi-Fi 6E mesh, 3-pack, 7200 Mbps, covers 7200 sq ft, AI-driven mesh", "Electronics", 249, 199, 110, 20, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Netgear Nighthawk RAXE500 Router", "ELC-028", "Netgear Nighthawk RAXE500 Wi-Fi 6E router, 12-stream, 10.8 Gbps, 2.5G port", "Electronics", 399, 349, 200, 12, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Bose QuietComfort Ultra Earbuds", "ELC-029", "Bose QC Ultra true wireless earbuds, spatial audio, world-class ANC, 6hr battery", "Electronics", 299, 279, 175, 35, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Anker 737 Power Bank 24000mAh 140W", "ELC-030", "Anker 737 power bank, 24000mAh, 140W max, smart digital display, USB-C PD 3.1", "Electronics", 109, 95, 45, 40, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),

    # ═══ TOYS & GAMES (20) ═══
    ("LEGO Star Wars Millennium Falcon 75375", "TOY-001", "LEGO Star Wars Millennium Falcon, 1,353 pieces, minifigures, buildable display set", "Toys & Games", 169, 149, 72, 30, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Nintendo Switch OLED Model", "TOY-002", "Nintendo Switch OLED model, 7-inch OLED screen, enhanced audio, wide adjustable stand, 64GB", "Toys & Games", 349, 299, 210, 25, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Sony PlayStation 5 Console", "TOY-003", "Sony PlayStation 5 console, 4K HDR gaming, 825GB SSD, DualSense controller, ray tracing", "Toys & Games", 499, 449, 350, 15, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Xbox Series X Console", "TOY-004", "Xbox Series X console, 12 teraflops, 4K 120fps, 1TB SSD, Quick Resume, backward compatible", "Toys & Games", 499, 449, 350, 18, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("LEGO Technic Lamborghini Sián", "TOY-005", "LEGO Technic Lamborghini Sián, 3,696 pieces, V12 engine, working doors, collectors set", "Toys & Games", 479, 429, 250, 10, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Monopoly Board Game Classic", "TOY-006", "Monopoly classic board game, Parker Brothers, the property trading game, 2-8 players", "Toys & Games", 20, 17, 5, 100, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Hasbro Jenga Classic Game", "TOY-007", "Jenga classic block-stacking game, 54 precision-cut hardwood blocks, stacking tower", "Toys & Games", 15, 12, 4, 120, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Scrabble Deluxe Edition", "TOY-008", "Scrabble deluxe edition, rotating game board, raised grid, tile bags, score-keeping", "Toys & Games", 50, 42, 18, 30, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("DJI Mini 3 Pro Drone", "TOY-009", "DJI Mini 3 Pro drone, 4K HDR video, 34min flight, tri-directional obstacle sensing, under 249g", "Toys & Games", 759, 659, 440, 8, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("LEGO City Space Rocket Launch Center", "TOY-010", "LEGO City Space Rocket Launch Center, 1,010 pieces, launch pad, astronaut minifigures", "Toys & Games", 129, 109, 52, 25, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("PlayStation DualSense Controller", "TOY-011", "PS5 DualSense wireless controller, haptic feedback, adaptive triggers, built-in mic", "ToY-011", 69, 59, 28, 50, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Risk Board Game Classic", "TOY-012", "Risk classic board game, world domination strategy, 2-6 players, global conquest", "Toys & Games", 30, 25, 8, 60, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("LEGO Architecture Eiffel Tower", "TOY-013", "LEGO Architecture Eiffel Tower, 10,009 pieces, tallest LEGO set, realistic display model", "Toys & Games", 629, 569, 380, 5, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Hasbro Connect 4 Strategy Game", "TOY-014", "Connect 4 classic strategy game, two-player, drop-disc, get 4 in a row", "Toys & Games", 15, 12, 4, 100, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("LEGO Creator Expert Roller Coaster", "TOY-015", "LEGO Creator Expert roller coaster, 4,124 pieces, motorized, moving cars, ticket booth", "Toys & Games", 399, 349, 220, 8, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Apples to Apples Party Game", "TOY-016", "Apples to Apples party card game, 756 cards, hilarious comparisons, 4-10 players, ages 12+", "Toys & Games", 20, 17, 5, 80, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("LEGO Harry Potter Hogwarts Castle", "TOY-017", "LEGO Harry Potter Hogwarts Castle, 6,020 pieces, 27 minifigures, 4 massive floors", "Toys & Games", 469, 429, 280, 10, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Catan Board Game", "TOY-018", "Catan strategy board game, trade resources, build settlements, 3-4 players, expandable", "Toys & Games", 44, 38, 14, 50, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("LEGO Super Mario Starter Course", "TOY-019", "LEGO Super Mario Starter Course, 231 pieces, interactive Mario figure, action bricks", "Toys & Games", 59, 49, 22, 35, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ("Codenames Board Game", "TOY-020", "Codenames word game, 200 key cards, teams compete, 4-8+ players, party deduction", "Toys & Games", 20, 17, 5, 60, "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
]

def main():
    import psycopg2
    from app.utils import hash_password
    conn = psycopg2.connect(CONN)
    conn.autocommit = True
    cur = conn.cursor()

    # Get existing product count
    cur.execute("SELECT COUNT(*) FROM products")
    existing = cur.fetchone()[0]
    print(f"Existing products: {existing}")

    # We need exactly len(CATALOG) products
    # If we have more, delete extras. If less, we handle it.
    needed = len(CATALOG)
    print(f"Catalog products: {needed}")

    # Ensure we have enough product IDs by creating placeholder rows if needed
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM products")
    max_id = cur.fetchone()[0]
    if max_id < needed:
        for i in range(max_id + 1, needed + 1):
            cur.execute(
                "INSERT INTO products (id, name, sku, description, category, base_price, current_price, cost_price, stock_quantity, revenue, status, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (i, f"Placeholder {i}", f"TMP-{i:03d}", "Temp", "Temp", 0, 0, 0, 0, 0, "active", "")
            )
    print("Ensured enough product slots exist")

    # Now replace each product in-place (preserves ID → sales_history stays linked)
    updated = 0
    for i, p in enumerate(CATALOG):
        pid = i + 1
        name, sku, desc, cat, base_price, curr_price, cost_price, stock, img = p
        # Calculate realistic revenue from price * estimated sales
        # Use random but seeded per product for consistency
        random.seed(pid)
        est_sales = random.randint(20, 200)
        revenue = round(curr_price * est_sales * random.uniform(0.5, 1.5), 2)

        cur.execute("""
            UPDATE products SET
                name = %s, sku = %s, description = %s, category = %s,
                base_price = %s, current_price = %s, cost_price = %s,
                stock_quantity = %s, revenue = %s, image_url = %s,
                status = 'active'
            WHERE id = %s
        """, (name, sku, desc, cat, base_price, curr_price, cost_price, stock, revenue, img, pid))
        updated += 1

    # Delete any extra products beyond our catalog
    cur.execute("DELETE FROM products WHERE id > %s", (needed,))
    deleted_extras = cur.rowcount
    if deleted_extras:
        print(f"Deleted {deleted_extras} extra products")

    # Also update the pricing_history for products that still have base_price references
    # We won't touch sales_history (it references product_id which is preserved)
    # We just update pricing_history old prices to match the new base_prices
    cur.execute("""
        UPDATE pricing_history ph
        SET old_price = p.base_price
        FROM products p
        WHERE ph.product_id = p.id AND ph.old_price != p.base_price
    """)
    updated_ph = cur.rowcount
    if updated_ph:
        print(f"Updated {updated_ph} pricing_history records")

    conn.commit()

    # Verify
    cur.execute("SELECT COUNT(*) FROM products")
    final_count = cur.fetchone()[0]
    cur.execute("SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY COUNT(*) DESC")
    cats = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM sales")
    sales_count = cur.fetchone()[0]

    print(f"\nFinal product count: {final_count}")
    print(f"Categories ({len(cats)}):")
    for cat, count in cats:
        print(f"  {cat}: {count}")
    print(f"Sales rows preserved: {sales_count}")

    conn.close()

if __name__ == "__main__":
    main()
