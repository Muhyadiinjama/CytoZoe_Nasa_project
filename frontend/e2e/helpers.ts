import type { Page } from "@playwright/test";

/**
 * Network isolation: every request that is not to the loopback service is aborted and recorded.
 * This proves the core flow needs no CDN, font, analytics or cloud request (T26/T27).
 */
export async function isolate(page: Page): Promise<string[]> {
  const external: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "127.0.0.1" || url.hostname === "localhost" || url.protocol === "data:" || url.protocol === "blob:") {
      return route.continue();
    }
    external.push(route.request().url());
    return route.abort("internetdisconnected");
  });
  return external;
}

export async function apiReset(page: Page) {
  // Each spec file shares one fresh server; tests use distinct findings to stay independent.
  await page.goto("/overview?participant=C001&sample=L-3");
}
