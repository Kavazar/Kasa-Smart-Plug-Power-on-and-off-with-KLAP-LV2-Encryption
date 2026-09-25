# Kasa-Smart-Plug-Power-on-and-off-with-KLAP-LV2-Encryption

Python scripts for turning TP-Link Kasa smart plugs on and off over the local network,
without going through the Kasa mobile app or TP-Link's cloud. They are built to be
triggered from [Bitfocus Companion](https://bitfocus.io/companion) buttons.

Each script targets a single plug by IP address, authenticates locally, reads the plug's
current state, acts on it, confirms the result, and writes the plug's final state (`On`
or `Off`) to a Companion custom variable so your buttons can show it.

**Version 26.3.1** (September 25, 2026) · Andrew Anguish and Forrest Doddington · [MIT License](LICENSE)

---

## What's included

| File | What it does |
|---|---|
| `switch.py` | Turns a plug on or off (`--mode on` or `--mode off`) |
| `toggle.py` | Flips a plug to the opposite of its current state |
| `state.py` | Reads a plug's state without changing it |
| `config.py` | Shared settings: TP-Link credentials and the Companion address |
| `LICENSE` | MIT License |

All three scripts import `config.py`, so keep these files together in one folder.

---

## Why this exists

I was trying to turn Kasa smart plugs on and off with the
[companion-module-tplink-kasasmartplug](https://github.com/bitfocus/companion-module-tplink-kasasmartplug),
which has not been updated in two years. It worked fine until a recent Kasa firmware update
changed the encryption method from XOR to KLAP. I wrote these scripts so I could control
the KLAP LV2 encrypted plugs with short Python scripts, which I can then trigger from
Companion using its internal **Run shell command** action, with the plug's state sent
back to Companion for button feedback.

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
work with these scripts.

### Login version 2

Some KLAP devices report `login_version: 2` and require a different transport class
(`KlapTransportV2`) than the one python-kasa selects automatically. These scripts force
the V2 transport explicitly, which works around
[python-kasa issue #1648](https://github.com/python-kasa/python-kasa/issues/1648).

---

## Requirements

- Python 3.11 or newer
- [`python-kasa`](https://github.com/python-kasa/python-kasa) 0.10.2 or newer
- [`requests`](https://pypi.org/project/requests/) (sends the plug state to Companion;
  python-kasa does not install it for you)
- Bitfocus Companion 3.2 or newer (the scripts use its HTTP API to set custom variables)
- A TP-Link account that **owns** the plug (a shared/guest account will not authenticate)
- The plug and the machine running the scripts on the same LAN

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

### 1. Put the files in one folder

For example `~/Documents/Kasa_Plug_Control/`. The examples in this README use that
path.

### 2. Create a virtual environment and install the libraries

```bash
python3 -m venv ~/kasa-env
~/kasa-env/bin/python -m pip install python-kasa requests
```

A virtual environment is the recommended route. Homebrew Python and recent
Debian/Ubuntu releases refuse system-wide `pip install` with an
`externally-managed-environment` error, and a venv gives Companion one fixed
interpreter path to call.

### 3. Verify the install

```bash
~/kasa-env/bin/kasa --version
~/kasa-env/bin/python -c "import kasa, requests; print(kasa.__file__)"
```

The second command prints where python-kasa is installed. If you later get
`ModuleNotFoundError`, the interpreter running the script isn't the one that has the
libraries.

---

## Configuration

Edit `config.py`:

| Setting | Meaning |
|---|---|
| `K_USER` | Email address of the TP-Link account that owns the plugs |
| `K_PASS` | Password for that account |
| `BC_IP` | IP address of the machine running Companion. Leave as `127.0.0.1` when the scripts run on the same machine as Companion (the normal case when Companion launches them). Change it if you're testing from a different machine. |
| `BC_PORT` | Companion's web interface port (default `8000`) |

`config.py` stores your TP-Link password in plain text. Restrict who can read it:

```bash
chmod 600 ~/Documents/Kasa_Plug_Control/config.py
```

and don't commit a copy with your real credentials to a public repository.

---

## Finding your plugs

Before running the scripts, confirm which devices exist and which protocol each uses:

```bash
~/kasa-env/bin/kasa discover list
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

Because the scripts address plugs by IP, give each plug a DHCP reservation in your
router so its address doesn't change.

Identifying which physical plug is which **before** switching anything is worth the
extra step if the plugs control equipment that matters.

---

## Setting up Companion

### Create a custom variable for each plug

In Companion's **Variables** page, add a custom variable for each plug, for example
`Stage_TV_Kasa_State`. The scripts update an existing variable; they don't create one.
If the name passed with `--var` doesn't match an existing custom variable exactly,
Companion rejects the update with a 404.

### Check the HTTP API is enabled

The scripts send the plug state to Companion with an HTTP request to:

```
POST http://<BC_IP>:<BC_PORT>/api/custom-variable/<name>/value?value=<On|Off>
```

The HTTP API is on by default. If it has been turned off, turn on **Settings →
Protocols → HTTP API**.

### Companion 5.0 and later: allow shell commands

Companion 5.0 disables shell commands by default, and the scripts are launched with a
shell command. Until you turn this on, pressing the button does nothing.

- **Desktop install:** in the Companion launcher, click the cog in the top right corner,
  open **Dangerous Features**, and tick **Shell command support**. Companion restarts
  when you change it.
- **Headless install:** start Companion with `--enable-shell-command-support`, or set
  the `COMPANION_ENABLE_SHELL_COMMAND_SUPPORT` environment variable.

---

## Usage

Every script requires:

| Parameter | Meaning |
|---|---|
| `--ip` | IP address of the Kasa plug |
| `--var` | Name of the Companion custom variable that receives the plug's state |

`switch.py` also requires `--mode`.

### switch.py — turn a plug on or off

```bash
~/kasa-env/bin/python ~/Documents/Kasa_Plug_Control/switch.py --ip 192.168.169.234 --var Stage_TV_Kasa_State --mode on
```

Output:

```
Kasa SWITCH 'on' called. Power changed from 'Off' to 'On'. Updated custom variable 'Stage_TV_Kasa_State' in Bitfocus Companion.'
```

Use `--mode off` to turn the plug off. The mode is case-sensitive: only lowercase `on`
and `off` are accepted. Any other value leaves the plug as it is, still updates the
custom variable with the plug's current state, and prints:

```
Kasa Control SWITCH called with invalid --mode parameter: ON. (Valid options are 'on' or 'off'.) Toggle not performed and plug remains in power state 'Off'.
```

### toggle.py — flip the current state

```bash
~/kasa-env/bin/python ~/Documents/Kasa_Plug_Control/toggle.py --ip 192.168.169.234 --var Stage_TV_Kasa_State
```

If the plug is off, it turns on; otherwise it turns off.

```
Kasa TOGGLE called. Power changed from 'Off' to 'On'. Updated custom variable 'Stage_TV_Kasa_State' in Bitfocus Companion.'
```

### state.py — read the state without changing it

```bash
~/kasa-env/bin/python ~/Documents/Kasa_Plug_Control/state.py --ip 192.168.169.234 --var Stage_TV_Kasa_State
```

```
Kasa STATE called. The power state of the Kasa plug is 'On'. Updated custom variable 'Stage_TV_Kasa_State' in Bitfocus Companion.'
```

### What each run does

1. Discovers the plug at `--ip` and authenticates with KLAP, forcing the V2 transport.
2. Reads the plug's current state.
3. For `switch.py` and `toggle.py`: sends the on/off command, then reads the state again.
4. Sends the confirmed state (`On` or `Off`) to the Companion custom variable named by `--var`.
5. Prints a one-line summary and disconnects from the plug.

The second read in step 3 is deliberate — `turn_on()` sends the command but does not
refresh the cached local state, so reading again afterward is the only way to know the
plug actually switched rather than merely accepting the command. The value sent to
Companion is always the state read back from the plug.

---

## Running from a Bitfocus Companion button

### Add the shell command action

1. Open your Companion admin UI.
2. Click the button you want to configure.
3. In the **Press actions** block, add the internal action **System: Run shell command
   (local)**. In Companion 4.2 and earlier it is called **System: Run shell path
   (local)**. Searching for "shell" finds it.
4. In the **Command** field (**Path** in older versions), enter the full path to the
   venv's Python followed by the full path to the script and its parameters.

**macOS example:**

```
/Users/YourName/kasa-env/bin/python /Users/YourName/Documents/Kasa_Plug_Control/switch.py --ip 192.168.169.234 --var Stage_TV_Kasa_State --mode on
```

**Linux example:**

```
/home/yourname/kasa-env/bin/python /home/yourname/Documents/Kasa_Plug_Control/toggle.py --ip 192.168.169.234 --var Stage_TV_Kasa_State
```

Always wrap paths in quotation marks if they contain spaces.

Absolute paths are the safest choice. `~` also works, because Companion runs the
command through a shell, but it expands to the home folder of whichever user runs
Companion. On a headless install that runs Companion under its own account, that is not
your home folder, and that account also needs permission to read the scripts and the
venv.

The action's **Timeout** defaults to 5000 ms, and Companion stops the script if it runs
longer. Raise it if a plug on a busy network sometimes takes longer to respond.

### Use the right Python interpreter

`/usr/bin/python3` is the operating system's Python, and `python-kasa` will almost
certainly not be installed there. Using it produces
`ModuleNotFoundError: No module named 'kasa'` when the button is pressed, even though
the script runs fine from your terminal. Point Companion at the venv's interpreter,
`~/kasa-env/bin/python`, written as a full path.

If you installed the libraries without a venv, this prints the interpreter that has
them:

```bash
python3 -c "import kasa, requests, sys; print(sys.executable)"
```

### Example button layout

Because the scripts take parameters, one set of scripts serves every plug:

| Button | Command |
|---|---|
| Stage TV On | `…/switch.py --ip 192.168.169.234 --var Stage_TV_Kasa_State --mode on` |
| Stage TV Off | `…/switch.py --ip 192.168.169.234 --var Stage_TV_Kasa_State --mode off` |
| Stage TV Toggle | `…/toggle.py --ip 192.168.169.234 --var Stage_TV_Kasa_State` |

### Show the plug's state on a button

- Put `$(custom:Stage_TV_Kasa_State)` in the button text to display `On` or `Off`.
- Add the internal **Variable: Check value** feedback, set to the custom variable and
  the value `On`, to change the button's color while the plug is on.

The variable only changes when one of the scripts runs. If the plug might also be
switched from the Kasa app or its physical button, run `state.py` from a Companion
trigger (for example on **Startup**, or on a fixed time interval) to keep the button
accurate.

---

## Troubleshooting

When a shell command fails, Companion's **Log** page shows a "Shell command failed"
entry that includes the script's error output.

| Symptom | Cause and fix |
|---|---|
| Button does nothing; the log says the shell command was rejected | Companion 5.0+ with shell commands disabled. See [Companion 5.0 and later](#companion-50-and-later-allow-shell-commands). |
| `ModuleNotFoundError: No module named 'kasa'` (or `'requests'`) | Wrong interpreter. Use the venv's full path. |
| `ModuleNotFoundError: No module named 'config'` | `config.py` isn't in the same folder as the script. |
| `TimeoutError: Timed out getting discovery response for <ip>` | The plug didn't answer: wrong IP, plug offline or unplugged, or the network blocks traffic between the machine and the plug. |
| Authentication error | `K_USER`/`K_PASS` are wrong, or the account doesn't own the plug. |
| `Failed. Status code: 404, Response: Not found` | The `--var` name doesn't match an existing Companion custom variable. Create it or fix the spelling. The plug was still switched. |
| `Failed. Status code: 403, …` | Companion's HTTP API is turned off. Enable **Settings → Protocols → HTTP API**. |
| Traceback ending in `NameError: name 'request' is not defined` | The script couldn't reach Companion at `BC_IP`:`BC_PORT` (Companion not running, wrong address, or wrong port). The plug was still switched, but the custom variable wasn't updated. Check `config.py`. |

---

## Related library calls

For anyone modifying the scripts:

| Call | Effect |
|---|---|
| `await plug.turn_on()` | Switch on |
| `await plug.turn_off()` | Switch off |
| `await plug.set_state(True)` | Switch to a variable state |
| `await plug.update()` | Refresh cached state from the device |
| `plug.is_on` | Current state (from last `update()`) |
| `plug.alias` | Device name as set in the Kasa app |

---

## References

- [python-kasa](https://github.com/python-kasa/python-kasa) — library and CLI
- [python-kasa supported devices](https://github.com/python-kasa/python-kasa/blob/master/SUPPORTED.md)
- [python-kasa issue #1648](https://github.com/python-kasa/python-kasa/issues/1648) — LV2 transport selection
- [Companion HTTP Remote Control](https://companion.free/user-guide/v5.0/remote-control/http-remote-control) — custom variable API
- [Kasa Smart Plug Companion Module](https://github.com/bitfocus/companion-module-tplink-kasasmartplug)

---

## License

MIT License, Copyright (c) 2026 Andrew Anguish. See [LICENSE](LICENSE).
