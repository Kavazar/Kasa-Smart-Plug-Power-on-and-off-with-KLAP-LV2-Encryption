# Kasa-Smart-Plug-Power-on-and-off-with-KLAP-LV2-Encryption

A small Python utility for turning TP-Link Kasa smart plugs on and off over the local
network, without going through the Kasa mobile app or TP-Link's cloud.

The script targets a single plug by IP address, authenticates locally, reports the
plug's current state, switches it, and confirms the new state before exiting.

---

## Why this exists

I was trying to turn Kasa smart plugs on and off with
[companion-module-tplink-kasasmartplug](https://github.com/bitfocus/companion-module-tplink-kasasmartplug),
which has not been updated in two years. It worked fine until a recent firmware update
changed the encryption method from XOR to KLAP. I wrote this program so I could control
the KLAP LV2 encrypted plugs with a short Python script, which I can then trigger from
Companion using its internal **Run shell command** action.

Older Kasa firmware exposed a simple, unauthenticated control protocol on **TCP port
9999**. Nearly every third-party Kasa project was built on it. TP-Link has been
progressively disabling that port through firmware updates and replacing it with
**KLAP** (Kasa Local Authentication Protocol) over **HTTP port 80**, which requires
your TP-Link account credentials.

Both protocols are still in the wild, often on identical hardware, because the
migration happens per-device as firmware rolls out. A fleet of identical plugs can be
split across both.

| | Legacy | Current |
|---|---|---|
| Port | TCP 9999 | HTTP 80 |
| Encryption | XOR autokey cipher (key 171) | KLAP (AES + auth) |
| Credentials | None | TP-Link account email + password |
| Status | Being phased out | Active |

**XOR is still in use on plugs running older firmware.** It performs no authentication
at all, which is why older tools never needed credentials.

**KLAP authentication is entirely local.** Your credentials are hashed and compared
against hashes the plug stored when it was first provisioned. No cloud round-trip
happens at control time, so plugs can be firewalled off from the internet and still
work with this script.

### Login version 2

Some KLAP devices report `login_version: 2` and require a different transport class
(`KlapTransportV2`) than the one python-kasa selects automatically. This script forces
the V2 transport explicitly, which works around
[python-kasa issue #1648](https://github.com/python-kasa/python-kasa/issues/1648).

---

## Requirements

- Python 3.11 or newer
- [`python-kasa`](https://github.com/python-kasa/python-kasa) 0.10.2 or newer
- A TP-Link account that **owns** the plug (a shared/guest account will not authenticate)
- The plug and the machine running the script on the same LAN

---

## Setting up Python on macOS

### Option A — Homebrew (recommended)

Install Homebrew if you don't have it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the post-install instructions it prints — on Apple Silicon it will ask you to
add `/opt/homebrew/bin` to your PATH.

Then:

```bash
brew install python
python3 --version
```

### Option B — python.org installer

Download the macOS installer from <https://www.python.org/downloads/macos/> and run it.
This installs to `/Library/Frameworks/Python.framework/Versions/<X.Y>/` and adds
`python3` and `pip3` to your PATH.

### Note on `pip`

On many macOS setups the bare `pip` command does not exist — only `pip3`. If you hit
`zsh: command not found: pip`, use:

```bash
python3 -m pip install <package>
```

This form always works because it invokes pip through the same interpreter that will
run your script, which avoids installing into the wrong Python.

---

## Setting up Python on Linux

Most distributions include a suitable Python 3. Install pip and venv support if needed.

**Debian / Ubuntu:**

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Verify:

```bash
python3 --version
```

---

## Installation

### Without a virtual environment

```bash
python3 -m pip install --user python-kasa
```

### Verify the install

```bash
kasa --version
python3 -c "import kasa; print(kasa.__file__)"
```

The second command prints the install location. If you later get `ModuleNotFoundError`
despite a successful install, compare this path against the interpreter running your
script — a mismatch means they are different Pythons.

---

## Finding your plugs

Before running the script, confirm which devices exist and which protocol each uses:

```bash
kasa discover list
```

Example output:

```
HOST            MODEL   DEVICE FAMILY        ENCRYPT HTTPS LV  ALIAS
192.168.170.18  HS103   IOT.SMARTPLUGSWITCH  KLAP    0     2   - Authentication failed
192.168.170.88  HS103   IOT.SMARTPLUGSWITCH  XOR     0     -   Robot
```

Reading the columns:

- **ENCRYPT** — `XOR` for legacy plugs, `KLAP` for migrated ones.
- **LV** — login version. `2` means the V2 transport is required.
- **ALIAS** — blank with "Authentication failed" on KLAP devices until you supply
  credentials. XOR devices show their alias unauthenticated because they don't verify
  anything.

Identifying which physical plug is which **before** switching anything is worth the
extra step if the plugs control equipment that matters.

---

## Usage

```bash
python3 POWERON_kasa_plug_test.py
```

Expected output:

```
Projector BMD Converters before: False
Projector BMD Converters after: True
```

The script reads state, switches the plug, then re-reads state. The second read is
deliberate — `turn_on()` sends the command but does not refresh the cached local state,
so confirming afterward is the only way to know the plug actually switched rather than
merely accepting the command.

### Related library calls

| Call | Effect |
|---|---|
| `await plug.turn_on()` | Switch on |
| `await plug.turn_off()` | Switch off |
| `await plug.set_state(True)` | Switch to a variable state |
| `await plug.update()` | Refresh cached state from the device |
| `plug.is_on` | Current state (from last `update()`) |
| `plug.alias` | Device name as set in the Kasa app |

---

## Running from a Bitfocus Companion button

Companion has no built-in text editor for writing Python inside a button, so the
standard approach is to use a shell execution action that targets your local Python
interpreter and this script.

### Using the core "System: Run shell command" action

Companion ships with a built-in shell utility that can trigger local files.

1. Open your Companion admin UI.
2. Click the button you want to configure.
3. In the **KeyDown actions** block, search for and add **System: Run shell command**
   (sometimes listed as `internal: Run shell command`).
4. In the command text box, provide the **absolute path** to both your Python
   executable and your script.

**macOS / Linux example:**

```
/usr/bin/python3 /Users/YourName/Scripts/my_script.py
```

**Windows example:**

```
"C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe" "C:\Scripts\my_script.py"
```

Always wrap paths in quotation marks if they contain spaces.

### Use the right Python interpreter

The `/usr/bin/python3` shown above is macOS's **system** Python, and `python-kasa` will
almost certainly not be installed there. Using it produces
`ModuleNotFoundError: No module named 'kasa'` when the button is pressed, even though
the script runs fine from your terminal.

Find the interpreter that actually has the library:

```bash
which python3
python3 -c "import kasa; print(kasa.__file__)"
```

Typical results:

| Install method | Interpreter path |
|---|---|
| Homebrew (Apple Silicon) | `/opt/homebrew/bin/python3` |
| Homebrew (Intel) | `/usr/local/bin/python3` |
| python.org | `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` |
| Virtual environment | `/path/to/project/.venv/bin/python3` |

Use that full path in the Companion action:

```
/opt/homebrew/bin/python3 /Users/YourName/Scripts/POWERON_kasa_plug_test.py
```

### One script per button

Companion buttons are simplest when each one does a single thing. Keep separate
scripts — for example `POWERON_kasa_plug.py` and `POWEROFF_kasa_plug.py` — and point
one button at each, rather than passing arguments.

---

## References

- [python-kasa](https://github.com/python-kasa/python-kasa) — library and CLI
- [python-kasa supported devices](https://github.com/python-kasa/python-kasa/blob/master/SUPPORTED.md)
- [python-kasa issue #1648](https://github.com/python-kasa/python-kasa/issues/1648) — LV2 transport selection
- [Kasa Smart Plug Companion Module](https://github.com/bitfocus/companion-module-tplink-kasasmartplug)
