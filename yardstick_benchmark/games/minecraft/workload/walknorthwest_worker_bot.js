
const mineflayer = require('mineflayer');
const pathfinder = require('mineflayer-pathfinder').pathfinder
const Movements = require('mineflayer-pathfinder').Movements
const { GoalNear, GoalXZ } = require('mineflayer-pathfinder').goals
const v = require("vec3");

// sub.js
const { workerData, parentPort } = require("worker_threads");

const host = workerData.host
const username = workerData.username
const time_left_ms = workerData.time_left_ms
const box_center = workerData.box_center
const box_width = workerData.box_width


// Define distances for walking north and west
const northDistance = workerData.northDistance ?? 80; // blocks to cover north
const westDistance = workerData.westDistance ?? 40;
const stepSize = workerData.stepSize ?? 4; 

function getRandomInt(max) {
    return Math.floor(Math.random() * max);
}

function nextGoal(bot) {
    if (!bot.walkPlan) {
        bot.walkPlan = { phase: 'north', traveled: 0 };
    }

    const plan = bot.walkPlan;

    if (plan.phase === 'north') {
        plan.traveled = Math.min(plan.traveled + stepSize, northDistance);
        if (plan.traveled >= northDistance) {
        plan.phase = 'west';
        plan.traveled = 0;
        }
        return new GoalXZ(box_center.x, box_center.z + plan.traveled);
    } else {
        plan.traveled = Math.min(plan.traveled + stepSize, westDistance);
        if (plan.traveled >= westDistance) {
        plan.phase = 'north';
        plan.traveled = 0;
        }
        return new GoalXZ(box_center.x - plan.traveled, box_center.z + northDistance);
    }
}

let worker_bot = mineflayer.createBot({
    host: host, // minecraft server ip
    username: username, // minecraft username
    port: 25565,                // only set if you need a port that isn't 25565
});
worker_bot.on('kicked', console.log)
worker_bot.on('error', console.log)
worker_bot.loadPlugin(pathfinder)
worker_bot.once("spawn", async () => {
    let defaultMove = new Movements(worker_bot)
    defaultMove.allowSprinting = false
    defaultMove.canDig = false
    worker_bot.pathfinder.setMovements(defaultMove)
    // worker_bot.pathfinder.thinkTimeout = 60000 // max 60 seconds to find path from start to finish
    while (true) {
        let goal = nextGoal(worker_bot);
        try {
            await worker_bot.pathfinder.goto(goal)
        } catch (e) {
            // if the bot cannot find a path, carry on and let it try to move somewhere else
            if (e.name != "NoPath" && e.name != "Timeout") {
                throw e
            }
        }
    }
});

// parentPort.postMessage({});
