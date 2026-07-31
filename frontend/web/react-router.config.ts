import type { Config } from '@react-router/dev/config';

// Client-side only build for Vercel static hosting
export default {
	appDirectory: './src/app',
	ssr: false,
	prerender: [],
} satisfies Config;
