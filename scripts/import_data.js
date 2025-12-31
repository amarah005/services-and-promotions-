const fs = require('fs');
const path = require('path');

const OUTPUT_PATH = path.join(__dirname, '../components/marketplace/mockData.ts');

const SOURCES = [
    {
        path: '../assets/data/data2.csv',
        type: 'MAHIR',
        imageDir: '../../assets/data/image2/' // Existing logic
    },
    {
        path: '../assets/data2/data2.csv',
        type: 'MAHIR',
        imageDir: '../../assets/data2/image2/image3/' // New Mahir data location
    },
    {
        path: '../assets/data2/data1.csv',
        type: 'GURU',
        imageDir: '../../assets/data2/image1/image2/' // Guru data location
    }
];

const services = [];
let globalId = 1;

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

SOURCES.forEach(source => {
    try {
        const csvPath = path.join(__dirname, source.path);
        if (!fs.existsSync(csvPath)) {
            console.warn(`Skipping missing file: ${csvPath}`);
            return;
        }

        const csvContent = fs.readFileSync(csvPath, 'utf8');
        const lines = csvContent.split('\n');

        // Skip header
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            const cols = parseCSVLine(line);

            let title, price, details, link, imageName;

            if (source.type === 'MAHIR') {
                // Platform, Service_Title, Details, Price, Link, Image_Path
                if (cols.length < 6) continue;
                title = cols[1].trim();
                details = cols[2].trim();
                let priceRaw = cols[3].trim();
                price = priceRaw.replace('Rs:', 'Rs ').replace('Rs', 'Rs '); // Normalize "Rs:" -> "Rs "
                link = cols[4].trim();
                const imagePathRaw = cols[5].trim();
                imageName = imagePathRaw.split('/').pop(); // Extract filename (mahir_x.jpg)
            } else if (source.type === 'GURU') {
                // Platform, Title, Company, Budget, Link, Image_Path
                if (cols.length < 6) continue;
                title = cols[1].trim();
                const company = cols[2].trim();
                details = company ? `By ${company}` : 'Professional Service';
                price = cols[3].trim().replace(/\s+/g, ' '); // Clean up budget string
                link = cols[4].trim();
                const imagePathRaw = cols[5].trim();
                imageName = imagePathRaw.split('/').pop(); // Extract filename (service_x.jpg)
            }

            // Capitalize Title
            const formattedTitle = title.replace(/\b\w/g, l => l.toUpperCase());

            // Badges & Colors
            const badges = ['Best Seller', 'New', 'Hot', 'Discount'];
            const badge = Math.random() > 0.85 ? badges[Math.floor(Math.random() * badges.length)] : null;
            const colors = ['#3b82f6', '#a855f7', '#22c55e', '#eab308', '#ec4899', '#14b8a6', '#f97316', '#ef4444', '#64748b'];
            const color = colors[globalId % colors.length];

            services.push({
                id: (globalId++).toString(),
                title: formattedTitle,
                badge,
                price,
                color,
                imageDir: source.imageDir,
                imageName,
                details,
                link
            });
        }
    } catch (e) {
        console.error(`Error processing ${source.path}:`, e);
    }
});

const fileContent = `export const SERVICES = [
${services.map(s => `  {
    id: '${s.id}',
    title: ${JSON.stringify(s.title)},
    badge: ${JSON.stringify(s.badge)},
    price: ${JSON.stringify(s.price)},
    color: '${s.color}',
    details: ${JSON.stringify(s.details)},
    link: ${JSON.stringify(s.link)},
    image: require('${s.imageDir}${s.imageName}')
  }`).join(',\n')}
];
`;

fs.writeFileSync(OUTPUT_PATH, fileContent);
console.log('Successfully generated mockData.ts with ' + services.length + ' items.');
