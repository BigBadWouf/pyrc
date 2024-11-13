from .logger import Logger
from .connection import Connection
from .parser import Parser
from .channel import Channel

import asyncio
import traceback
import base64
import importlib
import inspect
import os
import sys
import time

DEFAULT_OPTIONS = {
    'nickname': 'IRCBot',
    'username': 'PyDev',
    'gecos': 'IRCBot',
    'hostname': None,
    'port': 6667,
    'ssl': True,
    'password': None,
    'cap': [],
    'sasl_fail': True, # Continue connect if sasl fail
    'auto_reconnect': True, # Not yet implemented
    'retry_count': 5,  # 0 = unlimited
    'retry_delay': 5, # Delay in seconde
    'commands': [],
    'debug': False,
    'modules': 'modules'
}

class Client:
    """
    Base class for IRC client
    """

    def __init__(self, options):
        self.opt = {**DEFAULT_OPTIONS, **options}

        if self.opt.get('debug'):
            self.log.info(self.opt)

        self.opt['cap'] = self.opt.get('cap') + [x for x in ["extended-join", "sasl", "userhost-in-names"] if x not in self.opt.get('cap')]

        self.modules = {}
        self.activeCAP = []
        self.connected = False

        self.connection = None
        self.buffr = ""
        self._events = {}
        self._modules = {}
        self._channels = {}
        self._retry_count = 0

        self.eventloop = asyncio.get_event_loop()

        self.log = Logger()
        self.parser = Parser()

        self.on("connecting", self.connecting)
        self.on("ping", self.pong)
        self.on("cap", self.cap)
        self.on("authenticate", self.authenticate)
        self.on("903", self.auth_success)
        self.on("904", self.auth_failled)
        self.on("001", self.registered)
        self.on("nick", self.nick_event)
        self.on("quit", self.quit_event)
        self.on("closing link", self.disconnected)

        self.load_modules()

    """ Channels & userlist """

    def channel(self, name):
        return Channel(self, name)

    """ Modules loader """

    def load_modules(self):
        root = os.path.dirname(os.path.dirname(__file__))
        pwd = os.path.join(root, self.opt.get('modules'))
        for module in os.listdir(pwd):
            if module == '__init__.py' or os.path.isdir(os.path.join(pwd, module)) or module[-3:] != '.py':
                continue
            name = module[:-3]
            modulePath = '%s.%s' % (self.opt.get('modules'), name)
            loaded = importlib.import_module(modulePath)
            self.init_module(modulePath, loaded)
    
    def init_module(self, modulePath, module):
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                if obj.__module__ == modulePath:
                    if name.lower() not in self.modules:
                        self.modules[name.lower()] = obj(self)
                        self._modules[name.lower()] = module
    
    def reload_all(self):
        for module in self._modules:
            self._modules[module] = importlib.reload(self._modules[module])

    def get_module(self, name):
        if name.lower() in self.modules:
            return self.modules[name]
        return None

    """ IRC Connection handler """

    def run(self):
        """Connect and run client in event loop."""
        self.eventloop.run_until_complete(self.connect())
        try:
            self.eventloop.run_forever()
        finally:
            self.eventloop.stop()

    async def connect(self):
        """Connect to IRC server."""
        if not self.opt.get('hostname') or not self.opt.get('port'):
            self.log.error("Argument hostname or port missing")
            return

        # Disconnect from current connection.
        if self.connected:
            await self.disconnect()

        # Create socket
        if not self.connection:
            self.connection = Connection(self.opt.get('hostname'), self.opt.get('port'), self.opt.get('ssl'), eventloop=self.eventloop)

        # Connect.
        if not self.connection.connected:
            await self.connection.connect()

        self.connected = True
        self.emit("connecting", None)

        self.eventloop.create_task(self.handle_forever())

    async def disconnect(self):
        """Disconnect from server."""
        if self.connected:
            await self.connection.disconnect()
            self.connected = False

    async def handle_forever(self):
        """Handle data forever."""
        while self.connected:
            try:
                data = await self.connection.recv()
            except asyncio.TimeoutError:
                data = None

            if not data:
                if self.connected:
                    await self.disconnect()
                break

            await self.on_data(data)

    async def on_data(self, data):
        try:
            self.buffr += str(data, "UTF-8")
        except:
            pass
        lines = self.buffr.split("\n")
        self.buffr = lines.pop()
        for line in lines:
            try:
                e = self.parser.parse(line.rstrip())

                if e.has("channel") and e.get("channel"):
                    self.emit("%s%s" % (e.get("action"), e.get("channel")), e)

                self.emit(e.get("action"), e)

                if self.opt.get('debug'):
                    self.log.info("RAW : %s" % (line))
                    self.log.info("PARSED : %s" % (e.data))
                    

            except RuntimeError:
                if self.opt.get('debug'):
                    traceback.print_exception(RuntimeError)
                    traceback.print_stack()
    
    """ Event System """

    def ev(self, event):
        def decorator(func):
            self.on(event, func)
            return func
        return decorator

    def on(self, event, listener):
        if not event in self._events:
            self._events[event] = []
        self._events[event].append(listener)
    
    def remove(self, event, listener):
        if event in self._events:
            events = self._events[event]
            if listener in events:
                events.remove(listener)
    
    def emit(self, event, *args, **kwargs):
        if event in self._events:
            listeners = self._events[event][:]
            for listener in listeners:
                asyncio.create_task(listener(*args, **kwargs))

    """ Handle internal event """

    async def pong(self, event):
        await self.send("PONG %s" % (event.get("msg")))

    async def connecting(self, event):
        if self.opt.get('cap'):
            await self.send("CAP LS 302")
            await self.send("CAP REQ :%s" % (" ".join(self.opt.get('cap'))))
        else:
            await self.register()
    
    async def register(self):
        await self.send("NICK %s" % (self.opt.get('nickname')))
        await self.send("USER %s %s 0 :%s" % (self.opt.get('username'), self.opt.get('hostname'), self.opt.get('gecos')))

    async def cap(self, event):
        msg = event.get("msg").split()
        if msg[0] == "ACK":
            for cap in self.opt.get('cap'):
                if cap in msg:
                    self.activeCAP.append(cap)
            if "sasl" in self.activeCAP and self.opt.get('password'):
                await self.send("AUTHENTICATE PLAIN")
            else:
                await self.send("CAP END")
                await self.register()
        elif msg[0] == 'NAK':
            await self.send("CAP END")
            await self.register()

    async def authenticate(self, event):
        if event and event.get("msg") == "+":
            mystring = self.opt.get('username') + "\0" + self.opt.get('username') + "\0" + self.opt.get('password')
            mystring64 = base64.encodebytes(mystring.encode("utf8"))
            decoded = mystring64.decode("utf8").rstrip("\n")
            await self.send("AUTHENTICATE " + decoded)

    async def auth_failled(self, event):
        await self.send("CAP END")
        if self.opt.sasl_fail:
            await self.register()
        else:
            await self.disconnect()

    async def auth_success(self, event):
        await self.send("CAP END")
        await self.register()

    async def registered(self, event):
        for cmd in self.opt.get('commands'):
            await self.send(cmd)
        await self.send("MODE %s +B" % (self.opt.get('nickname')))
    
    async def quit_event(self, event):
        nick = event.get('from')[0].lower()
        
        if nick == self.opt.get('nickname').lower():
            self.disconnect

        channels = []
        for channel in self._channels:
            if nick in self._channels[channel].users:
                channels.append(channel)
                self.emit("quit%s" % (channel), event)
        self.emit("quit_channels", event, channels)

    async def nick_event(self, event):
        nick = event.get('from')[0].lower()
        channels = []
        for channel in self._channels:
            if nick in self._channels[channel].users:
                channels.append(channel)
                self.emit("nick%s" % (channel), event)
        self.emit("nick_channels", event, channels)
    
    async def disconnected(self, event):
        if self.opt.get('debug'): self.log.info('Disconnected.')
        await self.connection.disconnect()
        if self.opt.get('auto_reconnect'):
            if self.opt.get('debug'): self.log.info('Reconnecting...')
            while (self._retry_count < self.opt.get('retry_count')) and not self.connection.connected:
                try:
                    if self.opt.get('debug'): self.log.info('Trying to reconnect n°%d.' % (self._retry_count))
                    self._retry_count += 1
                    await self.connect()
                    time.sleep(self.opt.get('retry_delay'))
                except RuntimeError:
                    if self.opt.get('debug'):
                        traceback.print_exception(RuntimeError)
                        traceback.print_stack()

    """ Client helper """

    async def send(self, message):
        await self.connection.send(message)

    async def join(self, channel, key=None):
        await self.send("JOIN %s %s" % (channel, key))

    async def part(self, channel, msg=None):
        await self.send("PART %s %s" % (channel, msg))

    async def say(self, target, message):
        await self.send("PRIVMSG %s :%s" % (target, message))

    async def notice(self, target, message):
        await self.send("NOTICE %s :%s" % (target, message))

    async def mode(self, target, mode, params=None):
        await self.send("MODE %s %s %s" % (target, mode, params))

    async def ban(self, target, mask):
        await self.send("MODE %s +b %s" % (target, mask))

    async def unban(self, target, mask):
        await self.send("MODE %s -b %s" % (target, mask))

    

