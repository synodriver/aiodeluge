"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""
import asyncio
import struct

# https://deluge.readthedocs.io/en/latest/reference/rpc.html
import zlib
from typing import Dict, Optional

import rencode

# log = logging.getLogger(__name__)
from loguru import logger as log

from aiodeluge import exception as error
from aiodeluge.request import DelugeRPCRequest

PROTOCOL_VERSION = 1
MESSAGE_HEADER_FORMAT = "!BI"
MESSAGE_HEADER_SIZE = struct.calcsize(MESSAGE_HEADER_FORMAT)

RPC_RESPONSE = 1
RPC_ERROR = 2
RPC_EVENT = 3


class DelugeTransferProtocol(asyncio.Protocol):
    """
    Deluge RPC wire protocol.
    Data messages are transferred with a header containing a protocol version
    and the length of the data to be transferred (payload).
    The format is::
            ubyte    uint4     bytestring
        |.version.|..size..|.....body.....|
    The version is an unsigned byte that indicates the protocol version.
    The size is a unsigned 32-bit integer that is equal to the length of the body bytestring.
    The body is the compressed rencoded byte string of the data object.
    """

    def __init__(self):
        self._buffer = bytearray()
        self._message_length = 0
        self._bytes_received = 0
        self._bytes_sent = 0
        self._drain_waiter = asyncio.Event()
        self._drain_waiter.set()
        self._lock = asyncio.Lock()
        self._close_waiter = asyncio.get_running_loop().create_future()
        self.transport: asyncio.Transport = None

    def connection_made(self, transport) -> None:
        self.transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.transport = None
        if exc is not None:
            self._close_waiter.set_exception(exc)
        else:
            self._close_waiter.set_result(None)

    def pause_writing(self) -> None:
        self._drain_waiter.clear()

    def resume_writing(self) -> None:
        self._drain_waiter.set()

    async def close(self):
        try:
            self.transport.write_eof()
        except (NotImplementedError, OSError, RuntimeError):
            pass  # Likely SSL connection
        self.transport.close()
        await self._close_waiter

    async def drain(self):
        await self._drain_waiter.wait()

    async def transfer_message(self, data):
        """
        Transfer the data.
        :param data: data to be transferred in a data structure serializable by rencode.
        """
        body = zlib.compress(rencode.dumps(data))
        body_len = len(body)
        message = struct.pack(
            f"{MESSAGE_HEADER_FORMAT}{body_len}s",
            PROTOCOL_VERSION,
            body_len,
            body,
        )
        self._bytes_sent += len(message)
        async with self._lock:  # prevent concurrent write
            self.transport.write(message)
            await self.drain()

    def data_received(self, data: bytes) -> None:  # NOQA: N802
        """
        This method is called whenever data is received.
        :param data: a message as transferred by transfer_message, or a part of such
                     a message.
        Global variables:
            _buffer         - contains the data received
            _message_length - the length of the payload of the current message.
        """
        self._buffer.extend(data)
        self._bytes_received += len(data)

        while len(self._buffer) >= MESSAGE_HEADER_SIZE:
            if self._message_length == 0:
                self._handle_new_message()
            # We have a complete packet
            if len(self._buffer) >= self._message_length:
                self._handle_complete_message(self._buffer[: self._message_length])
                # Remove message data from buffer
                # self._buffer = self._buffer[self._message_length:]
                del self._buffer[: self._message_length]
                self._message_length = 0
            else:
                break

    def _handle_new_message(self):
        """
        Handle the start of a new message. This method is called only when the
        beginning of the buffer contains data from a new message (i.e. the header).
        """
        try:
            # Read the first bytes of the message (MESSAGE_HEADER_SIZE bytes)
            header = self._buffer[:MESSAGE_HEADER_SIZE]
            # Extract the length stored as an unsigned 32-bit integer
            version, self._message_length = struct.unpack(MESSAGE_HEADER_FORMAT, header)
            if version != PROTOCOL_VERSION:
                raise Exception(
                    "Received invalid protocol version: {}. PROTOCOL_VERSION is {}.".format(
                        version, PROTOCOL_VERSION
                    )
                )
            # Remove the header from the buffer
            # self._buffer = self._buffer[MESSAGE_HEADER_SIZE:]
            del self._buffer[:MESSAGE_HEADER_SIZE]
        except Exception as ex:
            log.warning("Error occurred when parsing message header: %s.", ex)
            log.warning(
                "This version of Deluge cannot communicate with the sender of this data."
            )
            self._message_length = 0
            self._buffer.clear()

    def _handle_complete_message(self, data):
        """
        Handles a complete message as it is transferred on the network.
        :param data: a zlib compressed string encoded with rencode.
        """
        try:
            self.message_received(
                rencode.loads(zlib.decompress(data), decode_utf8=True)
            )
        except Exception as ex:
            log.warning(
                "Failed to decompress (%d bytes) and load serialized data with rencode: %s",
                len(data),
                ex,
            )

    def get_bytes_recv(self):
        """
        Returns the number of bytes received.
        :returns: the number of bytes received
        :rtype: int
        """
        return self._bytes_received

    def get_bytes_sent(self):
        """
        Returns the number of bytes sent.
        :returns: the number of bytes sent
        :rtype: int
        """
        return self._bytes_sent

    def message_received(self, message: tuple):
        """Override this method to receive the complete message"""
        pass


