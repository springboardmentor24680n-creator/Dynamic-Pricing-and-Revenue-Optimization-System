"""
PricePilot AI - Competitor Monitoring & Pricing Comparison Service

Identifies genuine **competitor products** for a selected catalog item and
attaches **marketplace/source listings** where each product can be verified.

BUSINESS MODEL (competitors are products, not websites)
-------------------------------------------------------
* **Competitor** = another product (exact same listing, or a closely matching
  variant) — never a marketplace name such as Amazon India or Flipkart.
* **Marketplace / source** = where a product is sold (Amazon India, Flipkart,
  Croma, Reliance Digital, Acer Official Store, …). Sources carry optional
  listing prices; they are not competitors themselves.
* The selected product is compared against:
    1. Exact / same product entries in the catalog (when present).
    2. Closely matching products (same brand+model family or strong spec overlap)
       when an exact product is unavailable.
    3. Comparable alternatives in the same product type when no closer match exists.

DATA INTEGRITY POLICY
---------------------
- Competitor products are matched from the real catalog — no hardcoded lists.
- Live listing prices are only reported as ``price_source=verified`` when a
  permitted provider returns a confirmed price. No provider is configured by
  default, so marketplace prices are ``unavailable`` with real deep-link URLs.
- Catalog prices on competitor products are ``price_source=reference`` (real
  internal data, not live external market prices).
- A price is NEVER invented.
"""

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.models.product import Product

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand parsing
# ---------------------------------------------------------------------------

# Multi-word brands present in the catalog (and common global variants) so the
# parser does not split them incorrectly (e.g. "Under Armour", "New Balance").
MULTI_WORD_BRANDS = [
    "Under Armour",
    "New Balance",
    "Michael Kors",
    "Ralph Lauren",
    "Brooks Brothers",
    "Banana Republic",
    "Tommy Hilfiger",
    "Calvin Klein",
    "Todd Snyder",
    "Mountain Hardwear",
    "The North Face",
    "North Face",
    "Restoration Hardware",
    "Pottery Barn",
    "West Elm",
    "Herman Miller",
    "Crate & Barrel",
    "Boll & Branch",
    "Kate Spade",
    "Maui Jim",
    "Serena Lily",
    "First Aid Beauty",
    "Paula's Choice",
    "La Roche-Posay",
    "Dr. Martens",
    "Red Wing",
    "Cole Haan",
    "Drunk Elephant",
    "Charlotte Tilbury",
    "Tom Ford",
    "Estee Lauder",
    "Black+Decker",
    "Black & Decker",
    "Hamilton Beach",
    "De'Longhi",
    "Instant Pot",
    "Le Creuset",
    "All-Clad",
    "Hydro Flask",
    "Fjallraven",
    "Black Diamond",
    "Audio-Technica",
    "Beyerdynamic",
    "Sony PlayStation",
    "Apples to Apples",
    "Connect 4",
]

MULTI_WORD_BRANDS.sort(key=len, reverse=True)  # longest first for greedy match


def parse_brand(name: str) -> str:
    """Extract the brand from a product name. Falls back to the first token."""
    if not name:
        return "Unknown"
    for brand in MULTI_WORD_BRANDS:
        if name.lower().startswith(brand.lower()):
            return BRAND_ALIASES.get(brand, brand)
    first = name.split()[0]
    return BRAND_ALIASES.get(first, first)


# Brand aliases so the same manufacturer is matched across naming variants
# (e.g. "iPhone 13" is an Apple product, "Surface" is Microsoft).
BRAND_ALIASES = {
    "iPhone": "Apple",
    "Surface": "Microsoft",
}


# ---------------------------------------------------------------------------
# Specification extraction
# ---------------------------------------------------------------------------

PROCESSOR_PATTERNS = [
    (re.compile(r"(i\d-\d{4,5}[A-Z]?|i\d{1,2})", re.IGNORECASE), "processor"),
    (re.compile(r"(Ryzen \d)", re.IGNORECASE), "processor"),
    # Apple M-series chip: only when it stands as its own token (never "XM4")
    (re.compile(r"(?:^|\s)(M\d(?: Pro| Max| Ultra)?)", re.IGNORECASE), "processor"),
    (re.compile(r"(Intel Core Ultra \d)", re.IGNORECASE), "processor"),
    (re.compile(r"(Snapdragon \d+(?:[A-Z]+\d+)?)", re.IGNORECASE), "processor"),
    (re.compile(r"(Dimensity \d+)", re.IGNORECASE), "processor"),
    (re.compile(r"(Google Tensor [A-Z0-9]*)", re.IGNORECASE), "processor"),
    (re.compile(r"(Helio [A-Z]\d+)", re.IGNORECASE), "processor"),
]

GPU_PATTERNS = [
    re.compile(r"(RTX \d{4}(?: Ti| Super| Max-Q)?)", re.IGNORECASE),
    re.compile(r"(GTX \d{4}(?: Ti)?)", re.IGNORECASE),
    re.compile(r"(RX \d{4}(?: XT| X)?)", re.IGNORECASE),
    re.compile(r"(Intel Iris Xe Graphics)", re.IGNORECASE),
]


