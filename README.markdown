<h1 align="center"><i>✨ aiodeluge ✨ </i></h1>

<h3 align="center">An asyncio deluge client talk to <a href="https://github.com/deluge-torrent/deluge">deluge</a> </h3>



[![pypi](https://img.shields.io/pypi/v/aiodeluge.svg)](https://pypi.org/project/aiodeluge/)
![python](https://img.shields.io/pypi/pyversions/aiodeluge)
![implementation](https://img.shields.io/pypi/implementation/aiodeluge)
![wheel](https://img.shields.io/pypi/wheel/aiodeluge)
![license](https://img.shields.io/github/license/synodriver/aiodeluge.svg)
![action](https://img.shields.io/github/workflow/status/synodriver/aiodeluge/build%20wheel)

### Usage
```python
import asyncio

from aiodeluge import Client

async def main():
    async with Client(timeout=10) as client:
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
```

### Public api
```python
import ssl as ssl_
from typing import Callable, Dict, Optional, Union

class Client:
    host: str
    port: int
    username: str
    password: str
    event_handlers: dict
    ssl: ssl_.SSLContext
    timeout: Union[int, float]
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Optional[int] = 58846,
        username: Optional[str] = "",
        password: Optional[str] = "",
        event_handlers: Optional[Dict[str, Callable]] = None,
        ssl: Optional[ssl_.SSLContext] = None,
        timeout: Optional[Union[int, float]] = None,
    ): ...
    
    async def connect(self): ...
    async def disconnect(self): ...
    async def send_request(self, method: str, *args, **kwargs): ...
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    def __eq__(self, other: "Client"): ...

```