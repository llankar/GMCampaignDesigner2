(async () => {
    let jsonData = null;
    // Default fallback relative path for portrait images (without a "data/" prefix)
    let derivedPortraitBase = "images/DresdenFiles/Scenarios/portrait";

    // --- STEP 1: Prompt the user to select a local JSON file using a native file input ---
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
                        // Try to derive the relative portrait base directory from the file's full path.
                        const fullPath = file.path || file.webkitRelativePath || "";
                        if (fullPath) {
                            // Normalize to forward slashes.
                            let normalized = fullPath.replace(/\\/g, "/");
                            // Look for "/data/" in a case-insensitive way.
                            let lower = normalized.toLowerCase();
                            let idx = lower.indexOf("/data/");
                            if (idx !== -1) {
                                // Get the substring starting at "data/" (this will include "data/")
                                let relativePath = normalized.substring(idx + 1); // remove leading slash → "data/..."
                                // Remove the JSON filename by finding the last slash.
                                let lastSlash = relativePath.lastIndexOf("/");
                                if (lastSlash !== -1) {
                                    derivedPortraitBase = relativePath.substring(0, lastSlash) + "/portraits";
                                }
                            } else {
                                // If "/data/" not found, use the full path (without its filename) and append "/portraits"
                                let lastSlash = normalized.lastIndexOf("/");
                                if (lastSlash !== -1) {
                                    derivedPortraitBase = normalized.substring(0, lastSlash) + "/portraits";
                                }
                            }
                            // Remove a leading "data/" (or "Data/") if present.
                            if (derivedPortraitBase.toLowerCase().startsWith("data/")) {
                                derivedPortraitBase = derivedPortraitBase.substring(5);
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
                    callback: () => reject(new Error("User cancelled file selection"))
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

    // --- STEP 2: Create (or find) the folders for Scenarios, Places, and NPCs ---
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

    // --- STEP 4: Dictionary to avoid duplicate Actors for NPCs with the same name ---
    let actorsByName = {};

    /**
     * Helper function to create (or reuse) an Actor for an NPC token.
     * The portrait path is rebuilt using the derived portrait base directory.
     * @param {Object} t - A token-like object from the JSON (with properties: name, portrait, role, description, secrets, etc.)
     * @returns {String} The Actor's ID
     */
    async function getOrCreateActor(t) {
        if (actorsByName[t.name]) return actorsByName[t.name];

        const combinedDescription = `
<b>Role:</b> ${t.role || "—"}
<br><b>Description:</b> ${t.description || "—"}
<br><b>Secrets:</b> ${t.secrets || "—"}
    `.trim();

        let portrait = t.portrait || "";
        if (portrait) {
            portrait = portrait.replace("\\", "/");
            let fileName = portrait.split("/").pop();
            portrait = `${derivedPortraitBase}/${fileName}`;
        } else {
            portrait = "icons/svg/mystery-man.svg";
        }

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

        let createdActor = await Actor.create(actorData, { noHook: true });
        actorsByName[t.name] = createdActor.id;
        return createdActor.id;
    }

    // 5) Process each scenario in data.scenes
    if (Array.isArray(jsonData.scenes)) {
        for (let scenario of jsonData.scenes) {
            // Build an array of token data referencing Actors
            let tokens = [];
            if (Array.isArray(scenario.tokens)) {
                for (let t of scenario.tokens) {
                    // Create or reuse an Actor for this NPC
                    const actorId = await getOrCreateActor(t);
                    tokens.push({
                        actorId: actorId,
                        x: t.x || 0,
                        y: t.y || 0,
                        width: 1,  // 1 grid square wide
                        height: 1, // 1 grid square tall
                        img: t.portrait || "icons/svg/mystery-man.svg",
                        name: t.name
                    });
                }
            }

            // Combine summary + secrets into HTML for the scene's description
            let sceneDescription = `<h2>Summary</h2><p>${scenario.summary || ""}</p>`;
            if (scenario.secrets && scenario.secrets.trim() !== "") {
                sceneDescription += `<h2>Secrets</h2><p>${scenario.secrets}</p>`;
            }

            // Create the scenario scene
            let createdScene = await Scene.create({
                name: scenario.title || "Untitled Scenario",
                img: "", // Provide a default background image if you like
                width: sceneWidth,
                height: sceneHeight,
                grid: gridSize,
                navigation: true,
                padding: 0.25,
                description: sceneDescription,
                tokens: tokens,
                folder: scenarioFolder.id
            });

            // Create clickable markers as Tiles
            if (Array.isArray(scenario.markers) && scenario.markers.length > 0) {
                let tileData = [];
                for (let m of scenario.markers) {
                    tileData.push({
                        img: m.icon || "icons/svg/anchor.svg",
                        x: m.x || 0,
                        y: m.y || 0,
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

    // 6) Create separate Scenes for each place
    if (Array.isArray(jsonData.places)) {
        for (let place of jsonData.places) {
            await Scene.create({
                name: place.title || "Unnamed Place",
                img: place.image || "",
                width: sceneWidth,
                height: sceneHeight,
                grid: gridSize,
                navigation: true,
                padding: 0.25,
                description: `<p>${place.description || ""}</p>`,
                folder: placesFolder.id
            });
        }
    }

    ui.notifications.info("Import complete! Scenes and Actors created in their respective folders.");
})();