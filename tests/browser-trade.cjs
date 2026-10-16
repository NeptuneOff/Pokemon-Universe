// Optional real-browser check: npm install --no-save playwright && npx playwright install chromium
// node tests/browser-trade.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
async function run(chromium, launchOptions = {}) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "meridian-browser-"));
  process.env.MERIDIAN_SAVE_DIR = temp;
  const { server } = require("../server.cjs");
  let browser;
  try {
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    browser = await chromium.launch({ headless: true, ...launchOptions });
    const pages = [];
    const errors = [];
    const click = (p, name) =>
      p.getByRole("button", { name, exact: true }).evaluate((el) => el.click());
    const wait = (p, fn) =>
      p.waitForFunction(fn, null, { polling: 100, timeout: 15000 });
    for (const label of ["Alpha", "Beta"]) {
      const context = await browser.newContext({
        viewport: { width: 1440, height: 1000 },
      });
      const p = await context.newPage();
      pages.push(p);
      p.setDefaultTimeout(15000);
      p.on("pageerror", (e) => errors.push(e.message));
      await p.goto("http://127.0.0.1:" + server.address().port);
      await click(p, "Jouer en duo");
      await p.locator("#playerName").fill(label);
      if (label === "Alpha") await click(p, "Créer la partie");
      else {
        await p
          .locator("#joinCode")
          .fill(await pages[0].evaluate(() => Meridian.net.code));
        await click(p, "Rejoindre");
      }
      await p
        .getByRole("button", {
          name: label === "Alpha" ? /Bulbizarre/ : /Salamèche/,
        })
        .evaluate((el) => el.click());
      await click(p, "Continuer →");
      await wait(p, () => !!Meridian.net.snapshot.game);
    }
    const [a, b] = pages;
    await wait(a, () => Meridian.net.snapshot.players.every((p) => p.position));
    await a.locator("#menuBtn").evaluate((el) => el.click());
    await click(a, "Échanger avec mon partenaire");
    for (const p of pages) await p.locator("#tradePanel").waitFor();
    await a.locator("#tradePokemon").selectOption("0");
    await a.locator("#tradeBalls").fill("3");
    assert.ok(
      await a
        .getByRole("button", { name: "Confirmer cet échange", exact: true })
        .isDisabled(),
    );
    await click(a, "Mettre à jour mon offre");
    await wait(b, () =>
      Object.values(Meridian.net.snapshot.trade.offers).some(
        (o) => o.balls === 3,
      ),
    );
    await b.locator("#tradePokemon").selectOption("0");
    await b.locator("#tradePotions").fill("2");
    await click(b, "Mettre à jour mon offre");
    await wait(a, () =>
      Object.values(Meridian.net.snapshot.trade.offers).some(
        (o) => o.potions === 2,
      ),
    );
    await click(a, "Confirmer cet échange");
    await wait(
      b,
      () => Object.keys(Meridian.net.snapshot.trade.confirmed).length === 1,
    );
    // A reload must reopen the reserved exchange, without losing the partner's confirmation.
    await b.reload();
    await click(b, "Jouer en duo");
    await click(b, "Reprendre ma connexion");
    await b.locator("#tradePanel").waitFor();
    assert.equal(
      await b.evaluate(
        () => Object.keys(Meridian.net.snapshot.trade.confirmed).length,
      ),
      1,
    );
    if (process.env.TEST_SCREENSHOT)
      await b.screenshot({ path: process.env.TEST_SCREENSHOT });
    await click(b, "Confirmer cet échange");
    for (const p of pages)
      await wait(p, () => Meridian.net.snapshot.trade.status === "completed");
    assert.deepEqual(
      await a.evaluate(() => [
        Meridian.state.party[0].id,
        Meridian.state.balls,
        Meridian.state.potions,
      ]),
      ["charmander", 9, 8],
    );
    assert.deepEqual(
      await b.evaluate(() => [
        Meridian.state.party[0].id,
        Meridian.state.balls,
        Meridian.state.potions,
      ]),
      ["bulbasaur", 15, 4],
    );
    // Wait for a post-commit client sync to prove it cannot resurrect the old inventory.
    await a.evaluate(() =>
      Meridian.api("sync", {
        game: Meridian.state,
        revision: Meridian.net.revision,
      }),
    );
    await b.reload();
    await click(b, "Jouer en duo");
    await click(b, "Reprendre ma connexion");
    await wait(b, () => Meridian.state?.party[0]?.id === "bulbasaur");
    assert.equal(await b.evaluate(() => Meridian.state.balls), 15);
    assert.deepEqual(errors, []);
    console.log(
      "PASS: two browser clients, offer editing, consent, reload during trade, transfer, reconnect; no JS errors.",
    );
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
    fs.rmSync(temp, { recursive: true, force: true });
  }
}
module.exports = run;
if (require.main === module)
  run(require("playwright").chromium).catch((e) => {
    console.error(e);
    process.exitCode = 1;
  });
