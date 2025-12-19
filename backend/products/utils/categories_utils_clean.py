from typing import Dict, List, Optional
import re


# Clean category rules matching current 3-category database structure
CATEGORY_RULES: Dict[str, List[str]] = {
    # Electronics Categories
    'Audio & Accessories': [
        'earbuds', 'handsfree', 'headphone', 'headset', 'soundbar', 'speaker', 'bluetooth speaker', 'headphones', 'wireless headphones'
    ],
    'Cooling & Heating': [
        'split ac', 'air conditioner', 'inverter ac', '1.0 ton', '1.5 ton', '2 ton', 'heater', 'room heater'
    ],
    'Entertainment': [
        'led tv', 'smart tv', 'android tv', 'google tv', 'television', 'projector', 'uhd', 'qled', 'oled',
        'nintendo switch', 'playstation', 'xbox'
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
    'Mobile Accessories': [
        'charger', 'power bank', 'cable', 'cover', 'case', 'band', 'strap', 'screen protector', 'adapter', 'ear tip'
    ],
    'Smartphones & Mobiles': [
        'iphone', 'samsung galaxy', 'xiaomi', 'oppo', 'vivo', 'infinix', 'tecno', 'smartphone', 'android', 'ios', 'mobile', 'cell phone', 'phone'
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
        'cricket bat', 'football', 'soccer ball', 'basketball', 'volleyball', 'tennis ball', 'tennis racket', 'badminton racket', 'shuttlecock', 'hockey stick', 'golf club', 'golf ball', 'table tennis', 'ping pong', 'paddle', 'ball', 'shinpad', 'goggle', 'swimming', 'sport', 'athletic', 'competition', 'game'
    ],
    'Sportswear': [
        'tracksuit', 'jersey', 'shorts', 'leggings', 'athletic wear', 'sports clothing', 'workout clothes', 'gym wear', 'running shirt', 'joggers', 'sweatpants', 'hoodie', 'sports bra', 'compression shirt', 'moisture wicking', 'dri-fit', 'breathable fabric'
    ],
    'Outdoor & Adventure': [
        'tent', 'camping', 'hiking', 'cycling', 'outdoor gear', 'adventure equipment', 'backpack', 'sleeping bag', 'water bottle', 'camping chair', 'portable chair', 'outdoor furniture', 'fishing rod', 'fishing reel', 'tackle box', 'climbing rope', 'carabiner'
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
        'laptop', 'notebook', 'macbook'
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
}

# Hard pattern-based rules
HARD_RULES = [
    # Water dispensers and dispensers go to large appliances
    (re.compile(r'\b(?:water\s+)?dispenser\b', re.IGNORECASE), 'Home Appliances (Large)'),
    (re.compile(r'\b(?:smart\s+)?tv\b', re.IGNORECASE), 'Entertainment'),
    (re.compile(r'\btelevision\b', re.IGNORECASE), 'Entertainment'),
]


def _canonicalize_category(name: str) -> str:
    """Canonicalize category name using aliases."""
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
