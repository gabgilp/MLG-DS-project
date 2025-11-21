const mineflayer = require('mineflayer');
const v = require("vec3");

const host = process.env.MC_HOST;
const timeout_s = parseInt(process.env.DURATION);
const blazeCount = parseInt(process.env.BLAZE_COUNT);
const spawnAreaSize = parseInt(process.env.SPAWN_AREA_SIZE);
const spawnHeight = parseInt(process.env.SPAWN_HEIGHT);
const allowUsers = process.env.ALLOW_USERS === 'true';
const bot_index = process.env.BOT_INDEX || 0;

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
        console.log(`${ts} - Bot ${bot.username} spawned, preparing to spawn ${blazeCount} blazes`);

        try {
            await sleep(3000);

            console.log(`${Date.now() / 1000} - Requesting OP permissions...`);
            bot.chat('/op ' + bot.username);
            await sleep(1000);

            bot.chat('/gamemode creative');
            await sleep(1000);

            const spawnPos = bot.entity.position.clone();
            console.log(`${Date.now() / 1000} - Spawn center: X=${spawnPos.x.toFixed(2)}, Y=${spawnPos.y.toFixed(2)}, Z=${spawnPos.z.toFixed(2)}`);
            console.log(`${Date.now() / 1000} - Will spawn blazes in a ${spawnAreaSize}x${spawnAreaSize} area at height ${spawnHeight}`);

            let spawnedCount = 0;
            const blazesPerWave = 10;
            const waveDelay = 60000; // 1 minute in milliseconds
            const totalWaves = Math.ceil(blazeCount / blazesPerWave);

            console.log(`${Date.now() / 1000} - Starting blaze spawning process...`);
            console.log(`${Date.now() / 1000} - Will spawn ${blazeCount} blazes in ${totalWaves} waves of ${blazesPerWave} blazes each`);
            console.log(`${Date.now() / 1000} - 1 minute delay between waves`);

            for (let wave = 0; wave < totalWaves; wave++) {
                const waveStart = wave * blazesPerWave;
                const waveEnd = Math.min(waveStart + blazesPerWave, blazeCount);
                const blazesInThisWave = waveEnd - waveStart;

                console.log(`${Date.now() / 1000} - 🌊 Starting wave ${wave + 1}/${totalWaves}: spawning ${blazesInThisWave} blazes`);

                for (let i = waveStart; i < waveEnd; i++) {
                    try {
                        const blazePos = getRandomSpawnPosition(spawnPos.x, spawnPos.z, spawnAreaSize, spawnHeight);

                        const summonCommand = `/summon minecraft:blaze ${blazePos.x.toFixed(2)} ${blazePos.y.toFixed(2)} ${blazePos.z.toFixed(2)}`;
                        bot.chat(summonCommand);

                        spawnedCount++;

                        await sleep(200);

                    } catch (error) {
                        console.log(`${Date.now() / 1000} - Error spawning blaze ${i + 1}: ${error}`);
                    }
                }

                console.log(`${Date.now() / 1000} - ✅ Wave ${wave + 1} complete: ${spawnedCount}/${blazeCount} total blazes spawned`);

                if (wave < totalWaves - 1) {
                    console.log(`${Date.now() / 1000} - ⏳ Waiting 1 minute before next wave...`);
                    await sleep(waveDelay);
                }
            }

            console.log(`${Date.now() / 1000} - Blaze spawning completed! Spawned ${spawnedCount} blazes`);

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

                // Send welcome message
                bot.chat(`§6[BlazeSpawner] §aServer ready! ${spawnedCount} blazes spawned. Users can now join!`);
            }

            // Get final blaze count
            await sleep(2000);
            bot.chat('/execute store result score #blazecount blazecount run execute if entity @e[type=minecraft:blaze]');

            console.log(`${Date.now() / 1000} - Setup complete! Server status:`);
            console.log(`${Date.now() / 1000} - - Blazes spawned: ${spawnedCount}`);
            console.log(`${Date.now() / 1000} - - Spawn area: ${spawnAreaSize}x${spawnAreaSize} blocks`);
            console.log(`${Date.now() / 1000} - - Spawn height: ${spawnHeight} blocks`);
            console.log(`${Date.now() / 1000} - - Users allowed: ${allowUsers ? 'YES' : 'NO'}`);

            console.log(`${Date.now() / 1000} - Monitoring server... (will stay connected for ${timeout_s} seconds)`);

            const statusInterval = setInterval(() => {
                const elapsed = (Date.now() - start) / 1000;
                const remaining = timeout_s - elapsed;

                if (remaining > 0) {
                    console.log(`${Date.now() / 1000} - Status: ${spawnedCount} blazes active, ${remaining.toFixed(0)}s remaining`);

                    if (Math.floor(elapsed) % 300 === 0 && allowUsers) {
                        bot.chat(`§6[BlazeSpawner] §7${spawnedCount} blazes available for combat! Time remaining: ${Math.floor(remaining/60)}min`);
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
