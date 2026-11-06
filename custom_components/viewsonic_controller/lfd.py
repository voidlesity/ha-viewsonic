"""Async client for the ViewSonic "LFD RS-232 & LAN Protocol" (commercial displays, TCP 5000).

Frame format (ASCII, terminated by CR):
    <length><id:2><type><command><value:3>\r
    - length: number of bytes excluding CR (8 for regular frames)
    - type:   's' set, 'g' get, 'r' get reply, '+'/'-' ack/nack

Get replies use either the short form (``801rl001``) or a 32 byte form with a
leading length of ``2`` (``201r4CDE75G3-1C      ...``) for string values.

Replies are matched on their command code and anything else is ignored, as the
display has been observed sending replies to the wrong client when several TCP
connections are open. Only one connection should be used at a time.

In standby the display closes the TCP port; it can be woken with Wake-on-LAN.
"""

import asyncio
import ipaddress
import logging
import socket

_LOGGER = logging.getLogger(__name__)

CR = b"\r"

# After an input switch the display drops/garbles the reply to the next command,
# so hold off further commands for a moment.
INPUT_SELECT = '"'
INPUT_SETTLE_TIME = 1.5


class LFDError(Exception):
    """Raised when the display can't be reached or doesn't answer."""


class LFDClient:
    def __init__(
        self, host: str, port: int = 5000, display_id: str = "01", timeout: float = 5.0
    ):
        self._host = host
        self._port = port
        self._id = display_id
        self._timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def _connect(self):
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), timeout=self._timeout
            )
        except (OSError, asyncio.TimeoutError) as err:
            self._reader = self._writer = None
            raise LFDError(
                f"Unable to connect to {self._host}:{self._port}: {err}"
            ) from err

    async def close(self):
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def _readline(self, deadline: float) -> bytes:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError
        line = await asyncio.wait_for(self._reader.readuntil(CR), timeout=remaining)
        return line[:-1]

    async def _transact(
        self, frame: bytes, is_match, is_last, settle: float = 0
    ) -> list[bytes]:
        """Send a frame and collect reply lines until ``is_last`` returns True."""
        async with self._lock:
            await self._connect()
            _LOGGER.debug("LFD send %r", frame)
            lines = []
            try:
                self._writer.write(frame + CR)
                await self._writer.drain()
                deadline = asyncio.get_running_loop().time() + self._timeout
                while True:
                    line = await self._readline(deadline)
                    _LOGGER.debug("LFD recv %r", line)
                    if not is_match(line):
                        continue
                    lines.append(line)
                    if is_last(line):
                        break
            except (asyncio.TimeoutError, asyncio.IncompleteReadError, OSError) as err:
                await self.close()
                raise LFDError(f"No valid reply to {frame!r}: {err!r}") from err
            if settle:
                await asyncio.sleep(settle)
                self._discard_buffered()
            return lines

    def _discard_buffered(self):
        """Drop any stray data the display sent that nobody asked for."""
        buffer = getattr(self._reader, "_buffer", None)
        if buffer:
            _LOGGER.debug("LFD discarding %r", bytes(buffer))
            buffer.clear()

    def _frame(self, cmd_type: str, command: str, value: str = "000") -> bytes:
        body = f"{self._id}{cmd_type}{command}{value}"
        return f"{len(body) + 1}{body}".encode("ascii")

    def _is_nack(self, line: bytes) -> bool:
        return line[1:] == f"{self._id}-".encode()

    async def set(self, command: str, value: str, cmd_type: str = "s") -> bool:
        """Send a set command. Returns True if the display acknowledged it."""
        ack = f"{self._id}+".encode()
        nack = f"{self._id}-".encode()

        def match(line):
            return line[1:] in (ack, nack)

        settle = INPUT_SETTLE_TIME if command == INPUT_SELECT else 0
        lines = await self._transact(
            self._frame(cmd_type, command, value), match, lambda _l: True, settle
        )
        return lines[-1][1:] == ack

    async def get(
        self, command: str, value: str = "000", cmd_type: str = "g"
    ) -> str | None:
        """Send a get command. Returns the reply value or None if unsupported."""
        prefix = f"{self._id}r{command}".encode()
        # Sub-item queries (e.g. date "Y00") are answered with the same leading letter
        match_prefix = prefix + value[:1].encode() if value[:1].isalpha() else prefix

        def match(line):
            return line[1:].startswith(match_prefix) or self._is_nack(line)

        lines = await self._transact(
            self._frame(cmd_type, command, value), match, lambda _l: True
        )
        line = lines[-1]
        if self._is_nack(line):
            return None
        return (
            line[1 + len(prefix) :].rstrip(b" \x00").decode("ascii", errors="replace")
        )

    async def get_inputs(self) -> dict[str, str] | None:
        """Query the available inputs (``gk``). Returns {input code: label}."""
        prefix = f"{self._id}rk".encode()
        terminator = f"8{self._id}rk".encode()

        def match(line):
            return line[1:].startswith(prefix) or self._is_nack(line)

        def last(line):
            return line.startswith(terminator) or self._is_nack(line)

        lines = await self._transact(self._frame("g", "k"), match, last)
        if self._is_nack(lines[-1]):
            return None
        inputs = {}
        for line in lines:
            if line.startswith(terminator):
                continue
            data = line[1 + len(prefix) :].decode("ascii", errors="replace")
            code, label = data[:3].upper(), data[3:].strip(" \x00")
            inputs[code] = label
        return inputs


def wake_on_lan_targets(host: str) -> list[str]:
    """Addresses to send Wake-on-LAN to.

    255.255.255.255 alone is unreliable on multi-homed hosts (it may be routed out
    of a VPN/docker interface), so also try the display's /24 broadcast and the
    display itself.
    """
    targets = ["255.255.255.255"]
    try:
        ip = ipaddress.IPv4Address(host)
    except ValueError:
        return targets
    subnet = ipaddress.IPv4Network(f"{ip}/24", strict=False)
    return targets + [str(subnet.broadcast_address), str(ip)]


def send_wake_on_lan(mac: str, targets: list[str], port: int = 9):
    """Send a Wake-on-LAN magic packet to each target address."""
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError(f"Invalid MAC address: {mac}")
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in targets:
            try:
                sock.sendto(packet, (target, port))
            except OSError as err:
                _LOGGER.debug("Wake-on-LAN to %s failed: %s", target, err)
