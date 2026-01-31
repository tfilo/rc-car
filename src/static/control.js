/** Constants */
const HORN_OFF = 0;
const HORN_ON = 1;
const LIGHT_OFF = 0;
const LIGHT_ON = 1;
const WAIT_MS = 100;
const S_MIN = 0;
const S_MAX = 100;
const REVERSE_MAX = -2;
const FORWARD_MAX = 4;
const STOP = 0;
const BAT_MIN_V = 3.8;
const BAT_MAX_V = 4.8;

/** Global variables */
let steering = S_MAX / 2;
let drive = STOP;
let horn = HORN_OFF;
let light = LIGHT_OFF;
let requestCount = 0;
let horntimeout = null;

/** Control functions */
let steeringInterval = null;
let steeringTimeout = null;
let driveInterval = null;
let driveTimeout = null;

/** socket */
let socket = null;
let sendInterval = null;

function isSocketOpen() {
    return socket && socket.readyState === WebSocket.OPEN;
}

function steeringResetTimeout() {
    clearTimeout(steeringTimeout);
    clearInterval(steeringInterval);
}

function driveResetTimeout() {
    clearTimeout(driveTimeout);
    clearInterval(driveInterval);
}

function pressedLeft() {
    steeringResetTimeout();
    if (isSocketOpen()) {
        steeringTimeout = setTimeout(() => {
            steeringInterval = setInterval(() => {
                left();
            }, 50);
        }, 200);
    }
}

function pressedRight() {
    steeringResetTimeout();
    if (isSocketOpen()) {
        steeringTimeout = setTimeout(() => {
            steeringInterval = setInterval(() => {
                right();
            }, 50);
        }, 200);
    }
}

function pressedForward() {
    driveResetTimeout();
    if (isSocketOpen()) {
        driveTimeout = setTimeout(() => {
            driveInterval = setInterval(() => {
                forward();
            }, 150);
        }, 200);
    }
}

function pressedBrake() {
    driveResetTimeout();
    if (isSocketOpen()) {
        driveTimeout = setTimeout(() => {
            driveInterval = setInterval(() => {
                reverse();
            }, 150);
        }, 200);
    }
}

function forward() {
    if (isSocketOpen()) {
        drive = Math.min(drive + 1, FORWARD_MAX);
    }
}

function reverse() {
    if (isSocketOpen()) {
        drive = Math.max(drive - 1, REVERSE_MAX);
    }
}

function stop() {
    steeringResetTimeout();
    driveResetTimeout();
    drive = STOP;
}

function left() {
    if (isSocketOpen()) {
        steering = Math.max(steering - 5, S_MIN);
    }
}

function right() {
    if (isSocketOpen()) {
        steering = Math.min(steering + 5, S_MAX);
    }
}

function honk() {
    if (isSocketOpen()) {
        horn = HORN_ON;
        clearTimeout(horntimeout);
        horntimeout = setTimeout(() => {
            horn = HORN_OFF;
        }, 500);
    }
}

function lightToggle() {
    if (isSocketOpen()) {
        light = light === LIGHT_OFF ? LIGHT_ON : LIGHT_OFF;
    }
}

function reset() {
    if (sendInterval !== null) {
        clearInterval(sendInterval);
        sendInterval = null;
    }
    steeringResetTimeout();
    driveResetTimeout();
    steering = S_MAX / 2;
    drive = STOP;
    horn = HORN_OFF;
    light = LIGHT_OFF;
}

async function openSocket() {
    if (!socket || (socket.readyState !== WebSocket.OPEN && socket.readyState !== WebSocket.CONNECTING)) {
        document.querySelector('.overlay_connect').style.display = 'flex';
        socket = new WebSocket('ws://192.168.4.1/ws');

        socket.onopen = function () {
            console.log('WebSocket connection opened');
            document.querySelector('.overlay_connect').style.display = 'none';
            sendInterval = setInterval(() => {
                send();
            }, WAIT_MS);
        };

        socket.onmessage = function (event) {
            const rawData = event.data;
            if (rawData.includes(';')) {
                const [rawBattery, rawMemUsed] = rawData.split(';');
                if (rawBattery && !isNaN(+rawBattery)) {
                    const batteryVoltage = (+rawBattery).toFixed(2);

                    // convert range BAT_MIN_V to BAT_MAX_V to 0-100%
                    let batteryPercentage = ((batteryVoltage - BAT_MIN_V) / (BAT_MAX_V - BAT_MIN_V)) * 100;
                    batteryPercentage = Math.max(0, Math.min(100, batteryPercentage));

                    document.getElementById('battery').innerHTML = batteryPercentage.toFixed(0);
                }

                if (rawMemUsed && !isNaN(+rawMemUsed)) {
                    const memUsed = +rawMemUsed;
                    const memTotal = 532480; // total memory in bytes
                    let memPercentage = (memUsed / memTotal) * 100;
                    memPercentage = Math.max(0, Math.min(100, memPercentage));

                    document.getElementById('memory').innerHTML = memPercentage.toFixed(0);
                }
            }
        };

        socket.onclose = function () {
            console.log('WebSocket connection closed');
            reset();
            socket = null;
        };

        socket.onerror = function (error) {
            console.log('WebSocket connection error', error);
        };
    } else {
        document.querySelector('.overlay_connect').style.display = 'none';
    }
}

function closeSocket() {
    reset();
    if (isSocketOpen()) {
        socket.send('exit');
        socket.close();
        socket = null;
    } else {
        socket = null;
    }
}

