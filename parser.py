"""
IRC Parser class
return a dict with parsed data
ex : {
      'from_server': False,
      'server': server host,
      'from': (nick, ident, host),
      'target': Nick/Channel,
      'action': Code/Event,
      'message': data
}
"""


class Parser:

    def parse(self, raw):
        e = Event()
        t = self.tokenize(raw)

        # print(t)
        if raw.startswith("PING"):
            e.add("from_server", True)
            e.add("action", "ping")
            e.add("msg", t[0])
            return e
        elif raw.startswith("AUTHENTICATE"):
            e.add("from_server", True)
            e.add("action", "authenticate")
            e.add("msg", t[0])
            return e
        elif raw.startswith('ERROR'):
            e.add("from_server", True)
            e.add("action", t[0].lower())
            e.add("msg", ' '.join(': '.join(t[1:]).strip().split()[1:]))
            return e
        else:
            if self.isServerMessage(t):
                e.add("from_server", True)
            else:
                e.add("from_server", False)
                e.add("from", (self.getNickname(t), self.getUser(t), self.getHostname(t)))

            e.add("action", self.getAction(t).lower())
            e.add("msg", self.getMsg(t, action=e.get("action")))

            if e.get("action") == "part":
                msg = self.getMsg(t, action=e.get("action"))
                if msg.startswith("#"):
                    e.add("channel", msg)
                else:
                    e.add("channel", self.getChannel(t))

            elif e.get("action") == "nick":
                pass
            elif e.get("action") == "kick":
                e.add("channel", self.getChannel(t))
                e.add("target", self.getMsg(t, action=e.get("action")).split()[0])
                e.add(
                    "msg", " ".join(self.getMsg(t, action=e.get("action")).split()[1:])
                )
            elif e.get("action") == "quit":
                pass
            elif e.get("action") == 'kill' or e.get("action") == '465' or e.get("action") == 'closing link':
                e.add("channel", None)
                pass
            else:
                e.add("target", self.getTarget(t))
                e.add("channel", self.getChannel(t))

            return e

    def tokenize(self, s):
        """Tokenize the given IRC output."""
        s = s.split(":")
        if len(s) > 1:
            return s[1:]
        else:
            return []

    def getNickname(self, t):
        """Take in a token list, and return the nickname."""
        return t[0].split("!")[0]

    def getHostname(self, t):
        """Return the users host from a tokenized list."""
        return t[0].split("!")[1].split("@")[1].split()[0]

    def getUser(self, t):
        """Return the user from a tokenized list."""
        return t[0].split("!")[1].split("@")[0]

    def getServer(self, t):
        """Return the server address from a tokenized list."""
        return t[0].split()[0]

    def getAction(self, t):
        """Return the action from a tokenized list."""
        return t[0].split()[1]

    def getTarget(self, t):
        """Get the target of the event"""
        if len(t[0].split()) >= 3:
            return t[0].split()[2]
        return None

    def getChannel(self, t):
        """Return the channel from a tokenized list."""
        for item in t[0].split():
            if item.startswith("#"):
                return item
        return None

    def isServerMessage(self, t):
        """Check if the IRC output is a server message."""
        if "!" not in t[0].split()[0]:
            return True
        return False

    def getMsg(self, t, action=None):
        """Return the message from a tokenized list."""
        if action == "333":
            return " ".join(t[0].split()[4:])
        elif action == "mode":
            if len(t) > 1:
                return " ".join(t[0].split()[3:]) + " " + ":".join(t[1:])
            else:
                return "".join(t[0].split()[3:])
        elif action == "kick":
            return " ".join(t[0].split()[3:]) + " " + ":".join(t[1:])
        elif action == "cap":
            return " ".join(t[0].split()[3:]) + " " + ":".join(t[1:])
        elif action == "352":
            return " ".join(t[0].split()[4:]) + " " + " ".join(t[1].split()[1:])
        elif action == "367":
            time = str(t[-1])
            if len(t) > 2:
                return (
                    t[0].split()[4]
                    + ":"
                    + "".join(":".join(t[1:-1]).split()[:-1])
                    + " "
                    + time
                )
            else:
                return t[0].split()[4] + " " + time
        elif action == "311":
            return t[0].split()[3] + "!" + t[0].split()[4] + "@" + t[0].split()[5]
        elif action == "318":
            return t[0].split()[3]
        elif len(t) > 1:
            return ":".join(t[1:])
        return None


""" Class wrapper for manipulation of parsed event """


class Event:
    def __init__(self):
        self.data = {}

    def add(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data[key]

    def has(self, key):
        return key in self.data