def parse_specs(name: str, description: str = "", category: str = "") -> dict:
    """Extract meaningful specification tokens from a product name/description.

    Returns a dict of canonical spec features. Only values that genuinely
    appear in the name/description are returned - nothing is guessed.
    Category is used to disambiguate memory semantics (e.g. for smartphones a
    bare "128GB" is storage, while for laptops "8GB/256GB" splits RAM/storage).
    """
    text = f"{name} {description}"
    specs: dict = {}

    # Screen size: "13-inch", "27-inch", '15.6"'
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-inch|\b-inch\b|\")", text, re.IGNORECASE)
    if m:
        specs["screen_size_inches"] = float(m.group(1))

    storage_cats = {"Smartphones", "Tablets", "TVs & Monitors", "Toys & Games"}

    # Laptop-style "8GB/256GB" or "16GB 1TB"
    slash = re.search(r"(\d+)\s*GB\s*/\s*(\d+)\s*(GB|TB)", text, re.IGNORECASE)
    if slash:
        specs["ram_gb"] = int(slash.group(1))
        specs["storage_gb"] = int(slash.group(2)) * (1024 if slash.group(3).upper() == "TB" else 1)
    else:
        explicit_ram = re.search(r"(\d+)\s*GB\s*RAM", text, re.IGNORECASE)
        if explicit_ram:
            specs["ram_gb"] = int(explicit_ram.group(1))
        tb = re.search(r"(\d+)\s*TB", text, re.IGNORECASE)
        if tb:
            specs["storage_gb"] = int(tb.group(1)) * 1024
        else:
            gb = re.search(r"(\d+)\s*GB", text, re.IGNORECASE)
            if gb:
                val = int(gb.group(1))
                if category in storage_cats:
                    specs["storage_gb"] = val
                elif category in {"Laptops", "Electronics"}:
                    specs["ram_gb"] = val
                else:
                    specs["storage_gb"] = val

    for pattern, key in PROCESSOR_PATTERNS:
        m = pattern.search(text)
        if m:
            specs[key] = m.group(1).strip()
            break

    for pattern in GPU_PATTERNS:
        m = pattern.search(text)
        if m:
            specs["gpu"] = m.group(1)
            break

    # Watch case size: "47mm", "44mm"
    m = re.search(r"(\d{2})\s*mm", text)
    if m:
        specs["case_size_mm"] = int(m.group(1))

    # Battery capacity (mAh)
    m = re.search(r"(\d{3,4})\s*mAh", text, re.IGNORECASE)
    if m:
        specs["battery_mah"] = int(m.group(1))

    return specs


# ---------------------------------------------------------------------------
# Platform targeting
# ---------------------------------------------------------------------------

ELECTRONICS_CATEGORIES = {
    "Laptops", "Smartphones", "Tablets", "Headphones", "TVs & Monitors",
    "Smartwatches", "Electronics", "Kitchen Appliances",
}
FASHION_CATEGORIES = {
    "Shirts & Tops", "Shoes", "Accessories", "Beauty & Personal Care",
}
HOME_CATEGORIES = {"Home Furniture", "Home Decor & Bedding"}


def platform_targets(category: str) -> list:
    """Which real storefront platforms apply for a given category."""
    targets = [
        {"platform": "Amazon India", "kind": "marketplace", "url": _amazon_url},
        {"platform": "Flipkart", "kind": "marketplace", "url": _flipkart_url},
    ]
    if category in ELECTRONICS_CATEGORIES:
        targets.append({"platform": "Croma", "kind": "retailer", "url": _croma_url})
        targets.append({"platform": "Reliance Digital", "kind": "retailer", "url": _reliance_url})
    if category in FASHION_CATEGORIES:
        targets.append({"platform": "Myntra", "kind": "retailer", "url": _myntra_url})
    if category in HOME_CATEGORIES:
        targets.append({"platform": "Pepperfry", "kind": "retailer", "url": _pepperfry_url})
    return targets


def _q(query: str) -> str:
    return quote_plus(query)


def _amazon_url(query: str) -> str:
    return f"https://www.amazon.in/s?k={_q(query)}"


def _flipkart_url(query: str) -> str:
    return f"https://www.flipkart.com/search?q={_q(query)}"


def _croma_url(query: str) -> str:
    return f"https://www.croma.com/search/?q={_q(query)}"


def _reliance_url(query: str) -> str:
    return f"https://www.reliancedigital.in/search?q={_q(query)}"


def _myntra_url(query: str) -> str:
    return f"https://www.myntra.com/search?rawQuery={_q(query)}"


def _pepperfry_url(query: str) -> str:
    return f"https://www.pepperfry.com/search/{_q(query)}"


