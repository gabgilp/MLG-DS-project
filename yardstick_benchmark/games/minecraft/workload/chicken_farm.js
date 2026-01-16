// @ts-check
import mineflayer from "mineflayer";
import v from "vec3";
import rconPkg from "rcon-srcds";

const host = process.env.MC_HOST ?? "localhost";
const timeout = numberFromEnv("DURATION", 60);
const botIndex = numberFromEnv("BOT_INDEX", 0);
const playerCount = Math.max(1, numberFromEnv("PLAYER_COUNT", 1));
const spawnX = numberFromEnv("SPAWN_X", 0);
const spawnZ = numberFromEnv("SPAWN_Y", 0);

// Blueprint dims (from provided NBT)
const FARM_WIDTH = 7; // x dimension (0..6)
const FARM_DEPTH = 3; // z dimension (0..2)
const FARM_HEIGHT = 6; // y dimension (0..5)
const FARM_SPACING_X = 12;
const FARM_SPACING_Z = 8;
const CHICKENS_PER_FARM = 8;
const VIEW_HEIGHT = 10;
const COMMAND_DELAY_MS = 750; // chat fallback pacing
const RCON_DELAY_MS = 50; // small gap between RCON commands
const rconPassword = process.env.RCON_PASSWORD ?? "password";
const rconPort = numberFromEnv("RCON_PORT", 25575);
const RCON = rconPkg?.default?.default ?? rconPkg?.default ?? rconPkg;
/** @type {import("rcon-srcds").default | null} */
let rconClient = null;

const bot = mineflayer.createBot({
    host,
    username: `bot-${botIndex}`,
    port: 25565,
});
bot.on("error", console.error);
bot.on("kicked", console.log);

await onceSpawn(bot);

const groundY =
    numberFromEnv("GROUND_Y", Math.max(1, Math.floor(bot.entity.position.y) - 1));
const farmOrigin = v(spawnX, groundY, spawnZ);
const layout = createFarmLayout(playerCount, farmOrigin, groundY);
const assignedFarm = Math.min(botIndex, layout.positions.length - 1);

if (botIndex === 0) {
    await builderFlow(bot, layout);
} else {
    await waitForFarmReady(bot, layout.positions[assignedFarm]);
}

await teleportSpectator(bot, layout.positions[assignedFarm]);

console.log(
    `hi! bot-${botIndex} started chicken farms. Exiting after ${timeout} seconds.`,
);
await sleep(timeout * 1000);
process.exit(0);

async function builderFlow(bot, farmLayout) {
    await prepareWorld(bot);
    await flattenArea(bot, farmLayout);
    await buildFarm(bot, farmLayout.positions[0]);
    await cloneFarms(bot, farmLayout);
    await spawnChickens(bot, farmLayout);
}

/**
 * @param {mineflayer.Bot} bot
 */
async function prepareWorld(bot) {
    const commands = [
        "/time set day",
        "/gamerule doDaylightCycle false",
        "/gamerule doMobSpawning false",
        "/difficulty peaceful",
        "/weather clear",
        `/gamemode creative ${bot.username}`,
    ];
    for (const cmd of commands) {
        await sendCommand(bot, cmd);
    }
    bot.creative.startFlying();
}

/**
 * @param {mineflayer.Bot} bot
 * @param {ReturnType<typeof createFarmLayout>} farmLayout
 */
async function flattenArea(bot, farmLayout) {
    const box = farmsBoundingBox(farmLayout);
    const clearMinY = box.min.y + 1;
    const clearMaxY = box.min.y + FARM_HEIGHT + 3;
    await sendCommand(
        bot,
        `/fill ${box.min.x} ${clearMinY} ${box.min.z} ${box.max.x} ${clearMaxY} ${box.max.z} air`,
    );
}

/**
 * @param {mineflayer.Bot} bot
 * @param {import("vec3").Vec3} base
 */
async function buildFarm(bot, base) {
    const blocks = blueprintBlocks();
    for (const blk of blocks) {
        const worldX = base.x + blk.pos[0];
        const worldY = base.y + blk.pos[1];
        const worldZ = base.z + blk.pos[2];
        const blockString = paletteBlock(blk.state);
        await sendCommand(bot, `/setblock ${worldX} ${worldY} ${worldZ} ${blockString}`);
    }
}

/**
 * @param {mineflayer.Bot} bot
 * @param {ReturnType<typeof createFarmLayout>} farmLayout
 */
