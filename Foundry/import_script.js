(async () => {
    let jsonData = null;
    // Default fallback relative path for portrait images
    let derivedPortraitBase = "images/DresdenFiles/Scenarios/portrait";

    // --- STEP 1: Prompt user to select local JSON file ---
    await new Promise((resolve, reject) => {
        new Dialog({
            title: "Select Local JSON File",
            content: `
        <p>Select the JSON file you want to load from your local disk:</p>
        <input type="file" id="jsonFile" accept=".json" style="width:100%;" webkitdirectory />
      `,
            buttons: {
                load: {
                    label: "Load",
                    callback: (html) => {
                        const fileInput = html.find("#jsonFile")[0];
                        if (!fileInput.files.length) {
                            ui.notifications.error("No file selected!");
                            reject(new Error("No file selected"));
                            return;
                        }
                        const file = fileInput.files[0];

                        // Attempt to derive portrait base from the file path
                        const fullPath = file.path || file.webkitRelativePath || "";
                        if (fullPath) {
                            let normalized = fullPath.replace(/\\/g, "/");
                            let lower = normalized.toLowerCase();
                            let idx = lower.indexOf("/data/");
                            if (idx !== -1) {
                                // e.g. "data/images/..."
                                let relativePath = normalized.substring(idx + 1);
                                let lastSlash = relativePath.lastIndexOf("/");
                                if (lastSlash !== -1) {
                                    derivedPortraitBase = relativePath.substring(0, lastSlash) + "/portraits";
                                }
                            } else {
                                // If "/data/" not found, fallback to the directory
                                let lastSlash = normalized.lastIndexOf("/");
                                if (lastSlash !== -1) {
                                    derivedPortraitBase = normalized.substring(0, lastSlash) + "/portraits";
                                }
                            }
                            // Strip leading "data/" if present
                            if (derivedPortraitBase.toLowerCase().startsWith("data/")) {
                                derivedPortraitBase = derivedPortraitBase.substring(5);
                                if (derivedPortraitBase.startsWith("/")) {
                                    derivedPortraitBase = derivedPortraitBase.substring(1);
                                }
                            }
                        }

                        console.log("Derived portrait base:", derivedPortraitBase);

                        const reader = new FileReader();
                        reader.onload = (evt) => {
                            try {
                                jsonData = JSON.parse(evt.target.result);
                                resolve();
                            } catch (err) {
                                ui.notifications.error("Failed to parse JSON file!");
                                reject(err);
                            }
                        };
                        reader.readAsText(file);
                    }
                },
                cancel: {
                    label: "Cancel",
                    callback: () => reject("User cancelled file selection")
                }
            },
            default: "load"
        }).render(true);
    }).catch(err => {
        ui.notifications.error(err);
    });
    if (!jsonData) return;

    console.log("Loaded JSON data:", jsonData);
    console.log("Final derived portrait directory:", derivedPortraitBase);

    // --- STEP 2: Create/find folders for Scenarios, Places, and NPCs ---
    let scenarioFolder = game.folders.find(f => f.name === "Scenarios" && f.type === "Scene");
    if (!scenarioFolder) {
        scenarioFolder = await Folder.create({ name: "Scenarios", type: "Scene", parent: null });
    }
    let placesFolder = game.folders.find(f => f.name === "Places" && f.type === "Scene");
    if (!placesFolder) {
        placesFolder = await Folder.create({ name: "Places", type: "Scene", parent: null });
    }
    let npcFolder = game.folders.find(f => f.name === "NPCs" && f.type === "Actor");
    if (!npcFolder) {
        npcFolder = await Folder.create({ name: "NPCs", type: "Actor", parent: null });
    }

    // --- STEP 3: Basic scene settings ---
    const sceneWidth = 1920;
    const sceneHeight = 1080;
    const gridSize = 100;
    const defaultSceneImg = "icons/svg/scene.svg"; // fallback background

    // Dictionary to avoid duplicates
    let actorsByName = {};

    // Create or reuse an Actor
    async function getOrCreateActor(t) {
        if (actorsByName[t.name]) return actorsByName[t.name];

        const combinedDescription = `
<b>Role:</b> ${t.role || "—"}
<br><b>Description:</b> ${t.description || "—"}
<br><b>Secrets:</b> ${t.secrets || "—"}
    `.trim();

        // Rebuild portrait path
        let portrait = t.portrait || "";
        if (portrait) {
            portrait = portrait.replace("\\", "/");
            let fileName = portrait.split("/").pop();
            portrait = `${derivedPortraitBase}/${fileName}`;
        } else {
            portrait = "icons/svg/mystery-man.svg";
        }

        // Create the Actor
        const actorData = {
            name: t.name,
            type: "npc",
            img: portrait,
            folder: npcFolder.id,
            system: {
                details: {
                    biography: {
                        value: combinedDescription
                    }
                }
            },
            flags: {
                GMCampaignDesigner: {
                    factions: t.factions || [],
                    borderColor: t.borderColor || "#000000"
                }
            }
        };

        const actor = await Actor.create(actorData, { noHook: true });
        actorsByName[t.name] = actor.id;
        return actor.id;
    }

    // Helper: Use actor's actual token image
    function getTokenImage(actorId) {
        const actor = game.actors.get(actorId);
        if (!actor) return "icons/svg/mystery-man.svg";

        // Prefer the prototypeToken's texture if it exists, else actor.img
        const proto = actor.prototypeToken;
        console.log("proto=" + proto.texture.src)
        if (proto?.texture?.src) return proto.texture.src;
        return actor.img || "icons/svg/mystery-man.svg";
    }

    // --- STEP 5: Process Scenarios -> Scenes ---
    if (Array.isArray(jsonData.scenes)) {
        for (let scenario of jsonData.scenes) {
            let sceneTitle = scenario.title || scenario.Title || "Untitled Scenario";
            let sceneSummary = scenario.summary || scenario.Summary || "";
            let sceneSecrets = scenario.secrets || scenario.Secrets || "";

            // Build token data
            let tokens = [];
            let scenarioTokens = scenario.tokens || scenario.Tokens || [];
            for (let t of scenarioTokens) {
                const actorId = await getOrCreateActor(t);

                // We'll override the token's "img" with the actual actor image
                const finalTokenImg = getTokenImage(actorId);
                console.log("token:" + finalTokenImg)
                tokens.push({
                    actorId: actorId,
                    x: t.x ?? 0,
                    y: t.y ?? 0,
                    width: 1,
                    height: 1,
                    name: t.name || "",
                    texture: {
                        src: finalTokenImg
                    },
                    hidden: false,
                    // Set actorLink to true if you want the token to reflect changes to the Actor
                    actorLink: true
                });
            }

            // Combine summary + secrets
            let sceneDescription = `<h2>Summary</h2><p>${sceneSummary}</p>`;
            if (sceneSecrets.trim() !== "") {
                sceneDescription += `<h2>Secrets</h2><p>${sceneSecrets}</p>`;
            }

            // Create the scene
            let createdScene = await Scene.create({
                name: sceneTitle,
                img: defaultSceneImg, // fallback if none provided
                width: sceneWidth,
                height: sceneHeight,
                grid: gridSize,
                navigation: true,
                padding: 0.25,
                description: sceneDescription,
                tokens: tokens,
                folder: scenarioFolder.id,
                backgroundColor: "#222222" // a dark background
            });

            // Add clickable markers as tiles
            let scenarioMarkers = scenario.markers || scenario.Markers || [];
            if (Array.isArray(scenarioMarkers) && scenarioMarkers.length > 0) {
                let tileData = [];
                for (let m of scenarioMarkers) {
                    tileData.push({
                        img: m.icon || "icons/svg/anchor.svg",
                        x: m.x ?? 0,
                        y: m.y ?? 0,
                        width: 64,
                        height: 64,
                        alpha: 1.0,
                        locked: false,
                        flags: {
                            GMCampaignDesigner: {
                                targetScene: m.targetScene || "",
                                name: m.name || "",
                                description: m.description || ""
                            }
                        }
                    });
                }
                await createdScene.createEmbeddedDocuments("Tile", tileData);
            }
        }
    }

    // --- STEP 6: Process Places -> separate Scenes ---
    if (Array.isArray(jsonData.places)) {
        for (let p of jsonData.places) {
            let placeTitle = p.title || p.Title || "Unnamed Place";
            let placeDescription = p.description || p.Description || "";
            let placeImage = p.image || p.Image || defaultSceneImg;
            await Scene.create({
                name: placeTitle,
                img: placeImage,
                width: sceneWidth,
                height: sceneHeight,
                grid: gridSize,
                navigation: true,
                padding: 0.25,
                description: `<p>${placeDescription}</p>`,
                folder: placesFolder.id,
                backgroundColor: "#222222"
            });
        }
    }

    ui.notifications.info("Import complete! Scenes and Actors created in their respective folders.");
})();