# Curated official storefront URLs for brands in the catalog. Only brands with
# confidently-known storefront URLs are mapped; unknown brands simply do not
# get a brand-store platform entry (never a guessed URL).
BRAND_STOREFRONTS = {
    "Apple": "https://www.apple.com/in/shop",
    "iPhone": "https://www.apple.com/in/shop",
    "Samsung": "https://www.samsung.com/in",
    "Dell": "https://www.dell.com/en-in",
    "HP": "https://www.hp.com/in-en",
    "Lenovo": "https://www.lenovo.com/in/en",
    "ASUS": "https://www.asus.com/in",
    "Acer": "https://www.acer.com/in-en",
    "MSI": "https://www.msi.com",
    "Razer": "https://www.razer.com",
    "Framework": "https://frame.work",
    "Surface": "https://www.microsoft.com/en-in/surface",
    "Microsoft": "https://www.microsoft.com/en-in",
    "Google": "https://store.google.com/in",
    "OnePlus": "https://www.oneplus.in",
    "Sony": "https://www.sony.co.in",
    "LG": "https://www.lg.com/in",
    "TCL": "https://www.tcl.com/in/en",
    "Hisense": "https://www.hisense-india.com",
    "Bose": "https://www.bose.in",
    "JBL": "https://in.jbl.com",
    "Sennheiser": "https://www.sennheiser.com",
    "Skullcandy": "https://www.skullcandy.com",
    "Beats": "https://www.beatsbydre.com",
    "Jabra": "https://www.jabra.com",
    "Shure": "https://www.shure.com",
    "Beyerdynamic": "https://www.beyerdynamic.com",
    "Audio-Technica": "https://www.audio-technica.com",
    "Nike": "https://www.nike.com/in",
    "Jordan": "https://www.nike.com/in",
    "Adidas": "https://www.adidas.co.in",
    "Puma": "https://in.puma.com",
    "Reebok": "https://www.reebok.in",
    "ASICS": "https://www.asics.com/in/en",
    "New Balance": "https://www.newbalance.co.in",
    "Converse": "https://www.converse.com",
    "Vans": "https://www.vans.com",
    "Under Armour": "https://www.underarmour.co.in",
    "Levi's": "https://www.levi.in",
    "Calvin Klein": "https://www.calvinklein.in",
    "Tommy Hilfiger": "https://in.tommy.com",
    "Ralph Lauren": "https://www.ralphlauren.com",
    "H&M": "https://www2.hm.com/en_in",
    "Uniqlo": "https://www.uniqlo.com/in",
    "Zara": "https://www.zara.com/in",
    "GAP": "https://www.gap.com",
    "Banana Republic": "https://www.bananarepublic.com",
    "Brooks Brothers": "https://www.brooksbrothers.com",
    "J.Crew": "https://www.jcrew.com",
    "Carhartt": "https://www.carhartt.com",
    "Gildan": "https://www.gildan.com",
    "Mango": "https://shop.mango.com",
    "Todd Snyder": "https://www.toddsnyder.com",
    "Lululemon": "https://shop.lululemon.com",
    "Patagonia": "https://www.patagonia.com",
    "Columbia": "https://www.columbia.com",
    "The North Face": "https://www.thenorthface.com",
    "Mountain Hardwear": "https://www.mountainhardwear.com",
    "Salomon": "https://www.salomon.com",
    "Birkenstock": "https://www.birkenstock.com",
    "Clarks": "https://www.clarks.com",
    "Cole Haan": "https://www.colehaan.com",
    "Dr. Martens": "https://www.drmartens.com",
    "Hoka": "https://www.hoka.com",
    "Merrell": "https://www.merrell.com",
    "On": "https://www.on-running.com",
    "Red Wing": "https://www.redwingshoes.com",
    "Saucony": "https://www.saucony.com",
    "Timberland": "https://www.timberland.com",
    "Allbirds": "https://www.allbirds.com",
    "Brooks": "https://www.brooksrunning.com",
    "Casio": "https://www.casio.com/in",
    "Citizen": "https://www.citizenwatch.com",
    "Seiko": "https://www.seikowatches.com",
    "Tissot": "https://www.tissotwatches.com",
    "Fossil": "https://www.fossil.com",
    "Michael Kors": "https://www.michaelkors.com",
    "Coach": "https://www.coach.com",
    "Samsonite": "https://www.samsonite.com",
    "Bellroy": "https://bellroy.com",
    "Fjallraven": "https://www.fjallraven.com",
    "Maui Jim": "https://www.mauijim.com",
    "Oakley": "https://www.oakley.com",
    "Ray-Ban": "https://www.ray-ban.com",
    "YETI": "https://www.yeti.com",
    "Hydro Flask": "https://www.hydroflask.com",
    "Garmin": "https://www.garmin.com/en-IN",
    "Fitbit": "https://www.fitbit.com",
    "Whoop": "https://www.whoop.com",
    "Withings": "https://www.withings.com",
    "Amazfit": "https://www.amazfit.com",
    "DJI": "https://www.dji.com",
    "GoPro": "https://gopro.com",
    "Canon": "https://www.canon.co.in",
    "BenQ": "https://www.benq.com/en-in",
    "Logitech": "https://www.logitech.com",
    "WD": "https://www.westerndigital.com",
    "Anker": "https://www.anker.com",
    "Corsair": "https://www.corsair.com",
    "Elgato": "https://www.elgato.com",
    "TP-Link": "https://www.tp-link.com/in",
    "NVIDIA": "https://www.nvidia.com",
    "Sonos": "https://www.sonos.com",
    "Roku": "https://www.roku.com",
    "Ring": "https://ring.com",
    "Kindle": "https://www.amazon.in",
    "Amazon": "https://www.amazon.in",
    "KitchenAid": "https://www.kitchenaid.com",
    "Ninja": "https://ninjakitchen.com",
    "Breville": "https://www.breville.com",
    "Vitamix": "https://www.vitamix.com",
    "Nespresso": "https://www.nespresso.com",
    "Keurig": "https://www.keurig.com",
    "Dyson": "https://www.dyson.in",
    "iRobot": "https://www.irobot.com",
    "Instant Pot": "https://www.instantpot.com",
    "De'Longhi": "https://www.delonghi.com",
    "Le Creuset": "https://www.lecreuset.com",
    "All-Clad": "https://www.all-clad.com",
    "Cuisinart": "https://www.cuisinart.com",
    "Wusthof": "https://www.wusthof.com",
    "Pyrex": "https://www.pyrexware.com",
    "Thermapen": "https://www.thermoworks.com",
    "Technivorm": "https://www.technivorm.com",
    "Anova": "https://anovaculinary.com",
    "Ooni": "https://ooni.com",
    "Hamilton Beach": "https://www.hamiltonbeach.com",
    "Black+Decker": "https://www.blackanddecker.com",
    "Herman Miller": "https://www.hermanmiller.com",
    "IKEA": "https://www.ikea.com/in",
    "West Elm": "https://www.westelm.com",
    "Pottery Barn": "https://www.potterybarn.com",
    "Restoration Hardware": "https://www.rh.com",
    "CB2": "https://www.cb2.com",
    "Article": "https://www.article.com",
    "Wayfair": "https://www.wayfair.com",
    "Ashley": "https://www.ashleyfurniture.com",
    "Casper": "https://casper.com",
    "Brooklinen": "https://www.brooklinen.com",
    "Parachute": "https://www.parachutehome.com",
    "Ruggable": "https://ruggable.com",
    "Boll & Branch": "https://www.bollandbranch.com",
    "Serena": "https://www.serenaandlily.com",
    "Kate Spade": "https://www.katespade.com",
    "Crate & Barrel": "https://www.crateandbarrel.com",
    "Peloton": "https://www.onepeloton.com",
    "Bowflex": "https://www.bowflex.com",
    "NordicTrack": "https://www.nordictrack.com",
    "Concept2": "https://www.concept2.com",
    "Rogue": "https://www.roguefitness.com",
    "Theragun": "https://www.theragun.com",
    "Hyperice": "https://hyperice.com",
    "Manduka": "https://www.manduka.com",
    "Callaway": "https://www.callawaygolf.com",
    "Osprey": "https://www.osprey.com",
    "REI": "https://www.rei.com",
    "Black Diamond": "https://www.blackdiamond.com",
    "Scarpa": "https://us.scarpa.com",
    "Wahoo": "https://www.wahoofitness.com",
    "TRX": "https://www.trxtraining.com",
    "LEGO": "https://www.lego.com",
    "Nintendo": "https://www.nintendo.com",
    "Xbox": "https://www.xbox.com",
    "PS5": "https://www.playstation.com",
    "Sony PlayStation": "https://www.playstation.com",
    "Catan": "https://www.catan.com",
    "Monopoly": "https://shop.hasbro.com",
    "Jenga": "https://shop.hasbro.com",
    "Risk": "https://shop.hasbro.com",
    "Scrabble": "https://shop.hasbro.com",
    "Connect 4": "https://shop.hasbro.com",
    "Apples to Apples": "https://shop.mattel.com",
    "CeraVe": "https://www.cerave.com",
    "La Roche-Posay": "https://www.laroche-posay.com",
    "Paula's Choice": "https://www.paulaschoice.com",
    "First Aid Beauty": "https://firstaidbeauty.com",
    "The Ordinary": "https://theordinary.com",
    "Drunk Elephant": "https://drunkelephant.com",
    "Estee Lauder": "https://www.esteelauder.com",
    "Clinique": "https://www.clinique.com",
    "Lancome": "https://www.lancome.com",
    "Shiseido": "https://www.shiseido.com",
    "SK-II": "https://www.sk-ii.com",
    "Tatcha": "https://www.tatcha.com",
    "Olaplex": "https://olaplex.com",
    "Moroccanoil": "https://moroccanoil.com",
    "Bioderma": "https://www.bioderma.com",
    "Revlon": "https://www.revlon.com",
    "Charlotte Tilbury": "https://www.charlottetilbury.com",
    "Tom Ford": "https://www.tomford.com",
    "T3": "https://www.t3micro.com",
}

