"""
Generate a realistic 585-product catalog with proper brand/category distribution.
Replaces ALL products in-place (preserving IDs so sales_history stays linked).
"""
import sys, random
sys.stdout.reconfigure(encoding='ascii', errors='replace')
sys.path.insert(0, '.')

import psycopg2

CONN = 'postgresql://postgres:postgres@localhost:5432/dynamic_pricing'

# ─── Product templates by category ───────────────────────────────────────────
# Format: (name_template, base_price, cost_price_range, stock_range, image_url)
# We generate brand-prefixed products from these templates.

CATEGORIES = {
    # ═══ LAPTOPS (40) ═══
    "Laptops": [
        ("Apple MacBook Air 13-inch M3 8GB/256GB", 1099, (780, 820), (30, 55), "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
        ("Apple MacBook Pro 14-inch M3 Pro 18GB/512GB", 1999, (1450, 1500), (15, 35), "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
        ("Apple MacBook Pro 16-inch M3 Max 36GB/1TB", 3499, (2500, 2600), (5, 15), "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
        ("Apple MacBook Air 15-inch M3 8GB/256GB", 1299, (900, 940), (25, 45), "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
        ("Apple MacBook Air 13-inch M2 8GB/256GB", 999, (680, 720), (30, 50), "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
        ("Dell XPS 15 Intel i7-13700H 16GB/512GB", 1499, (1000, 1050), (20, 40), "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
        ("Dell XPS 13 Plus Intel i7-1360P 16GB/512GB", 1299, (850, 900), (20, 35), "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
        ("Dell Inspiron 16 Intel i5-1335U 8GB/512GB", 799, (500, 540), (40, 65), "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
        ("Dell Latitude 5540 Intel i5-1345U 16GB/512GB", 1149, (720, 760), (25, 45), "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
        ("Dell Alienware m18 R2 i9 RTX 4090 32GB/1TB", 3499, (2400, 2500), (5, 10), "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
        ("HP Spectre x360 14 Intel i7 16GB/1TB OLED", 1649, (1100, 1150), (15, 30), "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
        ("HP Envy 16 Intel i9 32GB/1TB RTX 4060", 1799, (1200, 1250), (10, 25), "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
        ("HP Pavilion 15 AMD Ryzen 7 16GB/512GB", 749, (450, 490), (45, 70), "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
        ("HP Omen 16 AMD Ryzen 9 RTX 4070 16GB/1TB", 1599, (1050, 1100), (15, 30), "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
        ("HP Victus 15 Intel i5 RTX 3050 8GB/512GB", 799, (480, 520), (30, 50), "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
        ("Lenovo ThinkPad X1 Carbon Gen 11 i7 16GB/512GB", 1849, (1250, 1300), (15, 30), "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
        ("Lenovo ThinkPad X1 Yoga Gen 8 i7 16GB/512GB", 1949, (1350, 1400), (10, 25), "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
        ("Lenovo ThinkPad T14s Gen 4 AMD Ryzen 7 16GB/512GB", 1649, (1050, 1100), (15, 30), "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
        ("Lenovo IdeaPad 5 AMD Ryzen 5 8GB/512GB", 549, (320, 350), (50, 80), "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
        ("Lenovo Legion Pro 5 i9 RTX 4070 32GB/1TB", 2099, (1500, 1550), (10, 20), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Lenovo Yoga 9i 14 Intel i7 16GB/512GB OLED", 1549, (1000, 1050), (15, 25), "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
        ("ASUS ROG Zephyrus G14 AMD Ryzen 9 RTX 4070 16GB", 1649, (1100, 1150), (10, 22), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("ASUS Zenbook 14 OLED Intel Ultra 7 16GB/1TB", 1299, (850, 900), (20, 35), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("ASUS Vivobook 15 Intel i5 8GB/512GB", 599, (360, 390), (45, 65), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("ASUS TUF Gaming A15 AMD Ryzen 7 RTX 4060 16GB", 1199, (780, 820), (20, 40), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("ASUS ProArt Studiobook 16 i9 RTX 4070 32GB", 2499, (1750, 1800), (5, 12), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("MSI Raider GE78 HX i9 RTX 4080 32GB/1TB", 2999, (2100, 2150), (5, 12), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("MSI Prestige 16 AI Evo Intel Ultra 7 32GB/1TB", 1599, (1050, 1100), (10, 20), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Dell G16 Intel i7 RTX 4060 16GB/512GB", 1399, (900, 950), (20, 35), "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
        ("Razer Blade 16 i9 RTX 4080 32GB/1TB", 3199, (2300, 2350), (4, 10), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Razer Blade 14 AMD Ryzen 9 RTX 4070 16GB", 2199, (1450, 1500), (5, 12), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Book 4 Pro Intel Ultra 7 16GB/512GB AMOLED", 1449, (950, 1000), (15, 30), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Book 3 Ultra i9 RTX 4070 32GB/1TB", 2399, (1650, 1700), (8, 15), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Acer Nitro 5 Intel i5 RTX 4050 8GB/512GB", 899, (550, 590), (30, 50), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Acer Aspire 5 AMD Ryzen 5 8GB/512GB", 549, (320, 350), (45, 65), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Acer Swift 3 OLED Intel i7 16GB/512GB", 999, (620, 660), (15, 30), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("LG Gram 17 Intel i7 16GB/512GB", 1799, (1200, 1250), (10, 20), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Surface Laptop 5 Intel i7 16GB/512GB", 1299, (850, 900), (15, 30), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Framework Laptop 16 AMD Ryzen 7 32GB/1TB", 1699, (1100, 1150), (8, 15), "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
        ("Lenovo IdeaPad Slim 3 AMD Ryzen 5 8GB/256GB", 449, (260, 290), (50, 75), "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
        ("HP Chromebook Plus Intel i3 8GB/256GB", 499, (280, 310), (40, 60), "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ],
    # ═══ SMARTPHONES (30) ═══
    "Smartphones": [
        ("Apple iPhone 15 Pro Max 256GB", 1199, (850, 880), (35, 60), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone 15 Pro 128GB", 999, (680, 710), (45, 75), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone 15 128GB", 799, (520, 550), (55, 90), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone 15 Plus 128GB", 899, (580, 610), (35, 55), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone 14 128GB", 699, (450, 480), (50, 80), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone 16 Pro Max 256GB", 1299, (880, 920), (30, 50), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone 16 128GB", 829, (540, 570), (50, 70), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Apple iPhone SE 2022 64GB", 429, (260, 280), (50, 70), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
        ("Samsung Galaxy S24 Ultra 256GB", 1299, (900, 930), (35, 55), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy S24+ 256GB", 999, (680, 710), (40, 60), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy S24 128GB", 799, (520, 550), (50, 70), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Z Fold5 256GB", 1799, (1250, 1300), (10, 20), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Z Flip5 256GB", 999, (680, 710), (25, 40), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy A55 5G 128GB", 449, (260, 280), (60, 100), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy S23 FE 128GB", 599, (380, 410), (35, 55), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy S25 256GB", 899, (580, 610), (25, 40), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Z Flip6 256GB", 1099, (720, 750), (15, 25), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Samsung Galaxy A35 5G 128GB", 399, (220, 240), (70, 100), "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
        ("Google Pixel 8 Pro 128GB", 999, (680, 710), (25, 45), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("Google Pixel 8 128GB", 699, (450, 480), (40, 60), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("Google Pixel 7a 128GB", 499, (300, 330), (45, 65), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("Google Pixel 8a 128GB", 499, (310, 340), (40, 60), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("Google Pixel 9 128GB", 799, (480, 510), (35, 50), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("OnePlus 12 256GB", 799, (520, 550), (25, 40), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("OnePlus 11 256GB", 699, (450, 480), (30, 45), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("OnePlus 12R 256GB", 499, (300, 330), (30, 45), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("OnePlus Nord N30 5G 128GB", 299, (170, 190), (60, 85), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("Sony Xperia 1 V 256GB", 1399, (950, 990), (8, 15), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("Nothing Phone 2 256GB", 599, (380, 410), (25, 40), "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
        ("iPhone 13 128GB", 599, (380, 410), (50, 75), "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ],
    # ═══ HEADPHONES (25) ═══
    "Headphones": [
        ("Sony WH-1000XM5 Wireless ANC Headphones", 399, (220, 240), (30, 55), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Sony WF-1000XM5 True Wireless ANC Earbuds", 299, (185, 200), (30, 50), "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
        ("Sony WH-1000XM4 Wireless ANC Headphones", 349, (200, 220), (25, 45), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Apple AirPods Pro 2nd Gen USB-C ANC", 249, (155, 170), (45, 75), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Apple AirPods Max Over-Ear ANC", 549, (370, 390), (10, 20), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Apple AirPods 3rd Gen Spatial Audio", 169, (100, 110), (50, 80), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Bose QuietComfort Ultra Headphones ANC", 429, (260, 280), (20, 35), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Bose QuietComfort Ultra Earbuds ANC", 299, (185, 200), (25, 40), "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
        ("Bose QuietComfort 45 ANC Headphones", 329, (185, 200), (25, 45), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Sennheiser Momentum 4 Wireless ANC", 349, (220, 240), (15, 30), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Sennheiser Momentum True Wireless 4 ANC", 299, (185, 200), (15, 30), "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
        ("Sennheiser HD 660S2 Open-Back Reference", 499, (330, 350), (8, 15), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Jabra Elite 85t True Wireless ANC", 229, (130, 145), (25, 45), "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
        ("Jabra Elite 85h Wireless ANC", 249, (145, 160), (20, 35), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Beats Studio Pro Wireless ANC", 349, (200, 220), (25, 40), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Beats Fit Pro True Wireless ANC", 199, (115, 130), (35, 55), "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
        ("Beats Solo 4 On-Ear Wireless", 199, (120, 135), (30, 45), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("JBL Tour One M2 Wireless ANC", 299, (175, 190), (20, 35), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("JBL Tune 770NC Wireless ANC", 99, (48, 55), (50, 75), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Beyerdynamic DT 900 Pro X Open-Back Studio", 269, (170, 185), (10, 18), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Audio-Technica ATH-M50xBT2 Wireless", 199, (115, 130), (25, 40), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Shure AONIC 50 Gen 2 Wireless ANC", 399, (250, 270), (10, 20), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Skullcandy Crusher ANC 2 Wireless", 229, (130, 145), (25, 45), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Buds2 Pro ANC", 229, (130, 145), (35, 55), "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
        ("Jabra Evolve2 85 Wireless ANC Headset", 379, (200, 220), (8, 15), "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ],
    # ═══ TVs & MONITORS (25) ═══
    "TVs & Monitors": [
        ("Samsung 65-inch QN90C Neo QLED 4K", 1799, (1150, 1200), (10, 20), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Samsung 55-inch S95C OLED 4K", 1599, (1000, 1050), (8, 15), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Samsung 75-inch QN85C Neo QLED 4K", 2199, (1450, 1500), (6, 12), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("LG 65-inch C3 OLED evo 4K", 1799, (1050, 1100), (10, 18), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("LG 55-inch B3 OLED 4K", 1299, (780, 820), (12, 22), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("LG 77-inch G3 OLED evo 4K", 3299, (2200, 2300), (4, 8), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Sony 65-inch A95L QD-OLED 4K", 2799, (1800, 1900), (5, 10), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Sony 55-inch X90L LED 4K", 1199, (740, 780), (12, 22), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("TCL 65-inch QM8 Mini LED 4K", 1099, (650, 690), (15, 28), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("TCL 55-inch S4 4K TV", 349, (190, 210), (30, 45), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Samsung 50-inch CU7000 4K UHD", 449, (250, 270), (25, 40), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Hisense 65-inch U8K Mini LED 4K", 999, (580, 620), (12, 22), "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&h=400&fit=crop"),
        ("Dell UltraSharp 27 4K USB-C Hub Monitor", 619, (380, 410), (15, 28), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("Dell 27 Gaming Monitor 165Hz QHD", 299, (165, 180), (25, 40), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("LG 27GP950-B 4K 160Hz Gaming Monitor", 799, (490, 520), (8, 15), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("ASUS ProArt PA279CRV 4K USB-C Monitor", 549, (340, 370), (12, 22), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("Samsung 34-inch Odyssey G5 Ultra-Wide", 449, (265, 285), (10, 18), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("Apple Studio Display 27-inch 5K", 1599, (1050, 1100), (5, 10), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("LG 34-inch UltraWide WQHD Curved", 599, (370, 400), (10, 18), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("LG 27-inch UltraGear OLED 240Hz", 999, (650, 690), (6, 10), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("ASUS ROG Swift PG27AQN 360Hz Gaming", 849, (530, 560), (5, 10), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("Samsung 32-inch ViewFinity S9 5K", 1599, (1000, 1050), (5, 10), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("HP U32 4K HDR USB-C Monitor", 449, (275, 295), (15, 22), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("BenQ EW3280U 4K Monitor", 699, (440, 470), (8, 15), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
        ("Dell 32 Curved 4K USB-C Hub Monitor", 499, (305, 325), (12, 22), "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop"),
    ],
    # ═══ TABLETS (12) ═══
    "Tablets": [
        ("Apple iPad Pro 12.9-inch M2 256GB", 1099, (740, 780), (15, 28), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Apple iPad Air M1 64GB", 599, (380, 410), (25, 45), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Apple iPad 10th Gen 64GB", 449, (280, 310), (35, 55), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Apple iPad Mini 6th Gen 64GB", 499, (310, 340), (20, 35), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Tab S9 Ultra 256GB", 1199, (780, 820), (10, 18), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Tab S9 FE 128GB", 449, (265, 285), (25, 40), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Microsoft Surface Pro 9 i7 256GB", 1599, (1050, 1100), (8, 15), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Lenovo Tab P12 Pro 256GB", 609, (380, 410), (12, 22), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Google Pixel Tablet 128GB", 499, (300, 330), (20, 30), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Amazon Fire HD 10 64GB", 149, (65, 75), (45, 65), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Tab A9+ 64GB", 229, (120, 135), (40, 60), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
        ("Apple iPad Pro 11-inch M2 128GB", 799, (530, 560), (18, 30), "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop"),
    ],
    # ═══ SMARTWATCHES (15) ═══
    "Smartwatches": [
        ("Apple Watch Series 9 45mm GPS", 429, (270, 290), (30, 50), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Apple Watch Series 9 41mm GPS", 399, (250, 270), (35, 55), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Apple Watch Ultra 2 Titanium 49mm", 799, (540, 570), (8, 15), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Apple Watch SE 2nd Gen 40mm", 249, (145, 160), (40, 60), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Watch 6 Classic 47mm", 399, (230, 250), (20, 35), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Watch 6 44mm", 329, (195, 210), (25, 40), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Samsung Galaxy Watch 5 Pro 45mm", 449, (250, 270), (12, 20), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Garmin Fenix 7X Solar", 899, (570, 600), (6, 12), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Garmin Venu 3", 449, (270, 290), (15, 25), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Garmin Forerunner 265 GPS Running", 449, (270, 290), (12, 20), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Google Pixel Watch 2 LTE", 399, (230, 250), (18, 28), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Fitbit Sense 2", 299, (160, 175), (25, 40), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Amazfit GTR 4", 199, (95, 110), (25, 40), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Withings ScanWatch 2", 349, (200, 220), (10, 18), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
        ("Whoop 4.0 Band", 299, (140, 155), (30, 45), "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop"),
    ],
    # ═══ SHIRTS & TOPS (30) ═══
    "Shirts & Tops": [
        ("Nike Dri-FIT Classic Polo", 55, (18, 22), (80, 130), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Nike Dri-FIT UV Miler Short-Sleeve", 40, (14, 17), (70, 110), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Adidas Originals Trefoil Tee", 35, (10, 13), (90, 160), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Adidas Climalite Soccer Jersey", 65, (22, 26), (50, 85), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Under Armour Tech 2.0 T-Shirt", 30, (9, 11), (90, 150), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Levi's 511 Slim Fit Oxford Shirt", 50, (17, 20), (55, 95), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Ralph Lauren Classic Fit Polo", 98, (35, 40), (35, 65), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Tommy Hilfiger Classic Crew Neck Tee", 40, (12, 15), (70, 120), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Calvin Klein Modern Cotton V-Neck Tee", 35, (10, 13), (80, 135), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("H&M Regular Fit Oxford Shirt", 25, (7, 9), (100, 170), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Uniqlo Supima Cotton T-Shirt", 20, (5, 7), (120, 210), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Polo Ralph Lauren Mesh Polo", 110, (40, 45), (25, 50), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Nike Sportswear Club T-Shirt", 30, (9, 11), (100, 180), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Lululemon Metal Vent Tech Short Sleeve", 68, (23, 27), (35, 55), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Zara Slim Fit Printed Shirt", 50, (15, 18), (45, 75), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Brooks Brothers Non-Iron Dress Shirt", 128, (45, 50), (20, 40), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Patagonia Capilene Cool Daily Graphic Tee", 45, (15, 18), (40, 70), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Carhartt Midweight Short-Sleeve Pocket Tee", 30, (9, 11), (80, 130), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Gildan Heavy Cotton T-Shirt", 10, (3, 4), (200, 510), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("GAP Classic Chambray Shirt", 45, (13, 16), (50, 80), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("J.Crew Ludlow Classic-Fit Dress Shirt", 98, (32, 36), (20, 40), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Banana Republic Italian Wool Dress Shirt", 148, (48, 53), (15, 30), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Amazon Essentials Slim-Fit Oxford Shirt", 22, (6, 8), (120, 210), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Mango Slim Fit Linen Shirt", 60, (20, 23), (25, 45), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Zara Linen Blend Shirt", 40, (11, 14), (50, 90), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Columbia PFG Terminal Tackle Shirt", 55, (18, 21), (25, 45), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("The North Face Drew Peak Polo", 55, (19, 22), (30, 55), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Todd Snyder Seersucker Camp Shirt", 168, (60, 65), (8, 18), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Columbia Silver Ridge Utility Shirt", 50, (16, 19), (35, 60), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
        ("Vintage Polo Sport Windbreaker Shirt", 145, (50, 55), (10, 22), "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ],
    # ═══ SHOES (30) ═══
    "Shoes": [
        ("Nike Air Max 90", 130, (52, 58), (50, 85), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Nike Air Force 1 Low", 115, (44, 48), (55, 95), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Nike Pegasus 40 Running Shoes", 130, (52, 58), (45, 75), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Nike Dunk Low Retro", 115, (44, 48), (45, 75), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Nike Metcon 9 Training Shoes", 150, (55, 60), (25, 40), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Adidas Ultraboost 23 Running", 190, (75, 82), (35, 60), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Adidas Stan Smith", 100, (38, 42), (50, 80), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Adidas Samba OG", 100, (38, 42), (40, 70), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("New Balance 990v6", 200, (80, 88), (15, 30), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("New Balance Fresh Foam X 1080v13", 165, (62, 68), (30, 50), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Converse Chuck Taylor All Star High-Top", 60, (18, 21), (75, 125), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Vans Old Skool", 70, (22, 25), (60, 105), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("ASICS Gel-Kayano 30 Running", 160, (58, 64), (25, 45), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Brooks Ghost 15 Running", 140, (52, 58), (30, 55), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Puma Suede Classic XXI", 75, (24, 27), (50, 85), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Reebok Classic Leather", 85, (28, 31), (40, 65), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Salomon XT-6 Trail", 180, (68, 73), (15, 28), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("On Cloud 5 Running", 150, (55, 60), (25, 45), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Hoka Clifton 9 Running", 145, (54, 58), (30, 50), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Timberland Premium 6-Inch Boot", 198, (78, 84), (20, 38), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Dr. Martens 1460 Boot", 170, (65, 70), (20, 35), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Jordan 1 Retro High OG", 180, (72, 78), (15, 28), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Merrell Moab 3 Hiking Boot", 145, (52, 57), (25, 40), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Birkenstock Arizona Sandal", 110, (40, 44), (40, 65), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Red Wing Iron Ranger Boot", 350, (160, 170), (8, 15), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Saucony Kinvara 14 Running", 110, (38, 42), (30, 55), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Allbirds Tree Dasher 2 Running", 125, (45, 49), (25, 40), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Under Armour HOVR Phantom 3 Running", 140, (52, 57), (20, 35), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Clarks Desert Boot", 130, (48, 52), (25, 48), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
        ("Cole Haan Zerogrand Stitchlite Oxford", 150, (52, 57), (25, 45), "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop"),
    ],
    # ═══ ACCESSORIES (20) ═══
    "Accessories": [
        ("Casio G-Shock GA-2100 Watch", 99, (35, 39), (40, 65), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
        ("Citizen Eco-Drive Promaster Diver Watch", 375, (180, 195), (15, 28), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
        ("Seiko Presage Cocktail Time Automatic", 425, (200, 220), (10, 18), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
        ("Tissot PRX Powermatic 80 Automatic", 695, (380, 400), (6, 12), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
        ("Ray-Ban Aviator Classic Sunglasses", 171, (55, 62), (30, 50), "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
        ("Ray-Ban Wayfarer Classic Sunglasses", 171, (55, 62), (35, 55), "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
        ("Oakley Holbrook Sunglasses", 181, (60, 65), (20, 38), "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
        ("Maui Jim Peahi Sunglasses", 249, (90, 100), (10, 22), "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&h=400&fit=crop"),
        ("Fjallraven Kanken Classic Backpack", 80, (28, 32), (40, 65), "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
        ("North Face Borealis Backpack", 99, (36, 40), (30, 50), "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
        ("Samsonite Freeform 21-Inch Carry-On", 249, (95, 105), (15, 28), "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
        ("Coach Crossbody Bag Leather", 195, (65, 72), (20, 38), "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
        ("Lululemon Everywhere Belt Bag", 42, (13, 15), (60, 110), "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop"),
        ("Bellroy Classic Wallet Leather", 89, (30, 34), (25, 45), "https://images.unsplash.com/photo-1627123424574-724758594e93?w=400&h=400&fit=crop"),
        ("Fossil RFID Bifold Wallet", 55, (16, 19), (40, 65), "https://images.unsplash.com/photo-1627123424574-724758594e93?w=400&h=400&fit=crop"),
        ("YETI Rambler 20oz Tumbler", 35, (12, 14), (60, 100), "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop"),
        ("Apple AirTag 4-Pack Tracker", 99, (38, 42), (50, 75), "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop"),
        ("Michael Kors Bradshaw Gold-Tone Watch", 295, (110, 120), (20, 38), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
        ("Fossil Gen 6 Hybrid Smartwatch", 229, (95, 105), (20, 35), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
        ("Fitbit Versa 4 Smartwatch", 229, (95, 105), (25, 40), "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400&h=400&fit=crop"),
    ],
    # ═══ KITCHEN APPLIANCES (25) ═══
    "Kitchen Appliances": [
        ("KitchenAid Artisan Stand Mixer 5qt", 449, (260, 280), (15, 28), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Ninja Professional Plus Blender 1100W", 90, (38, 42), (35, 55), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Breville Barista Express Espresso Machine", 699, (400, 420), (8, 15), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Keurig K-Supreme Plus Coffee Maker", 190, (80, 88), (25, 45), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Vitamix A3500 Ascent Series Blender", 649, (380, 400), (6, 12), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Instant Pot Duo 7-in-1 6qt", 100, (42, 48), (40, 65), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Cuisinart Chef's Classic 11-Piece Cookware", 230, (100, 110), (12, 22), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Dyson V15 Detect Absolute Vacuum", 749, (460, 490), (8, 15), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("iRobot Roomba j7+ Self-Emptying Vacuum", 799, (420, 450), (10, 18), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Cuisinart TOA-70 Air Fryer Toaster Oven", 230, (100, 110), (20, 35), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Le Creuset Dutch Oven 5.5qt", 410, (220, 240), (8, 16), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Nespresso Vertuo Next Coffee Maker", 200, (85, 92), (25, 40), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("All-Clad D3 Stainless 10-Piece Cookware", 699, (380, 400), (5, 10), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("De'Longhi Magnifica Super Automatic Espresso", 899, (540, 570), (5, 10), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Ninja Creami Ice Cream Maker", 200, (90, 98), (25, 45), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Wusthof Classic 8-Inch Chef's Knife", 170, (72, 78), (15, 28), "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=400&h=400&fit=crop"),
        ("Ooni Koda 12 Gas Pizza Oven", 399, (210, 230), (8, 16), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Black+Decker 12-Cup Programmable Coffeemaker", 40, (12, 15), (50, 75), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Anova Precision Cooker Nano Sous Vide", 130, (52, 57), (18, 30), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Ninja Air Fryer Max XL 5.5qt", 130, (52, 57), (25, 45), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Pyrex 18-Piece Glass Storage Set", 50, (16, 18), (30, 50), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Thermapen ONE Instant-Read Thermometer", 105, (40, 44), (20, 35), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Hamilton Beach FlexBrew Trio Coffee Maker", 120, (48, 53), (25, 40), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Technivorm Moccamaster KBGV Select", 349, (185, 200), (6, 12), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
        ("Breville Smart Oven Air Fryer Pro", 399, (210, 230), (8, 15), "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ],
    # ═══ HOME FURNITURE (25) ═══
    "Home Furniture": [
        ("Herman Miller Aeron Chair Size B", 1645, (1050, 1100), (4, 8), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA MALM 6-Drawer Dresser White", 229, (95, 105), (18, 32), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA KALLAX Shelf Unit 4x4 White", 179, (68, 75), (15, 28), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("West Elm Mid-Century Modern Desk 48\"", 799, (400, 430), (6, 12), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA HEMNES 8-Drawer Dresser", 299, (115, 125), (12, 22), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA BEKANT Sit/Stand Electric Desk", 499, (220, 240), (10, 18), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA ALEX Drawer Unit on Casters", 219, (80, 88), (18, 32), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("Ashley Furniture Realyn Dining Table", 699, (340, 370), (5, 10), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA POANG Armchair", 129, (45, 50), (25, 40), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA LACK Coffee Table", 30, (8, 10), (40, 65), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA BILLY Bookcase White", 79, (25, 28), (35, 55), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA HEMNES Nightstand White Stain", 99, (35, 39), (25, 42), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA ALEX Desk White", 229, (85, 92), (15, 28), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA KALLAX Shelf Unit 2x4 White", 109, (38, 42), (25, 40), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA NORDLI 6-Drawer Dresser White", 299, (115, 125), (10, 20), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("Pottery Barn Comfort Roll Arm Sofa", 2299, (1200, 1280), (3, 6), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("CB2 Avec Sofa 82-Inch", 1599, (850, 900), (4, 8), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("West Elm Lucas Swivel Chair", 699, (340, 370), (5, 10), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("Wayfair Andover Mills Queen Platform Bed", 199, (75, 82), (12, 22), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("Article Sven Charme Tan Sofa", 1799, (1000, 1050), (4, 7), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA STOCKHOLM Walnut Veneer Table", 599, (250, 270), (6, 12), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("Restoration Hardware Cloud Bed King", 3195, (2000, 2100), (2, 4), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("CB2 Drona Round Marble Dining Table", 899, (480, 510), (4, 8), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA MALM Bed Frame Queen", 249, (95, 105), (15, 28), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
        ("IKEA KLEPPSTAD Wardrobe with 2 Doors", 149, (55, 60), (18, 30), "https://images.unsplash.com/photo-1592078615290-033ee584e267?w=400&h=400&fit=crop"),
    ],
    # ═══ HOME DECOR & BEDDING (20) ═══
    "Home Decor & Bedding": [
        ("Casper Original Hybrid Mattress Queen", 1595, (850, 900), (8, 16), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Brooklinen Luxe Core Sheet Set Queen", 169, (55, 62), (25, 45), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Parachute Home Cloud Cotton Robe", 120, (38, 42), (20, 35), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Ruggable Washable Rug 5x7", 449, (180, 195), (12, 22), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("IKEA BERGPALM Duvet Cover Set Queen", 30, (8, 10), (40, 65), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("West Elm Chunky Wool Throw 50x60", 199, (68, 75), (12, 22), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Pottery Barn Belgian Flax Linen Duvet Queen", 259, (95, 105), (14, 25), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Frette Linen Bath Towel Set 4-Piece", 290, (115, 125), (8, 14), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Threshold Studio McGee Throw Pillow 18x18", 20, (5, 7), (55, 85), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Boll & Branch Signature Sheet Set Queen", 239, (85, 92), (12, 22), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("West Elm Stonewashed Velvet Duvet Cover", 249, (90, 98), (10, 18), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Kate Spade Melrose Place 3-Wick Candle", 40, (12, 14), (30, 45), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Pottery Barn Shag Tonal Rug 5x8", 499, (210, 230), (6, 12), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Serena & Coastal Stripe Duvet Cover Queen", 348, (135, 145), (6, 12), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("IKEA STOCKHOLM Cushion Cover 20x20", 25, (7, 9), (30, 50), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Crate & Barrel Autumn Throw Blanket", 70, (22, 25), (20, 35), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Opalhouse Ceramic Decorative Vase 11\"", 30, (8, 10), (35, 55), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Threshold Woven Outdoor Lumbar Pillow", 15, (4, 5), (60, 110), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Restoration RH Belgian Linen Duvet Queen", 349, (140, 152), (8, 15), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
        ("Amazon Basics Microfiber Sheet Set Queen", 22, (6, 8), (80, 130), "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&h=400&fit=crop"),
    ],
    # ═══ SPORTS & FITNESS (25) ═══
    "Sports & Fitness": [
        ("Peloton Bike+ Indoor Cycling", 2495, (1600, 1680), (3, 6), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Bowflex SelectTech 552 Adjustable Dumbbells", 549, (280, 300), (8, 14), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Theragun Pro Massage Gun", 449, (230, 250), (12, 20), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Manduka PRO Yoga Mat 6mm", 140, (48, 53), (18, 30), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("NordicTrack Commercial 1750 Treadmill", 1799, (1050, 1100), (4, 8), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Concept2 RowErg Indoor Rower", 990, (580, 620), (6, 10), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("TRX All-in-One Suspension Trainer", 170, (60, 66), (20, 35), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Garmin Forerunner 965 GPS Running Watch", 599, (380, 400), (8, 14), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Lululemon Align High-Rise Pant 25\"", 98, (32, 36), (40, 65), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Rogue Fitness Ohio Barbell 20kg", 395, (200, 220), (6, 10), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Callaway Paradym X Driver Golf", 599, (330, 350), (4, 8), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Osprey Atmos AG 65 Backpack", 300, (120, 130), (8, 15), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("REI Co-op Half Dome SL 2 Plus Tent", 229, (95, 105), (10, 18), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("YETI Hopper Flip 12 Soft Cooler", 250, (100, 110), (12, 20), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Garmin Edge 540 Solar GPS Cycling", 450, (240, 260), (6, 12), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Hyperice Hypervolt 2 Pro Massage Gun", 399, (200, 220), (10, 18), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Black Diamond Spot 400 Headlamp", 50, (16, 18), (25, 40), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Hydro Flask 32oz Wide Mouth", 45, (14, 16), (55, 85), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Garmin inReach Mini 2 Satellite", 400, (210, 225), (6, 10), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Scarpa Zodiac Plus GTX Hiking Boot", 349, (170, 182), (5, 10), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Salomon X Ultra 4 GTX Hiking Shoes", 175, (65, 70), (15, 28), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("The North Face Apex Bionic 3 Jacket", 199, (72, 78), (12, 22), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Wahoo KICKR Smart Trainer", 1299, (800, 840), (4, 8), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Patagonia Black Hole Duffel 55L", 149, (52, 57), (12, 22), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
        ("Mountain Hardwear Stretch Ozonic Rain Jacket", 225, (90, 98), (8, 16), "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ],
    # ═══ BEAUTY & PERSONAL CARE (20) ═══
    "Beauty & Personal Care": [
        ("Dyson Airwrap Multi-Styler Complete", 599, (380, 400), (8, 15), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Olaplex No. 3 Hair Perfector", 30, (8, 10), (55, 85), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("La Mer Creme de la Mer 2oz", 380, (190, 205), (5, 10), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Drunk Elephant Protini Polypeptide Cream", 68, (22, 25), (22, 38), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("CeraVe Moisturizing Cream 16oz", 19, (5, 7), (80, 130), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("The Ordinary Hyaluronic Acid 2% + B5", 10, (2.5, 3.5), (100, 160), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Charlotte Tilbury Pillow Talk Lipstick", 36, (10, 12), (30, 50), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Paula's Choice 2% BHA Liquid Exfoliant", 34, (10, 12), (28, 45), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("SK-II Facial Treatment Essence", 235, (110, 120), (6, 12), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Estee Lauder Advanced Night Repair Serum 1.7oz", 82, (30, 34), (20, 35), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Lancome La Vie Est Belle EDP 3.3oz", 130, (50, 56), (12, 22), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Bioderma Sensibio H2O Micellar Water 500ml", 18, (5, 7), (55, 85), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Tatcha The Dewy Skin Cream", 69, (24, 27), (15, 28), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("T3 AireLuxe Hair Dryer", 235, (105, 115), (8, 16), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Clinique Moisture Surge 100H", 52, (18, 21), (25, 40), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Tom Ford Noir Extreme EDP 3.3oz", 145, (60, 65), (8, 16), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("First Aid Beauty Ultra Repair Cream 6oz", 38, (12, 14), (30, 48), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Shiseido Ultimate Sun Protector SPF 60", 48, (15, 17), (35, 55), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Revlon One-Step Hair Dryer Volumizer", 42, (12, 14), (40, 65), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
        ("Moroccanoil Treatment Original", 48, (16, 18), (25, 40), "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ],
    # ═══ ELECTRONICS & GADGETS (35) ═══
    "Electronics": [
        ("Logitech MX Master 3S Mouse", 99, (40, 44), (35, 58), "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400&h=400&fit=crop"),
        ("Logitech MX Keys S Keyboard", 109, (45, 49), (28, 45), "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
        ("Samsung T7 2TB Portable SSD", 189, (95, 105), (30, 50), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("WD My Passport 5TB External HDD", 149, (70, 78), (22, 35), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Canon EOS R6 Mark II Camera Body", 2499, (1650, 1720), (4, 8), "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
        ("Sony a7 IV Mirrorless Camera Body", 2498, (1650, 1720), (4, 8), "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
        ("GoPro HERO12 Black", 399, (220, 240), (20, 35), "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
        ("DJI Mini 4 Pro Drone", 999, (620, 660), (6, 10), "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop"),
        ("JBL Flip 6 Portable Speaker", 129, (48, 53), (40, 65), "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
        ("JBL Charge 5 Portable Speaker", 179, (70, 76), (35, 55), "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
        ("Sonos Era 300 Spatial Audio Speaker", 449, (250, 270), (10, 18), "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
        ("Amazon Fire TV Stick 4K Max", 59, (18, 21), (65, 105), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("NVIDIA Shield TV Pro", 199, (95, 105), (12, 22), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Apple TV 4K 128GB", 149, (88, 95), (25, 42), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Anker PowerCore III 10000mAh Wireless", 36, (10, 12), (60, 95), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Anker 737 Power Bank 24000mAh 140W", 109, (45, 50), (25, 42), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Bose SoundLink Flex Speaker", 149, (55, 60), (28, 45), "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
        ("Ring Video Doorbell Pro 2", 249, (115, 125), (15, 28), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Samsung 990 Pro 1TB NVMe SSD", 119, (58, 65), (30, 48), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("WD Black SN850X 2TB NVMe SSD", 159, (80, 88), (22, 38), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Elgato Stream Deck MK.2", 149, (65, 70), (15, 28), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Razer DeathAdder V3 Gaming Mouse", 99, (40, 44), (25, 38), "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400&h=400&fit=crop"),
        ("Corsair K100 RGB Mechanical Keyboard", 229, (100, 110), (10, 18), "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
        ("TP-Link Deco XE75 Wi-Fi 6E Mesh 3-Pack", 249, (110, 120), (12, 22), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("DJI Air 3 Drone", 1099, (720, 760), (4, 8), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Kindle Paperwhite 2024 16GB", 159, (75, 82), (28, 45), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Dyson V12 Detect Slim Vacuum", 649, (380, 400), (6, 12), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Google Nest Hub Max Smart Display", 229, (115, 125), (12, 22), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Roku Streaming Stick 4K+", 49, (15, 18), (55, 85), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Chromecast with Google TV 4K", 49, (18, 21), (50, 80), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Logitech C920s HD Pro Webcam", 79, (28, 32), (35, 55), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("TP-Link Kasa Smart Plug 4-Pack", 30, (8, 10), (55, 85), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("Anker Nano II 65W USB-C GaN Charger", 36, (10, 12), (50, 75), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("TP-Link Archer AXE75 Wi-Fi 6E Router", 199, (90, 100), (12, 22), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
        ("BenQ ScreenBar Halo Monitor Light", 179, (78, 85), (10, 18), "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ],
    # ═══ TOYS & GAMES (20) ═══
    "Toys & Games": [
        ("LEGO Star Wars Millennium Falcon 75375", 169, (72, 78), (18, 32), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Nintendo Switch OLED Model 64GB", 349, (210, 225), (15, 28), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Sony PlayStation 5 Console", 499, (350, 370), (8, 15), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Xbox Series X Console 1TB", 499, (350, 370), (10, 18), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("LEGO Technic Lamborghini Sian 3696pc", 479, (250, 270), (5, 10), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Monopoly Classic Board Game", 20, (5, 7), (70, 110), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Jenga Classic Block Stacking Game", 15, (4, 5), (80, 130), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Scrabble Deluxe Edition Board Game", 50, (18, 21), (18, 32), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("DJI Mini 3 Pro Drone", 759, (440, 470), (4, 8), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("LEGO City Space Rocket Launch Center", 129, (52, 57), (15, 28), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("PS5 DualSense Wireless Controller", 69, (28, 32), (35, 55), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Risk World Domination Board Game", 30, (8, 10), (40, 65), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("LEGO Architecture Eiffel Tower 10009pc", 629, (380, 400), (3, 6), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Connect 4 Classic Strategy Game", 15, (4, 5), (70, 110), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("LEGO Harry Potter Hogwarts Castle 6020pc", 469, (280, 300), (5, 10), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Catan Strategy Board Game", 44, (14, 17), (35, 55), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("LEGO Creator Expert Roller Coaster 4124pc", 399, (220, 240), (4, 8), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("LEGO Super Mario Starter Course 231pc", 59, (22, 25), (25, 40), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Codenames Word Association Game", 20, (5, 7), (40, 65), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
        ("Apples to Apples Party Card Game", 20, (5, 7), (55, 85), "https://images.unsplash.com/photo-1587654780291-39c9404d7dd0?w=400&h=400&fit=crop"),
    ],
}

def main():
    conn = psycopg2.connect(CONN)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM products")
    existing = cur.fetchone()[0]
    print(f"Existing products: {existing}")

    # Build flat list of all products
    # Tuple format: (name, base_price, cost_price_range, stock_range, image_url)
    # SKU and description are auto-generated from name and category
    all_products = []
    cat_counters = {}
    for cat, products in CATEGORIES.items():
        cat_counters[cat] = 0
        for i, p in enumerate(products):
            name, bp, cpr, sr, img = p
            cat_counters[cat] += 1
            # Use unique 3-letter prefix per category
            prefix_map = {
                'Laptops': 'LAP', 'Smartphones': 'PHN', 'Headphones': 'AUD',
                'TVs & Monitors': 'TVM', 'Tablets': 'TAB', 'Smartwatches': 'WAT',
                'Shirts & Tops': 'SHT', 'Shoes': 'SHO', 'Accessories': 'ACC',
                'Kitchen Appliances': 'KIT', 'Home Furniture': 'FRN',
                'Home Decor & Bedding': 'DEC', 'Sports & Fitness': 'SPT',
                'Beauty & Personal Care': 'BTY', 'Electronics': 'ELC',
                'Toys & Games': 'TOY',
            }
            sku_prefix = prefix_map.get(cat, cat[:3].upper())
            sku = f"{sku_prefix}-{cat_counters[cat]:03d}"
            desc = f"{name} - premium {cat.lower().replace('&', 'and')} product"
            all_products.append((cat, name, sku, desc, bp, cpr, sr, img))

    total_needed = len(all_products)
    print(f"Catalog products defined: {total_needed}")

    # Ensure we have enough product IDs
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM products")
    max_id = cur.fetchone()[0]
    if max_id < total_needed:
        for i in range(max_id + 1, total_needed + 1):
            cur.execute(
                "INSERT INTO products (id, name, sku, description, category, base_price, current_price, cost_price, stock_quantity, revenue, status, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (i, f"Temp {i}", f"TMP-{i}", "Temp", "Temp", 0, 0, 0, 0, 0, "active", "")
            )
        print(f"Created {total_needed - max_id} temporary product slots")

    # Update each product
    updated = 0
    for idx, (cat, name, sku, desc, base_price, cost_price_range, stock_range, img) in enumerate(all_products):
        pid = idx + 1
        random.seed(pid)
        cost_price = round(random.uniform(*cost_price_range), 2)
        stock = random.randint(*stock_range)
        # discount is implicit: base_price vs current_price
        discount_pct = random.uniform(0.02, 0.12)
        curr_price = round(base_price * (1 - discount_pct), 2)
        est_sales = random.randint(15, 200)
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

    # Delete products beyond our catalog
    cur.execute("DELETE FROM products WHERE id > %s", (total_needed,))
    deleted = cur.rowcount
    if deleted:
        print(f"Deleted {deleted} excess products")

    # Sync pricing_history base prices
    cur.execute("""
        UPDATE pricing_history ph
        SET old_price = p.base_price
        FROM products p
        WHERE ph.product_id = p.id AND ph.old_price != p.base_price
    """)
    if cur.rowcount:
        print(f"Synced {cur.rowcount} pricing_history records")

    conn.commit()

    # Final verification
    cur.execute("SELECT COUNT(*) FROM products")
    final = cur.fetchone()[0]
    cur.execute("SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY COUNT(*) DESC")
    cats = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM sales")
    sales = cur.fetchone()[0]

    print(f"\n=== FINAL CATALOG ===")
    print(f"Total products: {final}")
    print(f"Categories ({len(cats)}):")
    for c, n in cats:
        print(f"  {c}: {n}")
    print(f"Sales rows preserved: {sales}")

    # Verify search works for key terms
    for term in ['laptop', 'iPhone', 'Samsung', 'shirt', 'headphone', 'Nike', 'Dell', 'Sony']:
        cur.execute("SELECT COUNT(*) FROM products WHERE name ILIKE %s OR description ILIKE %s OR category ILIKE %s",
                    (f"%{term}%", f"%{term}%", f"%{term}%"))
        count = cur.fetchone()[0]
        print(f"Search '{term}': {count} products found")

    conn.close()

if __name__ == "__main__":
    main()
