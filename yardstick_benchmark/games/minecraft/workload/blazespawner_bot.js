const mineflayer = require('mineflayer');
const v = require("vec3");

const host = process.env.MC_HOST;
const timeout_s = parseInt(process.env.DURATION);
const mobCount = parseInt(process.env.BLAZE_COUNT); // Renamed but keeping env var for compatibility
const spawnAreaSize = parseInt(process.env.SPAWN_AREA_SIZE);
const spawnHeight = parseInt(process.env.SPAWN_HEIGHT);
const allowUsers = process.env.ALLOW_USERS === 'true';
const bot_index = process.env.BOT_INDEX || 0;

let AVAILABLE_MOBS = [];

async function discoverAvailableMobs(bot) {
    console.log(`${Date.now() / 1000} - 🔍 Querying server for complete entity registry...`);

    let discoveredMobs = [];

    try {
        // Method 1: Use tab completion to get all entity types
        console.log(`${Date.now() / 1000} - Attempting tab completion method...`);

        // Create a promise to capture tab completion results
        const tabCompletionPromise = new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Tab completion timeout'));
            }, 10000);

            // Listen for tab completion results
            const onTabComplete = (matches) => {
                clearTimeout(timeout);
                bot.removeListener('tabComplete', onTabComplete);

                // Filter matches to only get entity types (should start with minecraft:)
                const entityTypes = matches
                    .filter(match => match.startsWith('minecraft:') && !match.includes(' '))
                    .filter(match => {
                        // Filter out non-entity types (blocks, items, etc.)
                        const entityName = match.replace('minecraft:', '');
                        return !entityName.includes('_') ||
                               entityName.includes('zombie') ||
                               entityName.includes('skeleton') ||
                               entityName.includes('pig') ||
                               entityName.includes('cow') ||
                               entityName.includes('sheep') ||
                               entityName.includes('chicken');
                    });

                resolve(entityTypes);
            };

            bot.on('tabComplete', onTabComplete);
        });

        // Trigger tab completion by typing incomplete summon command
        bot.chat('/summon minecraft:');
        await sleep(1000); // Wait for server processing

        // Try to get tab completion results
        try {
            const tabResults = await tabCompletionPromise;
            if (tabResults.length > 0) {
                discoveredMobs = tabResults;
                console.log(`${Date.now() / 1000} - ✅ Found ${discoveredMobs.length} entities via tab completion`);
            }
        } catch (tabError) {
            console.log(`${Date.now() / 1000} - Tab completion failed: ${tabError.message}`);
        }



        // Method 3: Fallback to just zombie if other methods fail
        if (discoveredMobs.length === 0) {
            console.log(`${Date.now() / 1000} - Using basic zombie fallback...`);
            discoveredMobs = ['minecraft:zombie'];
        }

    } catch (error) {
        console.log(`${Date.now() / 1000} - Error during mob discovery: ${error.message}`);
    }

    // Filter out obviously non-mob entities if we got too many results
    if (discoveredMobs.length > 100) {
        console.log(`${Date.now() / 1000} - Filtering results to remove non-mob entities...`);
        discoveredMobs = discoveredMobs.filter(mob => {
            const name = mob.replace('minecraft:', '');
            // Keep if it looks like a mob name
            return !name.includes('block') &&
                   !name.includes('item') &&
                   !name.includes('arrow') &&
                   !name.includes('potion') &&
                   !name.includes('boat') &&
                   !name.includes('minecart');
        });
    }

    if (discoveredMobs.length === 0) {
        console.log(`${Date.now() / 1000} - ⚠️ No mobs discovered, using zombie fallback`);
        discoveredMobs = ['minecraft:zombie'];
    }

    console.log(`${Date.now() / 1000} - ✅ Final mob list: ${discoveredMobs.length} available mob types`);
    console.log(`${Date.now() / 1000} - Sample mobs: ${discoveredMobs.slice(0, 10).map(m => m.replace('minecraft:', '')).join(', ')}${discoveredMobs.length > 10 ? '...' : ''}`);

    return discoveredMobs;
}

function getRandomMob() {
    if (AVAILABLE_MOBS.length === 0) {
        console.log(`${Date.now() / 1000} - ⚠️ No mobs discovered, falling back to zombie`);
        return 'minecraft:zombie';
    }
    return AVAILABLE_MOBS[Math.floor(Math.random() * AVAILABLE_MOBS.length)];
}

