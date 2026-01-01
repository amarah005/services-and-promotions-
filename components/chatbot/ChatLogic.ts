import { SERVICES } from '../marketplace/mockData';

export interface ChatMessage {
    id: string;
    text: string;
    sender: 'user' | 'bot';
    data?: any[]; // Array of services to display
    type?: 'text' | 'result';
}

const parsePrice = (priceStr: string) => {
    return parseInt(priceStr.replace(/[^0-9]/g, ''), 10) || 0;
};

// Knowledge base for "AI" advice
const ADVICE_KB: Record<string, string[]> = {
    ac: [
        "For ACs, regular servicing every 6 months can reduce electricity bills by up to 15%.",
        "If your AC is leaking water, it usually means the drain pipe is clogged.",
        "Gas refilling is only needed if there's a leak; don't let technicians oversell it!"
    ],
    plumb: [
        "For new fittings, ensure they use non-corrosive materials.",
        "Leaky taps can waste up to 20 liters of water a day, so fixing them is a great saving.",
        "If you have low water pressure, it might just be sediment in the aerator."
    ],
    electric: [
        "Always check for certified electricians for safety.",
        "LED lights can save you significant money on your monthly bill.",
        "If your breaker trips frequently, you might be overloading a single circuit."
    ],
    clean: [
        "Deep cleaning is recommended before major festivals or after renovations.",
        "Ensure they use eco-friendly chemicals if you have pets or kids.",
        "Sofa cleaning usually takes 4-6 hours to dry completely."
    ],
    paint: [
        "Lighter colors make small rooms look bigger.",
        "Make sure they scrape off the old paint completely before applying the new coat.",
        "Emulsion paint is easier to clean than distemper."
    ],
    default: [
        "I recommend checking the reviews and details before booking.",
        "Comparing a few options is always a good idea to get the best deal.",
        "Let me know if you need help comparing prices!"
    ]
};

const getAdvice = (term: string) => {
    let category = 'default';
    if (term.includes('ac') || term.includes('cool')) category = 'ac';
    else if (term.includes('plumb') || term.includes('pipe') || term.includes('leak')) category = 'plumb';
    else if (term.includes('electr') || term.includes('light') || term.includes('power')) category = 'electric';
    else if (term.includes('clean') || term.includes('wash') || term.includes('dust')) category = 'clean';
    else if (term.includes('paint') || term.includes('color')) category = 'paint';

    const adviceList = ADVICE_KB[category];
    return adviceList[Math.floor(Math.random() * adviceList.length)];
};

export const processUserQuery = (text: string): ChatMessage => {
    const query = text.toLowerCase();

    // 1. Identify Intent (Sort/Filter)
    let sortBy = 'default';
    if (query.includes('cheap') || query.includes('lowest') || query.includes('budget') || query.includes('low price')) {
        sortBy = 'price_asc';
    } else if (query.includes('expensive') || query.includes('highest') || query.includes('premium')) {
        sortBy = 'price_desc';
    }

    // 2. Identify Search Terms (remove stopwords for better matching)
    const stopWords = ['find', 'me', 'a', 'the', 'service', 'for', 'is', 'cheapest', 'expensive', 'show', 'list', 'about', 'need', 'want', 'looking'];
    const searchTerms = query.split(' ').filter(word => !stopWords.includes(word) && word.length > 2);

    // 3. Filter Data
    let results = SERVICES.filter(item => {
        if (searchTerms.length === 0) return true; // If no specific term, might just want "cheapest items"
        return searchTerms.some(term =>
            item.title.toLowerCase().includes(term) ||
            (item.details && item.details.toLowerCase().includes(term))
        );
    });

    // 4. precise filtering: if user said "AC", ensure we truly prioritize AC results
    // (The basic filter above handles this well enough for now)

    // 5. Apply Sorting
    if (sortBy === 'price_asc') {
        results.sort((a, b) => parsePrice(a.price) - parsePrice(b.price));
    } else if (sortBy === 'price_desc') {
        results.sort((a, b) => parsePrice(b.price) - parsePrice(a.price));
    }

    // Limit results to top 3 for chat
    const topResults = results.slice(0, 3);

    // 6. Generate "GPT-like" Contextual Response
    let responseText = '';
    const term = searchTerms.join(' ');
    const advice = getAdvice(term);

    if (topResults.length === 0) {
        responseText = `I understand you're looking for help with "${term}", but I couldn't find any specific services listed right now.\n\nHowever, ${advice.toLowerCase()} \n\nTry searching for broader terms like 'Cleaning' or 'Repair'.`;
    } else {
        // Construct rich response
        const intro = sortBy === 'price_asc'
            ? `I found some budget-friendly options for **${term}**.`
            : sortBy === 'price_desc'
                ? `Here are the most premium **${term}** services available.`
                : `I've found some highly-rated services for **${term}**.`;

        const reasoning = `\n\n💡 **Tip:** ${advice}`;

        const conclusion = `\n\nHere are the top ${topResults.length} picks I recommend based on your request:`;

        responseText = `${intro}${reasoning}${conclusion}`;
    }

    return {
        id: Date.now().toString(),
        text: responseText,
        sender: 'bot',
        type: topResults.length > 0 ? 'result' : 'text',
        data: topResults
    };
};
