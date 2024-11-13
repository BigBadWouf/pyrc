from datetime import datetime

"""
Class to log event in stdout
"""


class Logger:
    def info(self, msg):
        time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(".", "%s - %s" % (time, msg))

    def warn(self, msg):
        time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print("+", "%s - %s" % (time, msg))

    def error(self, msg):
        time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print("!", "%s - %s" % (time, msg))
