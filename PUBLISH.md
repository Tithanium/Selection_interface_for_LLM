# PUBLISH.md — rendre cet addon trouvable, puis le faire connaître

Ce fichier est un **kit de divulgation** : le diagnostic de ce qui bloque aujourd'hui,
le nom à utiliser, les mots-clés qui doivent apparaître où, et les textes prêts à
copier-coller (anglais + français). Il ne contient pas de code.

Version concernée : 2.1.1 (voir `CHANGELOG.md`).

---

## 1. Diagnostic : pourquoi « la recherche ne donne rien »

Quatre causes, mesurées sur cette machine le 2026-11-08 :

| # | Cause | Preuve | Correction |
|---|-------|--------|------------|
| 1 | **L'addon n'est pas dans l'index officiel** → il n'existe pas dans le gestionnaire d'addons de FreeCAD, donc aucune recherche interne ne peut le trouver. | `FreeCAD/Addons` → `Data/Index.json` contient 181 addons ; `Selection_interface_for_LLM` n'y est pas. | Soumettre une issue « Addon - Addition » (§4.7), possible à partir du **2026-12-08** (dépôt âgé de 30 jours). |
| 2 | **L'index ne contient aucun nom ni description** : pour chaque addon il ne stocke que `repository`, `git_ref`, `branch_display_name`, `freecadmin`, `zip_url`, `curated`. | `gh api repos/FreeCAD/Addons/contents/Data/Index.json` → structure ci-dessus. | Ce sont donc **les chaînes de `package.xml`** (nom, description, tags) qui *sont* l'index de recherche. Elles sont réécrites en 2.1.1 (§3). |
| 3 | **Le nom décrit l'interface, pas la fonction** — « selection interface » évoque la sélection de faces/objets, et « LLM » est un mot très bruité (modèles de langage, diplômes de droit). | Chercher « LLM » ne renvoie rien de pertinent ; l'addon voisin du même domaine s'appelle `freecad-mcp-bridge`. | Recommandation de nom en §2 (décision à prendre, rien n'est renommé d'office). |
| 4 | **Aucun mot de la description ne correspond à ce que les gens tapent** : « timelapse », « build order », « animation », « history », « step by step ». | La description commençait par « Steps through the real computation order… ». | Nouvelle description + 15 topics GitHub (§3). |

Le paysage, vérifié dans l'index (ne pas se tromper d'argumentaire) :

| Addon existant | Ce qu'il fait | Pourquoi ce n'est pas le même |
|---|---|---|
| **History** (`eblanshey/HistoryWorkbench`) | Contrôle de version du document (diffs 3D et d'arbre, type git/PDM). | Il compare des *versions* ; ici on rejoue la *construction* d'une version. |
| **Movie Workbench** (`Francisco-Rosa/FreeCAD-Movie`) | Anime la caméra, crée et lit des vidéos. | Il filme une scène figée ; ici la géométrie elle-même se construit, et l'angle de vue est conservé. |
| **Animation FreeCAD** (`QuentinTournier40`) | Animation par nœuds PyFlow (2022, beta, dépendances lourdes). | Rien à voir : pas d'ordre de calcul, pas de GIF, pas de description de fonction. |
| **freecad-mcp-bridge** | Pont MCP entre FreeCAD et un agent. | Il transporte ; ici on prépare la *description* d'une fonction, sans réseau ni serveur. |

Phrase de positionnement à réutiliser partout :

> **EN** — *The addon that replays how a PartDesign part was actually built: the real
> computation order, one feature at a time, exported as a GIF that keeps your viewing
> angle, plus a ready-to-paste description of any single feature for an LLM.*
>
> **FR** — *L'addon qui rejoue la construction réelle d'une pièce PartDesign : l'ordre de
> calcul, une fonction à la fois, exporté en GIF en conservant l'angle de vue, avec une
> description prête à coller d'une fonction pour un LLM.*

---

## 2. Le nom

**Recommandation : `Build Steps`** (dépôt `freecad-build-steps`).

Pourquoi ce nom plutôt qu'un autre :

- il se tape en deux mots que les gens emploient réellement (« build », « steps ») et il
  tient dans le champ de recherche du gestionnaire d'addons ;
- il reste vrai : le panneau *est* une liste d'étapes de construction ;
- le mot **timeline** est placé dans la description (pas dans le nom) pour capter
  « FreeCAD timeline », sans allonger le nom ;
- **aucune collision** dans l'index : `History`, `Movie`, `AnimationFreeCAD`, `stepParts`,
  `Part-o-magic`, `freecad-mcp-bridge` vérifiés ; « steps » seul est déjà pris par
  `stepParts`, « build » + « steps » ne l'est pas.

Alternatives, avec verdict :

| Nom | Dépôt | Verdict |
|---|---|---|
| **Build Steps** | `freecad-build-steps` | **Recommandé.** Court, descriptif, libre. |
| Feature Timeline | `freecad-feature-timeline` | Très clair pour un utilisateur FreeCAD, mais « timeline » promet un widget d'édition qu'on n'a pas. |
| Build Timeline | `freecad-build-timeline` | Bon compromis, un peu long à taper. |
| Construction Order | `freecad-build-order` | Précis, mais personne ne cherche ces mots-là. |
| PartDesign Player | `freecad-partdesign-player` | Sympa, ne dit rien de l'export GIF ni du LLM. |

Garder le nom actuel est **défendable** : avec la nouvelle description et les 15 topics
(§3), GitHub devient cherchable (`timelapse freecad`, `build order freecad`). Ce que le
nom ne fera jamais, c'est se trouver par « LLM ».

Ce que le renommage coûterait (procédure complète en §7, rien n'est fait d'office) :
l'URL du dépôt (GitHub pose une redirection automatique), `<name>` du manifeste (donc le
nom du dossier dans `Mod`), le paquet Python interne, la barre d'outils et les docs.

