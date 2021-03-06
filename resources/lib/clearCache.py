# -*- coding: utf-8 -*-

import os, xbmc, xbmcaddon, xbmcvfs

UTF8 = 'utf-8'

def cacheClear(fn):
    if xbmcvfs.exists(fn):
        xbmcvfs.delete(fn)


addon = xbmcaddon.Addon(id='plugin.video.hktv-app')
__addonname__    = addon.getAddonInfo('name')
__addonicon__    = addon.getAddonInfo('icon')
__addonprofile__ = addon.getAddonInfo('profile')

USERDATAPATH = xbmc.translatePath(__addonprofile__)
COOKIE = os.path.join(USERDATAPATH, 'cookie.txt')
FEATURE_CACHE = os.path.join(USERDATAPATH, 'feature.json')
PROGRAM_CACHE = os.path.join(USERDATAPATH, 'program.json')
SHOPPING_CACHE = os.path.join(USERDATAPATH, 'shopping.json')
EPG_CACHE = os.path.join(USERDATAPATH, 'epg.json')

cacheClear(COOKIE)
cacheClear(FEATURE_CACHE)
cacheClear(PROGRAM_CACHE)
cacheClear(SHOPPING_CACHE)
cacheClear(EPG_CACHE)

META_PATH = os.path.join(USERDATAPATH, 'meta')
(dirs, files) = xbmcvfs.listdir(META_PATH)
for fn in files:
    #xbmc.log(msg=fn, level=xbmc.LOGDEBUG)
    xbmcvfs.delete(os.path.join(META_PATH, fn))

txt = addon.getLocalizedString(1060)
xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__addonname__, txt.encode(UTF8), 5000, __addonicon__))
