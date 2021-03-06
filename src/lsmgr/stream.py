from .utils import urlopen, check_port
from .compat import str, is_win32, pbs
import livestreamer

import os
import time
import tempfile
import multiprocessing
import subprocess
import sys

class StreamError(Exception):
    pass

class Stream(object):
    """
        This is a base class that should be inherited when implementing
        different stream types. Should only be used directly from plugins.
    """

    def __init__(self, session):
        self.session = session

    def open(self):
        """
            Opens a connection to the stream.
            Returns a file-like object than can be used to read data.
            Raises :exc:`StreamError` on failure.
        """
        raise NotImplementedError

class StreamProcess(Stream):
    def __init__(self, session, params={}):
        Stream.__init__(self, session)

        self.params = params
        self.params["_bg"] = True
        self.params["_err"] = open(os.devnull, "w")
        self.errorlog = self.session.options.get("errorlog")

    def cmdline(self):
        return str(self.cmd.bake(**self.params))

    def open(self):
        if self.errorlog:
            tmpfile = tempfile.NamedTemporaryFile(prefix="livestreamer",
                                                  suffix=".err", delete=False)
            self.params["_err"] = tmpfile

        stream = self.cmd(**self.params)

        # Wait 0.5 seconds to see if program exited prematurely
        time.sleep(0.5)
        stream.process.poll()

        if stream.process.returncode is not None:
            if self.errorlog:
                raise StreamError(("Error while executing subprocess, error output logged to: {0}").format(tmpfile.name))
            else:
                raise StreamError("Error while executing subprocess")

        return stream.process.stdout

class RTMPStream(StreamProcess):
    def __init__(self, session, params):
        StreamProcess.__init__(self, session, params)

        self.rtmpdump = self.session.options.get("rtmpdump") or (is_win32 and "rtmpdump.exe" or "rtmpdump")
        self.params["flv"] = "-"

        try:
            self.cmd = getattr(pbs, self.rtmpdump)
        except pbs.CommandNotFound as err:
            raise StreamError(("Unable to find {0} command").format(str(err)))

    def open(self):
        if "jtv" in self.params and not self._has_jtv_support():
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        return StreamProcess.open(self)

    def _has_jtv_support(self):
        try:
            help = self.cmd(help=True, _err_to_out=True)
        except pbs.ErrorReturnCode as err:
            raise StreamError(("Error while checking rtmpdump compatibility: {0}").format(str(err.stdout, "ascii")))

        for line in help.split("\n"):
            if line[:5] == "--jtv":
                return True

        return False

class HTTPStream(Stream):
    def __init__(self, session, url):
        Stream.__init__(self, session)

        self.url = url

    def open(self):
        return urlopen(self.url)


