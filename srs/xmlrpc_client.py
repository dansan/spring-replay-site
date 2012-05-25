#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# example cmdline call:
# XMLRPC_USER=spads1 XMLRPC_PASSWORD=SeCr3t ./xmlrpc_client.py "awesome game" "checkout that dude in SE" tag1,tag2,tag3 20130229_123456_RustyDelta_v2_88.sdf Danchan
#

import os
import sys
import xmlrpclib
import argparse
import pyCURLTransport
import pycurl

def main(argv=None):
    XMLRPC_URL = "http://replays.admin-box.com/xmlrpc/"

    parser = argparse.ArgumentParser(description="Upload a spring demo file to the replays site.", epilog="Please set XMLRPC_USER and XMLRPC_PASSWORD in your OS environment to a lobby accounts credentials. In case it changes, XMLRPC_URL can also be set in your environment.")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-t", "--throttle", help="throttle upload to x byte/s, 0 means no throttling", type=int)
    parser.add_argument("title", help="short description (50 char max)")
    parser.add_argument("comment", help="long description (512 char max)")
    parser.add_argument("tags", help="tags (comma separated)")
    parser.add_argument("path", type=argparse.FileType('rb'), help="path to .sdf")
    parser.add_argument("owner", help="lobby account that will be saved as the uploader")
    args = parser.parse_args()


    if not os.environ.has_key("XMLRPC_USER") or not os.environ.has_key("XMLRPC_PASSWORD"):
        print "Please set XMLRPC_USER and XMLRPC_PASSWORD in your OS environment to a lobby"
        print "accounts credentials."
        return 1
    else:
        XMLRPC_USER = os.environ["XMLRPC_USER"]
        XMLRPC_PASSWORD = os.environ["XMLRPC_PASSWORD"]

    if os.environ.has_key("XMLRPC_URL"):
        XMLRPC_URL = os.environ["XMLRPC_URL"]

    if args.verbose:
        if args.throttle > 0:
            sp = "at %.2f kb/s"%(args.throttle/1024.0)
        else:
            sp = "without upload throttling"
        print "Uploading file '%s' for owner '%s' with subject '%s', comment '%s' and tags '%s' %s."%(args.path.name, args.owner, args.title, args.comment, args.tags, sp)

    demofile = xmlrpclib.Binary(args.path.read())

    curltrans = pyCURLTransport.PyCURLTransport()
    if args.throttle > 0:
        curltrans._curl.setopt(pycurl.MAX_SEND_SPEED_LARGE, args.throttle)

    rpc_srv = xmlrpclib.ServerProxy(XMLRPC_URL, transport=curltrans)
    result = rpc_srv.xmlrpc_upload(XMLRPC_USER, XMLRPC_PASSWORD, os.path.basename(args.path.name), demofile, args.title, args.comment, args.tags, args.owner)

    if args.verbose:
        print "%s" % result

    return int(result[0])

if __name__ == "__main__":
    sys.exit(main())
