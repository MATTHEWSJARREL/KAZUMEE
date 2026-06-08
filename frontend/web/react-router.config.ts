import type { Config } from '@react-router/dev/config';

export default {
	appDirectory: './src/app',
	ssr: true,
	// Keep prerender to root only; wildcard patterns like "/*?" create invalid
	// artifact paths during production builds.
	prerender: ['/'],
} satisfies Config;
