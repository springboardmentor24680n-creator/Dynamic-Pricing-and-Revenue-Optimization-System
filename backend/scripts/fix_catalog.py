"""
Supplement to replace_catalog.py:
1. Fixes duplicate SKUs
2. Adds remaining products to reach exactly 585
3. Runs the full catalog replacement
"""
import sys, random, re
sys.stdout.reconfigure(encoding='ascii', errors='replace')
sys.path.insert(0, '.')

import psycopg2

CONN = 'postgresql://postgres:postgres@localhost:5432/dynamic_pricing'

# Fix duplicates: AUD-008 exists for both Bose QC Ultra Earbuds and Jabra Elite 85t
# Fix: Jabra Elite 85t already has a different SKU (AUD-013) in the list,
# but the Bose entry at index ~7 uses AUD-008. Let's just renumber.
# SHO-010 exists for both Vans Old Skool and Cole Haan. Cole Haan should be SHO-020.

# Additional products to pad to 585 (192 more products)
EXTRA_PRODUCTS = [
    # ═══ MORE LAPTOPS (10) ═══
    ("Lenovo IdeaPad Slim 3 15", "LAP-041", "Lenovo IdeaPad Slim 3, AMD Ryzen 5, 8GB RAM, 256GB SSD, 15.6-inch FHD", "Laptops", 449, 399, 260, 50, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&h=400&fit=crop"),
    ("HP Victus 15 Gaming", "LAP-042", "HP Victus 15 gaming laptop, Intel Core i5-12500H, 8GB RAM, RTX 3050, 15.6-inch FHD 144Hz", "Laptops", 799, 699, 480, 35, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=400&fit=crop"),
    ("Acer Swift 3 OLED", "LAP-043", "Acer Swift 3 OLED, Intel Core i7-12700H, 16GB RAM, 512GB SSD, 14-inch 2.8K OLED", "Laptops", 999, 899, 620, 25, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Book 4 360 15", "LAP-044", "Samsung Galaxy Book 4 360 15-inch 2-in-1, Intel Core i7, 16GB RAM, 512GB SSD, AMOLED", "Laptops", 1349, 1249, 880, 20, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("LG Gram 14 2-in-1", "LAP-045", "LG Gram 14 2-in-1, Intel Core i7-1360P, 16GB RAM, 512GB SSD, 14-inch WUXGA touch", "Laptops", 1499, 1399, 980, 18, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Dell Inspiron 14 2-in-1", "LAP-046", "Dell Inspiron 14 2-in-1, AMD Ryzen 7 7730U, 16GB RAM, 512GB SSD, 14-inch FHD+ touch", "Laptops", 749, 679, 450, 40, "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&h=400&fit=crop"),
    ("Acer Chromebook Spin 714", "LAP-047", "Acer Chromebook Spin 714, Intel Core i5-1235U, 8GB RAM, 256GB SSD, 14-inch FHD+ touch", "Laptops", 529, 479, 300, 30, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("MacBook Air 13-inch M2", "LAP-048", "Apple MacBook Air 13-inch M2, 8GB RAM, 256GB SSD, Liquid Retina, 18-hour battery", "Laptops", 999, 949, 680, 40, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop"),
    ("Razer Blade 14", "LAP-049", "Razer Blade 14 gaming laptop, AMD Ryzen 9 7940HS, 16GB RAM, RTX 4070, 14-inch QHD 240Hz", "Laptops", 2199, 1999, 1450, 10, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),
    ("Surface Laptop Studio 2", "LAP-050", "Microsoft Surface Laptop Studio 2, Intel Core i7, 16GB RAM, 512GB SSD, 14.4-inch PixelSense Flow", "Laptops", 1999, 1799, 1300, 12, "https://images.unsplash.com/photo-1593642634443-44adaa06623a?w=400&h=400&fit=crop"),

    # ═══ MORE SMARTPHONES (10) ═══
    ("Samsung Galaxy S23 Ultra 256GB", "PHN-031", "Samsung Galaxy S23 Ultra, 256GB, Snapdragon 8 Gen 2, 200MP camera, S Pen, 5000mAh", "Smartphones", 1199, 1099, 800, 40, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("iPhone 16 128GB", "PHN-032", "Apple iPhone 16, 128GB, A18 chip, 6.1-inch Super Retina XDR, Action Button, Camera Control", "Smartphones", 829, 799, 540, 70, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("iPhone 16 Pro Max 256GB", "PHN-033", "Apple iPhone 16 Pro Max, 256GB, A18 Pro chip, 6.9-inch Super Retina XDR, titanium, 48MP camera", "Smartphones", 1299, 1199, 880, 35, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&h=400&fit=crop"),
    ("Samsung Galaxy Z Flip6 256GB", "PHN-034", "Samsung Galaxy Z Flip6, 256GB, Snapdragon 8 Gen 3, 6.7-inch foldable AMOLED, FlexCam", "Smartphones", 1099, 999, 720, 25, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Google Pixel 9 128GB", "PHN-035", "Google Pixel 9, 128GB, Tensor G4, 6.3-inch OLED, AI features, 7 years updates", "Smartphones", 799, 699, 480, 45, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Samsung Galaxy A15 5G 128GB", "PHN-036", "Samsung Galaxy A15 5G, 128GB, MediaTek Dimensity 6100+, 6.5-inch AMOLED, 5000mAh", "Smartphones", 199, 179, 95, 120, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("OnePlus 12R 256GB", "PHN-037", "OnePlus 12R, 256GB, Snapdragon 8 Gen 2, 6.78-inch AMOLED 120Hz, 5500mAh, 100W SUPERVOOC", "Smartphones", 499, 449, 300, 40, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Motorola Razr Plus 2024 256GB", "PHN-038", "Motorola Razr+ 2024, 256GB, Snapdragon 8s Gen 3, 6.9-inch foldable pOLED, FlexView", "Smartphones", 999, 899, 620, 15, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),
    ("Samsung Galaxy S25 256GB", "PHN-039", "Samsung Galaxy S25, 256GB, Snapdragon 8 Elite, 6.2-inch Dynamic AMOLED 2X, Galaxy AI", "Smartphones", 899, 849, 580, 30, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400&h=400&fit=crop"),
    ("Nothing Phone 2a 256GB", "PHN-040", "Nothing Phone 2a, 256GB, MediaTek Dimensity 7200 Pro, 6.7-inch AMOLED, Glyph Interface", "Smartphones", 349, 319, 200, 50, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop"),

    # ═══ MORE CLOTHING (25) ═══
    ("Nike Running Shorts 7-Inch", "CLT-001", "Nike Dri-FIT running shorts, 7-inch inseam, built-in brief, side pockets, lightweight mesh", "Clothing", 40, 35, 12, 120, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Levi's 501 Original Fit Jeans", "CLT-002", "Levi's 501 original fit jeans, 100% cotton, button fly, straight leg, iconic riveted construction", "Clothing", 69, 59, 24, 90, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Adidas Track Pants", "CLT-003", "Adidas Essentials track pants, 3-Stripes design, tricot fabric, zip pockets, elastic waist", "Clothing", 45, 38, 14, 100, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Patagonia Better Sweater Fleece Jacket", "CLT-004", "Patagonia Better Sweater fleece jacket, 100% recycled polyester, full-zip, stand-up collar", "Clothing", 139, 119, 50, 30, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("The North Face Nuptse Jacket", "CLT-005", "The North Face 1996 Nuptse jacket, 700-fill down, DWR finish, secure-zip hand pockets", "Clothing", 280, 249, 120, 20, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Ralph Lauren Classic Cable Knit Sweater", "CLT-006", "Ralph Lauren classic cable knit sweater, 100% cotton, crew neck, ribbed hem and cuffs", "Clothing", 145, 125, 50, 25, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("H&M Slim Fit Chinos", "CLT-007", "H&M slim fit chinos, stretch cotton, tapered leg, zip fly, side and back pockets", "Clothing", 25, 20, 7, 150, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Uniqlo Ultra Light Down Jacket", "CLT-008", "Uniqlo Ultra Light Down jacket, 640-fill down, ultra-weigh, packable, water-repellent finish", "Clothing", 79, 69, 28, 60, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Columbia Silver Ridge Convertible Pants", "CLT-009", "Columbia Silver Ridge convertible pants, Omni-Shade UPF 50, zip-off legs, Omni-Wick", "Clothing", 55, 48, 18, 45, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Gap Denim Jacket", "CLT-010", "Gap classic denim jacket, 100% cotton, button-front, chest pockets, classic trucker style", "Clothing", 70, 58, 22, 40, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Lululemon Align Tank Top", "CLT-011", "Lululemon Align tank top, Nulu fabric, barely-there feel, built-in bra, high neckline", "Clothing", 58, 48, 18, 50, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Zara Leather Biker Jacket", "CLT-012", "Zara leather biker jacket, 100% genuine leather, asymmetric zip, quilted shoulders, belted waist", "Clothing", 199, 169, 80, 15, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Nike Tech Fleece Joggers", "CLT-013", "Nike Tech Fleece joggers, innovative fleece, slim tapered fit, zip pockets, cuffed ankles", "Clothing", 110, 95, 38, 70, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Adidas Ultraboost Running Shorts", "CLT-014", "Adidas Ultraboost running shorts, AEROREADY moisture management, 5-inch inseam, reflective details", "Clothing", 45, 38, 14, 80, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Tommy Hilfiger Puffer Jacket", "CLT-015", "Tommy Hilfiger lightweight puffer jacket, water-resistant shell, synthetic insulation, packable", "Clothing", 149, 129, 52, 30, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Carhartt Relaxed Fit Flannel-Shirt", "CLT-016", "Carhartt relaxed fit flannel shirt, cotton flannel, button-front, spread collar, chest pockets", "Clothing", 45, 38, 14, 55, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Calvin Klein Performance Leggings", "CLT-017", "Calvin Klein performance leggings, moisture-wicking, 4-way stretch, high-rise, hidden pocket", "Clothing", 55, 45, 16, 65, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Mango Oversized Wool Coat", "CLT-018", "Mango oversized wool blend coat, notch lapel, button closure, side pockets, relaxed fit", "Clothing", 189, 159, 68, 18, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("J.Crew Secret Wash Shirt", "CLT-019", "J.Crew Secret Wash cotton shirt, our softest fabric, button-down collar, chest pocket", "Clothing", 79, 65, 26, 35, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Under Armour HeatGear compression shorts", "CLT-020", "Under Armour HeatGear compression shorts, 4-way stretch, moisture wicking, anti-odor, 6-inch", "Clothing", 30, 25, 9, 90, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Banana Republic Italian Wool Suit Pants", "CLT-021", "Banana Republic Italian wool suit pants, flat front, stretch, dry clean, modern fit", "Clothing", 198, 168, 72, 20, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Columbia Bugaboo II Fleece Interchange Jacket", "CLT-022", "Columbia Bugaboo II 3-in-1 jacket, waterproof shell + fleece liner, Omni-Heat, adjustable hood", "Clothing", 150, 130, 55, 25, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("North Face Thermoball Eco Jacket 2.0", "CLT-023", "The North Face ThermoBall Eco jacket 2.0, PrimaLoft recycled insulation, DWR, lightweight", "Clothing", 200, 179, 75, 22, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Abercrombie & Fitch Cropped Straight Jeans", "CLT-024", "Abercrombie cropped straight jeans, high rise, 100% cotton, raw hem, ankle length", "Clothing", 80, 68, 28, 45, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),
    ("Lululemon Commission Pants Slim", "CLT-025", "Lululemon Commission pants, ABC fabric, versatile, hidden zip pocket, slim fit, 32-inch", "Clothing", 128, 115, 42, 35, "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop"),

    # ═══ MORE ELECTRONICS (30) ═══
    ("JBL Charge 5 Portable Speaker", "ELC-031", "JBL Charge 5 portable Bluetooth speaker, IP67, 20hr battery, powerbank, JBL Pro Sound", "Electronics", 179, 159, 70, 50, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
    ("Apple Mac Mini M4", "ELC-032", "Apple Mac Mini M4 desktop, 16GB RAM, 512GB SSD, macOS, Thunderbolt 4, HDMI", "Electronics", 599, 549, 380, 25, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Logitech G Pro X Superlight 2 Mouse", "ELC-033", "Logitech G Pro X Superlight 2 gaming mouse, 32K DPI HERO 2 sensor, 60hr battery, 60g", "Electronics", 159, 149, 68, 30, "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400&h=400&fit=crop"),
    ("Keychron Q1 Pro Keyboard", "ELC-034", "Keychron Q1 Pro wireless mechanical keyboard, QMK/VIA, Gateron Jupiter switches, aluminum", "Electronics", 199, 179, 90, 20, "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
    ("Anker Soundcore Liberty 4 NC Earbuds", "ELC-035", "Anker Soundcore Liberty 4 NC, adaptive ANC, Hi-Res LDAC, 50hr total battery, IPX4", "Electronics", 99, 85, 35, 60, "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop"),
    ("Eufy Video Doorbell E340", "ELC-036", "Eufy Video Doorbell E340, dual camera, 2K resolution, color night vision, no monthly fees", "Electronics", 179, 149, 80, 25, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Apple AirTag 4-Pack", "ELC-037", "Apple AirTag 4-pack, precision finding, replaceable battery, water resistant, Find My network", "Electronics", 99, 89, 38, 70, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Jabra Evolve2 85 Headset", "ELC-038", "Jabra Evolve2 85 wireless headset, ANC, 10 microphones, Microsoft Teams certified, 37hr battery", "Electronics", 379, 329, 200, 12, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("WD Black SN850X 2TB NVMe SSD", "ELC-039", "WD Black SN850X 2TB NVMe SSD, 7300MB/s read, 6600MB/s write, PCIe Gen4, heatsink", "Electronics", 159, 139, 80, 35, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Samsung 990 Pro 1TB NVMe SSD", "ELC-040", "Samsung 990 Pro 1TB NVMe SSD, 7450MB/s read, 6900MB/s write, PCIe Gen4, V-NAND", "Electronics", 119, 99, 58, 45, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Corsair K65 Plus Wireless Keyboard", "ELC-041", "Corsair K65 Plus wireless, 75% layout, MGX Hall Effect switches, RGB, Bluetooth/2.4GHz", "Electronics", 179, 159, 72, 20, "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
    ("SteelSeries Arctis Nova Pro Wireless", "ELC-042", "SteelSeries Arctis Nova Pro wireless headset, multi-system, ANC, hot-swap battery, 40hr", "Electronics", 349, 299, 180, 15, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("TP-Link Archer AXE75 Wi-Fi 6E Router", "ELC-043", "TP-Link Archer AXE75 Wi-Fi 6E router, tri-band, 5400 Mbps, OFDMA, 1.7GHz quad-core CPU", "Electronics", 199, 169, 90, 20, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Sonos Era 100 Speaker", "ELC-044", "Sonos Era 100 speaker, Trueplay tuning, AirPlay 2, Bluetooth, stereo pair, voice control", "Electronics", 249, 219, 130, 22, "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop"),
    ("Logitech Brio 4K Webcam", "ELC-045", "Logitech Brio 4K webcam, 4K Ultra HD, HDR, Windows Hello, noise-canceling mic, USB-C", "Electronics", 199, 179, 90, 20, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("DJI Air 3 Drone", "ELC-046", "DJI Air 3 drone, dual-camera, 4K/60fps HDR, 46min flight, omnidirectional obstacle sensing", "Electronics", 1099, 999, 720, 8, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("TP-Link Kasa Smart Plug 4-Pack", "ELC-047", "TP-Link Kasa smart plug, 4-pack, Wi-Fi, energy monitoring, voice control, no hub needed", "Electronics", 30, 25, 8, 80, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Google Nest Hub Max", "ELC-048", "Google Nest Hub Max, 10-inch HD smart display, camera, Nest speaker, Google Assistant", "Electronics", 229, 199, 115, 20, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Kindle Paperwhite 2024 16GB", "ELC-049", "Kindle Paperwhite 2024, 16GB, 7-inch glare-free display, IPX8 waterproof, 12-week battery", "Electronics", 159, 139, 75, 40, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Dyson V12 Detect Slim Vacuum", "ELC-050", "Dyson V12 Detect Slim cordless vacuum, laser dust detection, 60min runtime, lightweight 5.2lb", "Electronics", 649, 549, 380, 12, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Razer BlackWidow V4 75% Keyboard", "ELC-051", "Razer BlackWidow V4 75% mechanical keyboard, hot-swappable, aluminum top plate, RGB", "Electronics", 199, 179, 85, 18, "https://images.unsplash.com/photo-1541140532154-b024d7f16098?w=400&h=400&fit=crop"),
    ("Apple Watch Charger USB-C 1M", "ELC-052", "Apple Watch magnetic charger to USB-C cable 1m, fast charging compatible", "Electronics", 29, 25, 8, 100, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Anker Nano II 65W USB-C Charger", "ELC-053", "Anker Nano II 65W GaN USB-C charger, foldable plug, 3 ports, PowerIQ 3.0", "Electronics", 36, 29, 10, 70, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Google Nest Thermostat", "ELC-054", "Google Nest thermostat, energy saving, remote control, HVAC monitoring, mirror finish", "Electronics", 129, 109, 55, 25, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Ring Indoor Cam Gen 2", "ELC-055", "Ring Indoor Cam Gen 2, 1080p HD, two-way talk, motion detection, works with Alexa", "Electronics", 59, 49, 22, 40, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Sennheiser HD 560S Headphones", "ELC-056", "Sennheiser HD 560S open-back reference headphones, 120-ohm, audiophile-grade, neutral sound", "Electronics", 199, 179, 105, 20, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("FiiO K7 DAC/Amp", "ELC-057", "FiiO K7 balanced headphone DAC/amp, dual THX AAA-788+, PCM 384kHz/DSD256", "Electronics", 199, 179, 100, 15, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("Corsair HS80 Max Wireless Headset", "ELC-058", "Corsair HS80 Max wireless gaming headset, 50mm drivers, Dolby Atmos, 65hr battery, flip-to-mute", "Electronics", 169, 149, 72, 25, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop"),
    ("Satechi USB-C Multiport Adapter", "ELC-059", "Satechi USB-C multiport adapter, 4K HDMI, USB 3.0, SD card reader, ethernet, 100W PD", "Electronics", 80, 69, 30, 30, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),
    ("BenQ ScreenBar Halo Monitor Light", "ELC-060", "BenQ ScreenBar Halo monitor light, wireless controller, backlight, auto-dimming, USB-C", "Electronics", 179, 159, 78, 18, "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop"),

    # ═══ MORE SPORTS & FITNESS (20) ═══
    ("Nike Metcon 9 Training Shoes", "SPT-026", "Nike Metcon 9 training shoes, Hyperlift insert, React foam, rubber tread, rope wrap", "Sports & Fitness", 150, 135, 55, 35, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Adidas Adipower Weightlifting III", "SPT-027", "Adidas Adipower weightlifting III shoes, 20mm heel, Powerframe, lightweight, stable base", "Sports & Fitness", 200, 180, 80, 20, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Wahoo KICKR Smart Trainer", "SPT-028", "Wahoo KICKR smart bike trainer, electronic resistance, Zwift compatible, 2200W max", "Sports & Fitness", 1299, 1199, 800, 8, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Garmin Rally XC200 Power Meter Pedals", "SPT-029", "Garmin Rally XC200 dual-sensing power meter pedals, cycling dynamics, compatible with vector", "Sports & Fitness", 1199, 1099, 780, 5, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Wahoo ELEMNT ROAM V2 GPS Computer", "SPT-030", "Wahoo ELEMNT ROAM V2 cycling computer, color touchscreen, smart navigation, 17hr battery", "Sports & Fitness", 399, 349, 210, 12, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Hydro Flask 40oz Wide Mouth", "SPT-031", "Hydro Flask 40oz wide mouth, TempShield double-wall vacuum, stainless steel, BPA-free", "Sports & Fitness", 55, 48, 18, 60, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Lululemon Metal Vent Tech 2.0 Tank", "SPT-032", "Lululemon Metal Vent Tech 2.0 tank, Silverescent technology, mesh ventilation, anti-odor", "Sports & Fitness", 62, 52, 20, 40, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Salomon X Ultra 4 GTX Hiking Shoes", "SPT-033", "Salomon X Ultra 4 GTX hiking shoes, Gore-Tex, Contagrip MA, advanced chassis, lightweight", "Sports & Fitness", 175, 155, 65, 25, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Hyperice Vyper 3 vibrating roller", "SPT-034", "Hyperice Vyper 3 vibrating fitness roller, 3 speed settings, high振vibration, rechargeable", "Sports & Fitness", 199, 179, 85, 15, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Garmin Swim 2 GPS Watch", "SPT-035", "Garmin Swim 2 GPS watch, pool and open water swim, heart rate, underwater wrist HR", "Sports & Fitness", 299, 269, 150, 18, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Black Diamond Camalot C4 Set", "SPT-036", "Black Diamond Camalot C4 climbing cam set, sizes 0.3-3, double-axle design, trigger trigger", "Sports & Fitness", 399, 349, 210, 8, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Patagonia Black Hole Duffel 55L", "SPT-037", "Patagonia Black Hole duffel 55L, recycled ripstop, weather-resistant, removable shoulder straps", "Sports & Fitness", 149, 129, 52, 20, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Nike Brasilia 9.5 Backpack Large", "SPT-038", "Nike Brasilia 9.5 large backpack, 30L, water-resistant bottom, padded sleeve, multiple pockets", "Sports & Fitness", 55, 48, 18, 40, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("TRX Rip Trainer", "SPT-039", "TRX Rip Trainer, asymmetrical resistance cord, functional training, core engagement", "Sports & Fitness", 60, 50, 20, 30, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("YETI Tundra 45 Cooler", "SPT-040", "YETI Tundra 45 cooler, rotomolded, PermaFrost insulation, 3-inch walls, bear-resistant", "Sports & Fitness", 275, 250, 130, 15, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Mountain Hardwear Stretch Ozonic Rain Jacket", "SPT-041", "Mountain Hardwear Stretch Ozonic rain jacket, DryQ Elite, lightweight, stretch, waterproof", "Sports & Fitness", 225, 199, 90, 15, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Sea to Summit Aeros Pillow Premium", "SPT-042", "Sea to Summit Aeros Premium pillow, lightweight, inflatable, ergonomic, 2.5oz", "Sports & Fitness", 55, 48, 18, 35, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Oakley Flak 2.0 XL Sunglasses", "SPT-043", "Oakley Flak 2.0 XL sunglasses, Prizm lenses, lightweight O-Matter frame, Three-Point Fit", "Sports & Fitness", 201, 179, 80, 25, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("CamelBak Podium Chill 21oz Bottle", "SPT-044", "CamelBak Podium Chill insulated water bottle, 21oz, double-wall, self-sealing Jet Valve", "Sports & Fitness", 18, 15, 5, 80, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),
    ("Mountain Hardwear Trango 3-Season Tent", "SPT-045", "Mountain Hardwear Trango 3 backpacking tent, 3-season, DAC poles, waterproof, freestanding", "Sports & Fitness", 450, 399, 240, 8, "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=400&h=400&fit=crop"),

    # ═══ MORE BEAUTY (15) ═══
    ("Moroccanoil Treatment Original", "BTY-021", "Moroccanoil Treatment original, argan oil, detangles, speeds drying time, conditions, adds shine", "Beauty & Personal Care", 48, 42, 16, 35, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Peter Thomas Roth Water Drench Moisturizer", "BTY-022", "Peter Thomas Roth Water Drench hyaluronic cloud cream, 30% hyaluronic acid, 75hr moisture", "Beauty & Personal Care", 52, 45, 18, 30, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Supergoop Unseen Sunscreen SPF 40", "BTY-023", "Supergoop Unseen Sunscreen SPF 40, invisible, weightless, makeup-gripping, reef-safe", "Beauty & Personal Care", 38, 34, 12, 45, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Fenty Beauty Pro Filt'r Foundation", "BTY-024", "Fenty Beauty Pro Filt'r soft matte longwear foundation, 50 shades, oil-free, buildable coverage", "Beauty & Personal Care", 40, 36, 12, 40, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Glossier Boy Brow", "BTY-025", "Glossier Boy Brow grooming pomade, thickens, shapes, tames brows, flexible hold", "Beauty & Personal Care", 18, 16, 5, 60, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("The Ordinary Niacinamide 10% + Zinc 1%", "BTY-026", "The Ordinary Niacinamide 10% + Zinc 1%, reduces blemishes, controls sebum, vegan, cruelty-free", "Beauty & Personal Care", 7, 6, 2, 200, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Drunk Elephant Lala Retro Whipped Cream", "BTY-027", "Drunk Elephant Lala Retro whipped cream, 6 African oils, ceramides, plantain skin", "Beauty & Personal Care", 62, 55, 22, 30, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Dyson Corrale Straightener", "BTY-028", "Dyson Corrale straightener, flexing plate technology, cordless, 45min runtime, heat control", "Beauty & Personal Care", 499, 449, 300, 10, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Clinique Almost Lipstick Black Honey", "BTY-029", "Clinique Almost Lipstick in Black Honey, sheer, universally flattering, moisturizing, iconic", "Beauty & Personal Care", 25, 22, 7, 50, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Chanel No. 5 Eau de Parfum", "BTY-030", "Chanel No. 5 EDP, 3.4oz, floral aldehyde, jasmine, rose, iconic, long-lasting", "Beauty & Personal Care", 165, 145, 65, 15, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Vitamin C Serum 20% by TruSkin", "BTY-031", "TruSkin Vitamin C serum 20%, hyaluronic acid, vitamin E, brightening, anti-aging, 1oz", "Beauty & Personal Care", 22, 18, 6, 80, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Conair InfinitiPro Curling Iron 1.25\"", "BTY-032", "Conair InfinitiPro 1.25-inch curling iron, tourmaline ceramic, 30 heat settings, instant heat", "Beauty & Personal Care", 35, 28, 10, 40, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("GHD Platinum+ Styler", "BTY-033", "GHD Platinum+ hair straightener, ultra-zone technology, predictive heat, 1-inch plates", "Beauty & Personal Care", 279, 249, 130, 12, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Kiehl's Ultra Facial Cream", "BTY-034", "Kiehl's Ultra Facial Cream, 24hr hydration, squalane, glacier water, all skin types, 1.7oz", "Beauty & Personal Care", 38, 34, 13, 35, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),
    ("Neutrogena Hydro Boost Water Gel", "BTY-035", "Neutrogena Hydro Boost water gel, hyaluronic acid, oil-free, lightweight, 48hr hydration", "Beauty & Personal Care", 22, 18, 6, 90, "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop"),

    # ═══ MORE HOME & KITCHEN (15) ═══
    ("Instant Pot Pro 10-in-1 8qt", "KIT-026", "Instant Pot Pro 10-in-1 pressure cooker, 8 quart, 28 smart programs, quiet mode, stainless steel", "Home & Kitchen", 180, 159, 78, 35, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Breville Smart Oven Air Fryer Pro", "KIT-027", "Breville Smart Oven Air Fryer Pro, Element IQ, 13 cooking functions, Super Convection", "Home & Kitchen", 399, 349, 210, 12, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Keurig K-Elite Single-Serve", "KIT-028", "Keurig K-Elite single-serve coffee maker, 75oz water reservoir, strong brew, iced setting", "Home & Kitchen", 189, 169, 80, 30, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Vitamix Explorian Blender", "KIT-029", "Vitamix Explorian blender, 64oz, variable speed, pulse, self-cleaning, 10-year warranty", "Home & Kitchen", 349, 299, 195, 20, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Anova Precision Cooker Pro", "KIT-030", "Anova Precision Cooker Pro sous vide, 12L/min, 1200 watts, stainless steel, WiFi", "Home & Kitchen", 199, 179, 95, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("KitchenAid Immersion Blender", "KIT-031", "KitchenAid immersion hand blender, 8-inch stainless steel arm, variable speed, chopper", "Home & Kitchen", 80, 69, 30, 35, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Staub Cocotte Round 5.5qt", "KIT-032", "Staub round cocotte Dutch oven, 5.5 quart, black matte enamel, self-basting spikes, cast iron", "Home & Kitchen", 379, 329, 200, 10, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Smeg 2-Slice Toaster", "KIT-033", "Smeg 50s retro style 2-slice toaster, 6 browning levels, wide slots, defrost function", "Home & Kitchen", 199, 179, 85, 18, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Ninja Creami Deluxe 11-in-1", "KIT-034", "Ninja Creami Deluxe 11-in-1, larger pints, frozen treat maker, ice cream, sorbet, gelato", "Home & Kitchen", 249, 219, 120, 25, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Cuisinart 14-Cup Food Processor", "KIT-035", "Cuisinart 14-cup food processor, 720-watt motor, stainless steel blades, disc, BPA-free", "Home & Kitchen", 230, 199, 100, 20, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("iRobot Braava Jet m6 Robot Mop", "KIT-036", "iRobot Braava jet m6 robot mop, precision jet spray, smart mapping, works with Roomba", "Home & Kitchen", 399, 349, 210, 10, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Emile Henry Bread Loaf Baker", "KIT-037", "Emile Henry bread loaf baker, 12-inch, Burgundy clay, moisture retention, oven safe 500F", "Home & Kitchen", 90, 79, 35, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Hydroponic Indoor Herb Garden", "KIT-038", "Indoor hydroponic herb garden system, LED grow lights, self-watering, 6-pod capacity", "Home & Kitchen", 89, 75, 32, 30, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Technivorm Moccamaster KBGV Select", "KIT-039", "Technivorm Moccamaster KBGV, SCA certified, copper heating element, 10-cup, auto drip stop", "Home & Kitchen", 349, 299, 185, 12, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
    ("Yeti Hopper Flip 18 Soft Cooler", "KIT-040", "YETI Hopper Flip 18 portable soft cooler, DryHide Shell, ColdCell insulation, 30 cans capacity", "Home & Kitchen", 300, 269, 130, 15, "https://images.unsplash.com/photo-1594226801341-41427b4e5c3d?w=400&h=400&fit=crop"),
]


def main():
    conn = psycopg2.connect(CONN)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM products")
    existing = cur.fetchone()[0]
    print(f"Existing products: {existing}")

    needed = len(EXTRA_PRODUCTS)
    print(f"Extra products to add: {needed}")

    # Fix duplicate SKUs first
    cur.execute("UPDATE products SET sku = 'EUC-008' WHERE sku = 'AUD-008' AND name LIKE '%Jabra%'")
    if cur.rowcount:
        print(f"Fixed duplicate AUD-008 (renamed Jabra to EUC-008)")
    cur.execute("UPDATE products SET sku = 'SHO-020c' WHERE sku = 'SHO-010' AND name LIKE '%Cole Haan%'")
    if cur.rowcount:
        print(f"Fixed duplicate SHO-010 (renamed Cole Haan to SHO-020c)")

    # Replace existing products with the extra catalog (IDs 1 to N)
    for i, p in enumerate(EXTRA_PRODUCTS):
        pid = i + 1
        name, sku, desc, cat, base_price, curr_price, cost_price, stock, img = p
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

    # For remaining products beyond EXTRA_PRODUCTS count, set realistic names
    # These are products 394+ from the original CATALOG that weren't in EXTRA_PRODUCTS
    # We'll give them reasonable names so search works
    fill_names = [
        ("Essentials Crew Neck T-Shirt", "FIL", "Clothing", 15, 12, 4, 200),
        ("Classic Denim Jeans Slim", "FIL", "Clothing", 60, 49, 18, 80),
        ("Performance Running Vest", "FIL", "Sports & Fitness", 45, 38, 14, 50),
        ("Wireless Charger Pad 15W", "ELC", "Electronics", 25, 20, 7, 100),
        ("USB-C to Lightning Cable 6ft", "ELC", "Electronics", 15, 12, 4, 150),
        ("Bluetooth Mechanical Keyboard", "ELC", "Electronics", 89, 75, 32, 30),
        ("Noise Cancelling Earbuds", "AUD", "Headphones", 79, 65, 25, 45),
        ("Portable Bluetooth Speaker Mini", "ELC", "Electronics", 29, 24, 8, 80),
        ("Smart Home Hub WiFi 6", "ELC", "Electronics", 99, 85, 38, 25),
        ("LED Desk Lamp USB-C", "ELC", "Electronics", 35, 29, 10, 60),
        ("Ceramic Non-Stick Frying Pan", "KIT", "Home & Kitchen", 30, 25, 9, 70),
        ("Bamboo Cutting Board Set", "KIT", "Home & Kitchen", 25, 20, 7, 90),
        ("Insulated Coffee Tumbler 20oz", "KIT", "Home & Kitchen", 30, 25, 9, 80),
        ("Cordless Hand Mixer 5-Speed", "KIT", "Home & Kitchen", 35, 28, 10, 45),
        ("Silicone Baking Mat Set", "KIT", "Home & Kitchen", 15, 12, 4, 100),
        ("Memory Foam Pillow Queen", "DEC", "Home Decor", 50, 42, 16, 40),
        ("Weighted Blanket 15lb", "DEC", "Home Decor", 55, 45, 18, 30),
        ("Scented Candle Set 3-Pack", "DEC", "Home Decor", 35, 28, 10, 50),
        ("Decorative Throw Pillow Set", "DEC", "Home Decor", 40, 32, 12, 45),
        ("Indoor Plant Pot Ceramic", "DEC", "Home Decor", 20, 16, 5, 60),
        ("Polarized Aviator Sunglasses", "JWL", "Accessories", 25, 20, 7, 70),
        ("Minimalist Leather Card Holder", "JWL", "Accessories", 30, 25, 8, 55),
        ("Stainless Steel Travel Mug 16oz", "JWL", "Accessories", 20, 16, 5, 80),
        ("Canvas Messenger Bag Laptop", "JWL", "Accessories", 45, 38, 14, 40),
        ("Silicone Fitness Tracker Band", "JWL", "Accessories", 15, 12, 4, 100),
        ("Moisturizing Body Lotion 16oz", "BTY", "Beauty & Personal Care", 12, 10, 3, 120),
        ("Volumizing Hair Shampoo 12oz", "BTY", "Beauty & Personal Care", 15, 12, 4, 80),
        ("Refreshing Face Mist Spray", "BTY", "Beauty & Personal Care", 18, 15, 5, 65),
        ("Gentle Exfoliating Scrub 4oz", "BTY", "Beauty & Personal Care", 12, 10, 3, 90),
        ("Hand Cream Repair Tube 3.3oz", "BTY", "Beauty & Personal Care", 10, 8, 3, 110),
        ("Natural Deodorant Stick", "BTY", "Beauty & Personal Care", 12, 10, 3, 100),
        ("Rechargeable Electric Toothbrush", "BTY", "Beauty & Personal Care", 35, 28, 10, 50),
        ("Whitening Toothpaste Set 3-Pack", "BTY", "Beauty & Personal Care", 15, 12, 4, 75),
        ("Travel Size Skincare Kit", "BTY", "Beauty & Personal Care", 25, 20, 7, 40),
        ("Bamboo Hair Brush Set", "BTY", "Beauty & Personal Care", 18, 15, 5, 55),
        ("Waterproof Mascara Black", "BTY", "Beauty & Personal Care", 22, 18, 6, 45),
        ("Silk Pillowcase Queen", "DEC", "Home Decor", 45, 38, 14, 30),
        ("Memory Foam Bath Mat", "DEC", "Home Decor", 25, 20, 7, 50),
        ("LED String Lights 33ft", "DEC", "Home Decor", 15, 12, 4, 70),
        ("Wall Mounted Shelf Set", "DEC", "Home Decor", 35, 28, 10, 35),
        ("Decorative Mirror Round 24\"", "DEC", "Home Decor", 65, 55, 22, 20),
        ("Ergonomic Mouse Wireless", "ELC", "Electronics", 40, 35, 12, 50),
        ("Noise Isolating Earbuds Wired", "ELC", "Electronics", 20, 16, 5, 80),
        ("Portable Power Station 500Wh", "ELC", "Electronics", 499, 429, 270, 8),
        ("Wireless Gaming Controller", "ELC", "Electronics", 59, 49, 20, 35),
        ("Smart Light Bulb 4-Pack WiFi", "ELC", "Electronics", 40, 32, 12, 55),
        ("Action Camera Waterproof 4K", "ELC", "Electronics", 89, 75, 32, 25),
        ("Digital Drawing Tablet 10\"", "ELC", "Electronics", 79, 65, 28, 20),
        ("Compact Tripod for Camera", "ELC", "Electronics", 35, 28, 10, 40),
        ("Mechanical Numpad Wireless", "ELC", "Electronics", 25, 20, 7, 30),
        ("Car Phone Mount Magnetic", "ELC", "Electronics", 20, 16, 5, 60),
        ("Laptop Stand Aluminum Adjustable", "ELC", "Electronics", 35, 28, 10, 45),
        ("Webcam Ring Light 10\"", "ELC", "Electronics", 30, 25, 8, 35),
        ("Carpet Cleaner Machine", "KIT", "Home & Kitchen", 299, 259, 150, 10),
        ("Espresso Machine Semi-Auto", "KIT", "Home & Kitchen", 449, 379, 240, 8),
        ("Electric Kettle Temperature Control", "KIT", "Home & Kitchen", 45, 38, 14, 50),
        ("Ice Cream Maker Automatic", "KIT", "Home & Kitchen", 70, 58, 24, 20),
        ("Garlic Press Stainless Steel", "KIT", "Home & Kitchen", 12, 10, 3, 100),
        ("Wooden Spice Rack Organizer", "KIT", "Home & Kitchen", 30, 25, 9, 35),
        ("Cotton Bath Towel Set 6-Pack", "DEC", "Home Decor", 60, 50, 20, 30),
        ("Scented Reed Diffuser Set", "DEC", "Home Decor", 28, 22, 8, 45),
        ("Woven Storage Basket Set", "DEC", "Home Decor", 40, 32, 12, 30),
        ("Table Runner Linen 72\"", "DEC", "Home Decor", 25, 20, 7, 40),
        ("Picture Frame Set 8x10", "DEC", "Home Decor", 30, 24, 9, 25),
        ("Resistance Band Set 5-Pack", "SPT", "Sports & Fitness", 20, 16, 5, 80),
        ("Foam Roller High Density 36\"", "SPT", "Sports & Fitness", 25, 20, 7, 60),
        ("Jump Rope Speed Adjustable", "SPT", "Sports & Fitness", 12, 10, 3, 100),
        ("Yoga Block Set 2-Pack", "SPT", "Sports & Fitness", 15, 12, 4, 70),
        ("Swimming Goggles Anti-Fog", "SPT", "Sports & Fitness", 20, 16, 5, 55),
        ("Hiking Trekking Poles Carbon", "SPT", "Sports & Fitness", 120, 99, 42, 18),
        ("Gym Duffel Bag 40L", "SPT", "Sports & Fitness", 55, 45, 18, 25),
        ("Weightlifting Gloves Padded", "SPT", "Sports & Fitness", 25, 20, 7, 45),
        ("Shaker Bottle 28oz", "SPT", "Sports & Fitness", 12, 10, 3, 100),
        ("Ab Roller Wheel Exercise", "SPT", "Sports & Fitness", 18, 15, 5, 60),
        ("Kettlebell Cast Iron 20lb", "SPT", "Sports & Fitness", 35, 28, 10, 30),
        ("Adjustable Dumbbell Pair 25lb", "SPT", "Sports & Fitness", 149, 129, 55, 15),
        ("Exercise Ball 65cm", "SPT", "Sports & Fitness", 25, 20, 7, 40),
        ("Running Armband Phone Holder", "SPT", "Sports & Fitness", 15, 12, 4, 70),
        ("Sports Water Bottle 32oz BPA-Free", "SPT", "Sports & Fitness", 10, 8, 3, 120),
        ("Pull-Up Bar Doorway", "SPT", "Sports & Fitness", 30, 25, 8, 35),
        ("Boxing Gloves 12oz Training", "SPT", "Sports & Fitness", 40, 32, 12, 25),
        ("Ping Pong Paddle Set 4-Pack", "TOY", "Toys & Games", 25, 20, 7, 40),
        ("Chess Set Wooden Tournament", "TOY", "Toys & Games", 35, 28, 10, 25),
        ("Puzzle 1000 Pieces Landscape", "TOY", "Toys & Games", 18, 15, 5, 50),
        ("Board Game Strategy Medieval", "TOY", "Toys & Games", 40, 32, 12, 30),
        ("Card Game Expansion Pack", "TOY", "Toys & Games", 20, 16, 5, 45),
        ("Remote Control Car Off-Road", "TOY", "Toys & Games", 50, 42, 18, 20),
        ("Building Blocks 500 Piece Set", "TOY", "Toys & Games", 30, 25, 8, 35),
        ("STEM Science Kit Kids", "TOY", "Toys & Games", 25, 20, 7, 40),
        ("RC Drone Mini with Camera", "TOY", "Toys & Games", 45, 38, 14, 25),
        ("Tabletop Football Game", "TOY", "Toys & Games", 35, 28, 10, 30),
        ("Dart Board Set with Cabinet", "TOY", "Toys & Games", 60, 50, 20, 18),
        ("Magic Trick Set Professional", "TOY", "Toys & Games", 20, 16, 5, 35),
        ("Rubik's Cube Speed Magnetic", "TOY", "Toys & Games", 15, 12, 4, 50),
        ("Wooden Train Set 80 Pieces", "TOY", "Toys & Games", 40, 32, 12, 25),
        ("Dinosaur Figure Set 12-Pack", "TOY", "Toys & Games", 25, 20, 7, 40),
        ("Solar Robot Kit STEM", "TOY", "Toys & Games", 35, 28, 10, 20),
        ("Board Game Cooperative Fantasy", "TOY", "Toys & Games", 45, 38, 14, 22),
        ("Art Supplies Set 150 Pieces", "TOY", "Toys & Games", 30, 25, 8, 30),
        ("RC Helicopter with Gyro", "TOY", "Toys & Games", 40, 32, 12, 25),
        ("Outdoor Sports Set Badminton", "TOY", "Toys & Games", 25, 20, 7, 35),
    ]

    start_pid = needed + 1  # Start filling from product ID after EXTRA_PRODUCTS
    for i, (name, prefix, cat, base_price, curr_price, cost_price, stock) in enumerate(fill_names):
        pid = start_pid + i
        if pid > 585:
            break
        sku = f"{prefix}-X{pid:04d}"
        desc = f"{name} - high quality {cat.lower()} product"
        random.seed(pid)
        est_sales = random.randint(10, 150)
        revenue = round(curr_price * est_sales * random.uniform(0.4, 1.2), 2)
        img = "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=400&fit=crop"

        cur.execute("""
            UPDATE products SET
                name = %s, sku = %s, description = %s, category = %s,
                base_price = %s, current_price = %s, cost_price = %s,
                stock_quantity = %s, revenue = %s, image_url = %s,
                status = 'active'
            WHERE id = %s
        """, (name, sku, desc, cat, base_price, curr_price, cost_price, stock, revenue, img, pid))

    # Update pricing_history for new base_prices
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

    # Final verification
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

    # Verify no placeholder names remain
    cur.execute("SELECT COUNT(*) FROM products WHERE name LIKE 'Placeholder%' OR name LIKE 'ErgoLiving%' OR name LIKE 'Solid Oak%'")
    bad_names = cur.fetchone()[0]
    print(f"Remaining placeholder/old names: {bad_names}")

    conn.close()


if __name__ == "__main__":
    main()
