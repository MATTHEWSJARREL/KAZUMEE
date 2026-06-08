// Minimal stub for `vite/client` when @types are not installed
interface ImportMetaEnv {
  readonly MODE?: string;
  readonly VITE_PUBLIC_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'vite/client' {}
