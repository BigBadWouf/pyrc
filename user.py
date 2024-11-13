""" Users class helper """

class User:

    """ Constants """

    REGULAR = 0
    VOICE = 1
    HALFOP = 2
    OP = 3

    def __init__(self, client, channel):
        self.client = client
        self.users = {}
        self.channel = channel

        self.client.on("join%s" % (self.channel.name), self.join_event)
        self.client.on("kick%s" % (self.channel.name), self.kick_event)
        self.client.on("part%s" % (self.channel.name), self.part_event)
        self.client.on("quit", self.quit_event)
        self.client.on("mode%s" % (self.channel.name), self.mode_event)
        self.client.on("nick", self.nick_event)
        self.client.on("353%s" % (self.channel.name), self.names_event)
    
    """ Event """

    async def join_event(self, event):
        print(event.data)
        pass
    async def part_event(self, event):
        pass
    async def nick_event(self, event):
        pass
    async def kick_event(self, event):
        pass
    async def quit_event(self, event):
        pass
    async def mode_event(self, event):
        print(event.data)

    async def names_event(self, event):
        users = self._parse_users_from_names(event.get('msg'))
        for user in users:
            if user.get('nick') not in self.users:
                self.users[user.get('nick')] = user
    
    """ Privates methods """

    def _parse_users_from_names(self, event_message):
        names = event_message.lower().split()
        users = []

        for user in names:
            current_user = User.User(self._get_user(user))
            if self._has_status(parsed_user.get('nick')):
                current_user.add('status', [self._get_status_symbol(current_user.get('nick'))])
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
    
    def _has_status(self, nick):
        if nick[0] in '+%@':
            return True
    
    def _get_status_symbol(self, nick):
        return nick[0]
    
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