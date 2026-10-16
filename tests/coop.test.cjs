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

test("trade commits once, locks saves, invalidates consent and survives reconnect", async () => {
  const a = await api("create", { profile: { name: "Donneur" } });
  const b = await api("join", { code: a.code, profile: { name: "Receveur" } });
  const ga = game("bulbasaur"),
    gb = game("charmander");
  ga.party = ga.party.slice(0, 2);
  gb.party = gb.party.slice(0, 2);
  C.validateSave(ga, D);
  C.validateSave(gb, D);
  const originalA = structuredClone(ga.party[0]),
    originalB = structuredClone(gb.party[0]);
  async function sync(who, g, extra = {}) {
    const snap = await api("state", null, who);
    return api("sync", { game: g, revision: snap.revision, ...extra }, who);
  }
  await sync(a, ga);
  await sync(b, gb);
  let snap = await api("trade", { action: "open" }, a);
  const id = snap.trade.id;
  async function trade(who, action, extra = {}, expected = 200) {
    const live = await api("state", null, who);
    return api(
      "trade",
      { action, id, version: live.trade.version, ...extra },
      who,
      expected,
    );
  }
  const frozen = await sync(a, {
    ...ga,
    balls: 999,
    party: [C.create("arceus", 100, D)],
  });
  assert.equal(frozen.game.balls, 12);
  assert.equal(frozen.game.party[0].id, "bulbasaur");
  await api("event", { type: "start" }, a, 409);
  await api("ready", {}, a, 409);
  await trade(a, "offer", { offer: { slot: 0, balls: 3, potions: 0 } });
  snap = await trade(b, "offer", { offer: { slot: 0, balls: 0, potions: 2 } });
  const staleVersion = snap.trade.version;
  await trade(a, "confirm");
  await api("trade", { action: "confirm", id, version: staleVersion }, b, 409);
  snap = await trade(b, "offer", { offer: { slot: 0, balls: 0, potions: 3 } });
  assert.deepEqual(snap.trade.confirmed, {});
  await trade(b, "confirm");
  snap = await trade(a, "confirm");
  assert.equal(snap.trade.status, "completed");
  assert.equal(snap.game.balls, 9);
  assert.equal(snap.game.potions, 9);
  assert.deepEqual(snap.game.party.at(-1), originalB);
  const sb = await api("state", null, b);
  assert.equal(sb.game.balls, 15);
  assert.equal(sb.game.potions, 3);
  assert.deepEqual(sb.game.party.at(-1), originalA);
  assert.ok(sb.game.caught.includes("bulbasaur"));
  assert.equal(sb.gameEpoch, 1);
  assert.ok(!JSON.stringify(sb).includes(a.token));
  // Even an old save carrying the latest campaign revision must not undo a transfer.
  const rejected = await api(
    "sync",
    { game: ga, revision: snap.revision, gameEpoch: 0 },
    a,
  );
  assert.equal(rejected.game.balls, 9);
  assert.equal(rejected.game.party.at(-1).uid, originalB.uid);
  await trade(a, "confirm", {}, 409);
  assert.equal((await api("state", null, a)).game.balls, 9);
  // Rehydrate the exact on-disk session, as at server restart, then reconnect with existing tokens.
  const disk = JSON.parse(fs.readFileSync(path.join(temp, a.code + ".json")));
  disk.players.forEach((p) => {
    p.online = 0;
  });
  sessions.set(a.code, disk);
  const reconnected = await api("state", null, b);
  assert.equal(reconnected.game.party.at(-1).uid, originalA.uid);
  assert.equal(reconnected.gameEpoch, 1);
  assert.equal(reconnected.trade.status, "completed");
});

test("trade rejects invalid gifts and quantities, cancels and expires without transfers", async () => {
  const a = await api("create", { profile: { name: "A" } });
  const b = await api("join", { code: a.code, profile: { name: "B" } });
  const ga = game("bulbasaur"),
    gb = game("squirtle");
  ga.party = ga.party.slice(0, 1);
  gb.party = gb.party.slice(0, 1);
  C.validateSave(ga, D);
  C.validateSave(gb, D);
  async function sync(who, g, extra = {}) {
    const snap = await api("state", null, who);
    return api("sync", { game: g, revision: snap.revision, ...extra }, who);
  }
  await sync(a, ga);
  await sync(b, gb, { activity: "battle" });
  await api("trade", { action: "open" }, a, 400);
  await sync(b, gb);
  let snap = await api("trade", { action: "open" }, a);
  const id = snap.trade.id;
  async function act(who, action, extra = {}, status = 200) {
    const live = await api("state", null, who);
    return api(
      "trade",
      { action, id, version: live.trade.version, ...extra },
      who,
      status,
    );
  }
  await act(a, "confirm", {}, 400);
  for (const offer of [
    { balls: -1 },
    { balls: 13 },
    { potions: 1.5 },
    { slot: 100 },
  ])
    await act(a, "offer", { offer }, 400);
  await act(a, "offer", { offer: { slot: 0 } });
  await act(a, "confirm", {}, 400); // cannot donate your only team member
  await act(b, "cancel");
  assert.deepEqual((await api("state", null, a)).game.party, ga.party);
  await act(a, "confirm", {}, 409);
  await api("trade", { action: "open" }, a);
  sessions.get(a.code).trade.expiresAt = Date.now() - 1;
  snap = await api("state", null, a);
  assert.equal(snap.trade.status, "expired");
  assert.equal(snap.game.balls, ga.balls);
  assert.equal(snap.gameEpoch, 0);
});