Aujourd'hui, les chaînes à donner à quelqu'un qui cherche :

- GitHub : `Tithanium/Selection_interface_for_LLM` — ou la recherche GitHub
  `timelapse partdesign freecad` / `build order freecad` (grâce aux topics) ;
- gestionnaire d'addons : **rien tant que l'addon n'est pas indexé** ; d'où la procédure
  d'installation manuelle du `README` ;
- si le renommage est fait : gestionnaire d'addons → chercher `build steps`.

---

## 3. Carte des mots-clés — ce qui doit apparaître où

La règle : un mot qui n'est **pas** dans le nom, la description ou les tags n'existe pas
pour la recherche. Répartition à respecter lors de toute réécriture :

| Mot / expression | Où il doit être (forme exacte) |
|---|---|
| build order, construction order | description du manifeste, 1re phrase du README, topic `build-order` |
| timelapse, time-lapse | description du manifeste, tag `Timelapse`, topics `timelapse` |
| build timeline | description du manifeste (2e phrase), `Overview.md` |
| feature, sketch, datum plane | description du manifeste, README (section « What it shows ») |
| animation | tag `Animation` (index), README (phrase « animate the construction ») |
| GIF | description, README (titre de section), tag `GIF` |
| LLM, AI | tag `LLM`, dernier paragraphe de la description, section dédiée du README |
| PartDesign, workbench, addon | nom des tags, topics, première ligne du README |
| step by step, one feature at a time, replay | README + posts forum (langage des gens) |

