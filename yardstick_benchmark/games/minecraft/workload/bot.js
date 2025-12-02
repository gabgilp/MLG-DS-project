// @ts-check
import mineflayer from "mineflayer";
import v from "vec3";

const host = process.env.MC_HOST ?? "localhost";
// Time (seconds) after which the script will be terminated
const timeout = parseInt(process.env.DURATION ?? "60");
const variant = process.env.WORKLOAD_VARIANT ?? "fly";

class Bot {
    /**
     * @param {string} host
     * @param {string} username
     */
    constructor(host, username) {
        console.log(`New bot: ${username}`);
        this.bot = mineflayer.createBot({
            host, // minecraft server ip
            username, // minecraft username
            port: 25565, // only set if you need a port that isn't 25565
        });
        this.bot.on("error", console.error);
        this.bot.on("kicked", console.log);
    }

    /**
     * Wait for the `spawn` event.
     */
    spawn() {
        return new Promise(
            /** @type {(fn: (x: void) => void) => void} */
            (res) => {
                this.bot.on("spawn", res);
            },
        );
    }

    /**
     * @param {number} index
     */
    async flyWorkload(index) {
        const coordinates = Botnet.coordinatesFromAngle(index);
        const from = coordinates.clone().scale(700);
        const to = coordinates.clone().scale(2_000);
        from.y = to.y = 90;
        console.log(`bot-${index} ${from} ${to}`);

        await this.spawn();
        this.bot.chat("/gamemode spectator");
        this.bot.creative.startFlying();
        this.bot.chat(`/teleport ${from.x} ${from.y} ${from.z}`);
        await this.bot.creative.flyTo(to);
    }
}

class Botnet {
    /**
     * @param {string} host
     */
    constructor(host) {
        this.host = host;
        this.bots = [];
    }

    /**
     * @param {number} index Bot index between 0 and 19 (inclusive)
     */
    static coordinatesFromAngle(index) {
        const angle = (index / 20) * 2 * Math.PI;
        return v(Math.cos(angle), 90, Math.sin(angle));
    }

    async flyWorkload() {
        for (let i = 0; i < 20; i++) {
            if (i === 5 || i === 10) {
                await sleep(20_000);
            }
            const bot = new Bot(this.host, `bot-${i}`);
            this.bots.push(bot);
            bot.flyWorkload(i);
        }
    }
}

/**
 * @param {number} ms
 * @returns Promise<void>
 */
function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

const botnet = new Botnet(host);
switch (variant) {
    case "fly":
        botnet.flyWorkload();
        break;
}

let ts = Date.now() / 1000;
console.log(`hi! Started at ${ts}. I will exit after ${timeout} seconds.`);
await sleep(timeout * 1000);
process.exit(0);
