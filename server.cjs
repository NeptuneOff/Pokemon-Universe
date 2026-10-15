"use strict";
const http = require("node:http"),
  fs = require("node:fs"),
  path = require("node:path"),
  crypto = require("node:crypto"),
  vm = require("node:vm"),
  os = require("node:os");
const ROOT = __dirname,
  PORT = Number(process.env.PORT) || 8787,
  STORE = process.env.MERIDIAN_SAVE_DIR || path.join(ROOT, ".sessions");
const ctx = { window: {} };
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, "data/game-data.js"), "utf8"),
  ctx,
);
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, "data/campaign.js"), "utf8"),
  ctx,
);
const D = ctx.window.GAME_DATA,
  R = ctx.window.CAMPAIGN,
  C = require("./src/core.js");
const sessions = new Map();
fs.mkdirSync(STORE, { recursive: true });
for (const f of fs.readdirSync(STORE)) {
  if (!/^[A-Z0-9]{6}\.json$/.test(f)) continue;
  try {
    const s = JSON.parse(fs.readFileSync(path.join(STORE, f)));
    for (const p of s.players) p.online = 0;
    sessions.set(s.code, s);
  } catch {}
}
const token = () => crypto.randomBytes(24).toString("hex"),
  clone = (x) => JSON.parse(JSON.stringify(x));
