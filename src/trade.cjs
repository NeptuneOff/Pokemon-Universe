"use strict";
const crypto = require("node:crypto");
const TTL = 10 * 60 * 1000;
const pending = (s) => s.trade?.status === "pending";
function fail(message, status = 400) {
  throw Object.assign(new Error(message), { status });
}
function expire(s, now = Date.now()) {
  if (pending(s) && now >= s.trade.expiresAt) {
    s.trade.status = "expired";
    s.trade.version++;
    s.revision++;
    return true;
  }
  return false;
}
function empty() {
  return { slot: null, balls: 0, potions: 0 };
}
function validateOffer(p, raw) {
  const o = {
    slot: raw.slot ?? null,
    balls: raw.balls ?? 0,
    potions: raw.potions ?? 0,
  };
  if (o.slot !== null && (!Number.isInteger(o.slot) || !p.game.party[o.slot]))
    fail("Pokémon proposé introuvable.");
  for (const key of ["balls", "potions"]) {
    if (
      !Number.isInteger(o[key]) ||
      o[key] < 0 ||
      o[key] > 99 ||
      o[key] > p.game[key]
    )
      fail("Quantité indisponible : " + key + ".");
  }
  return o;
}
// Persist this detached session before publishing it in memory.
function transact(source, playerId, body) {
  const s = structuredClone(source),
    p = s.players.find((x) => x.id === playerId);
  if (body.action === "open") {
    if (pending(s)) fail("Un échange est déjà ouvert.", 409);
    if (
      s.battle ||
      s.players.length !== 2 ||
      s.players.some(
        (x) =>
          !x.game ||
          x.game.zone !== "town" ||
          x.game.region !== p.game?.region ||
          x.activity === "battle" ||
          Date.now() - x.online > 6000,
      )
    )
      fail("Retrouvez-vous au même relais, connectés et hors combat.");
    s.trade = {
      id: crypto.randomBytes(10).toString("hex"),
      version: 1,
      status: "pending",
      expiresAt: Date.now() + TTL,
      offers: {},
      confirmed: {},
    };
    for (const x of s.players) s.trade.offers[x.id] = empty();
    s.ready = {};
  } else {
    const t = s.trade;
    if (!pending(s) || body.id !== t.id)
      fail("Cet échange n’est plus ouvert.", 409);
    if (body.action === "cancel") {
      t.status = "cancelled";
    } else {
      if (body.version !== t.version)
        fail("L’offre a changé. Relis le récapitulatif.", 409);
      if (body.action === "offer") {
        t.offers[p.id] = validateOffer(p, body.offer || {});
        t.confirmed = {};
      } else if (body.action === "confirm") {
        if (t.confirmed[p.id]) fail("Tu as déjà confirmé cette offre.", 409);
        const offers = s.players.map((x) => validateOffer(x, t.offers[x.id]));
        if (
          offers.every(
            (o) => o.slot === null && o.balls === 0 && o.potions === 0,
          )
        )
          fail("Ajoutez au moins un Pokémon ou un objet.");
        for (let i = 0; i < 2; i++) {
          const size =
            s.players[i].game.party.length -
            (offers[i].slot !== null ? 1 : 0) +
            (offers[1 - i].slot !== null ? 1 : 0);
          if (size < 1 || size > 6)
            fail("Chaque équipe doit conserver entre un et six Pokémon.");
          for (const key of ["balls", "potions"])
            if (
              s.players[i].game[key] - offers[i][key] + offers[1 - i][key] >
              1e8
            )
              fail("Inventaire destinataire plein.");
        }
        t.confirmed[p.id] = true;
        if (s.players.every((x) => t.confirmed[x.id])) {
          const outgoing = s.players.map((x, i) =>
            offers[i].slot === null
              ? null
              : x.game.party.splice(offers[i].slot, 1)[0],
          );
          s.players.forEach((x, i) => {
            for (const key of ["balls", "potions"])
              x.game[key] += offers[1 - i][key] - offers[i][key];
            const received = outgoing[1 - i];
            if (received) {
              received.mega = null;
              received.focus = false;
              x.game.party.push(received);
              for (const key of ["caught", "seen"])
                if (!x.game[key].includes(received.id))
                  x.game[key].push(received.id);
            }
            x.gameEpoch = (x.gameEpoch || 0) + 1;
          });
          t.status = "completed";
          t.completedAt = Date.now();
        }
      } else fail("Action d’échange inconnue.");
    }
    t.version++;
  }
  s.revision++;
  return s;
}
function view(s) {
  if (!s.trade) return null;
  const t = structuredClone(s.trade);
  if (t.status === "pending")
    t.preview = Object.fromEntries(
      s.players.map((p) => [
        p.id,
        t.offers[p.id].slot === null ? null : p.game.party[t.offers[p.id].slot],
      ]),
    );
  return t;
}
module.exports = { pending, expire, transact, view };
