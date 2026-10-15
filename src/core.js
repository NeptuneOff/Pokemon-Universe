/* Meridian battle kernel. Original code; species data is attributed separately. */
(function (root) {
  "use strict";
  const chart = {
    Normal: { Rock: 0.5, Ghost: 0, Steel: 0.5 },
    Fire: {
      Fire: 0.5,
      Water: 0.5,
      Grass: 2,
      Ice: 2,
      Bug: 2,
      Rock: 0.5,
      Dragon: 0.5,
      Steel: 2,
    },
    Water: { Fire: 2, Water: 0.5, Grass: 0.5, Ground: 2, Rock: 2, Dragon: 0.5 },
    Electric: {
      Water: 2,
      Electric: 0.5,
      Grass: 0.5,
      Ground: 0,
      Flying: 2,
      Dragon: 0.5,
    },
    Grass: {
      Fire: 0.5,
      Water: 2,
      Grass: 0.5,
      Poison: 0.5,
      Ground: 2,
      Flying: 0.5,
      Bug: 0.5,
      Rock: 2,
      Dragon: 0.5,
      Steel: 0.5,
    },
    Ice: {
      Fire: 0.5,
      Water: 0.5,
      Grass: 2,
      Ice: 0.5,
      Ground: 2,
      Flying: 2,
      Dragon: 2,
      Steel: 0.5,
    },
    Fighting: {
      Normal: 2,
      Ice: 2,
      Poison: 0.5,
      Flying: 0.5,
      Psychic: 0.5,
      Bug: 0.5,
      Rock: 2,
      Ghost: 0,
      Dark: 2,
      Steel: 2,
      Fairy: 0.5,
    },
    Poison: {
      Grass: 2,
      Poison: 0.5,
      Ground: 0.5,
      Rock: 0.5,
      Ghost: 0.5,
      Steel: 0,
      Fairy: 2,
    },
    Ground: {
      Fire: 2,
      Electric: 2,
      Grass: 0.5,
      Poison: 2,
      Flying: 0,
      Bug: 0.5,
      Rock: 2,
      Steel: 2,
    },
    Flying: {
      Electric: 0.5,
      Grass: 2,
      Fighting: 2,
      Bug: 2,
      Rock: 0.5,
      Steel: 0.5,
    },
    Psychic: { Fighting: 2, Poison: 2, Psychic: 0.5, Dark: 0, Steel: 0.5 },
    Bug: {
      Fire: 0.5,
      Grass: 2,
      Fighting: 0.5,
      Poison: 0.5,
      Flying: 0.5,
      Psychic: 2,
      Ghost: 0.5,
      Dark: 2,
      Steel: 0.5,
      Fairy: 0.5,
    },
    Rock: {
      Fire: 2,
      Ice: 2,
      Fighting: 0.5,
      Ground: 0.5,
      Flying: 2,
      Bug: 2,
      Steel: 0.5,
    },
    Ghost: { Normal: 0, Psychic: 2, Ghost: 2, Dark: 0.5 },
    Dragon: { Dragon: 2, Steel: 0.5, Fairy: 0 },
    Dark: { Fighting: 0.5, Psychic: 2, Ghost: 2, Dark: 0.5, Fairy: 0.5 },
    Steel: {
      Fire: 0.5,
      Water: 0.5,
      Electric: 0.5,
      Ice: 2,
      Rock: 2,
      Steel: 0.5,
      Fairy: 2,
    },
    Fairy: {
      Fire: 0.5,
      Fighting: 2,
      Poison: 0.5,
      Dragon: 2,
      Dark: 2,
      Steel: 0.5,
    },
  };
  const typeNames = {
    Normal: "Normal",
    Fire: "Feu",
    Water: "Eau",
    Electric: "Électrik",
    Grass: "Plante",
    Ice: "Glace",
    Fighting: "Combat",
    Poison: "Poison",
    Ground: "Sol",
    Flying: "Vol",
    Psychic: "Psy",
    Bug: "Insecte",
    Rock: "Roche",
    Ghost: "Spectre",
    Dragon: "Dragon",
    Dark: "Ténèbres",
    Steel: "Acier",
    Fairy: "Fée",
  };
  const colors = {
    Normal: "#b8afa0",
    Fire: "#e88b60",
    Water: "#65a8d6",
    Electric: "#e7c866",
    Grass: "#8cbd73",
    Ice: "#91ced1",
    Fighting: "#c9846a",
    Poison: "#b08ac4",
    Ground: "#c6a379",
    Flying: "#99b9d5",
    Psychic: "#da8ca4",
    Bug: "#a9bd67",
    Rock: "#bca780",
    Ghost: "#938fb9",
    Dragon: "#828fd0",
    Dark: "#897d91",
    Steel: "#a2b9bf",
    Fairy: "#d9a6c4",
  };
  function effectiveness(type, types) {
    return types.reduce((a, t) => a * (chart[type]?.[t] ?? 1), 1);
  }
  function stats(p, l) {
    let r = {};
    for (let [k, b] of Object.entries(p.stats))
      r[k] = Math.floor(((2 * b + 15) * l) / 100) + (k === "hp" ? l + 10 : 5);
    if (p.id === "shedinja") r.hp = 1;
    return r;
  }
  function movelist(p, db, level) {
    let pool = p.moves.map((id) => db[id]).filter(Boolean);
    let max = level < 12 ? 55 : level < 24 ? 75 : level < 40 ? 95 : 120;
    pool = pool.filter((m) => m.power <= max);
    let out = [];
    for (let type of p.types) {
      let m = pool
        .filter((m) => m.type === type)
        .sort((a, b) => b.power - a.power)[0];
      if (m && !out.includes(m.id)) out.push(m.id);
    }
    for (let m of pool.sort((a, b) => b.power - a.power))
      if (!out.includes(m.id) && !out.some((id) => db[id].type === m.type)) {
        out.push(m.id);
        if (out.length >= 3) break;
      }
    if (out.length < 3)
      for (let m of pool)
        if (!out.includes(m.id)) {
          out.push(m.id);
          if (out.length >= 3) break;
        }
    return [...(out.length ? out.slice(0, 3) : ["struggle"]), "focus"];
  }
  function create(id, level, data) {
    const p = data.pokemon[id];
    if (!p) throw Error("Espèce inconnue: " + id);
    let s = stats(p, level),
      moves = movelist(p, data.moves, level);
    return {
      uid: Math.random().toString(36).slice(2),
      id,
      level,
      xp: 0,
      hp: s.hp,
      moves,
      pp: moves.map((x) => data.moves[x]?.pp || 10),
      mega: null,
      stone: null,
    };
  }
  function species(mon, data) {
    return data.pokemon[mon.mega || mon.id];
  }
  function damage(att, def, move, data, rng = Math.random) {
    let a = species(att, data),
      d = species(def, data),
      as = stats(a, att.level),
      ds = stats(d, def.level);
    let eff = move.id === "struggle" ? 1 : effectiveness(move.type, d.types);
    if (!eff) return { damage: 0, effect: 0, crit: false };
    let crit = rng() < 1 / 24;
    let special = move.category === "Special";
    let raw =
      Math.floor(
        Math.floor(
          (((2 * att.level) / 5 + 2) *
            move.power *
            (special ? as.spa : as.atk)) /
            (special ? ds.spd : ds.def),
        ) / 50,
      ) + 2;
    return {
      damage: Math.max(
        1,
        Math.floor(
          raw *
            (move.id !== "struggle" && a.types.includes(move.type) ? 1.5 : 1) *
            eff *
            (crit ? 1.5 : 1) *
            (0.85 + rng() * 0.15) *
            (att.focus ? 1.35 : 1),
        ),
      ),
      effect: eff,
      crit,
    };
  }
  function catchChance(mon, data) {
    let p = species(mon, data),
      max = stats(p, mon.level).hp;
    return Math.min(
      0.95,
      Math.max(
        0.03,
        ((((3 * max - 2 * mon.hp) / (3 * max)) * (p.catchRate || 45)) / 255) *
          1.7,
      ),
    );
  }
  function megaOptions(mon, data) {
    return Object.values(data.pokemon).filter(
      (p) => p.mega && p.base === mon.id,
    );
  }
  function clearMega(mon) {
    mon.mega = null;
    mon.focus = false;
    return mon;
  }
  function validateSave(s, data) {
    if (
      !s ||
      s.version !== 1 ||
      !Array.isArray(s.party) ||
      s.party.length < 1 ||
      s.party.length > 6 ||
      !Array.isArray(s.box) ||
      s.box.length > 5000 ||
      !Number.isInteger(s.region) ||
      s.region < 0 ||
      s.region > 6 ||
      !["town", "route", "site"].includes(s.zone) ||
      !Array.isArray(s.progress) ||
      s.progress.length !== 7 ||
      s.progress.some((n) => !Number.isInteger(n) || n < 0 || n > 4)
    )
      throw Error("Sauvegarde incompatible.");
    for (let m of [...s.party, ...s.box]) {
      if (
        !data.pokemon[m.id] ||
        !Number.isInteger(m.level) ||
        m.level < 1 ||
        m.level > 100 ||
        !Array.isArray(m.moves) ||
        m.moves.length < 1 ||
        m.moves.length > 4 ||
        m.moves.some((id) => !data.moves[id]) ||
        !Array.isArray(m.pp) ||
        m.pp.length !== m.moves.length ||
        m.pp.some((x) => !Number.isFinite(x) || x < 0) ||
        !Number.isFinite(m.hp) ||
        m.hp < 0 ||
        !Number.isFinite(m.xp)
      )
        throw Error("Pokémon invalide.");
      m.mega = null;
      m.focus = false;
      m.hp = Math.min(m.hp, stats(data.pokemon[m.id], m.level).hp);
    }
    for (let n of ["money", "balls", "potions", "x", "y"])
      if (!Number.isFinite(s[n]) || s[n] < 0 || s[n] > 1e8)
        throw Error("Valeur invalide.");
    if (
      !Array.isArray(s.caught) ||
      s.caught.some((id) => !data.pokemon[id]) ||
      !Array.isArray(s.seen) ||
      !Array.isArray(s.stones) ||
      !Array.isArray(s.puzzles) ||
      s.puzzles.length !== 7 ||
      !s.flags ||
      typeof s.flags !== "object"
    )
      throw Error("Progression invalide.");
    return s;
  }
  const api = {
    chart,
    typeNames,
    colors,
    effectiveness,
    stats,
    movelist,
    create,
    species,
    damage,
    catchChance,
    megaOptions,
    clearMega,
    validateSave,
  };
  if (typeof module !== "undefined") module.exports = api;
  root.Core = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
