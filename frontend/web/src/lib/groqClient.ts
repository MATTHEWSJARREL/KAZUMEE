/**
 * Groq API Client
 * Routes requests through backend to avoid CORS issues
 */

const BACKEND_URL = typeof window !== "undefined"
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "http://localhost:8000";
const GROQ_API_URL = `${BACKEND_URL}/api/groq/chat`;

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
  systemPrompt: string = `You are Kazumee, the vibe streaming buddy. You're chill, real, and know the streamer life.
  - Keep it SHORT and conversational (1-3 sentences max, unless they ask for details)
  - Use casual language, drop some streaming slang when it fits
  - Be supportive and hyped about their stream
  - Use emojis sparingly but when it makes sense (like 🔥 for fire content, 💜 for love)
  - You're not a robot - you're a friend in their ear while they stream
  - If you don't know something specific, be honest about it but suggest what to try
  - No boring long paragraphs - keep it punchy`
): Promise<string> {
  try {
    // Build message history (excluding system prompt as it's handled separately)
    const messages: GroqMessage[] = [
      ...conversationHistory,
      { role: "user", content: userMessage }
    ];

    const response = await fetch(GROQ_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: messages,
        system_prompt: systemPrompt,
        temperature: 0.7,
        max_tokens: 500,
      }),
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to get response from Kazumee");
    }

    const data = await response.json();
    return data.response;
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
  const systemPrompt = `You are Kazumee, the streaming buddy. Give quick, real streaming tips.
  - 1-2 sentences MAX
  - Make it actionable right now
  - Be genuine, not generic
  - Sound like you're texting a friend, not reading from a guide`;

  return askGroq(
    `Quick tip about: ${topic}`,
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
  const systemPrompt = `You are Kazumee, the hype backseat gamer. Give quick play tips like a buddy watching their screen.
  - 1-2 sentences MAX
  - Be encouraging but real
  - If you see the play, call it out excitedly
  - Sound like you're vibing with them, not coaching them`;

  return askGroq(
    `${game} - ${situation}. What's the move?`,
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
