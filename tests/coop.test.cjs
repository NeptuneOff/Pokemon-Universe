const { test, after } = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  os = require("node:os"),
  path = require("node:path");
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "meridian-test-"));
process.env.MERIDIAN_SAVE_DIR = temp;
const { server, sessions, D, R, C } = require("../server.cjs");
let url;
const ready = new Promise((resolve) =>
  server.listen(0, "127.0.0.1", () => {
    url = "http://127.0.0.1:" + server.address().port;
    resolve();
  }),
);
after(() => {
  server.close();
  fs.rmSync(temp, { recursive: true, force: true });
});
async function api(route, body, auth, expect = 200) {
  await ready;
  let r = await fetch(url + "/api/" + route, {
    method: body ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
      ...(auth ? { "X-Session": auth.code, "X-Player": auth.token } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let v = await r.json();
  assert.equal(r.status, expect, JSON.stringify(v));
  return v;
}
function game(id) {
  return {
    version: 1,
    region: 0,
    zone: "town",
    x: 20,
    y: 18,
    party: [
      C.create(id, 100, D),
      C.create("mewtwo", 100, D),
      C.create("kyogre", 100, D),
      C.create("rayquaza", 100, D),
      C.create("groudon", 100, D),
      C.create("arceus", 100, D),
    ],
    box: [],
    money: 1200,
    balls: 12,
    potions: 6,
    progress: Array(7).fill(0),
    puzzles: Array(7).fill(0),
    flags: {},
    caught: [id],
    seen: [id],
    stones: [],
    megaUnlocked: false,
    finished: false,
    playtime: 0,
  };
}
test("two independent clients complete all seven cooperative chapters", async () => {
  let a = await api("create", {
      profile: { name: "Alpha", role: "analyst", color: "#567dab" },
    }),
    b = await api("join", {
      code: a.code,
      profile: { name: "Beta", role: "analyst" },
    });
  assert.equal(b.profile.role, "ranger");
  let ga = game("mewtwo"),
    gb = game("rayquaza");
  async function sync(auth, g) {
    let snap = await api("state", null, auth);
    return api("sync", { game: g, revision: snap.revision }, auth);
  }
  for (let i = 0; i < 7; i++) {
    ga.region = gb.region = i;
    ga.zone = gb.zone = "town";
    await sync(a, ga);
    await sync(b, gb);
    await api("event", { type: "start" }, a);
    ga.zone = gb.zone = "route";
    await sync(a, ga);
    await sync(b, gb);
    await api("event", { type: "guard" }, a);
    ga.zone = gb.zone = "site";
    await sync(a, ga);
    await sync(b, gb);
    await api("event", { type: "rune", index: R[i].puzzle[0] }, b, 400);
    await api("event", { type: "rune", index: R[i].puzzle[0] }, a);
    await api("event", { type: "rune", index: R[i].puzzle[1] }, b);
    await api("event", { type: "rune", index: R[i].puzzle[2] }, a);
    let snap = await api("event", { type: "evidence" }, a);
    assert.equal(snap.progress[i], 1);
    snap = await api("event", { type: "evidence" }, b);
    assert.equal(snap.progress[i], 2);
    await api("ready", {}, a);
    snap = await api("ready", {}, b);
    assert.equal(snap.battle.status, "active");
    await api("ready", {}, a, 400);
    let rounds = 0;
    while (snap.battle.status === "active" && rounds++ < 100) {
      let round = snap.battle.round;
      for (let auth of [a, b]) {
        if (snap.battle.status !== "active") break;
        let u = snap.battle.players.find((p) => p.id === auth.id);
        if (u.party.every((m) => m.hp <= 0)) continue;
        let m = u.party[u.active],
          options = m.moves
            .map((id, slot) => ({
              slot,
              power: C.damage(
                m,
                snap.battle.enemies.find((e) => e.hp > 0),
                D.moves[id],
                D,
                () => 0.5,
              ).damage,
              pp: m.pp[slot],
            }))
            .filter((m) => m.pp > 0 && m.power > 0)
            .sort((x, y) => y.power - x.power);
        let action = options.length
          ? { type: "move", slot: options[0].slot }
          : { type: "move", slot: m.pp.findIndex((v) => v > 0) };
        if (action.slot < 0) action = { type: "struggle" };
        snap = await api(
          "action",
          {
            ...action,
            target: snap.battle.enemies.findIndex((m) => m.hp > 0),
            round,
          },
          auth,
        );
      }
    }
    assert.equal(snap.battle.status, "won", "chapter " + i);
    assert.equal(snap.progress[i], 3);
    await api("ack", {}, a);
    await api("ack", {}, b);
    ga = (await api("state", null, a)).game;
    gb = (await api("state", null, b)).game;
    ga.zone = gb.zone = "town";
    await sync(a, ga);
    await sync(b, gb);
    await api("event", { type: "choice", choice: "restore" }, a);
    snap = await api("event", { type: "complete" }, a);
    assert.equal(snap.progress[i], 3, "must wait for both decisions");
    await api("event", { type: "choice", choice: "publish" }, b);
    snap = await api("event", { type: "complete" }, b);
    assert.equal(snap.progress[i], 4);
    assert.equal(snap.outcomes[i], "compromise");
  }
  assert.equal(
    (await api("state", null, a)).progress.filter((x) => x === 4).length,
    7,
  );
  assert.ok(fs.existsSync(path.join(temp, a.code + ".json")));
  await api("state", null, { code: a.code, token: "wrong" }, 403);
  let secret = await fetch(url + "/.sessions/" + a.code + ".json");
  assert.equal(secret.status, 404);
  await api("join", { code: a.code, profile: { name: "Third" } }, null, 400);
});
