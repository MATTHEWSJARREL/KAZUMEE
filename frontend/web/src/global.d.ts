import 'react-router';

/* ---------------- Virtual / Build-time modules ---------------- */

declare module 'virtual:load-fonts.jsx' {
  export function LoadFonts(): null;
}

/* ---------------- React Router augmentation ---------------- */

declare module 'react-router' {
  interface AppLoadContext {
    // extend if needed
  }
}

/* ---------------- Third-party modules without local types ---------------- */

declare module 'npm:stripe' {
  import Stripe from 'stripe';
  export default Stripe;
}

/* ---------------- Local JSX modules (TSX importing JSX) ---------------- */

declare module '@/lib/ClipSearchContext' {
  import { ReactNode } from 'react';

  export function ClipSearchProvider(props: {
    children: ReactNode;
  }): JSX.Element;
}

declare module '@/components/ClipSearchResults' {
  export default function ClipSearchResults(): JSX.Element;
}

declare module '@/components/ObsStatus' {
  export default function ObsStatus(): JSX.Element;
}

/* ---------------- Global environment stubs ---------------- */

declare global {
  type SpeechRecognition = any;
  type SpeechRecognitionEvent = any;

  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }

  interface ImportMetaEnv {
    readonly MODE?: string;
    readonly VITE_API_URL?: string;
    readonly VITE_PUBLIC_URL?: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }

  namespace NodeJS {
    interface ProcessEnv {
      [key: string]: string | undefined;
    }
  }

  var process: NodeJS.Process;
}

export {};
