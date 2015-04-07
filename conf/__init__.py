'''Defines environment variables'''
import os
from biicode.common.conf.configure_environment import get_env
from biicode.common.conf import MEGABYTE

BII_RESTURL = get_env('BII_RESTURL', 'https://biiserverproduction.herokuapp.com')
# web url, for loading resources, such as javascript and css files
BII_WEBURL = get_env('BII_WEBURL', 'http://www.biicode.com')
BII_WEBSTATIC = get_env('BII_WEBSTATIC', 'https://biiwebproduction.s3.amazonaws.com')