const start = Date.now();

function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

function getRandomSpawnPosition(centerX, centerZ, areaSize, height) {
    const x = centerX + (Math.random() - 0.5) * areaSize;
    const z = centerZ + (Math.random() - 0.5) * areaSize;
    return v(x, height, z);
}

async function run() {
    let bot = mineflayer.createBot({
        host: host,
        username: `blazespawner-${bot_index}-${Date.now()}`,
        port: 25565,
    });

    bot.on('kicked', (reason) => {
        console.log(`${Date.now() / 1000} - Bot ${bot.username} was kicked: ${reason}`);
    });

    bot.on('error', (err) => {
        console.log(`${Date.now() / 1000} - Bot ${bot.username} error: ${err}`);
    });

    bot.once("spawn", async () => {
        let ts = Date.now() / 1000;
        console.log(`${ts} - Bot ${bot.username} spawned, preparing to spawn ${mobCount} random mobs`);

        try {
            await sleep(3000);

            console.log(`${Date.now() / 1000} - Requesting OP permissions...`);
            bot.chat('/op ' + bot.username);
            await sleep(1000);

            bot.chat('/gamemode creative');
            await sleep(1000);

            const spawnPos = bot.entity.position.clone();
            console.log(`${Date.now() / 1000} - Spawn center: X=${spawnPos.x.toFixed(2)}, Y=${spawnPos.y.toFixed(2)}, Z=${spawnPos.z.toFixed(2)}`);
            console.log(`${Date.now() / 1000} - Will spawn random mobs in a ${spawnAreaSize}x${spawnAreaSize} area at height ${spawnHeight}`);
            console.log(`${Date.now() / 1000} - Will discover available mob types from server...`);

            let spawnedCount = 0;
            let mobTypesCounts = {}; // Track how many of each mob type we spawn
            const mobsPerWave = 10;
            const waveDelay = 60000; // 1 minute in milliseconds
            const totalWaves = Math.ceil(mobCount / mobsPerWave);

            console.log(`${Date.now() / 1000} - Starting random mob spawning process...`);
            console.log(`${Date.now() / 1000} - Will spawn ${mobCount} random mobs in ${totalWaves} waves of ${mobsPerWave} mobs each`);
            console.log(`${Date.now() / 1000} - 1 minute delay between waves`);

            console.log(`${Date.now() / 1000} - 🔍 First, discovering what mobs are available in this server version...`);
            AVAILABLE_MOBS = await discoverAvailableMobs(bot);

            if (AVAILABLE_MOBS.length === 0) {
                console.log(`${Date.now() / 1000} - ❌ No valid mobs found in this server version! Aborting.`);
                return;
            }

            for (let wave = 0; wave < totalWaves; wave++) {
                const waveStart = wave * mobsPerWave;
                const waveEnd = Math.min(waveStart + mobsPerWave, mobCount);
                const mobsInThisWave = waveEnd - waveStart;

                console.log(`${Date.now() / 1000} - 🌊 Starting wave ${wave + 1}/${totalWaves}: spawning ${mobsInThisWave} random mobs`);

                for (let i = waveStart; i < waveEnd; i++) {
                    try {
                        const mobPos = getRandomSpawnPosition(spawnPos.x, spawnPos.z, spawnAreaSize, spawnHeight);

                        const mobType = getRandomMob();

                        mobTypesCounts[mobType] = (mobTypesCounts[mobType] || 0) + 1;

                        const summonCommand = `/summon ${mobType} ${mobPos.x.toFixed(2)} ${mobPos.y.toFixed(2)} ${mobPos.z.toFixed(2)}`;
                        bot.chat(summonCommand);

                        spawnedCount++;

                        if (i % 5 === 0) {
                            const mobName = mobType.replace('minecraft:', '');
                            console.log(`${Date.now() / 1000} - Spawned ${mobName} at ${mobPos.x.toFixed(1)}, ${mobPos.y}, ${mobPos.z.toFixed(1)}`);
                        }

                        await sleep(200);

                    } catch (error) {
                        console.log(`${Date.now() / 1000} - Error spawning mob ${i + 1}: ${error}`);
                    }
                }

                console.log(`${Date.now() / 1000} - ✅ Wave ${wave + 1} complete: ${spawnedCount}/${mobCount} total mobs spawned`);

                if ((wave + 1) % 10 === 0) {
                    const uniqueTypes = Object.keys(mobTypesCounts).length;
                    console.log(`${Date.now() / 1000} - 📊 Diversity: ${uniqueTypes} different mob types spawned so far`);
                }

                if (wave < totalWaves - 1) {
                    console.log(`${Date.now() / 1000} - ⏳ Waiting 1 minute before next wave...`);
                    await sleep(waveDelay);
                }
            }

            console.log(`${Date.now() / 1000} - Random mob spawning completed! Spawned ${spawnedCount} mobs`);

            const uniqueTypes = Object.keys(mobTypesCounts).length;
            console.log(`${Date.now() / 1000} - 📊 Final Diversity Report: ${uniqueTypes} different mob types spawned`);
            console.log(`${Date.now() / 1000} - Top 5 most spawned:`,
                Object.entries(mobTypesCounts)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5)
                    .map(([type, count]) => `${type.replace('minecraft:', '')}(${count})`)
                    .join(', ')
            );

            if (allowUsers) {
                console.log(`${Date.now() / 1000} - Configuring server to allow user connections...`);

                bot.chat('/whitelist off');
                await sleep(500);
                bot.chat('/difficulty normal');
                await sleep(500);
                bot.chat('/gamerule keepInventory true');
                await sleep(500);
                bot.chat('/gamerule doMobSpawning false'); // Prevent more mobs from spawning naturally
                await sleep(500);

                console.log(`${Date.now() / 1000} - Server configured for user access:`);
                console.log(`${Date.now() / 1000} - - Whitelist: OFF (anyone can join)`);
                console.log(`${Date.now() / 1000} - - Difficulty: NORMAL`);
                console.log(`${Date.now() / 1000} - - Keep Inventory: ON`);
                console.log(`${Date.now() / 1000} - - Natural Mob Spawning: OFF`);

                bot.chat(`§6[MobSpawner] §aServer ready! ${spawnedCount} random mobs spawned. Users can now join!`);
            }

            console.log(`${Date.now() / 1000} - Setup complete! Server status:`);
            console.log(`${Date.now() / 1000} - - Random mobs spawned: ${spawnedCount}`);
            console.log(`${Date.now() / 1000} - - Mob types diversity: ${uniqueTypes} different types`);
            console.log(`${Date.now() / 1000} - - Spawn area: ${spawnAreaSize}x${spawnAreaSize} blocks`);
            console.log(`${Date.now() / 1000} - - Spawn height: ${spawnHeight} blocks`);
            console.log(`${Date.now() / 1000} - - Users allowed: ${allowUsers ? 'YES' : 'NO'}`);

            console.log(`${Date.now() / 1000} - Monitoring server... (will stay connected for ${timeout_s} seconds)`);

            const statusInterval = setInterval(() => {
                const elapsed = (Date.now() - start) / 1000;
                const remaining = timeout_s - elapsed;

                if (remaining > 0) {
                    console.log(`${Date.now() / 1000} - Status: ${spawnedCount} random mobs active, ${remaining.toFixed(0)}s remaining`);

                    if (Math.floor(elapsed) % 300 === 0 && allowUsers) {
                        bot.chat(`§6[MobSpawner] §7${spawnedCount} random mobs spawned! Diversity: ${uniqueTypes} types. Time: ${Math.floor(remaining/60)}min`);
                    }
                } else {
                    clearInterval(statusInterval);
                }
            }, 30000);

        } catch (error) {
            console.log(`${Date.now() / 1000} - Error during setup: ${error}`);
        }
    });

    setTimeout(() => {
        console.log(`${Date.now() / 1000} - Session timeout reached, shutting down`);

        if (allowUsers) {
            bot.chat(`§6[BlazeSpawner] §cSession ending. Thank you for playing!`);
        }

        bot.quit("Session complete");
        process.exit(0);
    }, timeout_s * 1000);
}

process.on('SIGINT', () => {
    console.log(`${Date.now() / 1000} - Received SIGINT, shutting down gracefully...`);
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log(`${Date.now() / 1000} - Received SIGTERM, shutting down gracefully...`);
    process.exit(0);
});

run().catch(console.error);
