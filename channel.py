import asyncio

""" Channel class helper """

class Channel:
    """ Constants """

    REGULAR = 0
    VOICE = 1
    HALFOP = 2
    OP = 3

    def __init__(self, client, name, key=None):
        self.client = client
        self.name = name.lower()
        self.key = key
        self.users = {}

        self.client.on("join%s" % (self.name), self.join_event)
        self.client.on("kick%s" % (self.name), self.kick_event)
        self.client.on("part%s" % (self.name), self.part_event)
        self.client.on("quit%s" % (self.name), self.quit_event)
        self.client.on("mode%s" % (self.name), self.mode_event)
        self.client.on("nick%s" % (self.name), self.nick_event)
        self.client.on("353%s" % (self.name), self.names_event)
    
    """ Public methods """
        
    def join(self):
        asyncio.create_task(self.client.join(self.name, self.key))
  
    def part(self, message=None):
        asyncio.create_task(self.client.part(self.name, message))

    def is_op(self, nick):
        if nick.lower() in self.users:
            return self.OP in self.users['nick'].get('status')
        return False

    def is_halfop(self, nick):
        if nick.lower() in self.users:
            return self.HALFOP in self.users['nick'].get('status')
        return False
    
    def is_voice(self, nick):
        if nick.lower() in self.users:
            return self.VOICE in self.users['nick'].get('status')
        return False

    def is_on(self, nick):
        return nick.lower() in self.users

    def get_userlist(self):
        return self.users
    
    def get_user_status(self, nick):
        nick = nick.lower()
        if self.is_on(nick):
            return self.users[nick].get('status')
        return []
    
    """ Event """

    async def join_event(self, event):
        nick, ident, host = event.get('from')
        user = Channel.User({
            'nick': nick.lower(), 
            'ident': ident, 
            'host': host,
            'status': []
            })
        if user.get('nick') not in self.users:
            self.users[user.get('nick')] = user

    async def part_event(self, event):
        nick, ident, host = event.get('from')
        if nick.lower() in self.users:
            del self.users[nick.lower()]

    async def nick_event(self, event):
        nick, ident, host = event.get('from')
        new_nick = event.get('msg').lower()
        if self.is_on(nick):
            copy = self.users[nick.lower()]
            copy.add('nick', new_nick)
            self.users[new_nick] = copy
            del self.users[nick.lower()]

    async def kick_event(self, event):
        nick = event.get('target').lower()
        if self.is_on(nick):
            await asyncio.sleep(3)
            del self.users[nick]

    async def quit_event(self, event):
        nick, ident, host = event.get('from')
        if self.is_on(nick):
            del self.users[nick.lower()]

    async def mode_event(self, event):
        if event.get('channel'):
            modes = self._parse_status_from_mode(event.get('msg'))
            for is_giving, status, nick in modes:
                self._update_user_status(is_giving, status, nick)
        
    async def names_event(self, event):
        users = self._parse_users_from_names(event.get('msg'))
        for user in users:
            if user.get('nick') not in self.users:
                self.users[user.get('nick')] = user
    
    """ Private methods """

    def _parse_status_from_mode(self, event_message):
        modes, users = event_message.split(" ", 1)
        users = users.split()
        users.reverse()

        users_status = []

        for token in modes:
            if token == "+":
                add = True
            elif token == "-":
                add = False
            else:
                status = self._get_status_from_letter(token)
                if status:
                    user_status.append((add, status, users.pop()))
        return users_status


    def _parse_users_from_names(self, event_message):
        names = event_message.lower().split()
        users = []

        for user in names:
            current_user = Channel.User(self._get_user(user))
            if self._has_status_symbol(current_user.get('nick')):
                current_user.add('status', [self._get_status_from_nick(current_user.get('nick'))])
                current_user.add('nick', self._strip_status_symbol_from_nick(current_user.get('nick')))
            else:
                current_user.add('status', [])
            users.append(current_user)
        
        return users

    def _get_user(self, user):
        return {
            "nick": user.split("!")[0],
            "ident": user.split("!")[1].split("@")[0],
            "host": user.split("!")[1].split("@")[1].split()[0],
        } 
    
    def _has_status_symbol(self, nick):
        if nick[0] in '+%@':
            return True
    
    def _update_user_status(self, is_giving, nick, status):
        if nick in self.users:
            if is_giving:
                self._giving_status(nick, status)
            else:
                self._remove_status(nick, status)
    
    def _has_status(nick, status):
        return status in self.users[nick].get('status')
    
    def _giving_status(nick, status):
        if not self._has_status(nick, status):
            self.users[nick].get('status').append(status)

    def _remove_status(nick, status):
        if self._has_status(nick, status):
            self.users[nick].get('status').remove(status)

    def _get_status_from_symbol(self, symbol):
        if symbol == '+':
            return self.VOICE
        elif symbol == '%':
            return self.HALFOP
        elif symbol == '@':
            return self.OP
    
    def _get_status_from_letter(self, letter):
        letter = letter.lower()
        if letter == 'v':
            return self.VOICE
        elif letter == 'h':
            return self.HALFOP
        elif letter == 'o':
            return self.OP
        else:
            return None
    
    def _get_status_from_nick(self, nick):
        return self._get_status_from_symbol(nick[0])
    
    def _strip_status_symbol_from_nick(self, nick):
        return nick[1:]

    """ Wrapprer for individual user """
    class User:
        def __init__(self, user):
            self.user = user

        def get(self, key):
            return self.user[key]

        def add(self, key, value):
            self.user[key] = value

        def has(self, key):
            return key in self.user