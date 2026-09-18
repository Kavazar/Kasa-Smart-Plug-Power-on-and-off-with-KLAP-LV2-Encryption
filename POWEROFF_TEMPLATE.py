# This is a test to turn off Kasa plugs that are using KLAP LV2 encryption

import asyncio
from kasa import Discover
from kasa.transports.klaptransport import KlapTransportV2
from kasa.protocols import IotProtocol
from kasa.iot import IotPlug

HOST = "127.0.0.1"  # Plug IP Address
USER = "username"   # your real TP-Link email
PASS = "password"   # your real password

async def main():
    disc = await Discover.discover_single(HOST, username=USER, password=PASS)
    protocol = IotProtocol(transport=KlapTransportV2(config=disc.config))
    plug = IotPlug(host=HOST, protocol=protocol)
    try:
        await plug.update()
        print(plug.alias, "power status before:", plug.is_on)

        await plug.turn_off()

        await plug.update()
        print(plug.alias, "power status after:", plug.is_on)
    finally:
        await plug.disconnect()

asyncio.run(main())
