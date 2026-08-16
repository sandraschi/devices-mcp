import { test, expect } from '@playwright/test';
const BACKEND = 'http://127.0.0.1:10717';
const FRONTEND = 'http://127.0.0.1:10716';

test.describe('Fleet Audit', () => {
    test('Backend health check', async ({ request }) => {
        const resp = await request.get(BACKEND + '/health');
        expect(resp.status()).toBe(200);
    });
    test('Frontend loads', async ({ page }) => {
        const resp = await page.goto(FRONTEND, { timeout: 15000 });
        expect(resp?.status()).toBe(200);
    });
    test('No console errors', async ({ page }) => {
        const errors = [];
        page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
        await page.goto(FRONTEND, { timeout: 15000 });
        await page.waitForTimeout(5000);
        expect(errors.length).toBe(0);
    });
});