test("simultaneous confirmations cannot apply a transfer twice", async () => {
  const a = await api("create", { profile: {} });
  const b = await api("join", { code: a.code, profile: {} });
  for (const who of [a, b]) {
    const s = await api("state", null, who);
    await api("sync", { game: game("pikachu"), revision: s.revision }, who);
  }
  let snap = await api("trade", { action: "open" }, a);
  snap = await api(
    "trade",
    {
      action: "offer",
      id: snap.trade.id,
      version: snap.trade.version,
      offer: { balls: 2 },
    },
    a,
  );
  const payload = {
    action: "confirm",
    id: snap.trade.id,
    version: snap.trade.version,
  };
  const results = await Promise.all(
    [a, b].map((who) =>
      fetch(url + "/api/trade", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session": who.code,
          "X-Player": who.token,
        },
        body: JSON.stringify(payload),
      }),
    ),
  );
  assert.deepEqual(results.map((r) => r.status).sort(), [200, 409]);
  snap = await api("state", null, a);
  const remaining = snap.trade.confirmed[a.id] ? b : a;
  await api("trade", { ...payload, version: snap.trade.version }, remaining);
  assert.equal((await api("state", null, a)).game.balls, 10);
  assert.equal((await api("state", null, b)).game.balls, 14);
});

test("failed save leaves both inventories untouched and final confirmation can be retried", async () => {
  const a = await api("create", { profile: {} });
  const b = await api("join", { code: a.code, profile: {} });
  for (const who of [a, b]) {
    const s = await api("state", null, who);
    await api("sync", { game: game("eevee"), revision: s.revision }, who);
  }
  let snap = await api("trade", { action: "open" }, a);
  snap = await api(
    "trade",
    {
      action: "offer",
      id: snap.trade.id,
      version: snap.trade.version,
      offer: { potions: 1 },
    },
    a,
  );
  snap = await api(
    "trade",
    { action: "confirm", id: snap.trade.id, version: snap.trade.version },
    a,
  );
  const final = {
    action: "confirm",
    id: snap.trade.id,
    version: snap.trade.version,
  };
  const rename = fs.renameSync,
    log = console.error;
  try {
    fs.renameSync = (from, to) => {
      if (to === path.join(temp, a.code + ".json"))
        throw new Error("Simulated disk failure");
      return rename(from, to);
    };
    console.error = () => {};
    await api("trade", final, b, 500);
  } finally {
    fs.renameSync = rename;
    console.error = log;
  }
  assert.equal((await api("state", null, a)).game.potions, 6);
  assert.equal((await api("state", null, b)).game.potions, 6);
  const disk = JSON.parse(fs.readFileSync(path.join(temp, a.code + ".json")));
  assert.equal(disk.trade.status, "pending");
  await api("trade", final, b);
  assert.equal((await api("state", null, a)).game.potions, 5);
  assert.equal((await api("state", null, b)).game.potions, 7);
});

test("trade refuses a seventh team member and accepts a one-way gift with space", () => {
  const Trade = require("../src/trade.cjs");
  const source = {
    revision: 1,
    players: [
      { id: "a", online: Date.now(), game: game("bulbasaur") },
      { id: "b", online: Date.now(), game: game("charmander") },
    ],
  };
  let s = Trade.transact(source, "a", { action: "open" });
  const step = (who, action, extra = {}) => {
    s = Trade.transact(s, who, {
      action,
      id: s.trade.id,
      version: s.trade.version,
      ...extra,
    });
  };
  step("a", "offer", { offer: { slot: 0 } });
  assert.throws(() => step("a", "confirm"), /six Pokémon/);
  assert.deepEqual(s.trade.confirmed, {});
  s.players[1].game.party.pop(); // fixture with a free receiving slot
  const uid = s.players[0].game.party[0].uid;
  step("a", "confirm");
  step("b", "confirm");
  assert.equal(s.players[0].game.party.length, 5);
  assert.equal(s.players[1].game.party.length, 6);
  assert.equal(s.players[1].game.party.at(-1).uid, uid);
  assert.equal(
    source.players[0].game.party.length,
    6,
    "the source remains untouched",
  );
});
