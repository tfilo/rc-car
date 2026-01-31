import asyncio
import gc
import os
import machine

from microdot import Microdot, send_file
from microdot.websocket import with_websocket
from time import sleep_ms
from rc_car import RcCar
from battery import Battery
from access_point import AP

try:
    # Backup old log file if exists
    os.remove("/static/log.old.txt")
    os.rename("/static/log.txt", "/static/log.old.txt")
except Exception as e:
    pass

# Redirect stdout and stderr to log file
logfile = open("/static/log.txt", "w+")
os.dupterm(logfile)

# ====== ADC BATTERY =====

battery = Battery()

voltage_history = [0] * 100
for i in range(100):
    sleep_ms(10)
    voltage_history[i] = battery.read_voltage()

# ====== CAR CONTROLS ======
rc_car = RcCar(
    motor_a_pin=14,
    motor_b_pin=15,
    steer_servo_pin=0,
    light_pin=1,
    horn_pin=16,
)

# ====== ACCESS POINT =====
AP()

# ====== SERVER ======
app = Microdot()


# Utility functions
def _safe_relpath(p: str) -> str:
    # Keep it simple: disallow absolute and traversal.
    if not p:
        return ""
    if p.startswith("/"):
        p = p[1:]
    p = p.split("?", 1)[0]
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        return ""
    return "/".join(parts)


def ensure_dir(path: str):
    # Create parent dirs progressively
    parts = [p for p in path.split("/") if p]
    cur = ""
    for p in parts:
        cur = cur + "/" + p if cur else p
        try:
            os.mkdir(cur)
        except OSError:
            pass


def read_exact(stream, n: int) -> bytes:
    out = b""
    while len(out) < n:
        chunk = stream.read(n - len(out))
        if not chunk:
            break
        out += chunk
    return out


@app.route("/", methods=["GET"])
async def index(request):
    return send_file("/static/index.html")


@app.route("/index.html", methods=["GET"])
async def index_html(request):
    return send_file("/static/index.html")


@app.route("/style.css", methods=["GET"])
async def style(request):
    return send_file("/static/style.css")


@app.route("/control.js", methods=["GET"])
async def control(request):
    return send_file("/static/control.js")


@app.route("/log.old.txt", methods=["GET"])
async def old_log(request):
    return send_file("/static/log.old.txt")


@app.route("/log.txt", methods=["GET"])
async def log(request):
    return send_file("/static/log.txt")


@app.route("/update", methods=["POST"])
async def ota_update(request):
    # Save raw request body as ota.tar.gz
    try:
        gc.collect()
        with open("ota.tar.gz", "wb") as f:
            while True:
                chunk = await request.stream.read(1024)
                if not chunk:
                    break
                f.write(chunk)
            f.flush()
            f.close()
        gc.collect()
        import gzip

        # Extract the tar.gz file
        files_extracted = 0
        with gzip.open("ota.tar.gz", "rb") as f:
            while True:
                header = f.read(512)
                if not header or len(header) < 512:
                    break

                # Check for end of archive (empty block)
                if header == b"\x00" * 512:
                    break

                # Parse TAR header
                name = header[:100].rstrip(b"\x00").decode().strip()
                size = int(header[124:136].rstrip(b"\x00 "), 8)
                file_type = header[156]

                # Type '0' (48) or \0 (0) is a normal file
                if file_type in (0, 48) and name:
                    with open(name, "wb") as out_f:
                        remaining = size
                        while remaining > 0:
                            chunk = f.read(min(remaining, 1024))
                            if not chunk:
                                break
                            out_f.write(chunk)
                            remaining -= len(chunk)
                        files_extracted += 1
                else:
                    # Skip data for directories or other types
                    remaining = size
                    while remaining > 0:
                        chunk = f.read(min(remaining, 1024))
                        remaining -= len(chunk)
                # Consume padding to align to 512-byte block
                padding = (512 - (size % 512)) % 512
                if padding:
                    f.read(padding)
        if files_extracted == 0:
            raise ValueError("Archive was empty or contained no valid files")

        sleep_ms(500)

        try:
            os.remove("ota.tar.gz")
        except Exception:
            pass

        sleep_ms(500)

        async def delayed_reset():
            await asyncio.sleep(2)
            print("Reseting pico...")
            machine.reset()

        loop = asyncio.get_event_loop()
        loop.create_task(delayed_reset())

        return {"message": "SUCCESS, Pico will reboot..."}, 200

    except Exception as e:
        print("OTA save error:", e)
        return "ERROR"


@app.route("/ws")
@with_websocket
async def web_socket(request, ws):
    try:
        counter = 0
        while True:
            message = await ws.receive()
            gc.collect()
            if message is not None:
                if message == "exit":
                    break
                match = message.split(";")
                if match is not None:
                    result = (
                        int(match[0]),
                        int(match[1]),
                        bool(int(match[2])),
                        bool(int(match[3])),
                    )
                    rc_car.update(result[0], result[1], result[2], result[3])

                counter += 1
                if counter >= 10:
                    counter = 0
                    # Send battery voltage every 10th message
                    voltage_history.pop(0)
                    voltage_history.append(battery.read_voltage())
                    voltage = sum(voltage_history) / len(voltage_history)

                    mem_used = 532480 - gc.mem_free()

                    await ws.send(str(voltage) + ";" + str(mem_used))
                else:
                    sleep_ms(10)
            else:
                break
    except asyncio.CancelledError:
        print("Client disconnected!")


try:
    app.run(port=80)
except KeyboardInterrupt:
    pass