# Live-price provider. When a permitted source is configured (a URL that
# returns {"price": <number>} for {"query": "..."}), live prices are reported
# as "verified". By default no provider is configured and prices are honestly
# reported as unavailable with the platform URL for manual verification.
LIVE_PRICE_PROVIDER_URL = None

# Product-type keyword clusters for heterogeneous categories. Keeps comparisons
# genuine: a dumbbell is compared with other strength gear, not a golf driver,
# even though both share the "Sports & Fitness" category and a price band.
# Categories not listed here are treated as one homogeneous type.
TYPE_CLUSTERS = {
    "Sports & Fitness": [
        (1, ["dumbbell", "barbell", "kettlebell", "weight", "plate", "rack", "suspension", "resistance"]),
        (2, ["treadmill", "rower", "indoor cycle", "spin bike", "stair stepper", "elliptical"]),
        (3, ["massage gun", "massage", "percussion", "foam roller"]),
        (4, ["smart trainer", "kickr", "gps", "cycling computer", "edge", "satellite", "inreach"]),
        (5, ["yoga mat", "yoga block", "yoga strap"]),
        (6, ["pant", "jacket", "top", "hoodie", "bra", "short", "rain jacket"]),
        (7, ["backpack", "tent", "headlamp", "cooler", "bottle", "duffel", "hiking boot", "hiking shoes"]),
        (8, ["golf", "driver", "iron", "wedge", "putter"]),
    ],
    "Toys & Games": [
        (1, ["lego", "technic", "architecture", "creator", "super mario", "city space"]),
        (2, ["monopoly", "scrabble", "jenga", "catan", "codenames", "risk", "connect 4", "apples to apples", "board game", "card game", "party game", "strategy game"]),
        (3, ["playstation", "ps5", "xbox", "nintendo", "switch", "dual", "console"]),
    ],
    "Home Furniture": [
        (1, ["chair", "armchair", "swivel"]),
        (2, ["desk", "sit/stand", "standing desk"]),
        (3, ["dresser", "wardrobe", "shelf", "bookcase", "drawer", "nightstand", "kallax", "malm", "hemnes", "alex", "billy", "kleppstad"]),
        (4, ["table", "dining"]),
        (5, ["bed", "mattress", "platform bed"]),
        (6, ["sofa", "couch", "loveseat", "arm sofa"]),
    ],
    "Home Decor & Bedding": [
        (1, ["sheet", "comforter", "duvet", "pillow", "blanket", "throw"]),
        (2, ["cushion", "vase", "lamp", "rug", "curtain", "candle", "frame", "clock", "mirror"]),
    ],
    "Kitchen Appliances": [
        (1, ["coffee", "espresso", "keurig", "nespresso", "brew"]),
        (2, ["knife", "chef's", "cutlery"]),
        (3, ["air fryer", "instant pot", "slow cooker", "pressure", "sous vide", "thermometer"]),
        (4, ["mixer", "blender", "food processor"]),
        (5, ["pan", "pot", "skillet", "dutch", "wok", "cookware"]),
        (6, ["pizza", "grill", "baking"]),
    ],
    "Beauty & Personal Care": [
        (1, ["cleanser", "serum", "moisturizer", "exfoliant", "cream", "sunscreen", "treatment", "lotion"]),
        (2, ["lipstick", "foundation", "mascara", "concealer", "blush", "powder", "eye", "makeup", "palette"]),
        (3, ["shampoo", "conditioner", "hair", "dryer", "straightener", "curler", "oil"]),
    ],
    "Accessories": [
        (1, ["watch", "chronograph", "diver", "timepiece"]),
        (2, ["sunglasses", "eyewear", "frames"]),
        (3, ["backpack", "luggage", "briefcase", "duffel", "wallet", "travel"]),
    ],
    "Shirts & Tops": [
        (1, ["oxford", "dress shirt", "button-down", "camp shirt"]),
        (2, ["polo", "golf polo", "dri-fit"]),
        (3, ["tee", "t-shirt", "crewneck", "vintage"]),
        (4, ["flannel", "overshirt", "jacket"]),
    ],
    "Shoes": [
        (1, ["running", "trainer", "road"]),
        (2, ["basketball", "court", "training"]),
        (3, ["sneaker", "chuck", "slip-on", "casual", "samba", "old skool", "suede", "classic", "gum"]),
        (4, ["boot", "hiking", "work", "chelsea"]),
        (5, ["sandal", "birkenstock", "slide"]),
        (6, ["oxford", "loafer", "derby", "dress"]),
    ],
    "Electronics": [
        (1, ["camera", "action", "drone", "gopro", "canon"]),
        (2, ["streaming", "roku", "chromecast", "fire stick", "tv"]),
        (3, ["smart home", "ring", "doorbell", "kasa", "plug", "security"]),
        (4, ["speaker", "soundbar", "sonos", "jbl"]),
        (5, ["ssd", "hdd", "external drive", "storage", "wd"]),
        (6, ["keyboard", "mouse", "webcam", "mic", "capture", "controller"]),
        (7, ["tablet", "kindle", "e-reader"]),
    ],
}


