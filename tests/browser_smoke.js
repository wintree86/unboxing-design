// Optional Playwright MCP probe. Navigate to a fresh SYNTHETIC fixture board first.
// Never run this against a real design decision; it submits a synthetic choice.
async (page) => {
  const origin = new URL(page.url()).origin;
  const initial = await (await page.request.get(`${origin}/status`)).json();
  if (initial.run_id !== "browser" || initial.phase !== "awaiting_direction" ||
      initial.references?.[0]?.url !== "https://example.com/reference" ||
      initial.candidates?.[0]?.concept !== "Concept a") {
    throw new Error("This probe only accepts a fresh synthetic installation fixture.");
  }
  const measurements = [];
  for (const width of [390, 1200]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(origin);
    await page.locator("#gallery img[src]").first().waitFor();
    await page.evaluate(async () => {
      await Promise.all(Array.from(document.querySelectorAll("#gallery img[src]")).map(i => i.decode()));
    });
    measurements.push(await page.evaluate(() => {
      const images = Array.from(document.querySelectorAll("#gallery img[src]"));
      return {
        width: innerWidth,
        overflow: Math.max(0, document.documentElement.scrollWidth - innerWidth),
        images: images.length,
        loadedImages: images.filter(i => i.complete && i.naturalWidth > 0).length,
        choices: document.querySelectorAll("input[type=radio]").length,
        selectedChoices: document.querySelectorAll("input[type=radio]:checked").length,
      };
    }));
  }
  await page.locator("#choose-a").check();
  await page.locator("#reason").fill("Synthetic installation test; not a real user decision");
  const submitted = page.waitForResponse(r => r.url() === `${origin}/event` && r.request().method() === "POST");
  await page.locator("#decision button").click();
  const response = await submitted;
  const saved = await response.json();
  await page.reload();
  const resumed = await (await page.request.get(`${origin}/status`)).json();
  const result = { measurements, httpStatus: response.status(), saved,
    resumed: { phase: resumed.phase, candidate: resumed.selected?.candidate_id } };
  if (measurements.some(m => m.overflow !== 0 || m.images !== 2 || m.loadedImages !== 2 ||
      m.choices !== 2 || m.selectedChoices !== 0) || response.status() !== 200 ||
      resumed.phase !== "refining" || resumed.selected?.candidate_id !== "a") {
    throw new Error(JSON.stringify(result));
  }
  return result;
}