async function cloneFarms(bot, farmLayout) {
    if (farmLayout.positions.length < 2) {
        return;
    }
    const src = farmBoundingBox(farmLayout.positions[0]);
    for (let i = 1; i < farmLayout.positions.length; i++) {
        const dest = farmLayout.positions[i];
        await sendCommand(
            bot,
            `/clone ${src.min.x} ${src.min.y} ${src.min.z} ${src.max.x} ${src.max.y} ${src.max.z} ${dest.x} ${dest.y} ${dest.z}`,
        );
    }
}

/**
 * @param {mineflayer.Bot} bot
 * @param {ReturnType<typeof createFarmLayout>} farmLayout
 */
async function spawnChickens(bot, farmLayout) {
    await sendCommand(bot, "/kill @e[type=minecraft:chicken,distance=..256]");
    for (const base of farmLayout.positions) {
        const penCenter = v(base.x + 3.5, base.y + 4, base.z + 1.5);
        for (let i = 0; i < CHICKENS_PER_FARM; i++) {
            const offsetX = (i % 2) * 0.6 - 0.3;
            const offsetZ = Math.floor(i / 2) * 0.6 - 0.3;
            const x = penCenter.x + offsetX;
            const z = penCenter.z + offsetZ;
            await sendCommand(
                bot,
                `/summon minecraft:chicken ${x.toFixed(2)} ${penCenter.y} ${z.toFixed(2)} {Age:0,Health:4.0f,IsChickenJockey:0b}`,
            );
        }
        // Seed dispenser with eggs so the loop can fire
        await sendCommand(
            bot,
            `/data modify block ${base.x + 1} ${base.y + 2} ${base.z} Items set value [{Slot:0b,id:"minecraft:egg",Count:64b},{Slot:1b,id:"minecraft:egg",Count:64b},{Slot:2b,id:"minecraft:egg",Count:64b}]`,
        );
        // Hopper minecart under rails
        await sendCommand(
            bot,
            `/summon minecraft:hopper_minecart ${base.x + 2.5} ${base.y + 1.0625} ${base.z + 1.5}`,
        );
    }
}

/**
 * @param {mineflayer.Bot} bot
 * @param {import("vec3").Vec3} base
 */
async function waitForFarmReady(bot, base) {
    const box = farmBoundingBox(base);
    await waitForChunks(bot, box, 20_000);
    const roofCheck = v(
        Math.floor((box.min.x + box.max.x) / 2),
        box.min.y + FARM_HEIGHT,
        Math.floor((box.min.z + box.max.z) / 2),
    );
    const deadline = Date.now() + 20_000;
    while (Date.now() < deadline) {
        const block = bot.blockAt(roofCheck);
        if (block && block.name !== "air") {
            return;
        }
        await sleep(400);
    }
    console.warn("Timed out waiting for farm structure; proceeding anyway.");
}

/**
 * @param {mineflayer.Bot} bot
 * @param {import("vec3").Vec3} base
 */
async function teleportSpectator(bot, base) {
    const view = farmCenter(base).offset(0, VIEW_HEIGHT, 0);
    await sendCommand(bot, `/gamemode spectator ${bot.username}`);
    await sendCommand(bot, `/tp ${bot.username} ${view.x} ${view.y} ${view.z}`);
    await waitForChunks(bot, farmBoundingBox(base), 10_000);
}

/**
 * @param {mineflayer.Bot} bot
 */
async function onceSpawn(bot) {
    return new Promise((resolve) => {
        bot.once("spawn", resolve);
    });
}

/**
 * @param {number} ms
 */
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Ensure an RCON connection; fallback is null.
 */
async function ensureRcon() {
    if (rconClient !== null) {
        return rconClient;
    }
    try {
        const client = new RCON({ host, port: rconPort });
        await client.authenticate(rconPassword);
        rconClient = client;
        console.log("RCON connected.");
    } catch (err) {
        console.warn(`RCON unavailable, falling back to chat: ${err}`);
        rconClient = null;
    }
    return rconClient;
}

/**
 * Fill only the perimeter of a rectangle on one Y level.
 * @param {mineflayer.Bot} bot
 * @param {number} x
 * @param {number} y
 * @param {number} z
 * @param {number} width
 * @param {number} depth
 * @param {string} block
 */
async function fillPerimeter(bot, x, y, z, width, depth, block) {
    const x1 = x + width - 1;
    const z1 = z + depth - 1;
    await sendCommand(bot, `/fill ${x} ${y} ${z} ${x1} ${y} ${z1} ${block} outline`);
}

