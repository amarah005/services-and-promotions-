/**
 * Utility functions for category management
 * Ported from web frontend
 */

export const staticCategoryImages = {
    'Electronics': 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400&h=300&fit=crop&crop=center',
    'Home & Living': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop&crop=center',
    'Sports & Fitness': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop&crop=center',
    'Beauty & Personal Care': 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=300&fit=crop&crop=center',
    'Clothing & Fashion': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=300&fit=crop&crop=center',
    'Books & Stationery': 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=300&fit=crop&crop=center',
    'Toys & Games': 'https://plus.unsplash.com/premium_photo-1684795780266-ecd819f04f96?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&q=80&w=400&h=300',
    'Automobiles & Accessories': 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=400&h=300&fit=crop&crop=center'
};

/**
 * Gets category image URL with fallback
 * @param {string} categoryName - Name of the category
 * @returns {string} - Image URL for the category
 */
export const getCategoryImage = (categoryName) => {
    return staticCategoryImages[categoryName] || 'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400&h=300&fit=crop&crop=center';
};

/**
 * Ensures categories are unique by name
 * @param {Array} categories - Array of category objects
 * @returns {Array} - Array of unique categories
 */
export const getUniqueCategories = (categories) => {
    if (!Array.isArray(categories)) {
        return [];
    }

    return categories.filter((category, index, self) =>
        index === self.findIndex(c => c.name === category.name)
    );
};

// Preferred category order
export const categoryOrder = [
    'Electronics',
    'Home & Living',
    'Sports & Fitness',
    'Beauty & Personal Care',
    'Clothing & Fashion',
    'Books & Stationery',
    'Toys & Games',
    'Automobiles & Accessories'
];

/**
 * Sort categories by preferred order
 */
export const sortCategoriesByOrder = (categories) => {
    return [...categories].sort((a, b) => {
        const indexA = categoryOrder.indexOf(a);
        const indexB = categoryOrder.indexOf(b);

        // If both categories are in the order list, sort by their position
        if (indexA !== -1 && indexB !== -1) {
            return indexA - indexB;
        }

        // If only A is in the list, it comes first
        if (indexA !== -1) return -1;

        // If only B is in the list, it comes first
        if (indexB !== -1) return 1;

        // If neither is in the list, sort alphabetically
        return a.localeCompare(b);
    });
};

/**
 * Get icon name for category (using Feather icons)
 */
export const getCategoryIconName = (categoryName) => {
    const name = categoryName.toLowerCase();
    if (name.includes('electronic')) return 'smartphone';
    if (name.includes('fashion') || name.includes('clothing')) return 'shopping-bag'; // 'shirt' not in Feather, using shopping-bag
    if (name.includes('home') || name.includes('garden')) return 'home';
    if (name.includes('beauty') || name.includes('cosmetic')) return 'star'; // 'sparkles' not in Feather
    if (name.includes('sport') || name.includes('fitness')) return 'activity'; // 'dumbbell' not in Feather
    if (name.includes('book') || name.includes('education')) return 'book-open';
    if (name.includes('toy') || name.includes('game')) return 'smile'; // 'baby' not in Feather
    if (name.includes('automotive') || name.includes('car')) return 'truck'; // 'car' not in Feather
    return 'gift';
};
