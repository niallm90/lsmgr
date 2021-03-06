import livestreamer
from .compat import input, stdout, is_win32
from .logger import Logger
from .stream import StreamThread
from .utils import next_port, check_port, get_password, port, manager_args, port

import sys, os, argparse, subprocess, cmd, getpass
import prettytable

#logger = livestreamermanager.logger.new_module("manager")

class Manager(cmd.Cmd):
    prompt = "lsmgr$ "
    streamPool = dict()
    streamIndex = 0
    def __init__(self, lsmgr, args):
        cmd.Cmd.__init__(self)
        self.args = args
        self.lsmgr = lsmgr
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            print ""
            print "Caught keyboard interupted. Killing all streams."
            self.killAllStreams()

    def get_stream_id(self):
        self.streamIndex = self.streamIndex + 1
        return self.streamIndex

    def stream_table(self, streams):
        if type(streams) is not list: streams = [ streams ]

        table = prettytable.PrettyTable(["ID", "URL", "Stream", "Port"])
        for stream in streams:
            table.add_row(stream.get_info())
        return table

    def killAllStreams(self):
        for stream in self.streamPool.values():
            stream.kill_stream()
        for stream in self.streamPool.values():
            stream.join_stream()

    def remove_stale_streams(self):
        for id, stream in self.streamPool.items():    
            stream.process.join(timeout=0.1)
            if not stream.process.is_alive():
                del self.streamPool[id]

    def are_running_streams(self):
        self.remove_stale_streams()
        return len(self.streamPool) > 0

    def exit(self):
        if(self.are_running_streams()):
            while True:
                print "There are streams still running!"
                a = raw_input("Are you sure you want to quit? (y/n) ").lower()
                if "y" in a:
                    self.killAllStreams()
                    return True
                elif "n" in a:
                    return False
        print ""
        return True

    def do_k(self, args):
        'Kill a running stream'
        self.do_kill(args)

    def do_kill(self, args):
        'Kill running streams'
        parser = argparse.ArgumentParser(description='Kill running streams')
        parser.add_argument('streamid', metavar='id', help='the stream id or "all" to kill all streams', nargs="+")

        args = manager_args(parser, args)
        if not args:
            return False

        if len(args.streamid) == 0:
            print "At lease one stream ID is required"
            return False
        
        streams = []
        for id in args.streamid:
            if id == "all":
                streams = self.streamPool.values()
                break

            try:
                stream = self.streamPool[int(id)]
                streams.append(stream)
            except:
                print "{0} is not a valit stream ID.".format(id)
                print "Use the list command to list all streams"
                return False

        print self.stream_table(streams)
        while True:
            msg = "Are you sure you want to kill {0}? (y/n) "
            if len(streams) == 1:
                msg = msg.format("this stream")
            else:
                msg = msg.format("these streams")
                
            a = raw_input(msg).lower()
            if "y" in a:
                for stream in streams:
                    stream.kill_stream()
                    stream.join_stream()
                return False
            elif "n" in a:
                return False
    
    def do_e(self, args):
        'Exit the command line'
        return self.do_exit(args)

    def do_exit(self, args):
        'Exit the command line'
        return self.exit()

    def do_EOF(self, args):
        'Exit the command line'
        return self.exit()

    def do_l(self, args):
        'List streams currently running'
        self.do_list(args)

    def do_list(self, args):
        'List streams currently running'
        self.remove_stale_streams()

        if len(self.streamPool) == 0:
            print "There are no streams running"
            return False
        
        print self.stream_table(self.streamPool.values())

    def do_s(self, args):
        'Start a new stream'
        return self.do_stream(args)

    def do_stream(self, args):
        'Start a new stream'
        exampleusage = """example usage:

$ stream twitch.tv/onemoregametv
Found streams: 240p, 360p, 480p, 720p, best, iphonehigh, iphonelow, live
$ stream twitch.tv/onemoregametv 720p

Stream now playbacks in player (default is VLC).
"""
        parser = argparse.ArgumentParser(description='Start a new stream')
        parser.add_argument("url", help="URL to stream", nargs="?")
        parser.add_argument("stream", 
            help="Stream quality to play, use 'best' for highest quality available", 
            nargs="?")

        playeropt = parser.add_argument_group("player options")
        playeropt.add_argument("-p", "--player", metavar="player", 
            help="Command-line for player, default is 'vlc'", default=self.args.player)
        playeropt.add_argument("-Q", "--port", metavar="port", type=port,
            help="The port to use if the player command contains '{PORT}'", default=next_port(self.args))

        outputopt = parser.add_argument_group("file output options")
        outputopt.add_argument("-o", "--output", metavar="filename", 
            help="Write stream to file instead of playing it")
        outputopt.add_argument("-f", "--force", action="store_true", 
            help="Always write to file even if it already exists")

        pluginopt = parser.add_argument_group("plugin options")
        pluginopt.add_argument("-c", "--cmdline", action="store_true", default=self.args.cmdline,
            help="Print command-line used internally to play stream, this may not be available on all streams")
            

        args = manager_args(parser, args)
        if not args:
            return False
    
        if not args.url:
            print exampleusage
            return False

        
        # Copy usable args
        args.loglevel = self.args.loglevel
        args.errorlog = self.args.errorlog
        args.rtmpdump = self.args.rtmpdump
        args.xsplit = self.args.xsplit
        args.jtv_cookie = self.args.jtv_cookie
        args.gomtv_cookie = self.args.gomtv_cookie
        args.gomtv_username = self.args.gomtv_username
        args.gomtv_password = self.args.gomtv_password
    
        stream = StreamThread(self.get_stream_id(), self.lsmgr, args)
        self.streamPool[stream.id] = stream

    def do_jtvauth(self, args):
        "Specify JustinTV authentication with cookie to allow access to subscription channels"
        parser = argparse.ArgumentParser(description="Specify JustinTV authentication with cookie to allow access to subscription channels")
        parser.add_argument("-c", "--cookie", metavar="cookie", help="JustinTV cookie")
        
        args = manager_args(parser, args)
        if not args:
            return False

        if auth.cookie:
            self.args.jtv_cookie = args.cookie

    def do_gomtvauth(self, args):
        "Specify GOMTV authentication with the cookie or username and password to allow access to streams"
        parser = argparse.ArgumentParser(description="Specify GOMTV authentication with the cookie or username and password to allow access to streams")
        parser.add_argument("-c", "--cookie", metavar="cookie", help="GOMTV cookie")
        parser.add_argument("-u", "--username", metavar="username", help="GOMTV username")
        parser.add_argument("-p", "--password", metavar="password", nargs="?", const=True, default=None,
                            help="GOMTV password (If left blank you will be prompted)")

        args = manager_args(parser, args)
        if not args:
            return False

        if args.cookie:
            self.args.gomtv_cookie = args.cookie

        if args.username:
            self.args.gomtv_username = args.username

        if args.password:
            if args.password is True:
                password = getpass.getpass("GOMTV Password:")
            else:
                password = args.password
            
            self.args.gomtv_password = password

    def do_player(self, args):
        "Command-line for player"
        parser = argparse.ArgumentParser(description="Command-line for player")
        parser.add_argument("command", metavar="command", help="Command-line for player")
                               
        args = manager_args(parser, args)
        if not args:
            return False

        if not args.command:
            print "player requires one argument: player [command]"
        else:
            self.args.player = args.command

    def do_ports(self, args):
        "Specify ports to start streams on if streaming."
        parser = argparse.ArgumentParser(description="Specify ports to start streams on if streaming.")
        parser.add_argument("--min", metavar="port", type=port, help="Minimum port in the range to start streams. Must grater than 50000.")
        parser.add_argument("--max", metavar="port", type=port, help="Maximum port in the range to start streams. Must grater than 60000.")
                               
        args = manager_args(parser, args)
        if not args:
            return False

        if not args.min and not args.max:
            print "ports requires one argument: ports --min [port]"
        else:
            if args.min:
               self.args.min_port = args.min
            if args.max:
               self.args.max_port = args.max
