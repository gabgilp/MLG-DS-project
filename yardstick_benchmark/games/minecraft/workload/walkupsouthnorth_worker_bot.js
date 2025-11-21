const mineflayer = require("mineflayer");
const pathfinder = require("mineflayer-pathfinder").pathfinder;
const Movements = require("mineflayer-pathfinder").Movements;
const { GoalXZ } = require("mineflayer-pathfinder").goals;
const v = require("vec3");
const { workerData } = require("worker_threads");

const host = workerData.host;
const username = workerData.username;
const box_center = workerData.box_center;
const box_width = workerData.box_width;

const ascendHeight = workerData.ascend_height ?? 6;
const southDistance = workerData.south_distance ?? box_width / 2;
const northDistance = workerData.north_distance ?? box_width / 2;

const southZ = box_center.z - southDistance;
const northZ = box_center.z + northDistance;
const ascendY = (box_center.y ?? 0) + ascendHeight;

function logMove(bot, label, target) {
  const ts = Date.now() / 1000;
  console.log(
    `${ts} - bot ${bot.username} phase=${label} from ${bot.entity.position} to ${target}`
  );
}

async function gotoXZ(bot, x, z) {
  const goal = new GoalXZ(x, z);
  logMove(bot, "ground-move", v(x, bot.entity.position.y, z));
  try {
    await bot.pathfinder.goto(goal);
  } catch (err) {
    if (err.name !== "NoPath" && err.name !== "Timeout") {
      throw err;
    }
  }
}

async function ascend(bot) {
  if (!bot.creative || typeof bot.creative.flyTo !== "function") {
    return;
  }
  bot.creative.startFlying();
  const target = v(box_center.x, ascendY, box_center.z);
  logMove(bot, "ascend", target);
  await bot.creative.flyTo(target);
  bot.creative.stopFlying();
}

let worker_bot = mineflayer.createBot({
  host: host,
  username: username,
  port: 25565,
});

worker_bot.on("kicked", console.log);
worker_bot.on("error", console.log);
worker_bot.loadPlugin(pathfinder);

worker_bot.once("spawn", async () => {
  const moves = new Movements(worker_bot);
  moves.allowSprinting = false;
  moves.canDig = false;
  worker_bot.pathfinder.setMovements(moves);

  while (true) {
    await ascend(worker_bot);
    await gotoXZ(worker_bot, box_center.x, southZ);
    await gotoXZ(worker_bot, box_center.x, northZ);
  }
});