def _fetch_live_price(query: str) -> float:
    """Attempt to fetch a verified live price from a permitted provider.

    Returns None (never a guess) when no provider is configured or the
    provider does not return a confirmable price.
    """
    if not LIVE_PRICE_PROVIDER_URL:
        return None
    try:
        import requests

        resp = requests.post(
            LIVE_PRICE_PROVIDER_URL,
            json={"query": query},
            timeout=8,
        )
        data = resp.json()
        price = data.get("price")
        if isinstance(price, (int, float)) and price > 0:
            return float(price)
    except Exception as exc:  # noqa: BLE001 - provider failure must not fabricate
        logger.warning("Live price provider failed for %s: %s", query, exc)
    return None


class CompetitorService:
    """Competitor monitoring & price comparison for a given product."""

    MAX_COMPETITORS = 6
    MAX_EXACT_MATCHES = 4
    PRICE_BAND = 0.60  # comparable price must be within +/-60% of ours
    MIN_CATEGORY_POOL = 1
    MIN_SIMILARITY = 55.0  # below this, a same-category product is not a genuine comparable

    def __init__(self, db: Session):
        self.db = db

    # -- public API ---------------------------------------------------------

    def analyze(self, product_id: int) -> dict:
        product = self.db.get(Product, product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        name = product.name or ""
        description = product.description or ""
        category = product.category or ""
        brand = parse_brand(name)
        model = _model_family(name, brand)
        specs = parse_specs(name, description, category)

        pool = self._comparable_pool(product, brand, specs)
        competitors = self._score_and_rank(product, pool, brand, specs)
        for i, comp in enumerate(competitors, start=1):
            comp["rank"] = i

        exact_matches = [c for c in competitors if c["match_type"] != "comparable"]
        comparable_products = [c for c in competitors if c["match_type"] == "comparable"]

        category_sources = [t["platform"] for t in platform_targets(product.category)]
        selected_product_sources = self._marketplace_sources_for_product(
            brand=brand,
            model=_model_token(name, brand),
            specs=specs,
            category=product.category,
            product_name=name,
        )

        result = {
            "product": {
                "id": product.id,
                "name": product.name,
                "brand": brand,
                "category": product.category,
                "current_price": product.current_price,
                "base_price": product.base_price,
                "image_url": product.image_url,
                "sku": product.sku,
                "model": model,
                "stock_quantity": product.stock_quantity,
                "parsed_specs": specs,
            },
            "comparison": {
                "as_of": datetime.now(timezone.utc).isoformat(),
                "data_provenance": (
                    "reference" if LIVE_PRICE_PROVIDER_URL else "unavailable"
                ),
                "note": (
                    "Competitors are other products (exact or closely matching), "
                    "not marketplaces. Live external listing prices are not "
                    "available from a permitted source in this deployment. "
                    "Competitor product prices come from the PricePilot catalog "
                    "(reference data). Marketplace links below are verification "
                    "sources only — no price is estimated or invented."
                ),
                "live_provider_configured": bool(LIVE_PRICE_PROVIDER_URL),
                "category": product.category,
                "marketplace_sources_for_category": category_sources,
                "platforms": category_sources,
                "has_exact_matches": bool(exact_matches),
            },
            "selected_product_sources": selected_product_sources,
            "platform_links": selected_product_sources,
            "competitors": competitors,
            "exact_matches": exact_matches,
            "comparable_products": comparable_products,
        }

        if not competitors:
            result["message"] = (
                "No genuine competitor products were found in the catalog for "
                "this product within the matching criteria. Marketplace source "
                "links for the selected product are provided for external "
                "price verification."
            )
            result["comparison"]["note"] = (
                "No competitor products found. Marketplaces (Amazon India, "
                "Flipkart, etc.) are sources where this product can be verified "
                "— they are not competitors themselves."
            )
            result["comparison"]["has_exact_matches"] = False
        return result

    # -- matching -----------------------------------------------------------

    def _comparable_pool(self, product: Product, brand: str, specs: dict) -> list:
        """Candidate comparables: same category, not the product itself."""
        category = product.category or ""
        pool = []
        for p in self.db.query(Product).filter(
            Product.category == category,
            Product.id != product.id,
            Product.status == "active",
        ).all():
            if not p.current_price or p.current_price <= 0:
                continue
            lower = product.current_price * (1 - self.PRICE_BAND)
            upper = product.current_price * (1 + self.PRICE_BAND)
            if not (lower <= p.current_price <= upper):
                continue
            pool.append(p)
        return pool

    def _score_and_rank(self, product: Product, pool: list, brand: str, specs: dict) -> list:
        if not pool:
            return []

        model = _model_family(product.name or "", brand)
        our_clusters = self._type_clusters(product.category or "", product.name or "")
        heterogeneous = product.category in TYPE_CLUSTERS

        scored = []
        for p in pool:
            p_brand = parse_brand(p.name or "")
            p_specs = parse_specs(p.name or "", p.description or "", p.category or "")
            p_clusters = self._type_clusters(p.category or "", p.name or "")

            # In heterogeneous categories (e.g. Sports & Fitness, Toys & Games),
            # a shared category + price band is NOT enough: products must also be
            # the same product type, same brand, or share real specs. Otherwise a
            # golf driver would "compete" with a dumbbell, or Jenga with a LEGO
            # set. When our product's type is known but the candidate's is
            # unknown, the candidate only qualifies via brand or spec affinity.
            if heterogeneous:
                if our_clusters and p_clusters and not (p_clusters & our_clusters):
                    continue
                if not our_clusters and p_clusters:
                    continue
                if our_clusters and not p_clusters:
                    brand_affinity = p_brand.lower() == brand.lower()
                    spec_affinity = bool(set(p_specs) & set(specs))
                    if not (brand_affinity or spec_affinity):
                        continue

            score, reasons = self._similarity_score(
                brand, specs, product.current_price,
                p_brand, p_specs, p.current_price,
                our_clusters, p_clusters,
            )
            if score < self.MIN_SIMILARITY:
                continue

            p_model = _model_family(p.name or "", p_brand)
            match_type = self._match_type(
                product.name or "", brand, model, specs,
                p.name or "", p_brand, p_model, p_specs,
            )
            scored.append({
                "score": score, "reasons": reasons, "p": p,
                "p_brand": p_brand, "p_specs": p_specs,
                "p_model": p_model, "match_type": match_type,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        # Exact matches (exact product / exact brand+model / strong spec) always
        # outrank comparable alternatives and are never mixed with them.
        exact = [s for s in scored if s["match_type"] != "comparable"]
        comps = [s for s in scored if s["match_type"] == "comparable"]

        picked = exact[: self.MAX_EXACT_MATCHES]
        picked_ids = {s["p"].id for s in picked}
        seen_brands = {s["p_brand"].lower() for s in picked}

        # Fill remaining slots with comparable alternatives, promoting brand
        # diversity (a Dell laptop is compared with HP/Lenovo/ASUS, not 3 Dells).
        for s in comps:
            if len(picked) >= self.MAX_COMPETITORS:
                break
            if s["p"].id in picked_ids or s["p_brand"].lower() in seen_brands:
                continue
            picked.append(s)
            picked_ids.add(s["p"].id)
            seen_brands.add(s["p_brand"].lower())

        for s in comps:
            if len(picked) >= self.MAX_COMPETITORS:
                break
            if s["p"].id in picked_ids:
                continue
            picked.append(s)
            picked_ids.add(s["p"].id)

        return [self._build_competitor(product, s["score"], s["reasons"], s["p"],
                                       s["p_brand"], s["p_specs"], s["p_model"], s["match_type"])
                for s in picked]

    def _match_type(self, our_name, brand, model, specs,
                    p_name, p_brand, p_model, p_specs) -> str:
        """Classify a candidate as an exact match or a comparable alternative.

        Priority: 1) exact product/identifier match, 2) exact brand + model
        family, 3) strong specification match, 4) same product type/category
        only (fallback -> "comparable"). "Same category" is NEVER treated as an
        exact competitor.
        """
        if _normalize_name(our_name) and _normalize_name(our_name) == _normalize_name(p_name):
            return "exact_product"
        same_brand = brand.lower() == p_brand.lower()
        if same_brand and model and p_model and model.lower() == p_model.lower():
            return "exact_model"
        spec_keys = ("processor", "gpu", "ram_gb", "storage_gb",
                     "screen_size_inches", "battery_mah", "case_size_mm")
        overlap = [k for k in spec_keys
                   if k in specs and k in p_specs and specs[k] == p_specs[k]]
        if same_brand or len(overlap) >= 2:
            return "close_match"
        return "comparable"

    def _type_clusters(self, category: str, name: str) -> set:
        """Product-type keyword clusters for a product name.

        Used to avoid presenting unrelated products (e.g. a golf driver next to
        a dumbbell) as "comparable" just because they share a category and a
        price band. Categories without a cluster table are treated as one
        homogeneous type (all same-category products are comparables).
        """
        clusters = TYPE_CLUSTERS.get(category)
        if clusters is None:
            return {0}
        text = name.lower()
        matched = set()
        for cid, keywords in clusters:
            if any(kw in text for kw in keywords):
                matched.add(cid)
        return matched

    def _similarity_score(self, brand, specs, our_price, p_brand, p_specs, p_price,
                          our_clusters, p_clusters) -> tuple:
        """Heuristic 0-100 similarity: category is already equal at this point."""
        score = 40.0
        reasons = []

        if brand.lower() == p_brand.lower():
            score += 20
            reasons.append(f"same brand ({brand})")

        spec_keys = {"ram_gb", "storage_gb", "screen_size_inches", "processor", "gpu", "battery_mah"}
        overlaps = 0
        total = 0
        for key in spec_keys:
            if key in p_specs:
                total += 1
            if key in specs and key in p_specs and specs[key] == p_specs[key]:
                overlaps += 1
        if total:
            overlap_frac = overlaps / total
            score += overlap_frac * 20
            if overlaps:
                matched = [f"{k}={specs[k]}" for k in spec_keys if k in specs and k in p_specs and specs[k] == p_specs[k]]
                reasons.append("matching specs: " + ", ".join(matched[:3]))

        # Product-type similarity (clusters)
        if p_clusters and p_clusters & our_clusters:
            score += 20
            reasons.append("same product type")

        # Price proximity within the band
        diff_pct = abs(our_price - p_price) / our_price if our_price else 1.0
        score += max(0.0, 20.0 - diff_pct * 100.0 * 0.30)
        if diff_pct <= 0.15:
            reasons.append("price within 15% of selected product")

        return round(min(score, 100.0), 1), reasons

    def _build_competitor(self, product, score, reasons, p, p_brand, p_specs, p_model, match_type) -> dict:
        """Build one competitor-product entry (product + price + source listings)."""
        diff = round((p.current_price - product.current_price), 2)
        diff_pct = round((diff / product.current_price) * 100.0, 1) if product.current_price else None
        marketplace_sources = self._marketplace_sources_for_product(
            brand=p_brand,
            model=_model_token(p.name or "", p_brand),
            specs=p_specs,
            category=p.category,
            product_name=p.name or "",
        )
        price_label = "PricePilot catalog price (reference, not live)"
        competitor_product = {
            "product_id": p.id,
            "name": p.name,
            "brand": p_brand,
            "model": p_model,
            "category": p.category,
            "sku": p.sku,
            "parsed_specs": p_specs,
        }
        return {
            "rank": None,
            "competitor_product": competitor_product,
            "match_type": match_type,
            "price": p.current_price,
            "price_source": "reference",
            "price_label": price_label,
            "price_difference": diff,
            "price_difference_pct": diff_pct,
            "similarity_score": score,
            "match_reasons": reasons,
            "marketplace_sources": marketplace_sources,
            # Legacy flat aliases — competitor is the product above, not a marketplace.
            "product_id": p.id,
            "name": p.name,
            "brand": p_brand,
            "model": p_model,
            "category": p.category,
            "reference_price": p.current_price,
            "reference_price_label": price_label,
            "price_status": "reference",
            "parsed_specs": p_specs,
            "platforms": marketplace_sources,
        }

    # -- marketplace / source listings (NOT competitors) --------------------

    def _marketplace_sources_for_product(
        self,
        brand: str,
        model: str,
        specs: dict,
        category: str,
        product_name: str = "",
    ) -> list:
        """Deep-links to marketplaces/sources where a product can be verified.

        Returns source listings only — never competitor entities. Each entry
        describes one marketplace (or brand store) and an optional listing price.
        """
        query = (product_name or "").strip()
        if not query:
            query_tokens = [brand] if brand and brand != "Unknown" else []
            if model and model.lower() != brand.lower():
                query_tokens.append(model)
            for key, label in (
                ("screen_size_inches", "inch"),
                ("ram_gb", "GB"),
                ("storage_gb", "GB"),
            ):
                if key in specs:
                    query_tokens.append(f"{int(specs[key])}{label}")
            query = " ".join(query_tokens) if query_tokens else (f"{brand} {model}".strip())

        sources = []
        for target in platform_targets(category):
            url = target["url"](query)
            price_now = _fetch_live_price(query)
            entry = _source_entry(
                marketplace=target["platform"],
                source_type=target["kind"],
                url=url,
                price=price_now if price_now else None,
                price_source="verified" if price_now else "unavailable",
                note=(
                    "Listing price confirmed by the live price provider."
                    if price_now
                    else "Live listing price not retrievable from a permitted "
                         "source; verify on the marketplace directly."
                ),
            )
            sources.append(entry)

        store_url = BRAND_STOREFRONTS.get(brand)
        if store_url:
            sources.append(_source_entry(
                marketplace=f"{brand} Official Store",
                source_type="brand_store",
                url=store_url,
                price=None,
                price_source="unavailable",
                note="Brand official store — verify MSRP/offers directly.",
            ))
        return sources

    # -- metadata -----------------------------------------------------------

    def platform_catalog(self) -> dict:
        """Metadata about marketplace sources (not competitor products)."""
        marketplace_rows = [
            {"marketplace": "Amazon India", "source_type": "marketplace", "categories": sorted(ELECTRONICS_CATEGORIES | FASHION_CATEGORIES | HOME_CATEGORIES)},
            {"marketplace": "Flipkart", "source_type": "marketplace", "categories": sorted(ELECTRONICS_CATEGORIES | FASHION_CATEGORIES | HOME_CATEGORIES)},
            {"marketplace": "Croma", "source_type": "retailer", "categories": sorted(ELECTRONICS_CATEGORIES)},
            {"marketplace": "Reliance Digital", "source_type": "retailer", "categories": sorted(ELECTRONICS_CATEGORIES)},
            {"marketplace": "Myntra", "source_type": "retailer", "categories": sorted(FASHION_CATEGORIES)},
            {"marketplace": "Pepperfry", "source_type": "retailer", "categories": sorted(HOME_CATEGORIES)},
        ]
        return {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "data_provenance": "unavailable" if not LIVE_PRICE_PROVIDER_URL else "verified",
            "live_provider_configured": bool(LIVE_PRICE_PROVIDER_URL),
            "note": (
                "Marketplaces and brand stores are product sources for price "
                "verification — they are not competitors. Competitors are other "
                "products (exact or closely matching). No permitted live-price API "
                "is configured by default; listing prices are unavailable unless "
                "a provider confirms them."
            ),
            "marketplaces": marketplace_rows,
            "platforms": [
                {"platform": row["marketplace"], "kind": row["source_type"], "categories": row["categories"]}
                for row in marketplace_rows
            ],
            "brand_storefronts": sorted(BRAND_STOREFRONTS.keys()),
        }


def _model_token(name: str, brand: str) -> str:
    """Second meaningful token of the name (rough model identifier)."""
    tokens = name.replace("/", " ").split()
    brand_tokens = len(brand.split())
    if len(tokens) > brand_tokens:
        return tokens[brand_tokens]
    return ""


def _model_family(name: str, brand: str) -> str:
    """Rough model-family token appearing right after the brand.

    Examples: "MacBook Pro 14-inch M3" -> "MacBook", "Galaxy S24 Ultra" ->
    "Galaxy", "HP Pavilion 15" -> "Pavilion". Used to group variants of the
    same product family (exact brand + model match).
    """
    if not name:
        return ""
    name = name.replace("/", " ")
    brand_lower = (brand or "").lower()
    rest = name
    if name.lower().startswith(brand_lower):
        rest = name[len(brand):].strip()
    for token in rest.split():
        if re.search(r"[a-z]", token, re.IGNORECASE):
            return token
    return ""


def _normalize_name(name: str) -> str:
    """Case-insensitive, punctuation-insensitive product-name key."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _source_entry(
    marketplace: str,
    source_type: str,
    url: str,
    price,
    price_source: str,
    note: str,
) -> dict:
    """One marketplace/source listing for a product (not a competitor entity)."""
    return {
        "marketplace": marketplace,
        "source_type": source_type,
        "url": url,
        "price": price,
        "price_source": price_source,
        "note": note,
        # Legacy field names consumed by existing frontend components.
        "platform": marketplace,
        "kind": source_type,
        "price_status": price_source,
    }