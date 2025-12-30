import { GoogleGenerativeAI } from "@google/generative-ai";
import { SERVICES } from '../marketplace/mockData';
import { ChatMessage, processUserQuery } from './ChatLogic';

// ⚠️ REPLACE WITH YOUR API KEY
// Get one here for free: https://aistudio.google.com/app/apikey
const API_KEY = "AIzaSyBhaxYCzPqzOE2NJswCbaW2V4560ID1QVw";

const genAI = new GoogleGenerativeAI(API_KEY);

export const generateSmartResponse = async (userQuery: string): Promise<ChatMessage> => {
    try {
        // 1. RAG STEP: Improved Scoring Search
        const minKeywordLength = 2;
        const queryKeywords = userQuery.toLowerCase()
            .replace(/[^\w\s]/g, '') // remove punctuation
            .split(' ')
            .filter(w => w.length > minKeywordLength && !['what', 'where', 'how', 'when', 'who', 'show', 'tell', 'need', 'want'].includes(w));

        // Calculate score for each service
        const ScoredServices = SERVICES.map(item => {
            let score = 0;
            const content = (item.title + ' ' + (item.details || '')).toLowerCase();

            queryKeywords.forEach(keyword => {
                if (content.includes(keyword)) {
                    score += 1;
                    // Boost exact title matches
                    if (item.title.toLowerCase().includes(keyword)) score += 2;
                }
            });

            // Context boost: If query mentions "AC", boost services with "AC" in title significantly
            if (userQuery.toLowerCase().includes('ac') && item.title.toLowerCase().includes('ac')) {
                score += 5;
            }

            return { item, score };
        });

        // Filter and Sort by Score
        const relevantServices = ScoredServices
            .filter(s => s.score > 0)
            .sort((a, b) => b.score - a.score) // Descending score
            .slice(0, 5) // Take top 5 strictly relevant items
            .map(s => s.item);

        // 2. Construct the Prompt
        const contextString = relevantServices.map(s =>
            `- Service: ${s.title}, Price: ${s.price}, Details: ${s.details || 'N/A'}`
        ).join('\n');

        const prompt = `
        You are a helpful assistant for a Home Services Marketplace app.
        
        USER QUESTION: "${userQuery}"

        Here is the relevant data available in our catalog (Context):
        ${contextString}

        INSTRUCTIONS:
        1. Answer the user's question simply and helpfully.
        2. If you recommend specific services from the list, mention them by name and price.
        3. Do not mention "ID" or internal database fields.
        4. If no specific service fits, give general advice but mention we might not have it.
        5. Keep it conversational and friendly.
        `;

        // 3. Call Gemini
        // Try the flash model first
        const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
        const result = await model.generateContent(prompt);
        const response = await result.response;
        const text = response.text();

        // 4. Return formatted message
        return {
            id: Date.now().toString(),
            text: text,
            sender: 'bot',
            type: relevantServices.length > 0 ? 'result' : 'text',
            data: relevantServices.slice(0, 3)
        };

    } catch (error) {
        console.error("Gemini Error:", error);

        // FALLBACK: Use local logic if API fails (e.g. 404 Invalid Key/Model)
        console.log("Falling back to local logic...");
        const localResponse = processUserQuery(userQuery);
        localResponse.text = "(Offline Mode) " + localResponse.text; // Indicate fallback
        return localResponse;
    }
};
