import argparse
import os
import sys
import subprocess
import getpass

from livestreamermanager import *
from .compat import input, stdout, is_win32
from .stream import StreamProcess
from .utils import ArgumentParser, port
from .manager import Manager

exampleusage = """
example usage:

$ livestreamer twitch.tv/onemoregametv
Found streams: 240p, 360p, 480p, 720p, best, iphonehigh, iphonelow, live
$ livestreamer twitch.tv/onemoregametv 720p

Stream now playbacks in player (default is VLC).

"""

lsm = Livestreamermanager()
logger = lsm.logger.new_module("cli")

msg_output = sys.stdout
parser = ArgumentParser(description="CLI program that launches streams from various streaming services in a custom video player",
                        fromfile_prefix_chars="@",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog=exampleusage, add_help=False)

parser.add_argument("-h", "--help", action="store_true",
                    help="Show this help message and exit")
parser.add_argument("-l", "--loglevel", metavar="level",
                    help="Set log level, valid levels: none, error, warning, info, debug",
                    default="info")
parser.add_argument("--min-port", metavar="port", 
                    help="Minimum port in the range to start streams. Must grater than 50000. (default: 50000)", 
                    default=50000, type=port)
parser.add_argument("--max-port", metavar="port", 
                    help="Maximum port in the range to start streams. Must less than 65000. (default: 65000)", 
                    default=65000, type=port)

playeropt = parser.add_argument_group("player options")
playeropt.add_argument("-p", "--player", metavar="player",
                       help="Command-line for player, default is 'vlc'",
                       default="default")
playeropt.add_argument("-x", "--xsplit", action="store_true", 
                       help="Show XSplit URLS to open with IP Camera plugin and modify the default player")

pluginopt = parser.add_argument_group("plugin options")
pluginopt.add_argument("-c", "--cmdline", action="store_true",
                       help="Print command-line used internally to play stream, this may not be available on all streams")
pluginopt.add_argument("-e", "--errorlog", action="store_true",
                       help="Log possible errors from internal command-line to a temporary file, use when debugging")
pluginopt.add_argument("-r", "--rtmpdump", metavar="path",
                       help="Specify location of rtmpdump")
pluginopt.add_argument("-j", "--jtv-cookie", metavar="cookie",
                       help="Specify JustinTV cookie to allow access to subscription channels")
pluginopt.add_argument("--gomtv-cookie", metavar="cookie",
                       help="Specify GOMTV cookie to allow access to streams")
pluginopt.add_argument("--gomtv-username", metavar="username",
                       help="Specify GOMTV username to allow access to streams")
pluginopt.add_argument("--gomtv-password", metavar="password",
                       help="Specify GOMTV password to allow access to streams (If left blank you will be prompted)", 
                       nargs="?", const=True, default=None)

if is_win32:
    RCFILE = os.path.join(os.environ["APPDATA"], "livestreamer-manager", "lsm.conf")
else:
    RCFILE = os.path.expanduser("~/.lsm.conf")

def exit(msg):
    sys.exit(("error: {0}").format(msg))

def msg(msg):
    msg_output.write(msg + "\n")

def set_msg_output(output):
    msg_output = output
    lsm.set_logoutput(output)

def main():
    arglist = sys.argv[1:]

    if os.path.exists(RCFILE):
        arglist.insert(0, "@" + RCFILE)

    args = parser.parse_args(arglist)

    if args.gomtv_password is True:
        gomtv_password = getpass.getpass("GOMTV Password:")
    else:
        gomtv_password = args.gomtv_password

    if args.player == "default" and args.xsplit:
        args.player = "vlc --sout=#rtp{sdp=rtsp://:{PORT}/} --no-sout-rtp-sap --no-sout-standard-sap --ttl=1 --sout-keep"
    elif args.player == "default":
        args.player = "vlc"

    lsm.livestreamer.set_option("errorlog", args.errorlog)
    lsm.livestreamer.set_option("rtmpdump", args.rtmpdump)
    lsm.livestreamer.set_plugin_option("justintv", "cookie", args.jtv_cookie)
    lsm.livestreamer.set_plugin_option("gomtv", "cookie", args.gomtv_cookie)
    lsm.livestreamer.set_plugin_option("gomtv", "username", args.gomtv_username)
    lsm.livestreamer.set_plugin_option("gomtv", "password", gomtv_password)
    lsm.set_loglevel(args.loglevel)

    Manager(lsm, args)
