// @ts-check
import {Rcon} from "rcon-client";

const host = process.env.MC_HOST;
const spawn_x = process.env.SPAWN_X;
const spawn_z = process.env.SPAWN_Z ?? process.env.SPAWN_Y;
const playerCount = parseInt(process.env.PLAYER_COUNT ?? "20");
if (host === undefined) {
    throw new Error("No host specified");
}

try {
    console.log("Connecting...");
    const rcon = new Rcon({ host, port: 25575, password: "password" });
    await rcon.connect();
    console.log("Connected and authenticated.");
    const response = await rcon.send(
        `setworldspawn ${spawn_x} 4 ${spawn_z}`,
    );
    console.log(`Response: ${response}`);
    for (let i = 0; i < playerCount; i++) {
        const response = await rcon.execute(`op bot-${i}`);
        console.log(`Response: ${response}`);
    }
    rcon.end();
} catch (error) {
    console.error(`An error occured: ${error}`);
}
