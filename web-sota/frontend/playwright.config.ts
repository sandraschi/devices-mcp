import { defineConfig } from '@playwright/test';
export default defineConfig({
    testDir: './e2e',
    timeout: 60000,
    retries: 1,
    use: { headless: true, screenshot: 'only-on-failure' },
    webServer: [],
});