// Palette and blueprint derived from provided NBT
function paletteBlock(state) {
    switch (state) {
        case 0:
            return "minecraft:dirt";
        case 1:
            return "minecraft:grass_block[snowy=false]";
        case 2:
            return "minecraft:glass";
        case 3:
            return "minecraft:smooth_stone";
        case 4:
            return "minecraft:air";
        case 5:
            return "minecraft:rail[shape=east_west,waterlogged=false]";
        case 6:
            return "minecraft:smooth_stone_slab[type=bottom,waterlogged=false]";
        case 7:
            return "minecraft:redstone_wire[east=side,south=side,north=none,west=none,power=0]";
        case 8:
            return "minecraft:repeater[facing=east,delay=1,locked=false,powered=false]";
        case 9:
            return "minecraft:redstone_wire[east=none,south=none,north=none,west=side,power=0]";
        case 10:
            return "minecraft:repeater[facing=west,delay=1,locked=false,powered=false]";
        case 11:
            return "minecraft:redstone_wire[east=none,south=side,north=none,west=side,power=0]";
        case 12:
            return "minecraft:redstone_wire[east=none,south=side,north=side,west=side,power=0]";
        case 13:
            return "minecraft:redstone_wire[east=none,south=none,north=side,west=side,power=0]";
        case 14:
            return "minecraft:lava[level=0]";
        case 15:
            return "minecraft:chest[facing=north,type=left,waterlogged=false]";
        case 16:
            return "minecraft:chest[facing=north,type=right,waterlogged=false]";
        case 17:
            return "minecraft:hopper[facing=west,enabled=true]";
        case 18:
            return "minecraft:dispenser[facing=west,triggered=false]";
        case 19:
            return "minecraft:comparator[facing=west,mode=compare,powered=false]";
        case 20:
            return "minecraft:hopper[facing=down,enabled=true]";
        default:
            return "minecraft:air";
    }
}

