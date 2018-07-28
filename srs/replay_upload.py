#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2018 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

#
# example cmdline call:
# XMLRPC_USER=spads1 XMLRPC_PASSWORD=SeCr3t ./xmlrpc_client.py "awesome game" "checkout that dude in SE" tag1,tag2,tag3 20130229_123456_RustyDelta_v2_88.sdf Danchan
#

import os
import sys
import xmlrpclib
from time import sleep
from os.path import realpath, dirname, join as joinpath

try:
    import argparse
except ImportError:
    # argparse for python installations <2.7
    sys.path.append(joinpath(realpath(dirname(__file__)), "contrib"))
    import argparse


def parse_cmdline():
    parser = argparse.ArgumentParser(description="Upload a spring demo file to the replays site.",
                                     epilog="Please set XMLRPC_USER and XMLRPC_PASSWORD in your OS environment to a "
                                            "lobby accounts credentials. XMLRPC_URL can also be set in your environment"
                                            ", use 'https://replays-test.springrts.com/xmlrpc/' for upload testing "
                                            "purposes.")
    parser.add_argument("-d", "--duration", help="game duration in seconds (SPADS: %%gameDuration)", type=int,
                        default=9999)
    parser.add_argument("-r", "--result", help="end game result ('gameOver','undecided') (SPADS: %%result)", default="")
    parser.add_argument("-t", "--throttle", help="throttle upload to x byte/s, 0 means no throttling", type=int)
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("title", help="short description (50 char max)")
    parser.add_argument("comment", help="long description (512 char max)")
    parser.add_argument("tags", help="tags (comma separated)")
    parser.add_argument("path", help="path of .sdf")
    parser.add_argument("owner", help="lobby account that will be saved as the uploader")
    args = parser.parse_args()

    if (args.result == "undecided" and args.duration < 300) or args.duration < 180:
        print("[Replay Upload] Game did not start or very short - not uploading.")
        return 5
    return args


def main():
    args = parse_cmdline()

    try:
        XMLRPC_USER = os.environ["XMLRPC_USER"]
        XMLRPC_PASSWORD = os.environ["XMLRPC_PASSWORD"]
    except KeyError:
        print("[Replay Upload] Please set XMLRPC_USER and XMLRPC_PASSWORD in your OS")
        print("environment to a lobby accounts credentials.")
        sys.exit(1)
    try:
        XMLRPC_URL = os.environ["XMLRPC_URL"]
    except KeyError:
        XMLRPC_URL = "https://replays.springrts.com/xmlrpc/"

    if args.verbose:
        if args.throttle > 0:
            sp = "at %.2f kb/s" % (args.throttle / 1024.0)
        else:
            sp = "without upload throttling"
        print("[Replay Upload] Uploading file {!r}\n  authenticating as {!r}\n  to {!r}\n  for owner {!r}\n with "
              "subject {!r}\n  comment {!r}\n  and tags {!r}\n  {}.".format(args.path, XMLRPC_USER, XMLRPC_URL,
                                                                            args.owner, args.title, args.comment,
                                                                            args.tags, sp))

    try:
        with open(args.path, "rb") as fp:
            demofile = xmlrpclib.Binary(fp.read())
    except IOError, ioe:
        print("[Replay Upload] ERROR: could not open spring demo file: {}.".format(ioe))
        return 6

    if args.throttle > 0:
        try:
            import pycurl
            import pyCURLTransport
        except ImportError:
            print("""
[Replay Upload] ERROR: Please install pycurl to use bandwidth throttling.
  Homepage: http://pycurl.sourceforge.net/
  Debian/Ubuntu/Fedora/Arch: python-pycurl
  Gentoo: dev-python/pycurl
  Windows: compile from source or search binary packages (watch out for OS version
           and 32/64 bit). Success was reported with package from
           http://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl""")
            return 1

        curltrans = pyCURLTransport.PyCURLTransport()
        curltrans._curl.setopt(pycurl.MAX_SEND_SPEED_LARGE, args.throttle)
        trans = curltrans
    else:
        trans = None  # use xmlrpclib internal HTTP transport

    try:
        rpc_srv = xmlrpclib.ServerProxy(XMLRPC_URL, transport=trans)
        result = rpc_srv.xmlrpc_upload(XMLRPC_USER, XMLRPC_PASSWORD, os.path.basename(args.path), demofile, args.title,
                                       args.comment, args.tags, args.owner)
    except Exception as exc:
        print("[Replay Upload] Error sending data to replay site. Exception:\n{}\n".format(exc))
        return 1

    if args.verbose:
        print("[Replay Upload] {!r}".format(result))

    sleep(10)  # allow site to process replay before displaying the URL
    return int(result[0])


if __name__ == "__main__":
    sys.exit(main())
