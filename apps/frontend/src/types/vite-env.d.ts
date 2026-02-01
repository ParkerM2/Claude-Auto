/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_MODE?: 'development' | 'production'
  // Add more Vite env variables here as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
