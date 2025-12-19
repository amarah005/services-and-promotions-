from typing import Dict, List, Optional
import re


# Simple keyword-to-category rules. Tokens are matched case-insensitively in product name/description.
CATEGORY_RULES: Dict[str, List[str]] = {
    # Electronics Categories
    'Cooling & Heating': [
        'split ac', 'air conditioner', 'inverter ac', '1.0 ton', '1.5 ton', '2 ton', 'heater', 'room heater'
    ],
    'Home Appliances (Large)': [
        'refrigerator', 'fridge', 'deep freezer', 'washing machine', 'dryer', 'water dispenser', 'dispenser'
    ],
    'Kitchen Appliances (Small)': [
        'microwave', 'oven', 'air fryer', 'blender', 'juicer', 'toaster', 'kettle'
    ],
    'Laptops & Computers': [
        'laptop', 'notebook', 'macbook', 'gaming laptop', 'i5', 'i7', 'ryzen', 'ssd', 'ram', 'tablet', 'ipad', 'monitor', 'desktop', 'pc'
    ],
    'Smartphones & Mobiles': [
        'iphone', 'samsung galaxy', 'xiaomi', 'oppo', 'vivo', 'infinix', 'tecno', 'smartphone', 'android', 'ios', 'mobile', 'cell phone', 'phone'
    ],
    'Audio & Accessories': [
        'earbuds', 'handsfree', 'headphone', 'headset', 'soundbar', 'speaker', 'bluetooth speaker', 'headphones', 'wireless headphones'
    ],
    'Entertainment': [
        'led tv', 'smart tv', 'android tv', 'google tv', 'television', 'projector', 'uhd', 'qled', 'oled',
        'nintendo switch', 'playstation', 'xbox'
    ],
    'Mobile Accessories': [
        'charger', 'power bank', 'cable', 'cover', 'case', 'band', 'strap', 'screen protector', 'adapter', 'ear tip'
    ],
    
    # Home & Living Categories
    'Furniture': [
        'sofa', 'bed', 'wardrobe', 'table', 'chair', 'almirah', 'dining table', 'coffee table', 'bookshelf', 'cabinet', 'dresser', 'nightstand'
    ],
    'Home Decor': [
        'decoration', 'decor', 'wall art', 'curtain', 'lamp', 'vase', 'mirror', 'cushion', 'pillow', 'rug', 'carpet'
    ],
    'Kitchen & Dining': [
        'kitchen utensils', 'cookware', 'dinnerware', 'cutlery', 'plates', 'bowls', 'cups', 'glasses', 'pots', 'pans'
    ],
    'Gardening & Outdoor': [
        'plant', 'pot', 'garden', 'lawn', 'outdoor furniture', 'cactus', 'succulent', 'bonsai', 'tree', 'flower', 'seed', 'fertilizer', 'tool'
    ],
    
    # Sports and Fitness Categories
    'Gym Equipment': [
        'dumbbell', 'treadmill', 'bench press', 'yoga mat', 'weights', 'barbell', 'kettlebell', 'resistance band', 'exercise bike', 'elliptical', 'dumbbells', 'set'
    ],
    'Sports Gear': [
        'cricket bat', 'football', 'hockey stick', 'tennis racket', 'badminton', 'basketball', 'soccer ball', 'golf club', 'baseball bat'
    ],
    'Sportswear': [
        'tracksuit', 'jersey', 'shorts', 'leggings', 'sports bra', 'athletic wear', 'gym wear', 'running shoes', 'sneakers', 'shoes', 'running'
    ],
    'Outdoor & Adventure': [
        'tent', 'camping', 'hiking', 'cycling', 'backpack', 'sleeping bag', 'camping gear', 'outdoor gear', 'bike', 'bicycle',
        'xtc', 'talon', 'trinity', 'trekking', 'mountain bike', 'mtb', 'road bike', 'hybrid bike', 'commuter bike'
    ],
}

CANONICAL_ALIASES: Dict[str, str] = {
    # Map legacy or alternative names to existing canonical categories in DB
    'home appliances (small)': 'Kitchen Appliances (Small)',
    'home appliances': 'Home Appliances (Large)',
}

