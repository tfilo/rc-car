/** Constants */
const HORN_OFF = 0;
const HORN_ON = 1;
const LIGHT_OFF = 0;
const LIGHT_ON = 1;
const WAIT_MS = 25;
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
let steeringTimeout = null;

function steeringResetTimeout() {
    clearTimeout(steeringTimeout);
    clearInterval(steeringInterval);
}

function pressedLeft() {
    steeringResetTimeout();
    steeringTimeout = setTimeout(() => {
        steeringInterval = setInterval(() => {
            left();
        }, 50);
    }, 200);
}

function pressedRight() {
    steeringResetTimeout();
    steeringTimeout = setTimeout(() => {
        steeringInterval = setInterval(() => {
            right();
        }, 50);
    }, 200);
}

function forward() {
    steeringResetTimeout();
    if (drive === REVERSE) {
        drive = STOP;
    } else {
        drive = Math.min(drive + 1, FORWARD_MAX);
    }
}

function reverse() {
    steeringResetTimeout();
    if (drive > STOP) {
        drive = Math.max(drive - 1, STOP);
    } else {
        drive = REVERSE;
    }
}

function stop() {
    steeringResetTimeout();
    drive = STOP;
}

function left() {
    steering = Math.max(steering - 5, S_MIN);
}

function right() {
    steering = Math.min(steering + 5, S_MAX);
}

function honk() {
    steeringResetTimeout();
    horn = HORN_ON;
    clearTimeout(horntimeout);
    horntimeout = setTimeout(() => {
        horn = HORN_OFF;
    }, 500);
}

function lightToggle() {
    steeringResetTimeout();
    light = light === LIGHT_OFF ? LIGHT_ON : LIGHT_OFF;
}

function reset() {
    steeringResetTimeout();
    steering = S_MAX / 2;
    drive = STOP;
    horn = HORN_OFF;
    light = LIGHT_OFF;
}

let socket = null;
function openSocket() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        socket = new WebSocket('ws://' + window.location.hostname + '/ws');

        socket.onopen = function () {
            document.getElementById('connect').style.display = 'none';
            send();
        };

        socket.onmessage = function (event) {
            const rawBattery = event.data;
            if (rawBattery && !isNaN(+rawBattery)) {
                const batteryVoltage = (+rawBattery).toFixed(2);
                document.getElementById('battery').innerHTML = batteryVoltage;
            }
        };

        socket.onclose = function () {
            // if socket closes, try to reconnect after a short delay
            socket = null;
            document.getElementById('connect').style.display = 'inline-block';
        };

        socket.onerror = function () {
            try {
                // on error, close the socket to trigger reconnect
                socket.close();
            } catch (e) {}
        };
    }
}

/** Send control data to server */
async function send() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        try {
            socket.send(`steering=${steering}&drive=${drive}&horn=${horn}&light=${light}`);
            document.getElementById('status').innerHTML = 'OK';
            lastSuccessfullApiCall = Date.now();
        } catch (error) {
            document.getElementById('status').innerHTML = error.name;
        } finally {
            requestCount++;
            setTimeout(() => {
                send();
            }, WAIT_MS);
        }
    } else {
        document.getElementById('status').innerHTML = 'Offline';
        document.getElementById('connect').style.display = 'inline-block';
    }
}

/** Update UI periodically */
setInterval(() => {
    document.getElementById('requestCount').innerHTML = requestCount;
    requestCount = 0;
    if (!socket || socket.readyState === WebSocket.CLOSED) {
        document.getElementById('connect').style.display = 'inline-block';
    }
}, 1000);

setInterval(() => {
    if (Date.now() - lastSuccessfullApiCall > 1000) {
        reset();
    }
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
document.getElementById('connect').addEventListener('click', openSocket);
document.getElementById('light').addEventListener('click', lightToggle);
document.getElementById('horn').addEventListener('click', honk);
document.getElementById('up').addEventListener('click', forward);
document.getElementById('brake').addEventListener('click', reverse);
document.getElementById('left').addEventListener('click', left);
document.getElementById('right').addEventListener('click', right);
document.getElementById('stop').addEventListener('click', stop);

document.getElementById('right').addEventListener('pointerdown', pressedRight);
document.getElementById('left').addEventListener('pointerdown', pressedLeft);
document.getElementById('right').addEventListener('pointerup', steeringResetTimeout);
document.getElementById('left').addEventListener('pointerup', steeringResetTimeout);
document.getElementById('right').addEventListener('pointerleave', steeringResetTimeout);
document.getElementById('left').addEventListener('pointerleave', steeringResetTimeout);
document.getElementById('right').addEventListener('pointerout', steeringResetTimeout);
document.getElementById('left').addEventListener('pointerout', steeringResetTimeout);
document.getElementById('right').addEventListener('pointercancel', steeringResetTimeout);
document.getElementById('left').addEventListener('pointercancel', steeringResetTimeout);

document.getElementById('update').addEventListener('click', () => {
    document.getElementById('autoupdate').click();
});

document.getElementById('autoupdate').addEventListener('change', async (event) => {
    const file = event.target.files[0];

    if (file) {
        if (confirm('Are you sure you want to upload the update? The car will restart after a successful update.')) {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send('exit');
                socket.close();
                socket = null;
                await new Promise((resolve) => setTimeout(resolve, 2000));
            }
            fetch('/update', {
                method: 'POST',
                body: file
            })
                .then((response) => {
                    if (response.ok) {
                        alert('Update successful! The car will restart now.');
                        setTimeout(() => {
                            window.location.reload();
                        }, 5000);
                    } else {
                        alert('Update failed. Please try again.');
                    }
                })
                .catch((error) => {
                    alert('Error during update: ' + error.message);
                });
        }
    }
});