function blueprintBlocks() {
    return [
        { pos: [3, 0, 1], state: 0 },
        { pos: [3, 0, 2], state: 0 },
        { pos: [4, 0, 0], state: 0 },
        { pos: [4, 0, 1], state: 0 },
        { pos: [4, 0, 2], state: 0 },
        { pos: [5, 0, 0], state: 0 },
        { pos: [5, 0, 1], state: 0 },
        { pos: [5, 0, 2], state: 0 },
        { pos: [6, 0, 0], state: 0 },
        { pos: [6, 0, 1], state: 0 },
        { pos: [6, 0, 2], state: 0 },
        { pos: [3, 1, 1], state: 0 },
        { pos: [3, 1, 2], state: 0 },
        { pos: [4, 1, 0], state: 1 },
        { pos: [4, 1, 1], state: 1 },
        { pos: [4, 1, 2], state: 1 },
        { pos: [5, 1, 0], state: 1 },
        { pos: [5, 1, 1], state: 1 },
        { pos: [5, 1, 2], state: 1 },
        { pos: [6, 1, 0], state: 1 },
        { pos: [6, 1, 1], state: 1 },
        { pos: [6, 1, 2], state: 1 },
        { pos: [1, 2, 1], state: 2 },
        { pos: [2, 2, 0], state: 3 },
        { pos: [2, 2, 2], state: 3 },
        { pos: [3, 2, 2], state: 1 },
        { pos: [1, 3, 1], state: 2 },
        { pos: [2, 3, 0], state: 2 },
        { pos: [2, 3, 2], state: 2 },
        { pos: [3, 3, 2], state: 2 },
        { pos: [2, 4, 1], state: 2 },
        { pos: [3, 4, 0], state: 2 },
        { pos: [3, 4, 2], state: 2 },
        { pos: [4, 4, 0], state: 2 },
        { pos: [4, 4, 2], state: 2 },
        { pos: [5, 4, 0], state: 2 },
        { pos: [5, 4, 2], state: 2 },
        { pos: [6, 4, 1], state: 2 },
        { pos: [0, 0, 0], state: 4 },
        { pos: [0, 0, 2], state: 4 },
        { pos: [1, 0, 0], state: 4 },
        { pos: [1, 0, 2], state: 4 },
        { pos: [2, 0, 0], state: 4 },
        { pos: [2, 0, 2], state: 4 },
        { pos: [3, 0, 0], state: 4 },
        { pos: [0, 1, 0], state: 4 },
        { pos: [0, 1, 1], state: 4 },
        { pos: [0, 1, 2], state: 4 },
        { pos: [1, 1, 0], state: 4 },
        { pos: [1, 1, 1], state: 4 },
        { pos: [1, 1, 2], state: 4 },
        { pos: [2, 1, 0], state: 4 },
        { pos: [2, 1, 1], state: 5 },
        { pos: [2, 1, 2], state: 4 },
        { pos: [3, 1, 0], state: 4 },
        { pos: [0, 2, 0], state: 4 },
        { pos: [0, 2, 1], state: 4 },
        { pos: [0, 2, 2], state: 4 },
        { pos: [1, 2, 0], state: 4 },
        { pos: [1, 2, 2], state: 4 },
        { pos: [2, 2, 1], state: 6 },
        { pos: [3, 2, 0], state: 4 },
        { pos: [4, 2, 0], state: 7 },
        { pos: [4, 2, 2], state: 8 },
        { pos: [5, 2, 0], state: 9 },
        { pos: [5, 2, 1], state: 10 },
        { pos: [5, 2, 2], state: 9 },
        { pos: [6, 2, 0], state: 11 },
        { pos: [6, 2, 1], state: 12 },
        { pos: [6, 2, 2], state: 13 },
        { pos: [0, 3, 0], state: 4 },
        { pos: [0, 3, 1], state: 4 },
        { pos: [0, 3, 2], state: 4 },
        { pos: [1, 3, 0], state: 4 },
        { pos: [1, 3, 2], state: 4 },
        { pos: [2, 3, 1], state: 14 },
        { pos: [3, 3, 0], state: 4 },
        { pos: [4, 3, 0], state: 4 },
        { pos: [4, 3, 2], state: 4 },
        { pos: [5, 3, 0], state: 4 },
        { pos: [5, 3, 2], state: 4 },
        { pos: [6, 3, 0], state: 4 },
        { pos: [6, 3, 1], state: 4 },
        { pos: [6, 3, 2], state: 4 },
        { pos: [0, 4, 0], state: 4 },
        { pos: [0, 4, 1], state: 4 },
        { pos: [0, 4, 2], state: 4 },
        { pos: [1, 4, 0], state: 4 },
        { pos: [1, 4, 1], state: 4 },
        { pos: [1, 4, 2], state: 4 },
        { pos: [2, 4, 0], state: 4 },
        { pos: [2, 4, 2], state: 4 },
        { pos: [3, 4, 1], state: 4 },
        { pos: [4, 4, 1], state: 4 },
        { pos: [5, 4, 1], state: 4 },
        { pos: [6, 4, 0], state: 4 },
        { pos: [6, 4, 2], state: 4 },
        { pos: [0, 5, 0], state: 4 },
        { pos: [0, 5, 1], state: 4 },
        { pos: [0, 5, 2], state: 4 },
        { pos: [1, 5, 0], state: 4 },
        { pos: [1, 5, 1], state: 4 },
        { pos: [1, 5, 2], state: 4 },
        { pos: [2, 5, 0], state: 4 },
        { pos: [2, 5, 1], state: 6 },
        { pos: [2, 5, 2], state: 4 },
        { pos: [3, 5, 0], state: 6 },
        { pos: [3, 5, 1], state: 6 },
        { pos: [3, 5, 2], state: 6 },
        { pos: [4, 5, 0], state: 6 },
        { pos: [4, 5, 1], state: 6 },
        { pos: [4, 5, 2], state: 6 },
        { pos: [5, 5, 0], state: 6 },
        { pos: [5, 5, 1], state: 6 },
        { pos: [5, 5, 2], state: 6 },
        { pos: [6, 5, 0], state: 4 },
        { pos: [6, 5, 1], state: 6 },
        { pos: [6, 5, 2], state: 4 },
        { pos: [0, 0, 1], state: 15 },
        { pos: [1, 0, 1], state: 16 },
        { pos: [2, 0, 1], state: 17 },
        { pos: [3, 2, 1], state: 18 },
        { pos: [4, 2, 1], state: 19 },
        { pos: [3, 3, 1], state: 20 },
        { pos: [4, 3, 1], state: 17 },
        { pos: [5, 3, 1], state: 17 },
    ];
}

/**
 * @param {mineflayer.Bot} bot
 * @param {string} command
 */
async function sendCommand(bot, command) {
    const client = await ensureRcon();
    if (client) {
        console.log(`> [rcon] ${command}`);
        await client.execute(command);
        await sleep(RCON_DELAY_MS);
    } else {
        console.log(`> ${command}`);
        bot.chat(command);
        await sleep(COMMAND_DELAY_MS);
    }
}