function persist(s) {
  let file = path.join(STORE, s.code + ".json");
  fs.writeFileSync(file + ".tmp", JSON.stringify(s));
  fs.renameSync(file + ".tmp", file);
}
function fail(msg, status = 400) {
  let e = new Error(msg);
  e.status = status;
  throw e;
}
function profile(p = {}) {
  let name =
      String(p.name || "Voyageur")
        .trim()
        .slice(0, 20) || "Voyageur",
    role = p.role === "ranger" ? "ranger" : "analyst",
    color = ["#b45e56", "#567dab", "#8a68a1", "#5b9b7c"].includes(p.color)
      ? p.color
      : "#b45e56",
    origin = ["curieux", "protecteur", "audacieux"].includes(p.origin)
      ? p.origin
      : "curieux";
  return { name, role, color, origin };
}
function player(p, s) {
  let prof = profile(p);
  let seed = crypto
    .createHash("sha256")
    .update(s.seed + JSON.stringify(prof) + s.players.length)
    .digest()
    .readUInt32LE(0);
  return {
    id: crypto.randomBytes(5).toString("hex"),
    token: token(),
    profile: prof,
    seed,
    online: Date.now(),
    game: null,
  };
}
function auth(req) {
  let code = req.headers["x-session"],
    key = req.headers["x-player"];
  let s = sessions.get(code);
  if (!s) fail("Partie introuvable.", 404);
  let p = s.players.find((p) => p.token === key);
  if (!p) fail("Jeton de joueur invalide.", 403);
  p.online = Date.now();
  return { s, p };
}
function snapshot(s, p) {
  return {
    code: s.code,
    id: p.id,
    profile: p.profile,
    seed: p.seed,
    progress: s.progress,
    puzzles: s.puzzles,
    guards: s.guards,
    evidence: s.evidence,
    ready: s.ready,
    battle: s.battle,
    revision: s.revision,
    storyChoices: s.storyChoices,
    outcomes: s.outcomes || {},
    players: s.players.map((x) => ({
      id: x.id,
      profile: x.profile,
      online: Date.now() - x.online < 6000,
      position: x.game
        ? { region: x.game.region, zone: x.game.zone, x: x.game.x, y: x.game.y }
        : null,
    })),
    game: p.game,
  };
}
function bump(s) {
  s.revision++;
  persist(s);
}
function at(p, zone) {
  if (!p.game || p.game.zone !== zone)
    fail("Rejoins d’abord le lieu concerné.");
  return p.game.region;
}
function event(s, p, b) {
  let i = p.game?.region;
  if (!Number.isInteger(i)) fail("Choisis d’abord ton partenaire.");
  let r = R[i];
  if (s.battle?.status === "active") fail("Un combat commun est en cours.");
  if (b.type === "start") {
    at(p, "town");
    if (s.progress[i] === 0) s.progress[i] = 1;
  } else if (b.type === "guard") {
    at(p, "route");
    if (s.progress[i] < 1) fail("Mandat requis.");
    s.guards[i] = true;
  } else if (b.type === "rune") {
    at(p, "site");
    if (s.progress[i] !== 1 || !s.guards[i]) fail("Circuit inaccessible.");
    let n = s.puzzles[i];
    if (n >= 3) return;
    let role = n === 1 ? "ranger" : "analyst";
    if (p.profile.role !== role)
      fail(
        role === "ranger"
          ? "L’éclaireur doit stabiliser cette borne."
          : "L’analyste doit régler cette borne.",
      );
    if (b.index === r.puzzle[n]) s.puzzles[i]++;
    else s.puzzles[i] = 0;
  } else if (b.type === "evidence") {
    at(p, "site");
    if (s.puzzles[i] < 3) fail("Accordez d’abord les trois bornes.");
    s.evidence[i][p.profile.role] = true;
    if (s.evidence[i].analyst && s.evidence[i].ranger)
      s.progress[i] = Math.max(s.progress[i], 2);
  } else if (b.type === "complete") {
    at(p, "town");
    if (
      s.progress[i] === 3 &&
      s.players.length === 2 &&
      s.players.every((x) => s.storyChoices[i][x.id])
    ) {
      s.progress[i] = 4;
      let votes = Object.values(s.storyChoices[i]);
      s.outcomes ||= {};
      s.outcomes[i] = votes.every((v) => v === "restore")
        ? "restoration"
        : votes.every((v) => v === "publish")
          ? "publication"
          : "compromise";
    }
  } else if (b.type === "choice") {
    at(p, "town");
    if (s.progress[i] < 3) fail("Terminez d’abord le chapitre.");
    if (!["restore", "publish"].includes(b.choice)) fail("Choix inconnu.");
    s.storyChoices[i][p.id] = b.choice;
  } else fail("Événement inconnu.");
  bump(s);
}
function beginBattle(s) {
  let i = s.players[0].game.region;
  if (
    s.players.length !== 2 ||
    s.players.some(
      (p) =>
        !p.game ||
        p.game.region !== i ||
        p.game.zone !== "site" ||
        !p.game.party.some((m) => m.hp > 0),
    )
  )
    fail("Les deux équipes doivent être présentes sur le site et prêtes.");
  if (s.progress[i] !== 2)
    fail("Croisez d’abord vos deux rapports à la console.");
  let enemies = R[i].team.map((id, j) =>
    C.create(id, R[i].level + 5 + (j === R[i].team.length - 1 ? 1 : 0), D),
  );
  s.ready = {};
  s.battle = {
    id: crypto.randomBytes(6).toString("hex"),
    region: i,
    round: 1,
    status: "active",
    log: ["Le défi commun commence. Chaque joueur choisit son action."],
    players: s.players.map((p) => ({
      id: p.id,
      role: p.profile.role,
      name: p.profile.name,
      party: clone(p.game.party).map(C.clearMega),
      active: p.game.party.findIndex((m) => m.hp > 0),
      megaUsed: false,
      supportUsed: false,
      shield: false,
    })),
    enemies,
    actions: {},
    rewarded: false,
  };
}
function active(x) {
  return x.party[x.active];
}
function healthyEnemies(b) {
  return b.enemies
    .map((m, i) => ({ m, i }))
    .filter((x) => x.m.hp > 0)
    .slice(0, 2);
}
function resolve(s) {
  let b = s.battle,
    log = [],
    ops = [];
  for (let u of b.players) {
    let a = b.actions[u.id],
      m = active(u);
    if (!a) continue;
    if (a.type === "switch") {
      if (Number.isInteger(a.slot) && u.party[a.slot]?.hp > 0) {
        u.active = a.slot;
        log.push(u.name + " envoie " + D.pokemon[active(u).id].fr + ".");
      }
      continue;
    }
    if (m.hp <= 0) continue;
    if (a.type === "support") {
      if (!u.supportUsed) {
        u.supportUsed = true;
        if (u.role === "ranger") {
          for (let ally of b.players) ally.shield = true;
          log.push(u.name + " protège les deux équipes pour ce tour.");
        } else {
          for (let ally of b.players) active(ally).focus = true;
          log.push(
            u.name +
              " analyse une ouverture : les deux prochaines attaques sont renforcées.",
          );
        }
      }
      continue;
    }
    if (a.type === "mega") {
      let p = s.players.find((p) => p.id === u.id),
        mega = D.pokemon[m.stone];
      if (
        !u.megaUsed &&
        p.game.megaUnlocked &&
        mega?.mega &&
        mega.base === m.id &&
        p.game.stones.includes(mega.id)
      ) {
        m.mega = mega.id;
        u.megaUsed = true;
        log.push(D.pokemon[m.mega].fr + " méga-évolue.");
      }
      continue;
    }
    let idx = a.slot;
    if (a.type === "struggle") {
      ops.push({
        u,
        m,
        move: D.moves.struggle,
        slot: -1,
        target: a.target,
        enemy: false,
      });
      continue;
    }
    if (
      a.type === "move" &&
      Number.isInteger(idx) &&
      m.moves[idx] &&
      m.pp[idx] > 0
    )
      ops.push({
        u,
        m,
        move: D.moves[m.moves[idx]],
        slot: idx,
        target: a.target,
        enemy: false,
      });
  }
  for (let { m, i } of healthyEnemies(b)) {
    let possible = m.moves
      .map((id, j) => ({ move: D.moves[id], slot: j }))
      .filter((x) => x.move.power && m.pp[x.slot] > 0);
    let pick = possible.sort((a, c) => c.move.power - a.move.power)[0] || {
      move: D.moves.struggle,
      slot: -1,
    };
    ops.push({
      m,
      ...pick,
      enemy: true,
      target: Math.floor(Math.random() * 2),
    });
  }
  ops.sort(
    (a, c) =>
      c.move.priority - a.move.priority ||
      C.stats(C.species(c.m, D), c.m.level).spe -
        C.stats(C.species(a.m, D), a.m.level).spe,
  );
  for (let o of ops) {
    if (o.m.hp <= 0) continue;
    let target, tu;
    if (o.enemy) {
      tu = b.players[o.target];
      if (active(tu).hp <= 0) tu = b.players.find((u) => active(u).hp > 0);
      if (!tu) continue;
      target = active(tu);
    } else {
      target = b.enemies[o.target];
      if (!target || target.hp <= 0) target = healthyEnemies(b)[0]?.m;
      if (!target) continue;
    }
    if (o.slot >= 0) o.m.pp[o.slot]--;
    if (o.move.id === "focus") {
      o.m.focus = true;
      log.push(D.pokemon[o.m.id].fr + " se concentre.");
      continue;
    }
    if (Math.random() * 100 > o.move.accuracy) {
      log.push(o.move.name + " manque sa cible.");
      continue;
    }
    let h = C.damage(o.m, target, o.move, D);
    o.m.focus = false;
    if (tu?.shield) h.damage = Math.floor(h.damage / 2);
    target.hp = Math.max(0, target.hp - h.damage);
    log.push(
      D.pokemon[o.m.id].fr +
        " → " +
        o.move.name +
        " → " +
        D.pokemon[target.id].fr +
        " : −" +
        h.damage +
        " PV.",
    );
  }
  for (let u of b.players) {
    u.shield = false;
    if (active(u).hp <= 0) {
      let next = u.party.findIndex((m) => m.hp > 0);
      if (next >= 0) {
        u.active = next;
        log.push(u.name + " envoie " + D.pokemon[active(u).id].fr + ".");
      }
    }
  }
  if (b.enemies.every((m) => m.hp <= 0)) {
    b.status = "won";
    s.progress[b.region] = 3;
    log.push("Victoire commune ! Rapporte vos conclusions au relais.");
  } else if (b.players.every((u) => u.party.every((m) => m.hp <= 0))) {
    b.status = "lost";
    log.push("Les deux équipes sont secourues. Le défi pourra être repris.");
  }
  b.log = log;
  b.round++;
  b.actions = {};
  if (b.status !== "active") {
    for (let u of b.players) {
      let p = s.players.find((p) => p.id === u.id);
      p.game.party = u.party.map((m) => {
        C.clearMega(m);
        if (b.status === "won") {
          m.level = Math.max(m.level, R[b.region].cap - 1);
          m.moves = C.movelist(D.pokemon[m.id], D.moves, m.level);
        }
        m.hp = C.stats(D.pokemon[m.id], m.level).hp;
        m.pp = m.moves.map((id) => D.moves[id].pp);
        return m;
      });
      if (b.status === "won") p.game.money += 1300;
    }
    s.ready = {};
  }
  bump(s);
}
function action(s, p, a) {
  let b = s.battle;
  if (!b || b.status !== "active") fail("Aucun combat actif.");
  if (a.round !== b.round) fail("Ce tour est déjà terminé.", 409);
  let u = b.players.find((x) => x.id === p.id),
    m = active(u);
  if (!["move", "support", "mega", "switch", "struggle"].includes(a.type))
    fail("Action inconnue.");
  if (b.actions[p.id]) fail("Action déjà validée pour ce tour.", 409);
  if (a.type === "struggle" && m.pp.some((x) => x > 0))
    fail("Des capacités sont encore disponibles.");
  if (
    a.type === "move" &&
    (!Number.isInteger(a.slot) || !m.moves[a.slot] || m.pp[a.slot] <= 0)
  )
    fail("Capacité indisponible.");
  if (
    a.type === "switch" &&
    (!Number.isInteger(a.slot) || !u.party[a.slot] || u.party[a.slot].hp <= 0)
  )
    fail("Partenaire indisponible.");
  if (a.type === "support" && u.supportUsed) fail("Soutien déjà utilisé.");
  if (
    a.type === "mega" &&
    (u.megaUsed ||
      !p.game.megaUnlocked ||
      !D.pokemon[m.stone]?.mega ||
      D.pokemon[m.stone].base !== m.id ||
      !p.game.stones.includes(m.stone))
  )
    fail("Méga-Évolution indisponible.");
  b.actions[p.id] = a;
  if (
    b.players.every((x) => b.actions[x.id] || x.party.every((m) => m.hp <= 0))
  )
    resolve(s);
  else bump(s);
}
let lastPersist = 0;
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".json": "application/json; charset=utf-8",
  ".md": "text/plain; charset=utf-8",
};
const server = http.createServer(async (req, res) => {
  try {
    let url = new URL(req.url, "http://localhost");
    if (url.pathname.startsWith("/api/")) {
      if (
        req.headers.origin &&
        req.headers.origin !== `http://${req.headers.host}` &&
        req.headers.origin !== `https://${req.headers.host}`
      )
        fail("Origine refusée.", 403);
      res.setHeader("Content-Type", "application/json");
      res.setHeader("Cache-Control", "no-store");
      let body = {};
      if (req.method === "POST") {
        let chunks = [],
          length = 0;
        for await (const c of req) {
          length += c.length;
          if (length > 2000000) fail("Requête trop volumineuse.", 413);
          chunks.push(c);
        }
        try {
          body = JSON.parse(Buffer.concat(chunks).toString() || "{}");
        } catch {
          fail("JSON invalide.");
        }
      } else if (req.method !== "GET") fail("Méthode invalide.", 405);
      let result;
      if (url.pathname === "/api/create" && req.method === "POST") {
        if (sessions.size >= 100) fail("Limite de parties atteinte.");
        let code;
        do {
          code = crypto
            .randomBytes(4)
            .toString("hex")
            .slice(0, 6)
            .toUpperCase();
        } while (sessions.has(code));
        let s = {
          code,
          seed: token(),
          players: [],
          progress: Array(7).fill(0),
          puzzles: Array(7).fill(0),
          guards: Array(7).fill(false),
          evidence: Array.from({ length: 7 }, () => ({})),
          storyChoices: Array.from({ length: 7 }, () => ({})),
          ready: {},
          battle: null,
          revision: 1,
        };
        let p = player(body.profile, s);
        s.players.push(p);
        sessions.set(code, s);
        persist(s);
        result = { token: p.token, ...snapshot(s, p) };
      } else if (url.pathname === "/api/join" && req.method === "POST") {
        let s = sessions.get(String(body.code || "").toUpperCase());
        if (!s) fail("Code de partie inconnu.", 404);
        if (s.players.length >= 2)
          fail(
            "Cette partie a déjà deux joueurs. Reprends avec ton jeton existant.",
          );
        let p = player(body.profile, s);
        p.profile.role =
          s.players[0].profile.role === "analyst" ? "ranger" : "analyst";
        s.players.push(p);
        bump(s);
        result = { token: p.token, ...snapshot(s, p) };
      } else {
        let { s, p } = auth(req);
        if (url.pathname === "/api/sync" && req.method === "POST") {
          let g = body.game;
          if (g) {
            C.validateSave(g, D);
            let unlocked = s.progress.findIndex((x) => x !== 4);
            if (unlocked < 0) unlocked = 6;
            if (g.region > unlocked) fail("Région non débloquée.");
            if (
              g.x >= 40 ||
              g.y >= 26 ||
              !Number.isInteger(g.x) ||
              !Number.isInteger(g.y)
            )
              fail("Position invalide.");
            if (s.battle?.status === "active") {
              if (p.game) {
                p.game.x = g.x;
                p.game.y = g.y;
              }
            } else if (body.revision === s.revision || !p.game) {
              p.game = g;
            }
          }
          if (Date.now() - lastPersist > 3000) {
            persist(s);
            lastPersist = Date.now();
          }
          result = snapshot(s, p);
        } else if (url.pathname === "/api/state") result = snapshot(s, p);
        else if (url.pathname === "/api/event" && req.method === "POST") {
          event(s, p, body);
          result = snapshot(s, p);
        } else if (url.pathname === "/api/ready" && req.method === "POST") {
          at(p, "site");
          if (s.battle)
            fail("Attends la fin et la validation du combat précédent.");
          s.ready[p.id] = true;
          if (s.players.length === 2 && s.players.every((x) => s.ready[x.id]))
            beginBattle(s);
          bump(s);
          result = snapshot(s, p);
        } else if (url.pathname === "/api/action" && req.method === "POST") {
          action(s, p, body);
          result = snapshot(s, p);
        } else if (url.pathname === "/api/ack" && req.method === "POST") {
          if (s.battle && s.battle.status !== "active") {
            s.battle.ack ||= {};
            s.battle.ack[p.id] = true;
            if (s.players.every((x) => s.battle.ack[x.id])) s.battle = null;
            bump(s);
          }
          result = snapshot(s, p);
        } else fail("Route inconnue.", 404);
      }
      res.end(JSON.stringify(result));
      return;
    }
    if (!["GET", "HEAD"].includes(req.method)) fail("Méthode invalide.", 405);
    let rel = decodeURIComponent(
      url.pathname === "/" ? "/index.html" : url.pathname,
    );
    if (
      !/^\/(index\.html|src\/[^/]+\.(js|css)|data\/(game-data|campaign)\.js|assets\/pokemon-[0-9]+\.js|assets\/pokemon\/[a-z0-9-]+\.png)$/.test(
        rel,
      )
    )
      fail("Fichier inaccessible.", 404);
    let file = path.join(ROOT, rel);
    if (!fs.existsSync(file)) fail("Fichier absent.", 404);
    res.setHeader(
      "Content-Type",
      mime[path.extname(file)] || "application/octet-stream",
    );
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Cache-Control", "no-cache");
    if (req.method === "HEAD") res.end();
    else fs.createReadStream(file).pipe(res);
  } catch (e) {
    res.statusCode = e.status || 500;
    res.setHeader("Content-Type", "application/json");
    res.end(
      JSON.stringify({
        error: e.status ? e.message : "Erreur interne du serveur.",
      }),
    );
    if (!e.status) console.error(e);
  }
});
if (require.main === module)
  server.listen(PORT, "0.0.0.0", () => {
    console.log("Pokémon Universe / Méridien — http://localhost:" + PORT);
    try {
      for (let entries of Object.values(os.networkInterfaces()))
        for (let n of entries || [])
          if (n.family === "IPv4" && !n.internal)
            console.log("Deuxième PC : http://" + n.address + ":" + PORT);
    } catch {
      console.log(
        "Adresse réseau : utilise l’adresse IP locale de ce PC et le port " +
          PORT,
      );
    }
    console.log("Les sauvegardes coop sont enregistrées dans " + STORE);
  });
module.exports = { server, sessions, D, R, C, resolve, event, beginBattle };
