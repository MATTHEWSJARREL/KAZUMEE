/**
 * Groq API Client
 * Handles all AI/voice command processing through Groq
 */

const GROQ_API_KEY = process.env.NEXT_PUBLIC_GROQ_API_KEY;
const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";

interface GroqMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

interface GroqResponse {
  choices: Array<{
    message: {
      content: string;
    };
  }>;
}

/**
 * Send a message to Groq and get AI response
 */
export async function askGroq(
  userMessage: string,
  conversationHistory: GroqMessage[] = [],
  systemPrompt: string = "You are Kazumee, an AI streaming assistant. Help streamers with their questions about gaming, streaming, and content creation. Keep responses concise and helpful."
): Promise<string> {
  if (!GROQ_API_KEY) {
    throw new Error("Groq API key not configured. Add NEXT_PUBLIC_GROQ_API_KEY to .env.local");
  }

  try {
    // Build message history
    const messages: GroqMessage[] = [
      { role: "system", content: systemPrompt },
      ...conversationHistory,
      { role: "user", content: userMessage }
    ];

    const response = await fetch(GROQ_API_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${GROQ_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "mixtral-8x7b-32768",
        messages: messages,
        temperature: 0.7,
        max_tokens: 500,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Groq API error: ${error.error?.message || "Unknown error"}`);
    }

    const data: GroqResponse = await response.json();
    return data.choices[0].message.content;
  } catch (error) {
    console.error("Groq API Error:", error);
    throw error;
  }
}

/**
 * Process voice command and get Groq response
 * Can return links to videos, strategies, etc.
 */
export async function processVoiceCommand(
  voiceText: string,
  context: { game?: string; platform?: string } = {}
): Promise<{
  response: string;
  links?: Array<{ title: string; url: string; type: "video" | "guide" | "strategy" }>;
}> {
  const gameContext = context.game ? `The streamer is playing ${context.game}. ` : "";
  const prompt = `${gameContext}A viewer asked the streamer: "${voiceText}".

  Provide a helpful response. If relevant, suggest where to find video tutorials or guides (by saying "Check out [title] on YouTube" or "See [guide] on [site]").
  Keep it concise (1-2 sentences max).`;

  const response = await askGroq(voiceText, [], prompt);

  // Extract any links mentioned
  const linkRegex = /(?:https?:\/\/[^\s]+|(?:YouTube|Google|twitch\.tv|discord\.com)[^\s]*)/g;
  const links = response.match(linkRegex) || [];

  return {
    response,
    links: links.map(link => ({
      title: link,
      url: link.startsWith("http") ? link : `https://www.google.com/search?q=${encodeURIComponent(link)}`,
      type: "video" as const
    }))
  };
}

/**
 * Get streaming tips from Groq
 */
export async function getStreamingTip(topic: string): Promise<string> {
  const systemPrompt = `You are Kazumee, a streaming expert. Give quick, actionable tips for streamers.
  Keep responses to 1-2 sentences max. Be specific and practical.`;

  return askGroq(
    `Give me a tip about: ${topic}`,
    [],
    systemPrompt
  );
}

/**
 * Backseat gaming: Give strategy advice for a game
 */
export async function getGameStrategy(
  game: string,
  situation: string
): Promise<string> {
  const systemPrompt = `You are Kazumee, a gaming expert assistant. Give quick strategy tips for the streamer's current situation.
  Be concise (1-2 sentences). Focus on practical, actionable advice.`;

  return askGroq(
    `The streamer is playing ${game}. Their current situation: ${situation}. What should they do?`,
    [],
    systemPrompt
  );
}

/**
 * Format response for display
 */
export function formatGroqResponse(text: string): string {
  return text
    .replace(/\*\*/g, "") // Remove markdown bold
    .replace(/\*/g, "") // Remove remaining asterisks
    .trim();
}
