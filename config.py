# CONFIGURE the connection variables for controlling Kasa Smart Plugs that uses KLAP LV2 encryption.
#   Developers:  Andrew Anguish and Forrest Doddington -- version 26.3.1 (Sept 25, 2026)
#   License: see LICENSE

## This configuration file is imported into Python scripts for Kasa smart plug control:
#  * switch.py
#  * toggle.py
#  * state.py
#
# Change BC_IP to actual IP if testing from a different machine
##


# Kasa Smart Plugs access variables
K_USER = "user@email.com"    # Kasa - your real TP-Link email
K_PASS = "password"  # Kasa - your real password


# Bitfocus Companion access variables
BC_IP = "127.0.0.1"           # Bitfocus Companion IP address (localhost: 127.0.0.1)
BC_PORT = "8000"              # Bitfocus Companion server port (default: 8000)
