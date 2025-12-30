const fs = require('fs');
const path = require('path');

const csvPath = path.join(__dirname, '../assets/data/data2.csv');
const outputPath = path.join(__dirname, '../components/marketplace/mockData.ts');

const csvContent = fs.readFileSync(csvPath, 'utf8');
const lines = csvContent.split('\n');
const services = [];

// Simple CSV line parser that handles quotes
function parseCSVLine(text) {
    const result = [];
    let cell = '';
    let quote = false;
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        if (char === '"') {
            quote = !quote;
        } else if (char === ',' && !quote) {
            result.push(cell);
            cell = '';
        } else {
            cell += char;
        }
    }
    result.push(cell);
    return result;
}

// Skip header
for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Columns: Platform, Service_Title, Details, Price, Link, Image_Path
    const cols = parseCSVLine(line);
    if (cols.length < 6) continue;

    const id = (i).toString();
    const title = cols[1].trim();
    const details = cols[2].trim();
    const priceRaw = cols[3].trim(); // "Rs:3300"
    let price = priceRaw.replace('Rs:', 'Rs '); // Format to "Rs 3300"
    const link = cols[4].trim(); // Extract link URL

    // Image Path: image3/mahir_1.jpg -> we need maher_1.jpg and map to imagee2
    const imagePathRaw = cols[5].trim();
    const imageName = imagePathRaw.split('/')[1]; // maher_1.jpg

    // Randomly assign badges to 20% of items
    const badges = ['Best Seller', 'New', 'Hot', 'Discount'];
    const badge = Math.random() > 0.8 ? badges[Math.floor(Math.random() * badges.length)] : null;

    // Assign a color based on id logic to keep it colorful
    const colors = ['#3b82f6', '#a855f7', '#22c55e', '#eab308', '#ec4899', '#14b8a6', '#f97316', '#ef4444', '#64748b'];
    const color = colors[i % colors.length];

    // Fix capitalization in titles (e.g. "AC installation" -> "AC Installation")
    const formattedTitle = title.replace(/\b\w/g, l => l.toUpperCase());

    services.push({
        id,
        title: formattedTitle,
        badge,
        price,
        color,
        imageName: imageName,
        details,
        link
    });
}

const fileContent = `export const SERVICES = [
${services.map(s => `  {
    id: '${s.id}',
    title: ${JSON.stringify(s.title)},
    badge: ${JSON.stringify(s.badge)},
    price: ${JSON.stringify(s.price)},
    color: '${s.color}',
    details: ${JSON.stringify(s.details)},
    link: ${JSON.stringify(s.link)},
    image: require('../../assets/data/image2/${s.imageName}')
  }`).join(',\n')}
];
`;

fs.writeFileSync(outputPath, fileContent);
console.log('Successfully generated mockData.ts with ' + services.length + ' items.');
