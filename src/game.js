(function () {
  "use strict";
  const D = GAME_DATA,
    C = Core,
    $ = (id) => document.getElementById(id),
    canvas = $("game"),
    ctx = canvas.getContext("2d"),
    overlay = $("overlay");
  ctx.imageSmoothingEnabled = false;
  const KEY = "meridian-save-v1",
    BASE = Object.values(D.pokemon).filter((p) => !p.forme),
    escape = (s) =>
      String(s).replace(
        /[&<>"']/g,
        (c) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[c],
      );
  let state = null,
    map = World.make(0, "town"),
    battle = null,
    keys = {},
    lastStep = 0,
    steps = 0,
    frame = 0,
    sound = false,
    audio = null,
    toastTimer = null,
    transition = 0;
  const images = new Map();
  function img(path) {
    if (!path) return null;
    if (!images.has(path)) {
      let i = new Image();
      i.src = path;
      images.set(path, i);
    }
    return images.get(path);
  }
  const name = (m) => D.pokemon[m.mega || m.id]?.fr || m.id;
  const maxhp = (m) => C.stats(C.species(m, D), m.level).hp;
  function chirp(freq = 600, d = 0.06) {
    if (!sound) return;
    try {
      audio ||= new (window.AudioContext || window.webkitAudioContext)();
      let o = audio.createOscillator(),
        g = audio.createGain();
      o.type = "triangle";
      o.frequency.value = freq;
      g.gain.setValueAtTime(0.035, audio.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + d);
      o.connect(g);
      g.connect(audio.destination);
      o.start();
      o.stop(audio.currentTime + d);
    } catch {}
  }
  function toast(text) {
    $("toast").textContent = text;
    $("toast").style.opacity = 1;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => ($("toast").style.opacity = 0), 3000);
  }
  function modal(html) {
    keys = {};
    overlay.classList.remove("hidden");
    overlay.innerHTML = '<div class="modal">' + html + "</div>";
  }
  function close() {
    overlay.classList.add("hidden");
    overlay.innerHTML = "";
    keys = {};
    canvas.focus();
  }
  function button(label, fn, secondary = false) {
    let b = document.createElement("button");
    b.textContent = label;
    if (secondary) b.className = "secondary";
    b.onclick = () => {
      chirp();
      fn();
    };
    return b;
  }
  function rowButtons(actions) {
    let row = document.createElement("div");
    row.className = "row";
    for (let [a, f, s] of actions) row.append(button(a, f, s));
    overlay.querySelector(".modal").append(row);
  }
  function dialog(speaker, text, done = close) {
    modal(
      '<div class="eyebrow">' +
        escape(speaker) +
        "</div><p>" +
        escape(text) +
        "</p>",
    );
    rowButtons([["Continuer →", done]]);
  }
  function newState(id) {
    return {
      version: 1,
      region: 0,
      zone: "town",
      x: 20,
      y: 18,
      dir: 2,
      party: [C.create(id, 7, D)],
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
  function save(notify = false) {
    if (!state) return false;
    if (net) {
      if (notify) toast("La partie commune est sauvegardée par le PC hôte.");
      return true;
    }
    if (battle) {
      if (notify) toast("Termine le combat avant de sauvegarder.");
      return false;
    }
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
      $("saveStatus").textContent =
        "Sauvegardé à " +
        new Date().toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
        });
      if (notify) toast("Progression sauvegardée.");
      return true;
    } catch {
      if (notify)
        toast("Stockage indisponible : utilise Exporter dans le menu.");
      return false;
    }
  }
  function loadState(s) {
    C.validateSave(s, D);
    state = s;
    map = World.make(state.region, state.zone);
    if (!World.canWalk(map, state.x, state.y)) {
      state.x = 20;
      state.y = 18;
      state.zone = "town";
      map = World.make(state.region, "town");
    }
    close();
    refresh();
  }
  function title() {
    if (net && state) return menu();
    modal(
      '<div class="title-modal"><div class="eyebrow">UNE AVENTURE À TRAVERS SEPT RÉGIONS</div><h2>MÉRIDIEN</h2><p>Un même monde. Des liens qui grandissent.<br>Une route à tracer ensemble.</p><p class="tip">Campagne pilote originale · PC · Jeu local hors ligne</p></div>',
    );
    let saved = null;
    try {
      saved = localStorage.getItem(KEY);
    } catch {}
    let acts = [];
    if (saved)
      acts.push([
        "Reprendre le voyage",
        () => {
          try {
            loadState(JSON.parse(saved));
          } catch (e) {
            toast(e.message);
          }
        },
      ]);
    acts.push([
      "Nouvelle aventure",
      () => {
        if (saved)
          dialog(
            "Nouveau départ",
            "La nouvelle partie remplacera la sauvegarde locale. Tu peux d’abord la reprendre et l’exporter depuis le menu.",
            starter,
          );
        else starter();
      },
    ]);
    acts.push(["Jouer en duo", coopSetup]);
    rowButtons(acts);
  }
  function starter() {
    modal(
      '<div class="eyebrow">PROLOGUE / KANTO</div><h2>Ton premier partenaire.</h2><p>La professeure Lise t’attend au laboratoire du relais de Carmin. Choisis le Pokémon qui parcourra le Méridien à tes côtés.</p><div class="grid" id="starters"></div>',
    );
    for (let id of ["bulbasaur", "charmander", "squirtle"]) {
      let p = D.pokemon[id],
        b = document.createElement("button");
      b.className = "starter";
      b.innerHTML =
        '<img src="' +
        p.sprite +
        '" alt="' +
        p.fr +
        '"><strong>' +
        p.fr +
        "</strong><small>" +
        C.typeNames[p.types[0]] +
        "</small>";
      b.onclick = () => {
        state = newState(id);
        map = World.make(0, "town");
        close();
        save();
        refresh();
        dialog(
          "Carnet de départ",
          "Flèches ou ZQSD pour marcher, E pour parler. Va voir Lise devant le laboratoire, au nord de la place. Tu disposes de 12 Poké Balls et de 6 potions. Ton équipe et tes progrès seront conservés d’une région à l’autre.",
        );
      };
      $("starters").append(b);
    }
  }
  function objective() {
    if (!state) return "Choisis ton premier partenaire.";
    let p = state.progress[state.region],
      r = CAMPAIGN[state.region];
    return p === 0
      ? "Rencontre " + r.mentor + " au relais."
      : p === 1
        ? !state.flags["guard" + state.region]
          ? "Traverse " + r.route + " et affronte l’agent Atlas."
          : "À " +
            r.site +
            ", active les trois bornes dans l’ordre de l’inscription, puis examine la console."
        : p === 2
          ? "Affronte " + r.boss + " au sud du site."
          : p === 3
            ? "Rapporte tes découvertes à " + r.mentor + "."
            : state.finished
              ? "Le réseau est ouvert. Explore les habitats et complète ton Pokédex."
              : "Rejoins le quai au sud-est pour poursuivre le voyage.";
  }
  function refresh() {
    let r = CAMPAIGN[state?.region || 0];
    $("location").textContent = map.name;
    $("chapter").textContent =
      r.name.toUpperCase() +
      " / CHAPITRE " +
      String((state?.region || 0) + 1).padStart(2, "0");
    $("regionTitle").textContent = r.subtitle + ".";
    $("objectiveText").textContent = objective();
    $("regionTrack").innerHTML = CAMPAIGN.map(
      (x, i) =>
        '<div title="' +
        x.name +
        '" class="region-dot ' +
        (state?.progress[i] === 4
          ? "done"
          : i === (state?.region || 0)
            ? "active"
            : "") +
        '"></div>',
    ).join("");
    if (!state) return;
    $("money").textContent = state.money;
    $("balls").textContent = state.balls;
    $("potions").textContent = state.potions;
    $("party").innerHTML = state.party
      .map((m) => {
        let p = D.pokemon[m.id];
        return (
          '<div class="party-mini">' +
          (p.sprite
            ? '<img src="' + p.sprite + '" alt="">'
            : "<span>◇</span>") +
          '<div class="details"><strong>' +
          escape(p.fr) +
          "</strong><small>N. " +
          m.level +
          '</small><div class="hpbar"><i style="width:' +
          Math.max(0, (m.hp / maxhp(m)) * 100) +
          '%"></i></div></div></div>'
        );
      })
      .join("");
  }
  function heal() {
    for (let m of [...state.party, ...state.box]) {
      C.clearMega(m);
      m.hp = maxhp(m);
      m.pp = m.moves.map((id) => D.moves[id]?.pp || 15);
    }
    refresh();
  }
  function changeZone(zone, x, y) {
    state.zone = zone;
    state.x = x;
    state.y = y;
    map = World.make(state.region, zone);
    steps = 0;
    transition = 0.25;
    close();
    save();
    refresh();
    toast(map.name);
  }
  async function interact(o) {
    if (trading()) return tradeUI();
    if (!o || battle || !overlay.classList.contains("hidden")) return;
    if (await coopInteract(o)) return;
    const i = state.region,
      r = CAMPAIGN[i],
      p = state.progress[i];
    switch (o.kind) {
      case "exit":
        if (o.to === "site" && !state.flags["guard" + i])
          return dialog(
            "Passage surveillé",
            "L’agent Atlas sur la route bloque l’accès. Approche-toi de lui et parle-lui.",
          );
        changeZone(o.to, o.x2, o.y2);
        break;
      case "mentor":
        if (p === 0) {
          dialog(r.mentor, r.intro, () => {
            state.progress[i] = 1;
            close();
            save();
            refresh();
          });
        } else if (p === 3) {
          dialog(r.mentor, r.outro, () => {
            state.progress[i] = 4;
            if (i === 3) {
              state.megaUnlocked = true;
              if (!state.stones.includes("lucariomega"))
                state.stones.push("lucariomega");
              let m = C.create("lucario", 43, D);
              m.stone = "lucariomega";
              receive(m);
              toast("Bracelet de résonance, Lucarite et Lucario reçus.");
            }
            if (i === 6) state.finished = true;
            close();
            save();
            refresh();
          });
        } else
          dialog(
            r.mentor,
            p === 4
              ? "Le relais reste à ta disposition. Le centre soigne gratuitement ton équipe ; le bureau des habitats organise les recherches."
              : objective(),
          );
        break;
      case "heal":
        heal();
        save();
        dialog(
          "Centre Pokémon",
          "Toute ton équipe et les Pokémon du refuge sont soignés. Les capacités ont récupéré leurs PP. Bonne route !",
        );
        break;
      case "shop":
        shop();
        break;
      case "reserve":
        reserve();
        break;
      case "travel":
        travel();
        break;
      case "guard":
        if (p === 0)
          return dialog(
            "Agent Atlas",
            "La station est fermée. Obtiens d’abord un mandat auprès du relais.",
          );
        if (state.flags["guard" + i])
          return dialog(
            "Agent Atlas",
            "Tu as gagné. Le chemin du site est ouvert.",
          );
        dialog(
          "Agent Atlas",
          "Les relevés de la station appartiennent à Atlas. Si tu veux passer, montre que tu peux protéger ton équipe.",
          () => {
            close();
            startBattle(
              r.guardian.map((id) => C.create(id, r.level + 2, D)),
              "guard",
            );
          },
        );
        break;
      case "rune":
        if (p !== 1)
          return toast(
            p > 1
              ? "Le circuit est stabilisé."
              : "Demande d’abord ton mandat au relais.",
          );
        if (!state.flags["guard" + i])
          return toast("L’accès au circuit n’est pas encore autorisé.");
        let n = state.puzzles[i];
        if (n >= 3)
          return toast(
            "Les trois bornes sont accordées. Examine la console au nord.",
          );
        if (r.puzzle[n] === o.index) {
          state.puzzles[i]++;
          chirp(500 + state.puzzles[i] * 160);
          toast(o.name + " · " + state.puzzles[i] + "/3");
        } else {
          state.puzzles[i] = 0;
          chirp(150);
          toast("La résonance retombe. Relis l’inscription au sud-ouest.");
        }
        save();
        break;
      case "terminal":
        if (p > 1) return dialog("Console", r.reveal);
        if (state.puzzles[i] < 3)
          return dialog(
            "Console",
            "Le circuit doit être accordé. Une inscription au sud-ouest décrit l’ordre des trois bornes.",
          );
        dialog("Relevé sécurisé", r.reveal, () => {
          state.progress[i] = 2;
          close();
          save();
          refresh();
        });
        break;
      case "boss":
        if (p < 2)
          return dialog(
            r.boss,
            "Récupère d’abord les relevés de la console. Nous devons comprendre ce qui se passe avant de poursuivre.",
          );
        if (p >= 3)
          return dialog(
            r.boss,
            "Ta victoire est reconnue. Rapporte les résultats au relais.",
          );
        dialog(
          r.boss,
          "Tu as apporté les preuves. Maintenant, montre comment ton équipe a grandi.",
          () => {
            close();
            startBattle(
              r.team.map((id, j) =>
                C.create(
                  id,
                  r.level + 5 + (j === r.team.length - 1 ? 1 : 0),
                  D,
                ),
              ),
              "boss",
            );
          },
        );
        break;
      case "item":
        if (state.flags["crate" + i]) return toast("La caisse est vide.");
        state.flags["crate" + i] = true;
        state.balls += 4;
        state.potions += 2;
        save();
        refresh();
        toast("4 Poké Balls et 2 potions récupérées.");
        break;
      case "home":
        dialog(
          "Maison des voyageurs",
          "Des chercheurs de différentes régions partagent leurs observations. Le Méridien organise leurs voyages sans imposer les migrations des Pokémon.",
        );
        break;
      default:
        dialog(o.name, o.text || r.ambient[0]);
    }
  }
  function shop() {
    modal(
      '<div class="eyebrow">COMPTOIR DU RELAIS</div><h2>Préparer la route.</h2><p>Solde : ' +
        state.money +
        " ₽. Les soins du centre sont gratuits.</p>",
    );
    rowButtons([
      ["5 Poké Balls · 300 ₽", () => buy("balls", 5, 300)],
      ["3 potions · 180 ₽", () => buy("potions", 3, 180)],
      ["Méga-Gemmes", stones],
      ["Fermer", close, true],
    ]);
  }
  function buy(item, n, price) {
    if (state.money < price) return toast("Fonds insuffisants.");
    state.money -= price;
    state[item] += n;
    save();
    refresh();
    shop();
  }
  function stones() {
    if (!state.megaUnlocked)
      return dialog(
        "Chercheuse du relais",
        "Le bracelet de résonance sera confié à ton équipe à la fin de l’enquête de Sinnoh.",
        shop,
      );
    modal(
      '<div class="eyebrow">ATELIER DE RÉSONANCE</div><h2>Accorder une Méga-Gemme.</h2><p>Chaque gemme coûte 350 ₽. Équipe-la depuis le menu de ton équipe. Les variantes X, Y et Z restent distinctes.</p><input id="stoneSearch" placeholder="Rechercher un Pokémon"><div class="entries" id="stoneEntries"></div>',
    );
    const render = () => {
      let q = $("stoneSearch").value.toLowerCase();
      $("stoneEntries").innerHTML = "";
      for (let p of Object.values(D.pokemon)
        .filter((p) => p.mega && p.fr.toLowerCase().includes(q))
        .slice(0, 100)) {
        let owned = state.stones.includes(p.id);
        let b = button(p.fr + (owned ? " · acquise" : " · 350 ₽"), () => {
          if (owned) return;
          if (state.money < 350) return toast("Fonds insuffisants.");
          state.money -= 350;
          state.stones.push(p.id);
          save();
          refresh();
          render();
        });
        b.className = "entry";
        $("stoneEntries").append(b);
      }
    };
    $("stoneSearch").oninput = render;
    render();
    rowButtons([["Retour", shop, true]]);
  }
  function travel() {
    let r = state.region;
    if (state.progress[r] !== 4)
      return dialog(
        "Liaison Méridien",
        "La prochaine liaison nécessite ton accréditation régionale. Termine l’enquête et rapporte tes résultats au relais.",
      );
    modal(
      '<div class="eyebrow">LIAISONS INTER-RÉGIONALES</div><h2>Garder le cap.</h2><p>Ton équipe, tes objets et ton Pokédex voyagent avec toi. Aucune remise à zéro.</p>',
    );
    let max = Math.min(
      6,
      state.progress.findIndex((x) => x !== 4),
    );
    if (max < 0) max = 6;
    let actions = [];
    for (let i = 0; i <= max; i++)
      if (i !== r)
        actions.push([
          CAMPAIGN[i].name,
          () => {
            state.region = i;
            heal();
            changeZone("town", 20, 18);
            dialog("Arrivée à " + CAMPAIGN[i].name, CAMPAIGN[i].intro);
          },
        ]);
    if (!actions.length) actions.push(["Continuer", close]);
    actions.push(["Rester ici", close, true]);
    rowButtons(actions);
  }
  function receive(m) {
    state.caught = [...new Set([...state.caught, m.id])];
    state.seen = [...new Set([...state.seen, m.id])];
    if (state.party.length < 6) state.party.push(m);
    else state.box.push(m);
  }
  function habitatRegion(p) {
    if (p.num <= 151) return 0;
    if (p.num <= 251) return 1;
    if (p.num <= 386) return 2;
    if (p.num <= 493) return 3;
    if (p.num <= 649) return 4;
    if (p.num <= 721) return 5;
    if (p.num <= 809) return 6;
    let types = p.types;
    if (types.includes("Ice") || types.includes("Steel")) return 3;
    if (types.includes("Water")) return 2;
    if (types.includes("Grass") || types.includes("Bug")) return 1;
    if (types.includes("Fairy") || types.includes("Psychic")) return 5;
    if (types.includes("Dragon") || types.includes("Fire")) return 6;
    return 4;
  }
  function reserve() {
    if (state.progress[state.region] === 0)
      return dialog(
        "Bureau des habitats",
        "Enregistre d’abord ton mandat auprès du responsable du relais.",
      );
    modal(
      '<div class="eyebrow">RÉSEAU DES REFUGES / ' +
        CAMPAIGN[state.region].name.toUpperCase() +
        '</div><h2>Observer, puis rencontrer.</h2><p>Le réseau organise des rencontres de terrain avec les espèces recensées. Les espèces rares sont étudiées après la campagne. Les espèces de Galar et Paldea sont réparties selon leur habitat.</p><input id="reserveSearch" placeholder="Nom français ou numéro"><div class="entries" id="reserveEntries"></div>',
    );
    const render = () => {
      let q = $("reserveSearch").value.toLowerCase();
      $("reserveEntries").innerHTML = "";
      let list = BASE.filter(
        (p) =>
          habitatRegion(p) === state.region &&
          (!p.legendary || state.finished) &&
          (p.fr.toLowerCase().includes(q) || String(p.num) === q),
      );
      for (let p of list.slice(0, 150)) {
        let b = button("", () => {
          let lvl = Math.min(
            CAMPAIGN[state.region].cap - 2,
            CAMPAIGN[state.region].level + 3,
          );
          close();
          startBattle([C.create(p.id, lvl, D)], "wild");
        });
        b.className = "entry";
        b.innerHTML =
          (p.sprite
            ? '<img src="' + p.sprite + '" alt="">'
            : "<span>◇</span>") +
          "<span>" +
          escape(p.fr) +
          "<small>#" +
          p.num +
          " · " +
          p.types.map((t) => C.typeNames[t]).join(" / ") +
          "</small></span>";
        $("reserveEntries").append(b);
      }
      if (!list.length)
        $("reserveEntries").textContent =
          "Aucune espèce disponible pour cette recherche.";
    };
    $("reserveSearch").oninput = render;
    render();
    rowButtons([["Retour", close, true]]);
  }
  function partyMenu(inBattle = false) {
    if (trading()) return tradeUI();
    if (!state) return;
    if (battle && !inBattle) return;
    modal(
      '<div class="eyebrow">PARTENAIRES DE VOYAGE</div><h2>Une équipe qui grandit.</h2><div id="partyList"></div>',
    );
    state.party.forEach((m, i) => {
      let p = C.species(m, D),
        div = document.createElement("div");
      div.className = "list-card";
      div.innerHTML =
        (p.sprite ? '<img src="' + p.sprite + '" alt="">' : "") +
        "<strong>" +
        escape(p.fr) +
        "</strong> · N. " +
        m.level +
        '<p class="small">PV ' +
        m.hp +
        "/" +
        maxhp(m) +
        " · " +
        p.types.map((t) => C.typeNames[t]).join(" / ") +
        "</p>";
      let row = document.createElement("div");
      row.className = "row";
      if (inBattle) {
        row.append(
          button("Envoyer", () => {
            if (m.hp <= 0) return toast("Ce Pokémon est K.O.");
            if (i === battle.active) return;
            let forced = state.party[battle.active].hp <= 0;
            battle.active = i;
            close();
            if (!forced) {
              battle.busy = true;
              enemyTurn().then(() => {
                battle.busy = false;
                battleUI();
                refresh();
              });
            } else battleUI();
            refresh();
          }),
        );
      } else {
        row.append(
          button(i === 0 ? "En tête" : "Placer en tête", () => {
            [state.party[0], state.party[i]] = [state.party[i], state.party[0]];
            save();
            refresh();
            partyMenu();
          }),
        );
        let options = C.megaOptions(m, D).filter((p) =>
          state.stones.includes(p.id),
        );
        if (options.length) {
          let sel = document.createElement("select");
          sel.innerHTML =
            '<option value="">Sans Méga-Gemme</option>' +
            options
              .map(
                (x) =>
                  '<option value="' +
                  x.id +
                  '" ' +
                  (m.stone === x.id ? "selected" : "") +
                  ">" +
                  escape(x.fr) +
                  "</option>",
              )
              .join("");
          sel.onchange = () => {
            m.stone = sel.value || null;
            save();
          };
          row.append(sel);
        }
        let evo = p.evolutions
          .map((id) => D.pokemon[id])
          .find(
            (e) =>
              e &&
              ((e.evoLevel && m.level >= e.evoLevel) ||
                (!e.evoLevel && m.level >= 30)),
          );
        if (evo)
          row.append(
            button("Évoluer → " + evo.fr, () => {
              m.id = evo.id;
              m.moves = C.movelist(evo, D.moves, m.level);
              m.hp = maxhp(m);
              m.pp = m.moves.map((id) => D.moves[id].pp);
              m.stone = null;
              state.caught = [...new Set([...state.caught, m.id])];
              save();
              refresh();
              partyMenu();
            }),
          );
      }
      div.append(row);
      $("partyList").append(div);
    });
    rowButtons(
      inBattle
        ? [
            [
              "Retour au combat",
              () => {
                close();
                battleUI();
              },
              true,
            ],
          ]
        : [
            ["Refuge (" + state.box.length + ")", boxMenu],
            ["Fermer", close, true],
          ],
    );
  }
  function boxMenu() {
    if (trading()) return tradeUI();
    modal(
      '<div class="eyebrow">REFUGE</div><h2>Les autres partenaires.</h2><p>Sélectionne un Pokémon du refuge pour l’échanger avec le premier de ton équipe. Si une place est libre, il rejoint directement l’équipe.</p><div class="entries" id="boxEntries"></div>',
    );
    state.box.forEach((m, i) => {
      let b = button(name(m) + " · N. " + m.level, () => {
        if (state.party.length < 6) state.party.push(state.box.splice(i, 1)[0]);
        else [state.party[0], state.box[i]] = [state.box[i], state.party[0]];
        save();
        refresh();
        boxMenu();
      });
      $("boxEntries").append(b);
    });
    rowButtons([["Retour", () => partyMenu(), true]]);
  }
  function dex() {
    if (trading()) return tradeUI();
    if (!state || battle) return;
    modal(
      '<div class="eyebrow">POKÉDEX MONDIAL</div><h2>' +
        state.caught.filter((id) => !D.pokemon[id].forme).length +
        " / " +
        BASE.length +
        ' espèces.</h2><input id="dexSearch" placeholder="Nom, numéro ou type"><div class="entries" id="dexEntries"></div>',
    );
    const render = () => {
      let q = $("dexSearch").value.toLowerCase();
      $("dexEntries").innerHTML = "";
      for (let p of BASE.filter(
        (p) =>
          p.fr.toLowerCase().includes(q) ||
          String(p.num) === q ||
          p.types.some((t) => C.typeNames[t].toLowerCase().includes(q)),
      ).slice(0, 150)) {
        let div = document.createElement("div");
        div.className = "entry";
        div.innerHTML =
          (p.sprite
            ? '<img src="' + p.sprite + '" alt="">'
            : "<span>◇</span>") +
          "<span>" +
          escape(p.fr) +
          "<small>#" +
          p.num +
          " · " +
          (state.caught.includes(p.id)
            ? "Capturé"
            : state.seen.includes(p.id)
              ? "Observé"
              : "À découvrir") +
          " · " +
          CAMPAIGN[habitatRegion(p)].name +
          "</small></span>";
        $("dexEntries").append(div);
      }
    };
    $("dexSearch").oninput = render;
    render();
    rowButtons([["Fermer", close, true]]);
  }
  function journal() {
    if (trading()) return tradeUI();
    if (!state || battle) return;
    modal(
      '<div class="eyebrow">LE FIL DE L’ENQUÊTE</div><h2>Sept étapes. Une histoire.</h2>' +
        CAMPAIGN.map(
          (r, i) =>
            '<div class="list-card"><strong>' +
            String(i + 1).padStart(2, "0") +
            " / " +
            r.name +
            " — " +
            r.subtitle +
            '</strong><p class="small">' +
            (state.progress[i] >= 3
              ? escape(r.outro)
              : i === state.region
                ? escape(objective())
                : "Étape à venir.") +
            "</p></div>",
        ).join(""),
    );
    rowButtons([["Fermer", close, true]]);
  }
  function exportSave() {
    if (battle) return toast("Termine le combat avant d’exporter.");
    let blob = new Blob([JSON.stringify(state, null, 2)], {
        type: "application/json",
      }),
      u = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = u;
    a.download = "Meridien-sauvegarde.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(u), 1000);
  }
  function menu() {
    if (trading()) return tradeUI();
    if (!state) return title();
    if (battle || net?.snapshot?.battle?.status === "active") return;
    modal(
      '<div class="eyebrow">PAUSE</div><h2>Prendre une respiration.</h2><p>' +
        Math.floor(state.playtime / 60) +
        " minutes de voyage · " +
        state.progress.filter((x) => x === 4).length +
        ' accréditations régionales.</p><p class="notice">Version pilote : sept chapitres courts sur des lieux originaux. Les régions complètes, toutes les capacités et tous les talents ne sont pas encore réalisés.</p>',
    );
    rowButtons([
      ["Reprendre", close],
      ...(net ? [["Échanger avec mon partenaire", openTrade]] : []),
      ["Sauvegarder", () => save(true)],
      ["Exporter la sauvegarde", exportSave],
      [
        "Importer",
        () => {
          let input = document.createElement("input");
          input.type = "file";
          input.accept = ".json";
          input.onchange = async () => {
            let f = input.files[0];
            if (!f) return;
            if (f.size > 5000000) return toast("Fichier trop volumineux.");
            try {
              let s = JSON.parse(await f.text());
              C.validateSave(s, D);
              dialog(
                "Importer une progression",
                "Cette progression remplacera la sauvegarde locale actuelle.",
                () => {
                  loadState(s);
                  save();
                },
              );
            } catch (e) {
              toast("Import refusé : " + e.message);
            }
          };
          input.click();
        },
      ],
      ["Aide et état du projet", help],
      [
        "Retour au titre",
        () => {
          save();
          title();
        },
        true,
      ],
    ]);
  }
  function help() {
    modal(
      '<div class="eyebrow">CAMPAGNE PILOTE 0.1</div><h2>Ce qui est jouable.</h2><p>21 petites cartes, sept enquêtes reliées, capture, équipe de six, refuge, progression, objets, sauvegarde et Méga-Évolution. Toutes les espèces du catalogue sont accessibles par les bureaux des habitats ; les légendaires se débloquent après la fin.</p><p class="notice">Les capacités utilisent leurs puissance, précision, catégorie et PP. Les effets secondaires, talents et conditions d’évolution complexes restent simplifiés. Concentration est une action propre au prototype. Les Méga-formes sans sprite dédié utilisent provisoirement le sprite de base avec une aura, signalé en combat.</p><p>Les sources, l’inventaire des illustrations manquantes et la feuille de route accompagnent le jeu. Ce n’est pas encore la refonte complète demandée.</p>',
    );
    rowButtons([["Retour", menu, true]]);
  }
  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  function startBattle(enemies, kind) {
    if (trading()) return tradeUI();
    if (!state.party.some((m) => m.hp > 0)) {
      heal();
      return toast("Ton équipe a été soignée.");
    }
    for (let m of state.party) C.clearMega(m);
    battle = {
      enemies,
      index: 0,
      active: state.party.findIndex((m) => m.hp > 0),
      kind,
      busy: false,
      megaUsed: false,
      text:
        kind === "wild"
          ? "Un " + name(enemies[0]) + " sauvage apparaît !"
          : kind === "guard"
            ? "L’agent Atlas engage le combat."
            : CAMPAIGN[state.region].boss + " lance le défi.",
      flash: 0,
    };
    for (let e of enemies) state.seen = [...new Set([...state.seen, e.id])];
    close();
    keys = {};
    battleUI();
    refresh();
    chirp(280, 0.2);
  }
  function battleUI() {
    document.querySelector(".battle-ui")?.remove();
    if (!battle) return;
    let box = document.createElement("div");
    box.className = "battle-ui";
    let active = state.party[battle.active];
    box.innerHTML =
      '<p role="status">' +
      escape(battle.text) +
      '</p><div class="battle-grid"></div><div class="battle-options"></div>';
    active.moves.forEach((id, i) => {
      let m = D.moves[id];
      let b = button("", () => turn("move", i));
      b.innerHTML =
        escape(m.name) +
        "<small>" +
        C.typeNames[m.type] +
        " · " +
        active.pp[i] +
        "/" +
        m.pp +
        " PP</small>";
      b.style.borderLeft = "3px solid " + C.colors[m.type];
      b.disabled = battle.busy || active.hp <= 0 || active.pp[i] <= 0;
      box.querySelector(".battle-grid").append(b);
    });
    if (active.pp.every((p) => p <= 0)) {
      let b = button("Lutte", () => turn("struggle"));
      b.disabled = battle.busy;
      box.querySelector(".battle-grid").append(b);
    }
    let options = [
      [
        "Poké Ball (" + state.balls + ")",
        () => turn("ball"),
        battle.kind !== "wild" || !state.balls,
      ],
      ["Potion (" + state.potions + ")", () => turn("potion"), !state.potions],
      ["Équipe", () => partyMenu(true), false],
      ["Fuite", () => turn("run"), battle.kind !== "wild"],
    ];
    if (state.megaUnlocked)
      options.push(["Méga", mega, battle.megaUsed || !active.stone]);
    for (let [label, fn, disabled] of options) {
      let b = button(label, fn);
      b.disabled = battle.busy || disabled;
      if (label === "Méga" && active.mega) b.classList.add("active-mega");
      box.querySelector(".battle-options").append(b);
    }
    $("viewport").append(box);
  }
  async function say(t) {
    if (!battle) return;
    battle.text = t;
    battleUI();
    await delay(380);
  }
  function mega() {
    if (!battle || battle.busy || battle.megaUsed) return;
    let m = state.party[battle.active],
      p = D.pokemon[m.stone];
    if (!p || !p.mega || p.base !== m.id || !state.stones.includes(p.id))
      return toast("Équipe une Méga-Gemme compatible depuis le menu Équipe.");
    m.mega = p.id;
    battle.megaUsed = true;
    chirp(850, 0.3);
    battle.text =
      p.fr +
      " entre en résonance !" +
      (!p.sprite ? " Illustration Méga provisoire." : "");
    battleUI();
    refresh();
  }
  async function attack(a, d, mi, opponent = false) {
    if (!battle || a.hp <= 0 || d.hp <= 0) return;
    let move = typeof mi === "string" ? D.moves[mi] : D.moves[a.moves[mi]];
    if (typeof mi === "number") a.pp[mi] = Math.max(0, a.pp[mi] - 1);
    if (move.id === "focus") {
      a.focus = true;
      await say(
        name(a) + " se concentre. Sa prochaine attaque sera renforcée.",
      );
      return;
    }
    if (Math.random() * 100 > move.accuracy) {
      await say(name(a) + " utilise " + move.name + "… mais manque sa cible.");
      return;
    }
    let hit = C.damage(a, d, move, D);
    a.focus = false;
    d.hp = Math.max(0, d.hp - hit.damage);
    battle.flash = opponent ? -1 : 1;
    chirp(180 + hit.damage * 3, 0.09);
    refresh();
    await say(
      name(a) +
        " utilise " +
        move.name +
        ". " +
        (hit.effect === 0
          ? "Sans effet."
          : hit.crit
            ? "Coup critique ! "
            : hit.effect > 1
              ? "Super efficace ! "
              : hit.effect < 1
                ? "Peu efficace. "
                : "") +
        " −" +
        hit.damage +
        " PV.",
    );
    if (battle) battle.flash = 0;
  }
  function aiMove(enemy, defender) {
    let candidates = enemy.moves
      .map((id, i) => ({ i, m: D.moves[id] }))
      .filter(({ i, m }) => enemy.pp[i] > 0 && m.power > 0);
    if (!candidates.length) return "struggle";
    candidates.sort(
      (a, b) =>
        b.m.power * C.effectiveness(b.m.type, C.species(defender, D).types) -
        a.m.power * C.effectiveness(a.m.type, C.species(defender, D).types),
    );
    return Math.random() < 0.2
      ? candidates[Math.floor(Math.random() * candidates.length)].i
      : candidates[0].i;
  }
  async function enemyTurn() {
    if (!battle) return;
    let enemy = battle.enemies[battle.index],
      active = state.party[battle.active];
    if (enemy.hp > 0 && active.hp > 0)
      await attack(enemy, active, aiMove(enemy, active), true);
    await settle();
  }
  async function turn(kind, index) {
    if (!battle || battle.busy || state.party[battle.active].hp <= 0) return;
    battle.busy = true;
    battleUI();
    let a = state.party[battle.active],
      e = battle.enemies[battle.index];
    if (kind === "ball") {
      if (battle.kind !== "wild" || state.balls <= 0) {
        battle.busy = false;
        battleUI();
        return;
      }
      state.balls--;
      await say("La Poké Ball se referme…");
      if (
        Math.random() <
        Math.min(
          0.98,
          C.catchChance(e, D) * (net?.profile?.role === "ranger" ? 1.2 : 1),
        )
      ) {
        receive(e);
        await say(
          name(e) +
            " rejoint " +
            (state.party.includes(e) ? "ton équipe" : "le refuge") +
            " !",
        );
        finishBattle(true, true);
        return;
      }
      await say(name(e) + " se libère !");
      await enemyTurn();
    } else if (kind === "potion") {
      if (state.potions > 0) {
        state.potions--;
        a.hp = Math.min(
          maxhp(a),
          a.hp + Math.max(30, Math.floor(maxhp(a) * 0.55)),
        );
        await say(name(a) + " récupère des PV.");
        await enemyTurn();
      }
    } else if (kind === "run") {
      if (battle.kind === "wild") {
        await say("Tu quittes le combat.");
        finishBattle(false);
        return;
      }
    } else {
      let move =
        kind === "struggle" ? D.moves.struggle : D.moves[a.moves[index]];
      if (!move || (kind !== "struggle" && a.pp[index] <= 0)) {
        battle.busy = false;
        battleUI();
        return;
      }
      let ei = aiMove(e, a),
        em = typeof ei === "string" ? D.moves[ei] : D.moves[e.moves[ei]],
        as = C.stats(C.species(a, D), a.level).spe,
        es = C.stats(C.species(e, D), e.level).spe;
      let first =
        move.priority > em.priority ||
        (move.priority === em.priority && as >= es);
      if (first) {
        await attack(a, e, kind === "struggle" ? "struggle" : index);
        if (e.hp > 0) await attack(e, a, ei, true);
      } else {
        await attack(e, a, ei, true);
        if (a.hp > 0)
          await attack(a, e, kind === "struggle" ? "struggle" : index);
      }
      await settle();
    }
    if (battle) {
      battle.busy = false;
      battleUI();
    }
    refresh();
  }
  async function settle() {
    if (!battle) return;
    let e = battle.enemies[battle.index],
      a = state.party[battle.active];
    if (e.hp <= 0) {
      await say(name(e) + " est K.O.");
      awardXP(e.level);
      battle.index++;
      if (battle.index >= battle.enemies.length) {
        finishBattle(true);
        return;
      }
      e = battle.enemies[battle.index];
      await say("Le prochain adversaire est " + name(e) + " !");
    }
    if (a.hp <= 0) {
      await say(name(a) + " est K.O.");
      if (!state.party.some((m) => m.hp > 0)) {
        finishBattle(false, false, true);
        return;
      }
      battle.busy = false;
      partyMenu(true);
    }
    refresh();
  }
  function awardXP(level) {
    let cap = CAMPAIGN[state.region].cap;
    for (let m of state.party) {
      if (m.hp <= 0) continue;
      m.xp += level * 24;
      let raised = false;
      while (m.xp >= m.level * 16 && m.level < cap) {
        m.xp -= m.level * 16;
        let old = maxhp(m);
        m.level++;
        m.hp += maxhp(m) - old;
        raised = true;
      }
      if (raised) {
        m.moves = C.movelist(D.pokemon[m.id], D.moves, m.level);
        m.pp = m.moves.map((id) => D.moves[id].pp);
      }
    }
  }
  function finishBattle(win, captured = false, lost = false) {
    let kind = battle.kind;
    document.querySelector(".battle-ui")?.remove();
    battle = null;
    for (let m of state.party) {
      C.clearMega(m);
      m.hp = Math.min(m.hp, maxhp(m));
    }
    if (win) {
      state.money += kind === "boss" ? 1300 : kind === "guard" ? 500 : 100;
      if (kind === "guard") {
        state.flags["guard" + state.region] = true;
        if (net) coopEvent("guard");
        state.balls += 5;
        toast("Accès au site obtenu · 500 ₽ et 5 Balls.");
      }
      if (kind === "boss") {
        state.progress[state.region] = 3;
        let target = CAMPAIGN[state.region].cap - 1;
        for (let m of state.party) {
          m.level = Math.max(m.level, target);
          m.moves = C.movelist(D.pokemon[m.id], D.moves, m.level);
        }
        heal();
        toast("Défi réussi. Ton équipe progresse. Retourne au relais.");
      }
    }
    if (lost) {
      state.money = Math.max(0, state.money - 100);
      heal();
      changeZone("town", 20, 18);
      dialog(
        "Centre Pokémon",
        "Ton équipe a été secourue. Les objectifs déjà accomplis sont conservés. Capture d’autres partenaires, choisis les types adaptés et équipe des potions avant de repartir.",
      );
    } else if (!captured) close();
    steps = 0;
    save();
    refresh();
  }
  function pixelRect(x, y, w, h, c) {
    ctx.fillStyle = c;
    ctx.fillRect(Math.floor(x), Math.floor(y), w, h);
  }
  function text(t, x, y, size = 10, color = "#24453a", align = "left") {
    ctx.fillStyle = color;
    ctx.font = size + "px monospace";
    ctx.textAlign = align;
    ctx.fillText(t, Math.floor(x), Math.floor(y));
    ctx.textAlign = "left";
  }
  function tree(x, y, r, seed) {
    pixelRect(x + 6, y + 9, 5, 8, "#6b7150");
    pixelRect(x + 3, y + 2, 11, 11, r.dark);
    pixelRect(x + 1, y + 5, 15, 8, r.dark);
    pixelRect(x + 4, y, 8, 9, "#648668");
    pixelRect(x + 5, y + 2, 5, 3, "#85a779");
    pixelRect(x + 2, y + 12, 13, 3, "#39574c");
  }
  function tile(t, x, y, r, seed) {
    pixelRect(x, y, 16, 16, r.floor);
    let n = (seed * 37 + seed * seed) % 17;
    if (t === "lawn" || t === "grass" || t === "flower") {
      if (n % 3 === 0) {
        pixelRect(x + 3, y + 7, 2, 1, "#85a16a");
        pixelRect(x + 11, y + 3, 1, 2, "#c1c892");
      }
      if (t === "grass") {
        pixelRect(x, y, 16, 16, "#729866");
        for (let a = 2; a < 16; a += 5) {
          pixelRect(x + a, y + 5 + (a % 3), 1, 6, "#456f51");
          pixelRect(x + a - 1, y + 7 + (a % 3), 3, 2, "#a0b977");
          pixelRect(x + a, y + 13, 1, 3, "#b2c080");
        }
      }
      if (t === "flower") {
        for (let a = 3; a < 15; a += 7) {
          pixelRect(x + a, y + 8, 1, 6, "#587955");
          pixelRect(x + a - 1, y + 5, 3, 3, "#efc895");
          pixelRect(x + a, y + 6, 1, 1, "#efeee0");
        }
      }
    }
    if (t === "tree") tree(x, y, r, seed);
    if (t === "path") {
      pixelRect(x, y, 16, 16, "#d6c49c");
      pixelRect(x + 2 + (n % 8), y + 3, 2, 1, "#b6aa83");
      pixelRect(x + 10, y + 11, 3, 1, "#e7d7b1");
    }
    if (t === "water") {
      pixelRect(x, y, 16, 16, r.water);
      let v = Math.floor(frame / 35) % 4;
      pixelRect(x + ((n + v) % 10), y + 5, 6, 1, "#a1cbd0");
      pixelRect(x + ((n + v + 3) % 10), y + 12, 4, 1, "#6baabc");
    }
    if (t === "wood") {
      pixelRect(x, y, 16, 16, "#a38a68");
      for (let a = 1; a < 16; a += 4) pixelRect(x, y + a, 16, 1, "#6d7255");
      pixelRect(x + 1, y, 1, 16, "#ceba8a");
    }
    if (t === "rock") {
      pixelRect(x, y, 16, 16, "#6b7a73");
      pixelRect(x + 1, y + 1, 14, 10, "#9da591");
      pixelRect(x + 3, y + 2, 9, 2, "#c4c6ae");
      pixelRect(x + 8, y + 10, 6, 2, "#55685e");
    }
    if (t === "stone") {
      pixelRect(x, y, 16, 16, "#b9bba3");
      pixelRect(x, y + 15, 16, 1, "#99a18b");
      pixelRect(x + 15, y, 1, 16, "#99a18b");
      if (n < 7) pixelRect(x + 3, y + 6, 3, 1, "#ced0b8");
    }
    if (t === "wall") {
      pixelRect(x, y, 16, 16, "#e2d9b8");
      pixelRect(x, y + 14, 16, 2, "#adad8c");
      if (seed % 3 === 0) {
        pixelRect(x + 3, y + 2, 9, 9, "#637d73");
        pixelRect(x + 4, y + 3, 7, 6, "#95bec1");
        pixelRect(x + 7, y + 3, 1, 7, "#e4dcc0");
      }
    }
    if (t === "roof") {
      pixelRect(x, y, 16, 16, r.roof);
      pixelRect(x, y + 14, 16, 2, "#665e5a");
      pixelRect(x, y + 3, 16, 1, "#ffffff26");
      pixelRect(x + 7, y, 1, 14, "#2f48352b");
    }
    if (t === "door") {
      pixelRect(x, y, 16, 16, "#dcd3b0");
      pixelRect(x + 3, y + 1, 10, 15, "#405b50");
      pixelRect(x + 4, y + 2, 8, 10, "#789a83");
      pixelRect(x + 10, y + 9, 1, 2, "#e9cf85");
    }
  }
  function person(x, y, color = "#b45e56", player = false) {
    let foot =
      player && Object.values(keys).some(Boolean)
        ? Math.floor(frame / 8) % 2
        : 0;
    pixelRect(x + 3, y + 13, 11, 3, "#244c3944");
    pixelRect(x + 5, y + 11, 3, 5 + foot, "#3d5263");
    pixelRect(x + 10, y + 11, 3, 5 - foot, "#3d5263");
    pixelRect(x + 4, y + 5, 10, 8, color);
    pixelRect(x + 5, y + 2, 8, 6, "#e5c49a");
    pixelRect(x + 4, y, 10, 3, player ? "#e2d6a8" : "#5b5b4b");
    pixelRect(x + 8, y + 4, 2, 1, "#354b43");
    if (player) {
      pixelRect(x + 4, y - 1, 10, 2, "#be6957");
      pixelRect(x + 3, y + 7, 4, 6, "#d5b981");
      pixelRect(x + 6, y + 1, 9, 1, "#a95045");
    }
  }
  function drawPokemon(p, x, y, scale = 2, back = false, mega = false) {
    let path = back ? p.back || p.sprite : p.sprite,
      actual = img(path),
      fallback = false;
    if (!actual && p.base) {
      let base = D.pokemon[p.base];
      actual = img(back ? base?.back || base?.sprite : base?.sprite);
      fallback = true;
    }
    if (mega) {
      ctx.strokeStyle = "#d2a2dc";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(x, y - 36 * scale, 35 * scale, 39 * scale, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (actual?.complete && actual.naturalWidth) {
      let s = Math.min(
        scale,
        (130 * scale) / Math.max(actual.width, actual.height),
      );
      ctx.drawImage(
        actual,
        Math.round(x - (actual.width * s) / 2),
        Math.round(y - actual.height * s),
        Math.round(actual.width * s),
        Math.round(actual.height * s),
      );
    } else {
      pixelRect(x - 12, y - 35, 24, 24, "#617a73");
      text("?", x, y - 17, 16, "#f6e6bd", "center");
    }
    if (fallback) text("VISUEL PROVISOIRE", x, y + 12, 7, "#8c597f", "center");
  }
  function drawWorld() {
    let r = map.r;
    for (let y = 0; y < 26; y++)
      for (let x = 0; x < 40; x++)
        tile(
          map.tiles[y][x],
          x * 16,
          y * 16,
          r,
          x + y * 40 + state?.region * 19 || x + y * 40,
        );
    for (let o of map.objects) {
      let x = o.x * 16,
        y = o.y * 16;
      if (o.building) {
        if (o.kind === "heal") {
          pixelRect(x - 3, y - 22, 20, 12, "#e8dfc0");
          pixelRect(x + 5, y - 20, 4, 8, "#ba635a");
          pixelRect(x + 3, y - 18, 8, 4, "#ba635a");
        }
        continue;
      }
      if (o.kind === "exit") {
        text(
          o.to === "town" || (o.to === "route" && map.zone === "site")
            ? "◀"
            : "▶",
          x + 8,
          y + 10,
          12,
          "#385c49",
          "center",
        );
        continue;
      }
      if (o.kind === "rune") {
        let on =
          state &&
          map.r.puzzle.slice(0, state.puzzles[state.region]).includes(o.index);
        pixelRect(x + 2, y + 5, 13, 12, "#6d7b73");
        pixelRect(x + 3, y + 1, 11, 11, on ? "#ddc77c" : "#9cbaab");
        pixelRect(x + 6, y + 3, 5, 5, on ? "#fff2b6" : "#527d79");
        text(String(o.index + 1), x + 8, y + 24, 8, "#35594d", "center");
        continue;
      }
      if (o.kind === "terminal") {
        pixelRect(x - 4, y - 6, 24, 22, "#657c72");
        pixelRect(x, y - 2, 16, 11, "#b5d1ba");
        pixelRect(x + 3, y + 1, 10, 5, "#557c79");
        continue;
      }
      if (o.kind === "sign") {
        pixelRect(x + 7, y + 8, 2, 10, "#6d7153");
        pixelRect(x + 1, y, 15, 10, "#d3c296");
        text("?", x + 8, y + 8, 8, "#567054", "center");
        continue;
      }
      if (o.kind === "item") {
        if (state?.flags["crate" + state.region]) continue;
        pixelRect(x + 2, y + 4, 12, 10, "#bc9a65");
        pixelRect(x + 7, y + 4, 2, 10, "#776e53");
        continue;
      }
      person(
        x,
        y,
        o.kind === "guard"
          ? "#62677b"
          : o.kind === "boss"
            ? "#8e728d"
            : o.kind === "heal"
              ? "#e0cab1"
              : "#7192a3",
      );
      if (
        state &&
        ((o.kind === "mentor" &&
          [0, 3].includes(state.progress[state.region])) ||
          (o.kind === "boss" && state.progress[state.region] === 2))
      )
        text("!", x + 8, y - 6, 12, "#fff1a1", "center");
    }
    let px = (state?.x || 20) * 16,
      py = (state?.y || 18) * 16;
    person(px, py, net?.profile?.color || "#b45e56", true);
    drawPartner();
    if (state) {
      let o = World.nearby(map, state.x, state.y);
      $("prompt").textContent =
        o && !battle && overlay.classList.contains("hidden")
          ? "E · " + o.name
          : "";
    }
    pixelRect(0, 0, 640, 5, "#193d3033");
    if (transition > 0) {
      ctx.fillStyle = "rgba(244,237,214," + transition * 2 + ")";
      ctx.fillRect(0, 0, 640, 416);
      transition -= 0.02;
    }
  }
  function hpPanel(mon, x, y, w) {
    let p = C.species(mon, D),
      max = maxhp(mon),
      percent = Math.max(0, mon.hp / max);
    pixelRect(x + 3, y + 3, w, 47, "#3b625b44");
    pixelRect(x, y, w, 47, "#f4efdb");
    pixelRect(x, y, w, 2, "#6c8974");
    text(p.fr, x + 9, y + 15, 10);
    text("N." + mon.level, x + w - 9, y + 15, 9, "#5c7363", "right");
    pixelRect(x + 29, y + 25, w - 41, 5, "#b8c3ad");
    pixelRect(
      x + 29,
      y + 25,
      Math.floor((w - 41) * percent),
      5,
      percent < 0.25 ? "#c97665" : "#80a873",
    );
    text("PV", x + 8, y + 30, 8);
    text(mon.hp + "/" + max, x + w - 9, y + 41, 8, "#5c7363", "right");
  }
  function drawBattle() {
    let r = CAMPAIGN[state.region];
    pixelRect(0, 0, 640, 416, "#dce3cc");
    pixelRect(0, 0, 640, 100, "#b7d5cf");
    for (let i = 0; i < 8; i++) {
      pixelRect(i * 96 - 20, 80 - (i % 3) * 12, 110, 50, r.floor);
      pixelRect(i * 96, 74 - (i % 3) * 12, 60, 12, r.floor);
    }
    pixelRect(0, 125, 640, 291, "#cbd5ac");
    ctx.fillStyle = "#a9bd91";
    ctx.beginPath();
    ctx.ellipse(459, 160, 115, 23, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#b1bd95";
    ctx.beginPath();
    ctx.ellipse(170, 285, 130, 30, 0, 0, Math.PI * 2);
    ctx.fill();
    let e = battle.enemies[battle.index],
      a = state.party[battle.active];
    if (!e) return;
    drawPokemon(
      C.species(e, D),
      459,
      158 + (battle.flash === 1 ? 3 : 0),
      1.6,
      false,
      !!e.mega,
    );
    drawPokemon(
      C.species(a, D),
      168,
      285 + (battle.flash === -1 ? 3 : 0),
      2,
      true,
      !!a.mega,
    );
    hpPanel(e, 38, 33, 236);
    hpPanel(a, 358, 213, 247);
    text(
      battle.kind === "wild"
        ? "RENCONTRE SAUVAGE"
        : battle.kind === "guard"
          ? "CONSORTIUM ATLAS"
          : "DÉFI RÉGIONAL",
      610,
      20,
      8,
      "#4e7165",
      "right",
    );
    $("prompt").textContent = "";
  }
  function walk(dx, dy) {
    let nx = state.x + dx,
      ny = state.y + dy;
    if (!World.canWalk(map, nx, ny)) return;
    state.x = nx;
    state.y = ny;
    steps++;
    if (map.tiles[ny][nx] === "grass" && steps > 7 && Math.random() < 0.14) {
      let r = CAMPAIGN[state.region],
        id = r.pool[Math.floor(Math.random() * r.pool.length)];
      startBattle(
        [
          C.create(
            id,
            Math.max(3, r.level + Math.floor(Math.random() * 4) - 1),
            D,
          ),
        ],
        "wild",
      );
      return;
    }
    if (steps % 12 === 0) save();
  }
  let lastTime = performance.now();
  function loop(now) {
    let dt = Math.min(0.1, (now - lastTime) / 1000);
    lastTime = now;
    frame++;
    if (
      state &&
      !battle &&
      net?.snapshot?.battle?.status !== "active" &&
      overlay.classList.contains("hidden")
    ) {
      state.playtime += dt;
      if (now - lastStep > (keys.shift ? 85 : 145)) {
        let dx =
            keys.arrowleft || keys.q || keys.a
              ? -1
              : keys.arrowright || keys.d
                ? 1
                : 0,
          dy =
            keys.arrowup || keys.z || keys.w
              ? -1
              : keys.arrowdown || keys.s
                ? 1
                : 0;
        if (dx || dy) {
          walk(dx, dx ? 0 : dy);
          lastStep = now;
        }
      }
    }
    if (net?.snapshot?.battle?.status === "active") drawCoopBattle();
    else if (battle) drawBattle();
    else drawWorld();
    requestAnimationFrame(loop);
  }
  document.addEventListener("keydown", (e) => {
    if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;
    let k = e.key.toLowerCase();
    if (["arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(k))
      e.preventDefault();
    if (e.repeat && ["e", "enter", "escape"].includes(k)) return;
    if (trading()) {
      if (k === "escape") tradeUI();
      return;
    }
    if (k === "escape") {
      if (battle) {
        if (!overlay.classList.contains("hidden")) {
          close();
          battleUI();
        }
      } else if (overlay.classList.contains("hidden")) menu();
      else if (state) close();
      return;
    }
    if (
      !state ||
      battle ||
      net?.snapshot?.battle?.status === "active" ||
      !overlay.classList.contains("hidden")
    )
      return;
    if (k === "e" || k === "enter") {
      interact(World.nearby(map, state.x, state.y));
      return;
    }
    keys[k] = true;
  });
  document.addEventListener("keyup", (e) => {
    keys[e.key.toLowerCase()] = false;
  });
  window.addEventListener("blur", () => {
    keys = {};
  });
  window.addEventListener("beforeunload", () => save());
  $("partyBtn").onclick = () => partyMenu();
  $("journalBtn").onclick = journal;
  $("dexBtn").onclick = dex;
  $("saveBtn").onclick = () => save(true);
  $("menuBtn").onclick = menu;
  $("soundBtn").onclick = () => {
    sound = !sound;
    $("soundBtn").textContent = "Son : " + (sound ? "ON" : "OFF");
    chirp();
  };
  $("fullBtn").onclick = () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.();
  };

  // BEGIN COOP ADAPTER
  // Inserted into game.js by tools/assemble_coop.py; this file owns the co-op adapter.
  let net = null,
    netTimer = null;
  async function api(route, body) {
    // Capture the inventory epoch with the outgoing state, never after awaiting I/O.
    if (route === "sync")
      body = {
        ...body,
        gameEpoch: net?.gameEpoch || 0,
        activity: battle ? "battle" : "world",
      };
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
    if (!net || s.revision < (net.revision || 0)) return;
    if (
      state &&
      s.game &&
      (s.gameEpoch !== (net.gameEpoch || 0) ||
        (s.trade?.status === "pending" &&
          net.snapshot?.trade?.id !== s.trade.id))
    ) {
      state = cloneJSON(s.game);
      map = World.make(state.region, state.zone);
    }
    net.gameEpoch = s.gameEpoch || 0;
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
    if (s.trade?.status === "pending") {
      if (battle) {
        if (!net.cancellingTrade) {
          net.cancellingTrade = true;
          api("trade", { action: "cancel", id: s.trade.id })
            .then(applyNet)
            .catch((e) => toast(e.message))
            .finally(() => {
              if (net) net.cancellingTrade = false;
            });
        }
      } else tradeUI();
    } else if (net.tradeKey) {
      net.tradeKey = null;
      close();
      toast(
        s.trade?.status === "completed"
          ? "Échange terminé et sauvegardé pour vous deux."
          : s.trade?.status === "expired"
            ? "Échange expiré. Rien n’a été transféré."
            : "Échange annulé. Rien n’a été transféré.",
      );
    }
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
    megaBtn.disabled =
      pending || me.megaUsed || !state.megaUnlocked || !m.stone;
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

  function trading() {
    return net?.snapshot?.trade?.status === "pending";
  }
  async function openTrade() {
    if (!net || !state || battle) return;
    try {
      applyNet(await api("sync", { game: state, revision: net.revision }));
      applyNet(await api("trade", { action: "open" }));
    } catch (e) {
      toast(e.message);
    }
  }
  async function sendTrade(action, extra = {}) {
    const t = net?.snapshot?.trade;
    if (!t) return;
    try {
      applyNet(
        await api("trade", { action, id: t.id, version: t.version, ...extra }),
      );
    } catch (e) {
      toast(e.message);
      try {
        applyNet(await api("state"));
      } catch {}
    }
  }
  function tradeUI() {
    const t = net?.snapshot?.trade;
    if (!t || t.status !== "pending") return;
    const key = t.id + ":" + t.version;
    if (net.tradeKey === key && $("tradePanel")) return;
    net.tradeKey = key;
    const mine = t.offers[net.id],
      other = net.snapshot.players.find((p) => p.id !== net.id);
    const summarize = (id) => {
      const o = t.offers[id],
        m = t.preview?.[id];
      return (
        (m
          ? name(m) +
            " · niv. " +
            m.level +
            " · PV " +
            m.hp +
            "/" +
            maxhp(m) +
            " · " +
            m.moves.map((id) => D.moves[id].name).join(", ")
          : "Aucun Pokémon") +
        " · " +
        o.balls +
        " Balls · " +
        o.potions +
        " potions"
      );
    };
    modal(
      '<div id="tradePanel"><div class="eyebrow">ÉCHANGE AU RELAIS</div><h2>Un accord à deux.</h2>' +
        "<p>Vos équipes et sacs sont réservés pendant cet échange. Chaque modification annule les deux confirmations. Sans accord sous dix minutes, rien ne sera transféré.</p>" +
        "<h3>Tu donnes</h3><p>" +
        escape(summarize(net.id)) +
        "</p>" +
        "<h3>" +
        escape(other.profile.name) +
        " donne</h3><p>" +
        escape(summarize(other.id)) +
        "</p>" +
        '<label>Pokémon de ton équipe<select id="tradePokemon"><option value="">Aucun Pokémon</option>' +
        state.party
          .map(
            (m, i) =>
              '<option value="' +
              i +
              '"' +
              (mine.slot === i ? " selected" : "") +
              ">" +
              escape(name(m) + " · niv. " + m.level) +
              "</option>",
          )
          .join("") +
        "</select></label>" +
        '<label>Balls à donner<input id="tradeBalls" type="number" min="0" max="' +
        Math.min(99, state.balls) +
        '" value="' +
        mine.balls +
        '"></label>' +
        '<label>Potions à donner<input id="tradePotions" type="number" min="0" max="' +
        Math.min(99, state.potions) +
        '" value="' +
        mine.potions +
        '"></label>' +
        '<p id="tradeStatus" role="status">' +
        (t.confirmed[net.id]
          ? "Tu as confirmé. "
          : "Ta confirmation est attendue. ") +
        (t.confirmed[other.id]
          ? "Ton partenaire a confirmé."
          : "Ton partenaire n’a pas encore confirmé.") +
        "</p></div>",
    );
    const apply = button("Mettre à jour mon offre", () =>
      sendTrade("offer", {
        offer: {
          slot:
            $("tradePokemon").value === ""
              ? null
              : Number($("tradePokemon").value),
          balls: Number($("tradeBalls").value),
          potions: Number($("tradePotions").value),
        },
      }),
    );
    const confirm = button("Confirmer cet échange", () => sendTrade("confirm"));
    confirm.disabled = !!t.confirmed[net.id];
    for (const id of ["tradePokemon", "tradeBalls", "tradePotions"])
      $(id).oninput = () => {
        confirm.disabled = true;
        $("tradeStatus").textContent =
          "Modifications non envoyées : mets ton offre à jour avant de confirmer.";
      };
    const row = document.createElement("div");
    row.className = "row";
    row.append(
      apply,
      confirm,
      button("Annuler l’échange", () => sendTrade("cancel"), true),
    );
    overlay.querySelector(".modal").append(row);
  }

  // END COOP ADAPTER
  // Inspection hook: useful for the included integration tests.
  window.Meridian = {
    get net() {
      return net;
    },
    coopEvent,
    api,
    get state() {
      return state;
    },
    get battle() {
      return battle;
    },
    get map() {
      return map;
    },
    loadState,
    interact,
    startBattle,
    turn,
    mega,
    save,
    habitatRegion,
    refresh,
  };
  refresh();
  title();
  requestAnimationFrame(loop);
})();