/** Send control data to server */
async function send() {
    if (isSocketOpen()) {
        try {
            socket.send(`${steering};${drive};${horn};${light}`);
            document.getElementById('status').innerHTML = 'OK';
            requestCount++;
        } catch (error) {
            document.getElementById('status').innerHTML = error.name;
        }
    } else {
        document.getElementById('status').innerHTML = 'Offline';
    }
}

async function update(event) {
    try {
        const file = event.target.files[0];

        if (file) {
            if (confirm('Are you sure you want to upload the update? The car will restart after a successful update.')) {
                document.querySelector('.overlay_update').style.display = 'flex';
                closeSocket();
                await new Promise((resolve) => setTimeout(resolve, 2000));
                const response = await fetch('http://192.168.4.1/update', {
                    method: 'POST',
                    body: file
                });

                if (response.ok) {
                    alert('Update successful! The car will restart now.');
                    setTimeout(() => {
                        window.location.reload();
                    }, 5000);
                } else {
                    throw new Error('Update failed. Please try again.');
                }
            }
        }
    } catch (error) {
        alert('Error during update: ' + error.message);
    }
}

async function downloadLog() {
    try {
        if (isSocketOpen()) {
            document.querySelector('.overlay_download').style.display = 'flex';
            closeSocket();
            await new Promise((resolve) => setTimeout(resolve, 1000));
        }
        window.open('http://192.168.4.1/log.txt', '_blank');
        window.open('http://192.168.4.1/log.old.txt', '_blank');
    } finally {
        document.querySelector('.overlay_download').style.display = 'none';
    }
}

/** Update UI periodically */
let i = 0;
setInterval(() => {
    if (++i % 10 === 0) {
        // udpate request count once every second
        document.getElementById('requestCount').innerHTML = requestCount;
        requestCount = 0;
    }
    document.getElementById('drive').value = drive + 2;
    document.getElementById('steering').value = steering;
    document.getElementById('drive_value').innerHTML = drive;
    document.getElementById('steering_value').innerHTML = steering - S_MAX / 2;
    document.getElementById('horn').style.backgroundColor = horn === HORN_ON ? 'orange' : 'lightgray';
    document.getElementById('light').style.backgroundColor = light === LIGHT_ON ? 'orange' : 'lightgray';
    document.getElementById('up').style.backgroundColor = drive > STOP ? `hsl(120, 73%, ${80 - drive * 10}%)` : 'lightgray';
    document.getElementById('brake').style.backgroundColor = drive < STOP ? `hsl(195, 53%, ${80 - Math.abs(drive) * 10}%)` : 'lightgray';
    document.getElementById('left').style.backgroundColor =
        steering < S_MAX / 2 ? `hsl(0, 0%, ${70 - Math.abs(steering - S_MAX / 2) / 2}%)` : 'lightgray';
    document.getElementById('right').style.backgroundColor =
        steering > S_MAX / 2 ? `hsl(0, 0%, ${70 - Math.abs(steering - S_MAX / 2) / 2}%)` : 'lightgray';
    document.getElementById('connect').style.display = isSocketOpen() ? 'none' : 'inline-block';
    document.getElementById('disconnect').style.display = isSocketOpen() ? 'inline-block' : 'none';
}, 100);

/** Keyboard controls */
document.getElementById('connect').addEventListener('click', openSocket);
document.getElementById('disconnect').addEventListener('click', closeSocket);
document.getElementById('light').addEventListener('click', lightToggle);
document.getElementById('horn').addEventListener('click', honk);
document.getElementById('up').addEventListener('click', forward);
document.getElementById('brake').addEventListener('click', reverse);
document.getElementById('left').addEventListener('click', left);
document.getElementById('right').addEventListener('click', right);
document.getElementById('stop').addEventListener('click', stop);

document.getElementById('up').addEventListener('pointerdown', pressedForward);
document.getElementById('brake').addEventListener('pointerdown', pressedBrake);
document.getElementById('right').addEventListener('pointerdown', pressedRight);
document.getElementById('left').addEventListener('pointerdown', pressedLeft);
document.getElementById('up').addEventListener('pointerup', driveResetTimeout);
document.getElementById('brake').addEventListener('pointerup', driveResetTimeout);
document.getElementById('right').addEventListener('pointerup', steeringResetTimeout);
document.getElementById('left').addEventListener('pointerup', steeringResetTimeout);
document.getElementById('up').addEventListener('pointerleave', driveResetTimeout);
document.getElementById('brake').addEventListener('pointerleave', driveResetTimeout);
document.getElementById('right').addEventListener('pointerleave', steeringResetTimeout);
document.getElementById('left').addEventListener('pointerleave', steeringResetTimeout);
document.getElementById('up').addEventListener('pointerout', driveResetTimeout);
document.getElementById('brake').addEventListener('pointerout', driveResetTimeout);
document.getElementById('right').addEventListener('pointerout', steeringResetTimeout);
document.getElementById('left').addEventListener('pointerout', steeringResetTimeout);
document.getElementById('up').addEventListener('pointercancel', driveResetTimeout);
document.getElementById('brake').addEventListener('pointercancel', driveResetTimeout);
document.getElementById('right').addEventListener('pointercancel', steeringResetTimeout);
document.getElementById('left').addEventListener('pointercancel', steeringResetTimeout);

document.getElementById('update').addEventListener('click', () => {
    document.getElementById('update_file').click();
});
document.getElementById('update_file').addEventListener('change', update);
document.getElementById('log').addEventListener('click', downloadLog);

window.onload = () => {
    openSocket();
};

window.onbeforeunload = () => {
    closeSocket();
};

window.onpagehide = () => {
    closeSocket();
};