# Negative keywords per category to prevent wrong matches
NEGATIVE_KEYWORDS: Dict[str, List[str]] = {
    # Electronics Categories
    'Laptops & Computers': [
        'water dispenser', 'dispenser', 'washing machine', 'microwave', 'oven', 'air fryer',
        'refrigerator', 'fridge', 'deep freezer', 'heater', 'tv', 'television', 'sofa', 'bed', 'chair',
        'stylus', 'pencil', 'pen', 'capacitive pen'
    ],
    'Entertainment': [
        'washing machine', 'dispenser', 'oven', 'air fryer', 'refrigerator', 'fridge', 'sofa', 'bed',
        'stylus', 'pencil', 'pen'
    ],
    'Kitchen Appliances (Small)': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'tv', 'television', 'sofa', 'bed', 'stylus', 'pencil', 'pen'
    ],
    'Home Appliances (Large)': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'sofa', 'bed', 'chair', 'stylus', 'pencil', 'pen'
    ],
    'Mobile Accessories': [
        'microwave', 'oven', 'washing machine', 'dispenser', 'refrigerator', 'fridge', 'sofa', 'bed', 'car', 'seat'
    ],
    'Smartphones & Mobiles': [
        'tv', 'television', 'led', 'uhd', 'qled', 'oled', 'inch', 'screen', 'display', 'tablet', 'ipad', 'sofa', 'bed',
        'stylus', 'pencil', 'pen'
    ],
    'Cooling & Heating': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'sofa', 'bed', 'chair', 'table', 'stylus', 'pencil', 'pen'
    ],
    'Audio & Accessories': [
        'sofa', 'bed', 'chair', 'table', 'laptop', 'notebook', 'macbook'
    ],
    
    # Home & Living Categories
    'Furniture': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'tv', 'television', 'microwave', 'oven', 'washing machine', 'dumbbell', 'dumbbells', 'shoes', 'uniform'
    ],
    
    # Sports and Fitness Categories
    'Gym Equipment': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'sofa', 'bed', 'chair', 'table', 'lipstick', 'pen', 'tyre'
    ],
    'Sports Gear': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'sofa', 'bed', 'chair', 'table'
    ],
    'Sportswear': [
        'laptop', 'notebook', 'macbook', 'sofa', 'bed', 'chair', 'table', 'leather'
    ],
    'Outdoor & Adventure': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'sofa', 'bed', 'chair', 'table', 'yamaha'
    ],
    
    # Home & Living Categories
    'Home Decor': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'mobile', 'phone', 'charger', 'cable'
    ],
    'Kitchen & Dining': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'mobile', 'phone', 'charger', 'cable'
    ],
    'Gardening & Outdoor': [
        'laptop', 'notebook', 'macbook', 'iphone', 'galaxy', 'mobile', 'phone', 'charger', 'cable'
    ],
}

# Targeted hard rules to correct common false-positives from keyword matching.
# Each entry is (compiled_regex, canonical_category_name)
HARD_RULES: List[tuple] = [
    # Appliances and cooling/heating
    (re.compile(r"\bwater\s+dispenser(s)?\b", re.I), 'Home Appliances (Large)'),
    (re.compile(r"\b(bladeless\s+)?fan\b", re.I), 'Cooling & Heating'),
    (re.compile(r"\bair\s+purifier\b", re.I), 'Cooling & Heating'),
    (re.compile(r"\bvacuum\s+cleaner\b", re.I), 'Home Appliances (Large)'),
    (re.compile(r"\bbedroom\s+(size\s+)?refrigerator\b", re.I), 'Home Appliances (Large)'),
    (re.compile(r"\b(single|bedroom)\s+door\s+refrigerator\b", re.I), 'Home Appliances (Large)'),

    # Audio
    (re.compile(r"\b(soundbar|portable\s+(bluetooth\s+)?speaker)\b", re.I), 'Audio & Accessories'),

    # Gaming consoles
    (re.compile(r"\b(nintendo\s+switch|playstation|ps\s*5|xbox)\b", re.I), 'Entertainment'),

    # Pens/stylus (avoid Stationery)
    (re.compile(r"\b(stylus|apple\s+pencil|capacitive\s+pen|drawing\s+pen|xp-?pen)\b", re.I), 'Mobile Accessories'),
]

def _canonicalize_category(name: str) -> str:
    key = (name or '').strip().lower()
    return CANONICAL_ALIASES.get(key, name)


def suggest_category(name: str, description: str = '') -> Optional[str]:
    """Suggest a category based on simple keyword rules.

    Returns the category name if a rule matches, otherwise None.
    """
    text = f"{name} {description}".lower()

    # 1) Apply hard rules first
    for pattern, target in HARD_RULES:
        if pattern.search(text):
            return _canonicalize_category(target)
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in text:
                # If any negative keyword for this category appears, skip
                negatives = NEGATIVE_KEYWORDS.get(category, [])
                if any(neg in text for neg in negatives):
                    continue
                return _canonicalize_category(category)
    return None


