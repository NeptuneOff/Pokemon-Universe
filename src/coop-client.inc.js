// Inserted into game.js by tools/assemble_coop.py; this file owns the co-op adapter.
let net = null,
  netTimer = null;
async function api(route, body) {
  let headers = { "Content-Type": "application/json" };
  if (net) {
    headers["X-Session"] = net.code;
    headers["X-Player"] = net.token;
  }
  let res = await fetch("/api/" + route, {
    method: body ? "POST" : "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let value = await res.json();
  if (!res.ok) throw Error(value.error || "Connexion interrompue.");
  return value;
}
function coopSetup() {
  if (location.protocol === "file:")
    return dialog(
      "Jouer en duo",
      "Lance le serveur avec DEMARRER-DUO.bat sur le PC hôte, puis ouvre l’adresse indiquée sur les deux PC. Le mode duo ne fonctionne pas en ouvrant directement le fichier HTML.",
    );
  modal(
    '<div class="eyebrow">DEUX VOYAGEURS / UNE HISTOIRE</div><h2>Créer ton identité.</h2><p>Vous partagez les conséquences de l’enquête, mais chacun détient ses propres indices et garde son équipe.</p><input id="playerName" maxlength="20" placeholder="Ton prénom ou pseudo" value="Karl"><select id="playerRole"><option value="analyst">Analyste · déchiffrage et tactique</option><option value="ranger">Éclaireur · terrain et protection</option></select><select id="playerColor"><option value="#b45e56">Veste corail</option><option value="#567dab">Veste azur</option><option value="#8a68a1">Veste violette</option><option value="#5b9b7c">Veste sauge</option></select><select id="playerOrigin"><option value="curieux">Tempérament curieux</option><option value="protecteur">Tempérament protecteur</option><option value="audacieux">Tempérament audacieux</option></select><input id="joinCode" maxlength="6" placeholder="Code de la partie à rejoindre"><p class="tip">Le deuxième joueur reçoit le rôle complémentaire. L’apparence et le tempérament contribuent à une graine personnelle : les rencontres scénarisées et les indices secondaires varieront.</p>',
  );
  let connect = async (join) => {
    let profile = {
      name: $("playerName").value,
      role: $("playerRole").value,
      color: $("playerColor").value,
      origin: $("playerOrigin").value,
    };
    try {
      let s = await api(join ? "join" : "create", {
        profile,
        code: $("joinCode").value,
      });
      net = {
        code: s.code,
        token: s.token,
        id: s.id,
        profile: s.profile,
        seed: s.seed,
        snapshot: s,
        revision: s.revision,
        lastResult: null,
        busy: false,
      };
      localStorage.setItem(
        "meridian-connection",
        JSON.stringify({ code: net.code, token: net.token }),
      );
      state = null;
      starter();
      startNet();
      toast(
        "Partie " +
          net.code +
          " · " +
          (net.profile.role === "ranger" ? "Éclaireur" : "Analyste"),
      );
    } catch (e) {
      toast(e.message);
    }
  };
  rowButtons([
    ["Créer la partie", () => connect(false)],
    ["Rejoindre", () => connect(true)],
    ["Reprendre ma connexion", resumeNet],
    ["Retour", title, true],
  ]);
}
async function resumeNet() {
  try {
    let info = JSON.parse(localStorage.getItem("meridian-connection"));
    if (!info) throw Error("Aucune connexion mémorisée sur ce navigateur.");
    net = { ...info, busy: false, lastResult: null };
    let s = await api("state");
    net.id = s.id;
    net.profile = s.profile;
    net.seed = s.seed;
    net.revision = s.revision;
    net.snapshot = s;
    if (s.game) loadState(s.game);
    else starter();
    applyNet(s);
    startNet();
  } catch (e) {
    net = null;
    toast(e.message);
  }
}
function applyNet(s) {
  if (!net) return;
  net.snapshot = s;
  net.revision = s.revision;
  if (!state) return;
  state.progress = [...s.progress];
  state.puzzles = [...s.puzzles];
  s.guards.forEach((v, i) => {
    if (v) state.flags["guard" + i] = true;
  });
  state.finished = s.progress[6] === 4;
  for (let [i, outcome] of Object.entries(s.outcomes || {})) {
    if (!state.flags["outcome" + i]) {
      state.flags["outcome" + i] = true;
      if (outcome === "restoration") {
        state.balls += 8;
        state.potions += 4;
      } else if (outcome === "publication") state.money += 800;
      else {
        state.money += 400;
        state.balls += 4;
      }
    }
  }
  if (s.progress[3] === 4 && !state.megaUnlocked) {
    state.megaUnlocked = true;
    state.stones.push("lucariomega");
    let gift = C.create("lucario", 43, D);
    gift.stone = "lucariomega";
    receive(gift);
  }
  if (s.battle) {
    if (s.battle.status === "active") {
      keys = {};
      close();
      coopBattleUI();
    } else if (net.lastResult !== s.battle.id) {
      net.lastResult = s.battle.id;
      if (s.game) {
        state = cloneJSON(s.game);
        state.progress = [...s.progress];
        state.puzzles = [...s.puzzles];
      }
      document.querySelector(".coop-ui")?.remove();
      let won = s.battle.status === "won";
      if (!won) {
        heal();
        state.zone = "town";
        state.x = 20;
        state.y = 18;
        map = World.make(state.region, "town");
      }
      dialog(
        won ? "Victoire du duo" : "Équipes secourues",
        s.battle.log.join(" "),
        () => {
          close();
          api("ack", {})
            .then(applyNet)
            .catch((e) => toast(e.message));
        },
      );
    }
  } else document.querySelector(".coop-ui")?.remove();
  refresh();
  let partner = s.players.find((p) => p.id !== net.id);
  $("saveStatus").textContent =
    "DUO " +
    s.code +
    " · " +
    (partner
      ? partner.online
        ? partner.profile.name + " connecté"
        : "Partenaire déconnecté"
      : "En attente du partenaire");
}
function cloneJSON(v) {
  return JSON.parse(JSON.stringify(v));
}
function startNet() {
  clearInterval(netTimer);
  netTimer = setInterval(async () => {
    if (!net || net.busy) return;
    net.busy = true;
    try {
      let s = await api("sync", { game: state, revision: net.revision });
      applyNet(s);
      net.error = false;
    } catch (e) {
      if (!net.error) {
        toast("Connexion : " + e.message);
        net.error = true;
      }
    } finally {
      if (net) net.busy = false;
    }
  }, 500);
}
async function coopEvent(type, extra = {}) {
  try {
    await api("sync", { game: state, revision: net.revision }).then(applyNet);
    let s = await api("event", { type, ...extra });
    applyNet(s);
    return true;
  } catch (e) {
    toast(e.message);
    return false;
  }
}
function privateClue() {
  let r = CAMPAIGN[state.region];
  if (net.profile.role === "analyst")
    return (
      "Tes relevés identifient les bornes de départ et d’arrivée : " +
      r.symbols[r.puzzle[0]] +
      " puis, à la fin, " +
      r.symbols[r.puzzle[2]] +
      ". Tu dois régler ces deux bornes. Ton partenaire possède l’étape intermédiaire."
    );
  return (
    "Les traces des Pokémon convergent vers " +
    r.symbols[r.puzzle[1]] +
    ". C’est la borne que tu dois stabiliser, entre les deux réglages de ton partenaire."
  );
}
function personalEvent() {
  let events = [
    "Un Pokémon blessé a retrouvé sa route grâce à tes soins.",
    "Un transporteur t’a confié le journal d’une cargaison disparue.",
    "Une empreinte étrangère à la région révèle un passage récent.",
    "Un habitant reconnaît le symbole que tu portes sur ton carnet.",
  ];
  let idx = (net.seed + state.region * 13) % events.length;
  return (
    events[idx] +
    " " +
    (net.profile.role === "analyst"
      ? "Ton analyse recoupe la fréquence des balises."
      : "Ton observation confirme que les migrations sont forcées.")
  );
}
async function coopInteract(o) {
  if (!net || !o) return false;
  let i = state.region,
    p = state.progress[i],
    r = CAMPAIGN[i];
  if (o.kind === "mentor") {
    if (p === 0) {
      dialog(
        r.mentor,
        r.intro +
          " Vous formez un binôme : les mesures de l’analyste et les observations de l’éclaireur seront indispensables.",
        async () => {
          close();
          await coopEvent("start");
        },
      );
    } else if (p === 3) {
      modal(
        '<div class="eyebrow">UNE DÉCISION À DEUX</div><h2>Que faire de vos découvertes ?</h2><p>' +
          escape(r.outro) +
          "</p><p>Publier immédiatement les preuves renforce la transparence. Restaurer d’abord le site protège les habitats avant l’annonce. Chacun dépose son choix ; vos deux positions sont conservées dans le journal partagé.</p>",
      );
      rowButtons([
        [
          "Publier les preuves",
          async () => {
            await coopEvent("choice", { choice: "publish" });
            await coopEvent("complete");
            close();
          },
        ],
        [
          "Restaurer d’abord",
          async () => {
            await coopEvent("choice", { choice: "restore" });
            await coopEvent("complete");
            close();
          },
        ],
      ]);
    } else
      dialog(
        r.mentor,
        p === 4
          ? "Votre mission commune est accomplie ici. " +
              ({
                restoration:
                  "Vous avez restauré les habitats : le réseau fournit des Balls et des soins.",
                publication:
                  "Vous avez publié les preuves : la Ligue finance la suite de l’enquête.",
                compromise:
                  "Vos points de vue ont conduit à une restauration accompagnée d’une publication progressive.",
              }[net.snapshot.outcomes?.[i]] || "")
          : objective(),
      );
    return true;
  }
  if (o.kind === "sign" && state.zone === "site") {
    dialog("Ton indice personnel", privateClue());
    return true;
  }
  if (o.kind === "rune") {
    let ok = await coopEvent("rune", { index: o.index });
    if (ok) toast("Circuit commun : " + state.puzzles[i] + "/3");
    return true;
  }
  if (o.kind === "terminal") {
    if (state.puzzles[i] < 3) {
      dialog(
        "Console",
        "Chaque rôle possède une partie de la séquence. Consultez séparément l’inscription et échangez vos informations.",
      );
      return true;
    }
    dialog(
      net.profile.role === "analyst"
        ? "Rapport de l’analyste"
        : "Rapport de l’éclaireur",
      personalEvent() + " " + r.reveal,
      async () => {
        close();
        if (await coopEvent("evidence"))
          toast(
            state.progress[i] >= 2
              ? "Vos preuves se recoupent. Le défi commun est ouvert."
              : "Ton rapport est enregistré. Il manque celui de ton partenaire.",
          );
      },
    );
    return true;
  }
  if (o.kind === "boss") {
    if (p < 2) {
      dialog(
        r.boss,
        "J’attends vos deux rapports complémentaires. Chacun doit examiner la console après l’accord des bornes.",
      );
      return true;
    }
    if (p >= 3) {
      dialog(
        r.boss,
        "Vous avez remporté le défi ensemble. Retournez au relais.",
      );
      return true;
    }
    dialog(
      r.boss,
      "Chacun choisira les actions de son équipe. Le combat commencera quand vous serez tous les deux prêts sur ce site.",
      async () => {
        close();
        try {
          await api("sync", { game: state, revision: net.revision }).then(
            applyNet,
          );
          applyNet(await api("ready", {}));
          toast("Prêt pour le défi commun.");
        } catch (e) {
          toast(e.message);
        }
      },
    );
    return true;
  }
  if (o.kind === "travel") {
    let other = net.snapshot.players.find((p) => p.id !== net.id);
    if (
      !other?.online ||
      other.position?.zone !== "town" ||
      Math.abs(other.position.region - state.region) > 1
    ) {
      dialog(
        "Départ coordonné",
        "Retrouvez-vous tous les deux au relais avant de choisir la prochaine région.",
      );
      return true;
    }
    return false;
  }
  if (o.kind === "item") {
    if (state.flags["personal" + i]) {
      dialog("Trace personnelle", personalEvent());
      return true;
    }
    state.flags["personal" + i] = true;
    state.money += net.profile.role === "analyst" ? 250 : 100;
    state.balls += net.profile.role === "ranger" ? 4 : 1;
    refresh();
    dialog(
      "Une découverte qui t’appartient",
      personalEvent() +
        " Tu reçois " +
        (net.profile.role === "analyst"
          ? "250 ₽ et 1 Ball."
          : "100 ₽ et 4 Balls."),
    );
    return true;
  }
  return false;
}
function coopBattleUI() {
  let b = net?.snapshot?.battle;
  if (!b || b.status !== "active") return;
  let old = document.querySelector(".coop-ui"),
    key = b.id + "-" + b.round + "-" + Object.keys(b.actions).length;
  if (old?.dataset.key === key) return;
  old?.remove();
  let me = b.players.find((p) => p.id === net.id),
    m = me.party[me.active],
    pending = !!b.actions[net.id],
    box = document.createElement("div");
  box.className = "battle-ui coop-ui";
  box.dataset.key = key;
  box.innerHTML =
    "<p>" +
    escape(
      "Tour " +
        b.round +
        " · " +
        (pending
          ? "Action validée. En attente du partenaire."
          : b.log.slice(-1)[0]),
    ) +
    '</p><div class="battle-grid"></div><div class="battle-options"></div>';
  let send = async (a) => {
    try {
      applyNet(await api("action", { ...a, round: b.round }));
    } catch (e) {
      toast(e.message);
    }
  };
  let target = b.enemies.findIndex((m) => m.hp > 0);
  m.moves.forEach((id, slot) => {
    let move = D.moves[id],
      btn = button(move.name, () => send({ type: "move", slot, target }));
    btn.disabled = pending || m.hp <= 0 || m.pp[slot] <= 0;
    box.querySelector(".battle-grid").append(btn);
  });
  if (m.pp.every((x) => x <= 0)) {
    let struggle = button("Lutte", () => send({ type: "struggle", target }));
    struggle.disabled = pending;
    box.querySelector(".battle-grid").append(struggle);
  }
  let support = button(
    me.role === "ranger" ? "Protéger le duo" : "Analyser une ouverture",
    () => send({ type: "support" }),
  );
  support.disabled = pending || me.supportUsed;
  box.querySelector(".battle-options").append(support);
  let megaBtn = button("Méga", () => send({ type: "mega" }));
  megaBtn.disabled = pending || me.megaUsed || !state.megaUnlocked || !m.stone;
  box.querySelector(".battle-options").append(megaBtn);
  let choose = document.createElement("select");
  choose.title = "Cible";
  b.enemies.forEach((e, i) => {
    if (e.hp > 0) {
      let opt = document.createElement("option");
      opt.value = i;
      opt.textContent = D.pokemon[e.id].fr;
      choose.append(opt);
    }
  });
  choose.onchange = () => (target = Number(choose.value));
  choose.disabled = pending;
  box.querySelector(".battle-options").append(choose);
  let swap = document.createElement("select");
  swap.title = "Changer de partenaire";
  swap.innerHTML =
    '<option value="">Changer…</option>' +
    me.party
      .map(
        (m, i) =>
          '<option value="' +
          i +
          '" ' +
          (m.hp <= 0 || i === me.active ? "disabled" : "") +
          ">" +
          escape(D.pokemon[m.id].fr) +
          "</option>",
      )
      .join("");
  swap.onchange = () => send({ type: "switch", slot: Number(swap.value) });
  swap.disabled = pending;
  box.querySelector(".battle-options").append(swap);
  $("viewport").append(box);
}
function drawCoopBattle() {
  let b = net.snapshot.battle;
  pixelRect(0, 0, 640, 416, "#dce3cc");
  pixelRect(0, 0, 640, 110, "#b9d7cf");
  pixelRect(0, 110, 640, 306, "#c9d4af");
  let foes = b.enemies.filter((m) => m.hp > 0).slice(0, 2);
  foes.forEach((m, i) => {
    drawPokemon(C.species(m, D), 385 + i * 165, 164, 1.1, false, !!m.mega);
    hpPanel(m, 310 + i * 165, 20, 155);
  });
  b.players.forEach((p, i) => {
    let m = p.party[p.active];
    drawPokemon(C.species(m, D), 90 + i * 175, 275, 1.35, true, !!m.mega);
    hpPanel(m, 15 + i * 180, 180, 170);
    text(
      p.name + " · " + (p.role === "ranger" ? "Éclaireur" : "Analyste"),
      25 + i * 180,
      173,
      8,
    );
  });
  $("prompt").textContent = "";
}
function drawPartner() {
  if (!net) return;
  for (let p of net.snapshot.players) {
    if (
      p.id === net.id ||
      !p.online ||
      !p.position ||
      p.position.region !== state?.region ||
      p.position.zone !== state?.zone
    )
      continue;
    person(p.position.x * 16, p.position.y * 16, p.profile.color);
    text(
      p.profile.name,
      p.position.x * 16 + 8,
      p.position.y * 16 - 5,
      8,
      "#f8efd1",
      "center",
    );
  }
}
