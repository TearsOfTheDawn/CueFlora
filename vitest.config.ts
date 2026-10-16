import { defineConfig } from 'vitest/config';
import { WxtVitest } from 'wxt/testing/vitest-plugin';

export default defineConfig({
  test: {
    include: ['entrypoints/**/*.test.ts', 'utils/**/*.test.ts'],
    mockReset: true,
    restoreMocks: true,
    environment: 'jsdom',
  },
  plugins: [WxtVitest()],
});