class StreamHandler():
    def __init__(self, lsmgr, args, queue):
        try:
            self.lsmgr = lsmgr
            self.livestreamer = livestreamer.Livestreamer()

            self.livestreamer.set_option("errorlog", args.errorlog)
            self.livestreamer.set_option("rtmpdump", args.rtmpdump)
            self.livestreamer.set_plugin_option("justintv", "cookie", args.jtv_cookie)
            self.livestreamer.set_plugin_option("gomtv", "cookie", args.gomtv_cookie)
            self.livestreamer.set_plugin_option("gomtv", "username", args.gomtv_username)
            self.livestreamer.set_plugin_option("gomtv", "password", args.gomtv_password)

            lsmgr.logger.set_output(sys.stdout)
            self.logger = lsmgr.logger.new_module("stream")
            self.args = args
            self.queue = queue
            
            if "{PORT}" in args.player:                
                if not check_port(args.port):
                    self.logger.error("The port ({0}) is already in use.", args.port)
                    return None

                # Put the port into the player.
                args.player = args.player.replace("{PORT}", str(args.port))
            else:
                args.port = False

            try:
                channel = self.livestreamer.resolve_url(args.url)
            except livestreamer.NoPluginError:
                self.logger.error("No plugin can handle URL: {0}".format(args.url))
                self.queuePut("failed")
                return None

            self.logger.info("Found matching plugin {0} for URL {1}".format(channel.module, args.url))

            try:
                streams = channel.get_streams()
            except StreamError as err:
                self.logger.error(str(err))
                self.queuePut("failed")
                return None
            except livestreamer.PluginError as err:
                self.logger.error(str(err))
                self.queuePut("failed")
                return None

            if len(streams) == 0:
                self.logger.error(("No streams found on this URL: {0}").format(args.url))
                self.queuePut("failed")
                return None

            keys = list(streams.keys())
            keys.sort()    
            validstreams = (", ").join(keys)

            if args.stream:
                if args.stream in streams:
                    stream = streams[args.stream]

                    if args.cmdline:
                        if isinstance(stream, self.livestreamer.stream.StreamProcess):
                            msg(stream.cmdline())
                        else:
                            exit("Stream does not use a command-line")
                    else:
                        while self.queueGet(False, 0) != "kill":
                            self.output_stream(stream)
                else:
                    self.logger.error(("Invalid stream quality: {0}").format(args.stream))
                    self.logger.error(("Valid streams: {0}").format(validstreams))
                    self.queuePut("failed")
                    return None
            else:
                self.logger.error(("Found streams: {0}").format(validstreams))
                if queue is not None:
                    self.queuePut("failed")
                return None
        except KeyboardInterrupt:
            pass
        
    def output_stream(self, stream):
        progress = False
        out = None
        player = None

        args = self.args

        self.logger.info("Opening stream {0}", args.stream)

        try:
            fd = stream.open()
        except StreamError as err:
            self.logger.error("Could not open stream - {0}").format(err)
            self.queuePut("failed")
            return False

        self.logger.debug("Pre-buffering 8192 bytes")
        try:
            prebuffer = fd.read(8192)
        except IOError:
            self.logger.error("Failed to read data from stream")
            if queue is not None:
                self.queuePut("failed")
            return False

        self.logger.debug("Checking output")

        if args.output:
            if args.output == "-":
                out = stdout
            else:
                out = self.check_output(args.output, args.force)
                progress = True
        else:
            cmd = args.player

            if "vlc" in args.player:
                cmd = cmd + " - vlc://quit"

            pout = open(os.devnull, "w")
            perr = open(os.devnull, "w")

            self.logger.info("Starting player: {0}", args.player)
            if args.port:
                self.logger.info("Stream port is: {0}", args.port)
                if args.xsplit:
                    self.logger.info("XSplit URL: rtsp://localhost:{0}/\\\\rtsp_transport:udp".format(args.port))
            player = subprocess.Popen(cmd, shell=True, stdout=pout, stderr=perr,
                                      stdin=subprocess.PIPE)
            out = player.stdin

        if not out:
            self.logger.error("Failed to open a valid stream output")
            self.queuePut("failed")
            return False

        if is_win32:
            import msvcrt
            msvcrt.setmode(out.fileno(), os.O_BINARY)

        self.logger.debug("Writing stream to output")
        out.write(prebuffer)

        self.queuePut("started")

        self.write_stream(fd, out, progress)

        if player:
            try:
                player.kill()
            except:
                pass

    def write_stream(self, fd, out, progress):
        written = 0
        kill = False

        while True:
            if self.queueGet(False, 0) == "kill":
                kill = True
                break
            try:
                data = fd.read(8192)
            except:
                self.logger.error("Error when reading from stream")
                break

            if len(data) == 0:
                break

            try:
                out.write(data)
            except IOError:
                self.logger.error("Error when writing to output")
                break

            written += len(data)

            if progress:
                sys.stderr.write(("\rWritten {0} bytes").format(written))

        if progress and written > 0:
            sys.stderr.write("\n")

        if kill == True:
            self.logger.info("Closing stream")
        fd.close()

        if out != sys.stdout:
            out.close()

    def check_output(output, force):
        if os.path.isfile(output) and not force:
            sys.stderr.write(("File {0} already exists! Overwrite it? [y/N] ").format(output))

            try:
                answer = input()
            except:
                sys.exit()

            answer = answer.strip().lower()

            if answer != "y":
                sys.exit()

        try:
            out = open(output, "wb")
        except IOError as err:
            exit(("Failed to open file {0} - ").format(output, err))

        return out

    def queuePut(self, data):
        try:
            if self.queue is not None:
                return self.queue.put(data)
        except:
            raise

    def queueGet(self, block=None, timeout=None):
        try:
            if self.queue is not None:
                output = self.queue.get(block, timeout)
                self.logger.debug("Reading from the queue returned " + output)
                return output
        except:
            return None


class StreamThread():
    def __init__(self, id, lsmgr, args):
        self.id = id
        self.args = args
        self.lsmgr = lsmgr
        self.queue = multiprocessing.Queue()

        self.process = multiprocessing.Process(target=StreamHandler, args=(self.lsmgr, self.args, self.queue))
        self.process.start()

        # Loop until we get a response as it will be pushing stuff 
        # to the logger and we dont want to clobber any input.
        while self.queue.get() is None:
            pass

    def get_id(self):
        return self.id

    def kill_stream(self):
        self.queue.put('kill')

    def join_stream(self):
        self.process.join()

    def get_info(self):
        info = [self.id, self.args.url, self.args.stream]
        if "{PORT}" in self.args.player:
            info.append(self.args.port)
        else:
            info.append("N/A")

        return info

__all__ = ["StreamError", "Stream", "StreamProcess", "RTMPStream", "HTTPStream", "StreamHandler", "StreamThread"]
