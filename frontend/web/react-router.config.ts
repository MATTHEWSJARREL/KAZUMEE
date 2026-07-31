import type { Config } from '@react-router/dev/config';

export default {
	appDirectory: './src/app',
	ssr: false,
	// Disable prerender for client-only build on Vercel
	prerender: [],
} satisfies Config;
