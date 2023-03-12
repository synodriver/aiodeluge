"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""
import asyncio

from aiodeluge import Client

cert = r'C:\Users\LAB\AppData\Roaming\deluge\ssl\daemon.cert'
pkey = r"C:\Users\LAB\AppData\Roaming\deluge\ssl\daemon.pkey"


async def evhandle(*args):
    print(args)

async def main():
    client = Client()  # DelugeRPCProtocol.dispatch break here
    await client.connect()
    client.timeout = 100
    print(await client.call("daemon.login", "synodriver", "123456", client_version="2.1.1"))
    print(await client.call("core.get_auth_levels_mappings"))
    print(await client.call("core.get_external_ip"))
    print(await client.call("core.get_config"))


asyncio.run(main())
