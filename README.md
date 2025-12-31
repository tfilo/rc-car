# RC-Car (Wi‑Fi AP Controller)

Simple RcCar created from Raspberry Pi Zero 2W. After power up it creates a Wi‑Fi Access Point (AP). After connecting to it you have the controller available at `http://192.168.4.1`.

![Controller screenshot](assets/controller.png)

## How it works

- The device starts in AP mode with SSID/password defined in `main.py`.
- A small HTTP server serves the controller UI (from `index.html`).
- The web UI sends control updates (steering/drive/horn) via HTTP requests.

## Files

- `main.py` — main firmware logic (AP + HTTP server + motor/servo control).
- `index.html` — controller web UI.
- `assets/controller.png` — screenshot used above.

## Usage

1. Flash MicroPython to the board.
2. Copy `main.py` and `index.html` to the device filesystem.
3. Power up the car.
4. On your phone/PC, connect to the Wi‑Fi AP (SSID: `RcCar`).
5. Open `http://192.168.4.1` in a browser.

## Development (UI)

- Run `npm run serve` to serve the UI locally in your browser for easier development.
- Run `npm run build` to generate a minified `index.min.html`.
	- The minified file is smaller, so it’s better to copy it to the Pico.
	- Easiest workflow: build locally, then copy `index.min.html` to the Pico *as* `index.html` (overwrite the old one).

## Notes

- If you change SSID/password or control mapping, edit `main.py`.
- The controller UI is designed for mobile and uses touch buttons.
