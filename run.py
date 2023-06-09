"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""
import asyncio

from aiodeluge import Client

# cert = r'C:\Users\LAB\AppData\Roaming\deluge\ssl\daemon.cert'
# pkey = r"C:\Users\LAB\AppData\Roaming\deluge\ssl\daemon.pkey"


async def evhandle(*args):
    print(args)


async def main():
    async with Client(timeout=10) as client:  # DelugeRPCProtocol.dispatch break here
        print(
            await client.send_request(
                "daemon.login", "synodriver", "123456", client_version="2.1.1"
            )
        )
        print(await client.send_request("core.get_auth_levels_mappings"))
        print(await client.send_request("core.get_external_ip"))
        print(await client.send_request("core.get_config"))


if __name__ == "__main__":
    asyncio.run(main())
