/**
 * Speech Recognition Utility
 * Handles browser speech-to-text conversion
 */

export interface SpeechRecognitionConfig {
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (error: string) => void;
  onStart?: () => void;
  onEnd?: () => void;
}

export class SpeechToText {
  private recognition: any;
  private isListening = false;
  private transcript = "";

  constructor() {
    const SpeechRecognition =
      (typeof window !== "undefined" &&
        ((window as any).SpeechRecognition ||
          (window as any).webkitSpeechRecognition)) ||
      null;

    if (!SpeechRecognition) {
      console.warn("Speech Recognition API not supported in this browser");
      return;
    }

    this.recognition = new SpeechRecognition();
  }

  start(config: SpeechRecognitionConfig = {}): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.recognition) {
        reject(new Error("Speech Recognition not supported"));
        return;
      }

      this.recognition.language = config.language || "en-US";
      this.recognition.continuous = config.continuous || false;
      this.recognition.interimResults = config.interimResults !== false;

      this.transcript = "";
      this.isListening = true;

      this.recognition.onstart = () => {
        config.onStart?.();
      };

      this.recognition.onresult = (event: any) => {
        let interimTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;

          if (event.results[i].isFinal) {
            this.transcript += transcript + " ";
          } else {
            interimTranscript += transcript;
          }
        }

        const finalTranscript = this.transcript.trim();
        config.onResult?.(
          finalTranscript || interimTranscript,
          event.results[event.results.length - 1].isFinal
        );
      };

      this.recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        config.onError?.(event.error || "Unknown error");
        reject(event.error);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        config.onEnd?.();
        resolve(this.transcript.trim());
      };

      this.recognition.start();
    });
  }

  stop(): string {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
    }
    return this.transcript.trim();
  }

  abort(): void {
    if (this.recognition) {
      this.recognition.abort();
      this.isListening = false;
      this.transcript = "";
    }
  }

  isSupported(): boolean {
    return !!this.recognition;
  }
}

/**
 * Hook-friendly function to start speech recognition
 */
export async function startListening(
  config: SpeechRecognitionConfig = {}
): Promise<string> {
  const speech = new SpeechToText();
  return speech.start(config);
}
