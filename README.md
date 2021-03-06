Live Streamer Manager (lsmgr)
=============================

Livestreamer Manager is a CLI program that interfaces with Livestreamer to launche streams from various streaming services (Twitch.tv, Own3d.tv etc) in a custom video player (VLC, mplayer etc)

Installing (Linux, OS X etc)
----------
Make sure you have Python and Python setuptools then run:

    $ sudo python setup.py install


Installing (Windows)
--------------------
1. Install Python
2. Install Python setuptools
3. Get rtmpdump and unpack it somewhere (rtmpdump-20110925-git-6230845-win32.zip from http://rtmpdump.mplayerhq.hu/ should work)
4. Add these paths to your Path environment variable:
  * [Python path]\
  * [Python path]\scripts\
  * [rtmpdump path]\ (or specify full path with --rtmpdump option)
  * [VLC/mplayer/other path]\ (or specify full path with --player option)

5. Open a command prompt and change directory to livestreamer source, then run:

    python setup.py install

Note: If you want to use VLC be aware there is currently a bug in version 2.0.1/2.0.2
that prevents stdin reading from working. The bug has been fixed in version 2.0.3.

XSplit
------
Run Livestreamer Manager with and -x to enable XSplit tweaks.

	lsm -x

The player will default to this you can adjust this as you wish.
I would recommend only doing this if you know what you are doing.

	vlc --sout=#rtp{sdp=rtsp://:{PORT}/} --no-sout-rtp-sap --no-sout-standard-sap --ttl=1 --sout-keep

To start a stream you can use the following. Use stream --help to see more info.

	stream url stream

The XSplit URL will be shown in the command line output.

Saving arguments AKA config file
--------------------------------
Livestreamer can read arguments from the file ~/.lsm.conf on Unix based operating systems
and %APPDATA%\livestreamer-manager\lsm.conf on windows based operating systems.
A example file:

    player=mplayer
    jtv-cookie=_jtv3_session_id=arandomhash
    username=username
    password=password