**Description du manifeste livrée en 2.1.1** (c'est elle que lit le gestionnaire
d'addons, donc la plus importante des chaînes) :

> Build timeline of a PartDesign document: lists the real construction order of every
> feature, shows them one at a time (datum planes and the driving sketch included)
> without modifying your model, replays the build-up as an animated GIF that keeps your
> viewing angle, and copies a ready-to-paste description of one feature for an LLM.

**Tags du manifeste** : `PartDesign`, `Animation`, `Timelapse`, `Sketch`, `GIF`, `LLM`,
`Documentation`.

**Topics GitHub** (15) :

```
freecad freecad-addon addon workbench partdesign timelapse build-order
feature-history animation gif sketch datum-planes llm cad python
```

Commande (idempotente, à relancer si besoin) :

```powershell
gh repo edit Tithanium/Selection_interface_for_LLM `
  --description "FreeCAD addon - build timeline: replays the real construction order of a PartDesign part, one feature at a time, exports the build-up as a GIF (view angle preserved) and prepares a feature description for an LLM" `
  --add-topic freecad,freecad-addon,addon,workbench,partdesign,timelapse,build-order,feature-history,animation,gif,sketch,datum-planes,llm,cad,python
```

---

## 4. Textes prêts à coller

### 4.1 GitHub — champ « About »

> FreeCAD addon — build timeline: replays the real construction order of a PartDesign
> part, one feature at a time, exports the build-up as a GIF (view angle preserved) and
> prepares a feature description for an LLM.

### 4.2 Première phrase du README (déjà livrée) + le GIF d'accroche

Le README commence désormais par un GIF animé de 7 images (`resources/docs/preview_build.gif`,
109 kB, licence CC-BY-SA-4.0) suivi de trois phrases : ce qu'on voit, ce que l'addon ne
fait jamais, comment l'installer. Un visiteur qui n'ouvre qu'un écran a tout vu.

### 4.3 Post forum FreeCAD (anglais) — board *Announcements* / *Addons*

**Titre** : `Build Steps - see how your PartDesign part was actually built (and record it as a GIF)`

```text
Hi all,

I published a small addon for a question I kept running into: "in what order was this
part actually built, and what does it look like at each stage?".

What it does
- lists every building step in the real computation order (a dependency walk, not the
  alphabetical order, not the tree order), datum planes included;
- shows the model as it was at that step: each body draws the last feature built so far,
  datum planes already reached, and the sketch driving the selected feature is drawn as a
  thick orange line that shows through the material;
- five display styles (solid + edges / solid / edges only / transparent / points) and three
  "show also" filters (datum objects, profile sketch, other bodies) because a 60-step
  multi-body assembly in one frame is unreadable;
- "create GIF" replays every step with *your* viewing angle - the angle is preserved, only
  the fit changes - writes one annotated PNG per step and the assembled GIF into
  Downloads/FreeCAD_timelapse/<model>_<date>/ ;
- clicking a step also expands the model tree down to that object and selects it
  (the sketch when the profile is shown), so the part can be edited on the spot - the
  LLM handoff is there for the changes you do not want to make by hand;
- copies a self-contained description of one feature (parameters, driving sketch or
  pattern, the whole document's build order, volumes) to the clipboard *and* to a .md
  file, ready to paste into an LLM when you want a scripted modification.

What it never does
- never saves your document, never adds geometry to it;
- restores every visibility / display style / body tip / camera change when you close the
  panel;
- no network access, no server, it never talks to a model - it only writes text.

Known limits, stated in the report rather than hidden: a mirrored / fused / boolean result
is one atomic feature, so it appears once its origin body is complete; a step whose
geometry is interior from the chosen angle looks identical to the previous frame (each
frame carries a delta and a volume so you can see that).

Install: copy or clone https://github.com/Tithanium/Selection_interface_for_LLM into
<user>/Mod/ and restart (FreeCAD 1.1+, Pillow and NumPy already ship with FreeCAD). It is
not in the addon manager yet - I will submit it to the index once the repository is old
enough to qualify.

Feedback very welcome, especially from people with large multi-body documents - the step
ordering and the "one feature at a time" display are where the interesting cases are.
```

### 4.4 Post forum (français) — section francophone

**Titre** : `Build Steps - voir comment une pièce PartDesign a réellement été construite (et l'enregistrer en GIF)`

```text
Bonjour,

J'ai publié un petit addon pour une question qui revenait souvent : « dans quel ordre
cette pièce a-t-elle été construite, et à quoi ressemble-t-elle à chaque étape ? ».

Ce qu'il fait
- liste chaque étape dans l'ordre de calcul réel (parcours des dépendances, pas l'ordre
  alphabétique ni celui de l'arbre), plans de référence compris ;
- affiche le modèle tel qu'il était à cette étape : chaque corps dessine sa dernière
  fonction construite, les plans de référence déjà atteints, et l'esquisse qui pilote la
  fonction sélectionnée apparaît en trait orange épais, visible à travers la matière ;
- cinq styles d'affichage (arêtes+plein / plein / arêtes seules / transparent / points) et
  trois filtres « afficher aussi » (objets de référence, esquisse pilote, autres corps) ;
- « create GIF » rejoue toutes les étapes avec *votre* angle de vue (l'angle est conservé,
  seul le cadrage change), écrit une image PNG annotée par étape puis le GIF dans
  Téléchargements\FreeCAD_timelapse\<modele>_<date>\ ;
- cliquer une étape déplie aussi l'arbre du modèle jusqu'à cet objet et le sélectionne
  (l'esquisse quand le profil est affiché), donc la pièce se modifie sur place — le
  passage par un LLM sert aux changements qu'on ne veut pas faire à la main ;
- copie une description autonome d'une fonction (paramètres, esquisse ou motif d'origine,
  ordre de construction du document, volumes) dans le presse-papier *et* dans un fichier
  .md, prête à coller dans un LLM pour demander une modification scriptée.

Ce qu'il ne fait jamais
- n'enregistre pas le document, n'y ajoute aucune géométrie ;
- restaure visibilité, style d'affichage, tip de corps et caméra à la fermeture du panneau ;
- aucun accès réseau, aucun serveur, il ne parle jamais à un modèle : il écrit du texte.

Limites assumées, écrites dans le rapport au lieu d'être masquées : un miroir / une fusion /
un booléen est une fonction atomique, il n'apparaît qu'une fois le corps d'origine complet ;
une étape dont la géométrie est intérieure à l'angle choisi ressemble à l'image précédente
(chaque image porte un écart et un volume, donc ça se voit).

Installation : copier ou cloner https://github.com/Tithanium/Selection_interface_for_LLM
dans <user>/Mod/ puis redémarrer (FreeCAD 1.1+, Pillow et NumPy sont déjà fournis par
FreeCAD). Pas encore dans le gestionnaire d'addons : je le soumettrai à l'index quand le
dépôt aura l'ancienneté requise.

Retours bienvenus, en particulier sur de gros documents multi-corps.
```

### 4.5 Reddit r/FreeCAD (anglais, court)

**Titre** : `I made an addon that replays the real build order of a PartDesign part (and exports it as a GIF)`

```text
Short version: it walks the dependency graph of your document, shows one feature at a
time (datum planes included, driving sketch highlighted in orange, visible through the
material), and exports the whole build as an animated GIF using your current viewing angle.

It also copies a "here is the feature, here is the document's build order, here are the
parameters" block to the clipboard, which turned out to be the most useful thing when
asking an LLM to script a modification on a part whose dimensions are driven by a VarSet
two levels up.

Never saves the document, restores every view change, no network. FreeCAD 1.1+.

https://github.com/Tithanium/Selection_interface_for_LLM
```

### 4.6 Discord FreeCAD (une ligne)

```text
New addon, "build timeline" for PartDesign documents: steps through the real construction
order one feature at a time (datum planes + driving sketch shown), exports the build as a
GIF keeping your view angle, and writes an LLM-ready description of any single feature.
https://github.com/Tithanium/Selection_interface_for_LLM - feedback welcome.
```

### 4.7 Issue « Addon - Addition » sur `FreeCAD/Addons` (à ouvrir après le 2026-12-08)

Le formulaire officiel ne demande que deux champs (vérifié : `.github/ISSUE_TEMPLATE/Addon-Addition.yml`).
Ce qui est jugé, c'est le dépôt. À coller :

**Repository** : `https://github.com/Tithanium/Selection_interface_for_LLM`

**Notes** :

```text
Namespaced addon (freecad/SelectionInterfaceForLLM, no sys.path manipulation), workbench +
two commands, package.xml format 1, LGPL-2.1-or-later for code and CC-BY-SA-4.0 for the
icon and docs, both license texts at the repository root, SPDX headers in every source file.
freecadmin 1.1.0 (measured on 1.1.4 only), pythonmin 3.10. Pillow and NumPy are imported by
the GIF export and are already shipped by FreeCAD and allow-listed, so no <depend> entry.
Release branch: main (tagged v2.1.1). Development happens on dev.
The addon never saves the user's document and never adds geometry to it; it snapshots and
restores every visibility, display style, body tip and camera change it makes.
Headless test: tests/report_order.py (freecadcmd) prints the recovered order and a verdict.
Second test: tests/check_timelapse.py validates an output folder and the assembled GIF.
```

---

## 5. Visuels à joindre (chemins réels, tous déjà produits)

| Fichier | Ce qu'on voit | Où l'utiliser |
|---|---|---|
| `Downloads\FreeCAD_timelapse\guide_percage26_20261108-164756\timelapse_guide_percage26.gif` (109 kB, 7 images) | Plaque → plaque + demi-bossage + 1 nervure → pièce complète à 4 nervures. | **Copié dans le dépôt** en `resources/docs/preview_build.gif` et affiché en haut du README. C'est l'asset le plus efficace: un GIF en tête de README est ce qui fait cliquer. |
| `Downloads\pi-screenshots\mcp__windows_screenshot__Screenshot-20261108-214426.png` (829 kB) | Le panneau complet : listes, filtre « show also » 2×2, style d'affichage, pièce semi-transparente avec cavités visibles. | 2e image du README, et pièce jointe du post forum. |
| `Downloads\pi-screenshots\mcp__windows_screenshot__Screenshot-20261108-220322.png` (567 kB) | Trait orange épais de l'esquisse pilote par-dessus le piston semi-transparent. | 3e image, et illustration de la section « profile sketch ». |
| `Downloads\FreeCAD_timelapse\02_piston_cardanV3_20261108-222747\` (66 images + GIF) | Cas multi-corps de 66 étapes. | À mentionner, pas à joindre (lourd). |

Règles : héberger les images **dans le dépôt** (GitHub les affiche, le forum les accepte en
lien direct), jamais sur un hébergeur tiers qui peut disparaître. Toute image ajoutée est
sous CC-BY-SA-4.0 (`LICENSE-Assets`).

---

## 6. Ordre des opérations

1. **Fait en 2.1.1** : description du manifeste + tags + topics GitHub + GIF d'accroche +
   premier écran du README réécrits pour la recherche.
2. **Maintenant** : poster sur le forum (4.3 et 4.4), puis Reddit (4.5), puis Discord (4.6).
   Le forum d'abord : c'est là que les mainteneurs et les relecteurs de l'index lisent.
3. **Après le 2026-12-08** (30 jours d'ancienneté) : ouvrir l'issue 4.7.
4. **Quand un utilisateur dira « ça marche chez moi »** : le citer dans le README
   (« tested by … ») et dans les Notes de l'issue — l'index demande une preuve d'usage réel.
5. **Mesure** : GitHub → Insights → Traffic (vues uniques, clones) ; côté forum, le nombre
   de vues du sujet ; et le test qui compte vraiment : chercher `build steps` puis
   `timelapse` dans le gestionnaire d'addons une fois indexé.

---

## 7. Si vous décidez de renommer (procédure complète, non exécutée)

Le renommage est mécanique et déjà rodé une fois (v2.0.0 : `Timelapse_Features` →
`Selection_interface_for_LLM`, historique et tags préservés). Ordre à respecter :

1. sauvegardes : `git tag v2.1.1-backup` + `Compress-Archive` du dossier dans `Downloads\` ;
2. dépôt : `gh repo rename freecad-build-steps` (GitHub pose une redirection depuis
   l'ancienne URL, les tags et l'historique restent) ;
3. `<name>Build Steps</name>` dans `package.xml`, toutes les `<url>` réécrites, `<workbench><name>` idem ;
4. paquet Python : `freecad/SelectionInterfaceForLLM` → `freecad/BuildSteps`, classe
   `SelectionInterfaceWorkbench` → `BuildStepsWorkbench`, commandes `SelectionInterface_*` →
   `BuildSteps_*`, objectName Qt, `LIB_NAME` du shim, imports de `tests/` ;
5. docs : README, `Overview.md`, `CHANGELOG.md`, `task.md`, `ADDON_ROADMAP.md`, ce fichier ;
6. version 2.2.0 (le nom est visible par l'utilisateur), puis vérifications : `FreeCAD.Metadata`
   sur le manifeste, `py_compile`, `tests/report_order.py` (PASS attendu), un GIF de
   régression, et le panneau ouvert par la commande du workbench dans la GUI vivante ;
7. côté machine : renommer la jonction `Mod\Selection_interface_for_LLM` → `Mod\build-steps`
   et le `.FCMacro` du dossier Macro, redémarrer FreeCAD.

Tant que ce n'est pas demandé, **rien n'est renommé** : le dépôt, le manifeste et le dossier
installé gardent leur nom actuel.

---

## 8. Ce que le relecteur de l'index vérifiera (état actuel)

| Critère (Addon-Academy, *Qualities*) | État |
|---|---|
| mainteneur actif, dépôt ≥ 30 jours | mainteneur OK ; ancienneté atteinte le **2026-12-08** |
| licence adaptée, texte inclus, même identifiant SPDX partout | OK (LGPL-2.1-or-later + CC-BY-SA-4.0, en-têtes SPDX) |
| `package.xml` valide, `<content>` correct, `<classname>` résolvable | OK (format 1, workbench + other) |
| `freecad/<ModName>/`, pas de `sys.path` | OK (le shim `dev/` est hors addon) |
| pas de travail coûteux ni réseau à l'import | OK (l'import ne fait que déclarer la version) |
| compatibilité déclarée | `<freecadmin>1.1.0</freecadmin>` (mesuré sur 1.1.4) |
| dépendances seulement si nécessaires, dans `Allowed-Packages` | Pillow + NumPy, déjà fournis par FreeCAD |
| substantiellement complet | OK (v2.1.1, 2 documents de test multi-corps, tests fournis) |
| Bandit | rien de signalé à ce stade (plus de `subprocess`/`os.startfile`) |
| preuve d'usage réel | **manquant** : c'est l'objet des étapes 2 et 4 |
