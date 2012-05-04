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
# XMLRPC_USER=Dansan XMLRPC_PASSWORD=SeCr3t ./xmlrpc_client.py 20130229_123456_RustyDelta_v2_88.sdf "awesome game" "checkout that dude in SE" tag1,tag2,tag3
#

import os
import sys
import xmlrpclib

def main(argv=None):
    XMLRPC_URL = "http://replays.admin-box.com/xmlrpc/"

    if argv is None:
        argv = sys.argv
    if len(argv) < 2 or len(argv) > 5:
        print "Usage: %s <demofile> [subject] [comment] [tags (comma separated)]" % (argv[0])
        print "(don't forget the XMLRPC_USER and XMLRPC_PASSWORD environment vars)"
        return 1
    elif len(argv) > 2 and len(argv[2]) > 50:
        print "subject: 50 char max"
        return 1
    elif len(argv) > 3 and len(argv[3]) > 512:
        print "comment: 512 char max"
        return 1
    if not os.environ.has_key("XMLRPC_USER") or not os.environ.has_key("XMLRPC_PASSWORD"):
        print "Please set XMLRPC_USER and XMLRPC_PASSWORD in your OS environment to a lobby"
        print "accounts credentials."
        return 1
    else:
        XMLRPC_USER = os.environ["XMLRPC_USER"]
        XMLRPC_PASSWORD = os.environ["XMLRPC_PASSWORD"]
    if os.environ.has_key("XMLRPC_URL"):
        XMLRPC_URL = os.environ["XMLRPC_URL"]

    for _ in range(len(argv), 5):
        argv.append("")
    
    path, subject, comment, tags = argv[1], argv[2], argv[3], argv[4]

    print "Uploading file '%s' with subject '%s', comment '%s' and tags '%s'."%(path, subject, comment, tags)

    demofile = xmlrpclib.Binary(open(path, "rb").read())

    rpc_srv = xmlrpclib.ServerProxy(XMLRPC_URL)
    result = rpc_srv.xmlrpc_upload(XMLRPC_USER, XMLRPC_PASSWORD, os.path.basename(path), demofile, subject, comment, tags)
    print "%s" % result

    return 0

if __name__ == "__main__":
    sys.exit(main())
