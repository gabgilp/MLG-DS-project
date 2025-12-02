// @ts-check
import RCON from "rcon-srcds";

const host = process.env.MC_HOST;
const spawn_x = process.env.SPAWN_X;
const spawn_z = process.env.SPAWN_Y;
if (host === undefined) {
    throw new Error("No host specified");
}

try {
    const rcon = new RCON({ host, port: 25575 });
    await rcon.authenticate("password");
    console.log("Connected and authenticated.");
    const response = await rcon.execute(
        `setworldspawn ${spawn_x} 4 ${spawn_z}`,
    );
    console.log(`Response: ${response}`);
    for (let i = 0; i < 20; i++) {
        const response = await rcon.execute(`op bot-${i}`);
        console.log(`Response: ${response}`);
    }
    rcon.disconnect();
} catch (error) {
    console.error(`An error occured: ${error}`);
}
