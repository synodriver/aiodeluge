"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""
import asyncio
import ssl as ssl_

from aiodeluge.protocol import DelugeRPCProtocol
from aiodeluge.request import DelugeRPCRequest


class Client:
    def __init__(self, host: str = "127.0.0.1", port: int = 58846, username='',
                 password='', event_handlers=None, ssl=None, timeout = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        if ssl is None:
            sslcontext = ssl_.SSLContext(ssl_.PROTOCOL_TLS_CLIENT)
            sslcontext.options |= ssl_.OP_NO_SSLv2
            sslcontext.options |= ssl_.OP_NO_SSLv3
            sslcontext.check_hostname = False
            sslcontext.verify_mode = ssl_.CERT_NONE
            sslcontext.set_default_verify_paths()
            self.ssl = sslcontext
        else:
            self.ssl = ssl
        if event_handlers is None:
            self.event_handlers = {}
        self._loop = asyncio.get_running_loop()
        self._protocol: DelugeRPCProtocol = None
        self.connected: bool = False
        self._request_counter = 0
        if timeout is None:
            self._timeout = 5
        else:
            self._timeout = timeout

    async def connect(self):
        if not self._protocol and not self.connected:
            _, protocol = await self._loop.create_connection(lambda: DelugeRPCProtocol(self.event_handlers),
                                                             self.host, self.port, ssl=self.ssl)
            self._protocol = protocol
            self.connected = True

    async def disconnect(self):
        await self._protocol.close()
        self.connected = False
        self._protocol = None

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, v):
        self._timeout = v

    async def call(self, method: str, *args, **kwargs):
        try:
            request = DelugeRPCRequest()
            request.request_id = self._request_counter
            request.method = method
            request.args = args
            request.kwargs = kwargs
            return await self._protocol.send_request(request, self.timeout)
        finally:
            self._request_counter += 1