/**
 * @param {number} count
 * @param {import("vec3").Vec3} origin
 * @param {number} groundY
 */
function createFarmLayout(count, origin, groundY) {
    const perRow = Math.max(1, Math.ceil(Math.sqrt(count)));
    const positions = [];
    for (let i = 0; i < count; i++) {
        const row = Math.floor(i / perRow);
        const col = i % perRow;
        positions.push(
            v(origin.x + col * FARM_SPACING_X, groundY, origin.z + row * FARM_SPACING_Z),
        );
    }
    return { positions, perRow };
}

/**
 * @param {import("vec3").Vec3} base
 */
function farmBoundingBox(base) {
    return {
        min: v(base.x, base.y, base.z),
        max: v(
            base.x + FARM_WIDTH - 1,
            base.y + FARM_HEIGHT - 1,
            base.z + FARM_DEPTH - 1,
        ),
    };
}

/**
 * @param {import("vec3").Vec3} base
 */
function farmCenter(base) {
    return v(
        base.x + (FARM_WIDTH - 1) / 2 + 0.5,
        base.y + (FARM_HEIGHT - 1) / 2,
        base.z + (FARM_DEPTH - 1) / 2 + 0.5,
    );
}

/**
 * @param {{positions: import("vec3").Vec3[]}} farmLayout
 */
function farmsBoundingBox(farmLayout) {
    let minX = Infinity;
    let minZ = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxZ = -Infinity;
    let maxY = -Infinity;
    for (const pos of farmLayout.positions) {
        const box = farmBoundingBox(pos);
        minX = Math.min(minX, box.min.x);
        minZ = Math.min(minZ, box.min.z);
        minY = Math.min(minY, box.min.y);
        maxX = Math.max(maxX, box.max.x);
        maxZ = Math.max(maxZ, box.max.z);
        maxY = Math.max(maxY, box.max.y);
    }
    const padding = 2;
    return {
        min: v(minX - padding, minY, minZ - padding),
        max: v(maxX + padding, maxY + 2, maxZ + padding),
    };
}

/**
 * @param {mineflayer.Bot} bot
 * @param {{ min: import("vec3").Vec3, max: import("vec3").Vec3 }} box
 * @param {number} timeoutMs
 */
async function waitForChunks(bot, box, timeoutMs) {
    const coords = chunkCoordsForBox(box);
    const pending = new Set(coords.map(chunkKey));

    const check = () => {
        for (const chunk of coords) {
            if (bot.world.getColumn(chunk.x, chunk.z)) {
                pending.delete(chunkKey(chunk));
            }
        }
    };
    check();
    if (pending.size === 0) {
        return;
    }

    await new Promise((resolve) => {
        const onLoad = /** @param {import("vec3").Vec3} point */ (point) => {
            const cx = point.x >> 4;
            const cz = point.z >> 4;
            pending.delete(chunkKey({ x: cx, z: cz }));
            if (pending.size === 0) {
                cleanup();
            }
        };
        const timeoutHandle = setTimeout(cleanup, timeoutMs);
        const interval = setInterval(() => {
            check();
            if (pending.size === 0) {
                cleanup();
            }
        }, 300);
        const cleanup = () => {
            clearTimeout(timeoutHandle);
            clearInterval(interval);
            bot.removeListener("chunkColumnLoad", onLoad);
            resolve(undefined);
        };
        bot.on("chunkColumnLoad", onLoad);
    });
}

/**
 * @param {{ min: import("vec3").Vec3, max: import("vec3").Vec3 }} box
 */
function chunkCoordsForBox(box) {
    const startX = Math.floor(box.min.x / 16);
    const endX = Math.floor(box.max.x / 16);
    const startZ = Math.floor(box.min.z / 16);
    const endZ = Math.floor(box.max.z / 16);
    /** @type {{x: number, z: number}[]} */
    const coords = [];
    for (let x = startX; x <= endX; x++) {
        for (let z = startZ; z <= endZ; z++) {
            coords.push({ x, z });
        }
    }
    return coords;
}

/**
 * @param {{x: number, z: number}} chunk
 */
function chunkKey(chunk) {
    return `${chunk.x},${chunk.z}`;
}

/**
 * @param {string} key
 * @param {number} fallback
 */
function numberFromEnv(key, fallback) {
    const raw = process.env[key];
    if (raw === undefined) {
        return fallback;
    }
    const parsed = parseInt(raw, 10);
    if (Number.isNaN(parsed)) {
        return fallback;
    }
    return parsed;
}
