import asyncio
import ssl


class Connection:
    """A TCP connection over the IRC protocol."""

    CONNECT_TIMEOUT = 10
    MAX_LEN = 451

    def __init__(self, hostname, port, useSSL, eventloop=None):
        self.hostname = hostname
        self.port = port
        self.ssl = useSSL

        self.reader = None
        self.writer = None
        self.eventloop = eventloop or asyncio.new_event_loop()

    async def connect(self):
        """Connect to target."""

        if self.ssl:
            ssl_context = ssl.create_default_context()

        (self.reader, self.writer) = await asyncio.open_connection(
            host=self.hostname,
            port=self.port,
            ssl=self.ssl,
        )

    async def disconnect(self):
        """Disconnect from target."""
        if not self.connected:
            return

        self.writer.close()
        self.reader = None
        self.writer = None
        self.stop()

    @property
    def connected(self):
        """Whether this connection is... connected to something."""
        return self.reader is not None and self.writer is not None

    def stop(self):
        """Stop event loop."""
        #self.eventloop.call_soon(self.eventloop.stop)

    async def send(self, data):
        """Add data to send queue."""
        if len(data) > self.MAX_LEN:
            prefix_index = data.index(':')
            prefix = data[0:prefix_index+1]
            msg = data[prefix_index+1:]
            to_send = [ msg[i:i+(self.MAX_LEN-len(prefix))] for i in range(0, len(msg), self.MAX_LEN-len(prefix)) ]
            
            for line in to_send:
                self.writer.write(bytes(prefix + line + "\r\n", "UTF-8"))
        else:
            self.writer.write(bytes(data + "\r\n", "UTF-8"))
        await self.writer.drain()

    async def recv(self, *, timeout=None):
        return await asyncio.wait_for(self.reader.readline(), timeout=timeout)
