/** Constants */
const HORN_OFF = 0;
const HORN_ON = 1;
const LIGHT_OFF = 0;
const LIGHT_ON = 1;
const WAIT_MS = 50;
const S_MIN = 0;
const S_MAX = 100;
const REVERSE = -1;
const FORWARD_MIN = 1;
const FORWARD_MAX = 3;
const STOP = 0;

/** Global variables */
let steering = S_MAX / 2;
let drive = STOP;
let horn = HORN_OFF;
let light = LIGHT_OFF;
let requestCount = 0;
let totalElapsedTime = 0;
let horntimeout = null;
let lastSuccessfullApiCall = Date.now();

/** Control functions */
let steeringInterval = null;

function steeringReleased() {
    clearInterval(steeringInterval);
}

function pressedLeft() {
    clearInterval(steeringInterval);
    steeringInterval = setInterval(() => {
        left();
    }, 200);
}

function pressedRight() {
    clearInterval(steeringInterval);
    steeringInterval = setInterval(() => {
        right();
    }, 200);
}

function forward() {
    steeringReleased();
    if (drive === REVERSE) {
        drive = STOP;
    } else {
        drive = Math.min(drive + 1, FORWARD_MAX);
    }
}

function reverse() {
    steeringReleased();
    if (drive > STOP) {
        drive = Math.max(drive - 1, STOP);
    } else {
        drive = REVERSE;
    }
}

function stop() {
    steeringReleased();
    drive = STOP;
}

function left() {
    steering = Math.max(steering - 10, S_MIN);
}

function right() {
    steering = Math.min(steering + 10, S_MAX);
}

function honk() {
    steeringReleased();
    horn = HORN_ON;
    clearTimeout(horntimeout);
    horntimeout = setTimeout(() => {
        horn = HORN_OFF;
    }, 500);
}

function lightToggle() {
    steeringReleased();
    light = light === LIGHT_OFF ? LIGHT_ON : LIGHT_OFF;
}

function reset() {
    steeringReleased();
    steering = S_MAX / 2;
    drive = STOP;
    horn = HORN_OFF;
    light = LIGHT_OFF;
}

/** Send control data to server */
async function send() {
    const startTime = Date.now();
    let elapsedTime = 0;
    try {
        /** If control has no connection for more than 1 second, reset controls */
        if (Date.now() - lastSuccessfullApiCall > 1000) {
            reset();
        }
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 300);
        const res = await fetch(`/control?steering=${steering}&drive=${drive}&horn=${horn}&light=${light}`, {
            method: 'POST',
            signal: controller.signal
        });
        elapsedTime = Date.now() - startTime;
        document.getElementById('status').innerHTML = res.status;
        if (res.ok) {
            try {
                lastSuccessfullApiCall = Date.now();
                const data = await res.json();
                const rawBattery = data.battery;
                if (rawBattery && !isNaN(+rawBattery)) {
                    const batteryVoltage = (+rawBattery).toFixed(2);
                    document.getElementById('battery').innerHTML = batteryVoltage;
                }
            } catch (e) {
                console.warn('Invalid JSON response', e);
            }
        }
    } catch (error) {
        document.getElementById('status').innerHTML = error.name;
    } finally {
        requestCount++;
        totalElapsedTime += elapsedTime;
        setTimeout(() => {
            send();
        }, Math.min(Math.max(10, WAIT_MS - elapsedTime), WAIT_MS));
    }
}

/** Update UI periodically */
setInterval(() => {
    document.getElementById('requestCount').innerHTML = requestCount;
    document.getElementById('elapsedTime').innerHTML = Math.round(totalElapsedTime / requestCount) + ' ms';
    requestCount = 0;
    totalElapsedTime = 0;
}, 1000);

setInterval(() => {
    document.getElementById('drive').value = drive + 1;
    document.getElementById('steering').value = steering;
    document.getElementById('drive_value').innerHTML = drive;
    document.getElementById('steering_value').innerHTML = steering - 50;
    document.getElementById('horn').style.backgroundColor = horn === HORN_ON ? 'orange' : 'lightgray';
    document.getElementById('light').style.backgroundColor = light === LIGHT_ON ? 'orange' : 'lightgray';
    document.getElementById('up').style.backgroundColor = drive > 0 ? 'lightgreen' : 'lightgray';
    document.getElementById('brake').style.backgroundColor = drive === REVERSE ? 'lightblue' : 'lightgray';
    document.getElementById('left').style.backgroundColor = steering < S_MAX / 2 ? 'gray' : 'lightgray';
    document.getElementById('right').style.backgroundColor = steering > S_MAX / 2 ? 'gray' : 'lightgray';
}, 100);

/** Keyboard controls */
window.addEventListener('DOMContentLoaded', send);
document.getElementById('light').addEventListener('click', lightToggle);
document.getElementById('horn').addEventListener('click', honk);
document.getElementById('up').addEventListener('click', forward);
document.getElementById('brake').addEventListener('click', reverse);
document.getElementById('left').addEventListener('click', left);
document.getElementById('right').addEventListener('click', right);
document.getElementById('stop').addEventListener('click', stop);

document.getElementById('right').addEventListener('pointerdown', pressedRight);
document.getElementById('left').addEventListener('pointerdown', pressedLeft);
document.getElementById('right').addEventListener('pointerup', steeringReleased);
document.getElementById('left').addEventListener('pointerup', steeringReleased);
document.getElementById('right').addEventListener('pointerleave', steeringReleased);
document.getElementById('left').addEventListener('pointerleave', steeringReleased);
document.getElementById('right').addEventListener('pointerout', steeringReleased);
document.getElementById('left').addEventListener('pointerout', steeringReleased);
document.getElementById('right').addEventListener('pointercancel', steeringReleased);
document.getElementById('left').addEventListener('pointercancel', steeringReleased);
