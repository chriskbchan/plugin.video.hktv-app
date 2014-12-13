import os, xbmc, xbmcaddon, xbmcvfs

def cacheClear(fn):
    if xbmcvfs.exists(fn):
        xbmcvfs.delete(fn)


addon = xbmcaddon.Addon(id='plugin.video.hktv-app')
__addonprofile__ = addon.getAddonInfo('profile')

USERDATAPATH = xbmc.translatePath(__addonprofile__)
COOKIE = os.path.join(USERDATAPATH, 'cookie.txt')
FEATURE_CACHE = os.path.join(USERDATAPATH, 'feature.json')
PROGRAM_CACHE = os.path.join(USERDATAPATH, 'program.json')
EPG_CACHE = os.path.join(USERDATAPATH, 'epg.json')

cacheClear(COOKIE)
cacheClear(FEATURE_CACHE)
cacheClear(PROGRAM_CACHE)
cacheClear(EPG_CACHE)
