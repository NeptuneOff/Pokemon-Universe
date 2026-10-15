(function (root) {
  "use strict";
  const W = 40,
    H = 26,
    T = 16;
  const solid = new Set(["tree", "rock", "water", "wall", "roof"]);
  function make(region, zone) {
    let r = CAMPAIGN[region],
      tiles = Array.from({ length: H }, () => Array(W).fill("lawn")),
      objects = [];
    const put = (x, y, t) => {
      if (x >= 0 && y >= 0 && x < W && y < H) tiles[y][x] = t;
    };
    const rect = (x, y, w, h, t) => {
      for (let j = y; j < y + h; j++)
        for (let i = x; i < x + w; i++) put(i, j, t);
    };
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++)
        if (x < 2 || y < 2 || x > 37 || y > 23) put(x, y, "tree");
    const obj = (kind, x, y, name, extra = {}) =>
      objects.push({ kind, x, y, name, ...extra });
    const house = (x, y, w, h, kind, name) => {
      rect(x, y, w, h, "wall");
      rect(x - 1, y - 1, w + 2, 2, "roof");
      put(x + Math.floor(w / 2), y + h - 1, "door");
      obj(kind, x + Math.floor(w / 2), y + h, name, {
        building: true,
        x0: x,
        y0: y,
        w,
        h,
      });
    };
    if (zone === "town") {
      rect(3, 12, 35, 3, "path");
      rect(18, 7, 4, 16, "path");
      rect(5, 20, 29, 2, "path");
      house(5, 4, 7, 5, "home", "Maison des voyageurs");
      house(17, 3, 7, 5, "mentor", r.mentor);
      house(29, 4, 6, 5, "shop", "Comptoir de ravitaillement");
      house(6, 14, 7, 4, "heal", "Centre Pokémon");
      rect(27, 18, 10, 6, "water");
      rect(29, 19, 5, 3, "wood");
      rect(26, 20, 8, 2, "wood");
      obj("travel", 31, 20, "Liaison Méridien");
      obj("mentor", 20, 10, r.mentor);
      obj("heal", 10, 19, "Infirmière");
      obj("shop", 31, 10, "Marchand");
      obj("npc", 7, 11, "Habitant", { text: r.ambient[0] });
      obj("npc", 25, 17, "Voyageuse", { text: r.ambient[1] });
      obj("reserve", 25, 9, "Bureau des habitats");
      obj("exit", 38, 13, "Vers " + r.route, { to: "route", x2: 3, y2: 13 });
      rect(37, 12, 3, 3, "path");
      for (let [x, y] of [
        [4, 10],
        [14, 10],
        [28, 10],
        [15, 19],
        [23, 19],
      ])
        put(x, y, "flower");
    } else if (zone === "route") {
      rect(0, 12, 40, 3, "path");
      let k = region % 3;
      if (k === 0) {
        rect(16, 2, 5, 22, "water");
        rect(15, 12, 7, 3, "wood");
        rect(5, 5, 9, 6, "grass");
        rect(24, 16, 10, 6, "grass");
        rect(23, 4, 11, 6, "grass");
      }
      if (k === 1) {
        rect(4, 4, 13, 5, "rock");
        rect(22, 17, 12, 5, "rock");
        rect(4, 16, 13, 6, "grass");
        rect(22, 4, 12, 7, "grass");
        rect(17, 7, 4, 13, "path");
      }
      if (k === 2) {
        rect(3, 3, 34, 5, "water");
        rect(4, 17, 11, 6, "water");
        rect(5, 9, 29, 3, "grass");
        rect(21, 16, 14, 6, "grass");
        rect(16, 15, 4, 8, "path");
      }
      for (let x = 6; x < 36; x += 7) {
        put(x, 23, "flower");
        put(x, 3, "flower");
      }
      obj("exit", 1, 13, "Retour au relais", { to: "town", x2: 36, y2: 13 });
      obj("exit", 38, 13, "Vers " + r.site, { to: "site", x2: 3, y2: 13 });
      obj("guard", 29, 13, "Agent Atlas");
      obj("sign", 5, 13, "Repère de terrain", {
        text: "Les hautes herbes abritent des Pokémon sauvages. Affaiblis-les avant de lancer une Poké Ball. Le centre soigne gratuitement toute ton équipe.",
      });
      obj("item", 24, 21, "Caisse de terrain");
    } else {
      rect(0, 12, 40, 3, "path");
      rect(7, 5, 27, 17, "stone");
      rect(18, 4, 5, 20, "stone");
      rect(4, 4, 3, 18, "rock");
      rect(34, 4, 3, 18, "rock");
      if (region === 2 || region === 6) {
        rect(8, 6, 8, 3, "water");
        rect(26, 6, 7, 3, "water");
      }
      if (region === 3) {
        rect(9, 5, 5, 4, "rock");
        rect(27, 5, 5, 4, "rock");
      }
      obj("exit", 1, 13, "Retour à la route", { to: "route", x2: 36, y2: 13 });
      for (let i = 0; i < 3; i++)
        obj("rune", 12 + i * 8, 12, r.symbols[i], { index: i });
      obj("terminal", 20, 6, "Console de résonance");
      obj("boss", 20, 20, r.boss);
      obj("sign", 9, 18, "Inscription", { text: r.clue });
    }
    return { tiles, objects, region, zone, name: r[zone], r };
  }
  function canWalk(map, x, y) {
    return (
      x >= 0 &&
      y >= 0 &&
      x < W &&
      y < H &&
      !solid.has(map.tiles[y][x]) &&
      !map.objects.some(
        (o) =>
          o.kind !== "exit" &&
          !o.building &&
          o.kind !== "item" &&
          o.x === x &&
          o.y === y,
      )
    );
  }
  function nearby(map, x, y) {
    return map.objects
      .filter((o) => Math.abs(o.x - x) + Math.abs(o.y - y) <= 1)
      .sort(
        (a, b) => (a.kind === "exit" ? 1 : 0) - (b.kind === "exit" ? 1 : 0),
      )[0];
  }
  root.World = { make, canWalk, nearby, W, H, T };
  if (typeof module !== "undefined") module.exports = root.World;
})(globalThis);