class DelugeRPCProtocol(DelugeTransferProtocol):
    def __init__(self, event_handlers=None):
        super().__init__()
        if event_handlers is None:
            self.event_handlers = {}
        self._waiters: Dict[int, asyncio.Future] = {}  # Dict[int, Future]
        self._tasks = set()

    def connection_made(self, transport):  # NOQA: N802
        super().connection_made(transport)

    def message_received(self, request: tuple):
        """
        This method is called whenever we receive a message from the daemon.
        :param request: a tuple that should be either a RPCResponse, RCPError or RPCSignal
        """
        if not isinstance(request, tuple):
            log.debug("Received invalid message: type is not tuple")
            return
        if len(request) < 3:
            log.debug(
                "Received invalid message: number of items in " "response is %s",
                len(request),
            )
            return

        message_type = request[0]

        if message_type == RPC_EVENT:
            event: str = request[1]
            log.debug("Received RPCEvent: %s", event)
            # A RPCEvent was received from the daemon so run any handlers
            # associated with it.
            if event in self.event_handlers:
                for handler in self.event_handlers[event]:
                    task = asyncio.create_task(handler(*request[2]))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
            return
        # now response
        request_id = request[1]

        # We get the Deferred object for this request_id to either run the
        # callbacks or the errbacks dependent on the response from the daemon.
        # d = self.factory.daemon.pop_deferred(request_id)
        waiter = self._waiters.get(request_id)

        if message_type == RPC_RESPONSE:
            # Run the callbacks registered with this Deferred object
            # d.callback(request[2])
            waiter.set_result(request[2])
        elif message_type == RPC_ERROR:
            # Recreate exception and errback'it
            try:
                exception_cls = getattr(error, request[2])
                exception = exception_cls(*request[3], **request[4])
                waiter.set_exception(exception)
            except TypeError:
                log.warning("Received invalid RPC_ERROR (Old daemon?): %s", request[2])
                return

                # Ideally we would chain the deferreds instead of instance
                # checking just to log them. But, that would mean that any
                # errback on the fist deferred should returns it's failure
                # so it could pass back to the 2nd deferred on the chain. But,
                # that does not always happen.
                # So, just do some instance checking and just log rpc error at
                # different levels.
                # r = self.__rpc_requests[request_id]
                # msg = 'RPCError Message Received!'
                # msg += '\n' + '-' * 80
                # msg += '\n' + 'RPCRequest: ' + r.__repr__()
                # msg += '\n' + '-' * 80
                # if isinstance(exception, error.WrappedException):
                #     msg += '\n' + exception.type + '\n' + exception.message + ': '
                #     msg += exception.traceback
                # else:
                #     msg += '\n' + request[5] + '\n' + request[2] + ': '
                #     msg += str(exception)
                # msg += '\n' + '-' * 80
                #
                # if not isinstance(exception, error._ClientSideRecreateError):
                #     # Let's log these as errors
                #     log.error(msg)
                # else:
                #     # The rest just gets logged in debug level, just to log
                #     # what's happening
                #     log.debug(msg)
            except Exception:
                import traceback

                log.error(
                    "Failed to handle RPC_ERROR (Old daemon?): %s\nLocal error: %s",
                    request[2],
                    traceback.format_exc(),
                )
            # d.errback(exception)

    async def send_request(self, request: DelugeRPCRequest, timeout: int = 5):
        """
        Sends a RPCRequest to the server.
        :param request: RPCRequest
        """
        try:
            # Store the DelugeRPCRequest object just in case a RPCError is sent in
            # response to this request.  We use the extra information when printing
            # out the error for debugging purposes.
            # self.__rpc_requests[request.request_id] = request
            waiter = asyncio.get_running_loop().create_future()
            self._waiters[request.request_id] = waiter
            # log.debug('Sending RPCRequest %s: %s', request.request_id, request)
            # Send the request in a tuple because multiple requests can be sent at once
            await self.transfer_message((request.format_message(),))
            return await asyncio.wait_for(waiter, timeout)
        finally:
            del self._waiters[request.request_id]

    def num_pending_tasks(self):
        return len(self._tasks)
