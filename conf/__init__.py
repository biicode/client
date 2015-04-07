'''Defines environment variables'''
import os
from biicode.common.conf.configure_environment import get_env
from biicode.common.conf import MEGABYTE

BII_RESTURL = get_env('BII_RESTURL', 'https://biiserverproduction.herokuapp.com')
