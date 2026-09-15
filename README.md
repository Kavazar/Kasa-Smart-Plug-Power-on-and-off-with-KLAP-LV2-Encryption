# Kasa-Smart-Plug-Power-on-and-off-with-KLAP-LV2-Encryption
These are short python programs to turn on Kasa plugs using KLAP LV2 encryption. 


# Kasa Plug Control

A small Python utility for turning TP-Link Kasa smart plugs on and off over the local
network, without going through the Kasa mobile app or TP-Link's cloud.

The script targets a single plug by IP address, authenticates locally, reports the
plug's current state, switches it, and confirms the new state before exiting.

---

## Why this exists

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

macOS ships with a system Python that should not be used for installing packages.
Install your own. Either option below works.

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

**Fedora / RHEL:**

```bash
sudo dnf install python3 python3-pip
```

**Arch:**

```bash
sudo pacman -S python python-pip
```

Verify:

```bash
python3 --version
```

---

## Installation

### Using a virtual environment (recommended)

A venv keeps this project's dependencies isolated and avoids the
"externally-managed-environment" error that newer Debian/Ubuntu and Homebrew Pythons
raise on global installs.

```bash
cd /path/to/Random_Project

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install python-kasa
```

Your prompt will show `(.venv)` while the environment is active. Run `deactivate` to
exit it. You will need to re-run `source .venv/bin/activate` in each new terminal
session.

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

To populate KLAP aliases, pass credentials:

```bash
kasa --username "you@example.com" --password "yourpassword" discover
```

Identifying which physical plug is which **before** switching anything is worth the
extra step if the plugs control equipment that matters.

---

## Configuration

Set your credentials as environment variables rather than hardcoding them:

```bash
export KASA_USERNAME='you@example.com'
export KASA_PASSWORD='yourpassword'
export KASA_HOST='192.168.171.12'
```

Using single quotes prevents the shell from interpreting `$`, `!`, and backslashes in
your password. To make these persistent, add them to `~/.zshrc` (macOS default) or
`~/.bashrc` (most Linux shells).

To confirm the shell passed the value through intact:

```bash
python3 -c "import os; print(repr(os.environ.get('KASA_PASSWORD')))"
```

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

## Troubleshooting

### `ECONNREFUSED` on port 9999

The plug is reachable but nothing is listening on 9999. Almost always means the plug
has migrated to KLAP. Confirm with `kasa discover list` and check the ENCRYPT column.

A legacy XOR client (including the Node `tplink-smarthome-api` library) cannot talk to
a KLAP device at all — this is not fixable in the client code.

### `No route to host` / intermittent failures

The plug is offline or has dropped off Wi-Fi. Check with `ping`:

```bash
ping 192.168.171.12
```

Watch the first few replies. Times that decrease by roughly 1000ms each
(`7188ms, 6182ms, 5176ms...`) mean the packets were queued while the device was
unreachable and answered in a burst when it came back — the device was down, not slow.

Persistent latency above ~50ms on a LAN, or any packet loss, indicates a Wi-Fi problem.
Check signal strength via `kasa --host <ip> state` (the `RSSI` field). Anything worse
than about -70 dBm is weak. Metal racks and crowded 2.4GHz channels are common causes.

### `Device response did not match our challenge`

KLAP authentication failed. In order of likelihood:

1. **Login version 2 transport bug.** If `kasa discover list` shows `LV 2`, the CLI
   selects the wrong transport. This script's forced `KlapTransportV2` is the
   workaround. The plain `kasa` CLI will keep failing even with correct credentials.
2. **Account password changed after provisioning.** The plug still holds a hash of the
   old password. Try the password that was current when the plug was first set up.
3. **Wrong account.** KLAP validates against the account that *provisioned* the device.
   A plug set up on someone else's account and then shared to yours will fail, even
   though the app works fine. Check device ownership in the Kasa app.
4. **Email case mismatch.** The comparison is case-sensitive. Copy the address verbatim
   from your TP-Link account page.
5. **Firmware regression.** Some recent firmware builds fail KLAP auth even with
   confirmed-correct credentials and after a factory reset. See
   [python-kasa issue #1754](https://github.com/python-kasa/python-kasa/issues/1754).
   If you're here, no client-side fix currently exists.

Empty credentials (`--username "" --password ""`) failing is **not** diagnostic — they
fail on every KLAP device regardless of the underlying cause.

Note also that a successful `kasa --username "" --password "" state` against an XOR
plug proves nothing about your credentials, because XOR does not authenticate.

### `Unclosed client session` warnings

Cosmetic, caused by an exception skipping the `disconnect()` call. The script's
`try/finally` handles this. The warnings do not indicate a separate problem.

### `SyntaxError: invalid syntax` on a pip command

You're at the Python REPL (prompt shows `>>>`), not the shell. Type `exit()` first.

### `externally-managed-environment` error

Newer Debian/Ubuntu and Homebrew Pythons block global pip installs. Use a virtual
environment as described above.

---

## Operational notes

**Firmware migration is one-way.** Once a plug moves to KLAP it cannot be reverted, and
its legacy port 9999 access is gone permanently. There is no supported firmware
downgrade path.

**Adding a new device can migrate your whole fleet.** There are documented cases of the
Kasa app detecting new firmware when a device is added and updating every matching
device on the account. If you depend on XOR plugs, be deliberate about adding hardware.

**Blocking WAN access protects legacy plugs.** Since KLAP authenticates locally, denying
the plugs outbound internet access at the router or firewall prevents firmware updates
without breaking local control. This is the only reliable way to keep an XOR plug on
XOR.

**Use DHCP reservations.** Hardcoded IPs plus dynamic leases produce connection failures
that look like protocol problems but are just the device moving. Reserve by MAC.

**Handle transient failures in any long-running integration.** Treat `ECONNREFUSED` and
`EHOSTUNREACH` as recoverable, reconnect with exponential backoff, and never let a
momentary Wi-Fi dropout terminate the controlling process.

---

## Calling this from another language

`python-kasa` is the best-maintained KLAP implementation; equivalents in other
ecosystems generally lag behind or don't support KLAP at all. The Node library
`tplink-smarthome-api` is XOR-only and has not seen a release in roughly three years.

For non-Python projects, the practical approach is a small local HTTP service wrapping
this logic — exposing something like `/plug/<ip>/on`, `/off`, and `/state` on localhost —
and calling that. This keeps connections warm, keeps protocol handling in one place, and
insulates the rest of your stack from future protocol changes.

---

## References

- [python-kasa](https://github.com/python-kasa/python-kasa) — library and CLI
- [python-kasa supported devices](https://github.com/python-kasa/python-kasa/blob/master/SUPPORTED.md)
- [Issue #1648](https://github.com/python-kasa/python-kasa/issues/1648) — LV2 transport selection
- [Issue #1754](https://github.com/python-kasa/python-kasa/issues/1754) — firmware auth regression
