from constants import *
import optparse
import sys
import os
import pritunl_client

def client():
    parser = optparse.OptionParser()
    parser.add_option('--version', action='store_true', help='Print version')
    (options, args) = parser.parse_args()

    if options.version:
        print '%s v%s' % (pritunl.__title__, pritunl.__version__)
        sys.exit(0)

    interface = pritunl_client.Interface()
    interface.main()