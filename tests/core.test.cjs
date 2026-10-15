const { test } = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  vm = require("node:vm"),
  path = require("node:path");
let ctx = { window: {} };
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, "../data/game-data.js"), "utf8"),
  ctx,
);
vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, "../data/campaign.js"), "utf8"),
  ctx,
);
global.CAMPAIGN = ctx.window.CAMPAIGN;
const D = ctx.window.GAME_DATA,
  C = require("../src/core.js"),
  W = require("../src/world.js");
test("all 1025 national species are present with valid stats", () => {
  let base = Object.values(D.pokemon).filter((p) => !p.forme);
  assert.equal(base.length, 1025);
  for (let n = 1; n <= 1025; n++) assert.ok(base.some((p) => p.num === n));
  for (let p of Object.values(D.pokemon)) {
    assert.ok(p.stats.hp > 0);
    assert.ok(p.types.length);
    if (p.mega) assert.ok(D.pokemon[p.base]);
  }
});
test("damage respects immunities, dual types and category", () => {
  assert.equal(C.effectiveness("Electric", ["Ground", "Flying"]), 0);
  assert.equal(C.effectiveness("Ice", ["Dragon", "Flying"]), 4);
  assert.equal(C.effectiveness("Fire", ["Water", "Dragon"]), 0.25);
  let a = C.create("pikachu", 30, D),
    b = C.create("diglett", 30, D);
  assert.equal(
    C.damage(
      a,
      b,
      { type: "Electric", category: "Special", power: 90 },
      D,
      () => 0.5,
    ).damage,
    0,
  );
});
test("every species can produce a valid playable team member", () => {
  for (let p of Object.values(D.pokemon)) {
    let m = C.create(p.id, 25, D);
    assert.ok(m.moves.length >= 1 && m.moves.length <= 4, p.id);
    assert.equal(m.moves.length, m.pp.length);
    assert.ok(
      m.moves.every((id) => D.moves[id]),
      p.id,
    );
  }
});
test("mega changes stats and types, and clears after combat", () => {
  let m = C.create("charizard", 50, D);
  m.mega = "charizardmegax";
  assert.ok(C.species(m, D).types.includes("Dragon"));
  C.clearMega(m);
  assert.ok(!C.species(m, D).types.includes("Dragon"));
});
test("all required world interactions are reachable in every map", () => {
  for (let r = 0; r < 7; r++)
    for (let z of ["town", "route", "site"]) {
      let map = W.make(r, z),
        start = z === "town" ? [20, 18] : [3, 13],
        seen = new Set(),
        queue = [start];
      while (queue.length) {
        let [x, y] = queue.shift(),
          k = x + "," + y;
        if (seen.has(k) || !W.canWalk(map, x, y)) continue;
        seen.add(k);
        for (let [dx, dy] of [
          [1, 0],
          [-1, 0],
          [0, 1],
          [0, -1],
        ])
          queue.push([x + dx, y + dy]);
      }
      for (let o of map.objects.filter((o) => !o.building)) {
        assert.ok(
          [
            [1, 0],
            [-1, 0],
            [0, 1],
            [0, -1],
          ].some(([dx, dy]) => seen.has(o.x + dx + "," + (o.y + dy))),
          r + " " + z + " " + o.kind + " " + o.name,
        );
      }
    }
});
test("all campaign teams and encounters refer to known species", () => {
  for (let r of CAMPAIGN)
    for (let id of [...r.team, ...r.guardian, ...r.pool])
      assert.ok(D.pokemon[id], id);
});
