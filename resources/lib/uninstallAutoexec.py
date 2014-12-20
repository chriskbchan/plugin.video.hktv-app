# -*- coding: utf-8 -*-

import os, xbmc, xbmcaddon, xbmcvfs

UTF8 = 'utf-8'

addon = xbmcaddon.Addon(id='plugin.video.hktv-app')
__addonname__    = addon.getAddonInfo('name')
__addonicon__    = addon.getAddonInfo('icon')
__addonprofile__ = addon.getAddonInfo('profile')
__addonpath__    = addon.getAddonInfo('path')

USERDATAPATH = xbmc.translatePath(__addonprofile__)
AUTOEXEC = 'autoexec.py'
AUTOEXEC_SRC = os.path.join(__addonpath__, AUTOEXEC)
AUTOEXEC_DST = os.path.join('special://userdata',  AUTOEXEC)

try:
    xbmc.log('dst=%s' % AUTOEXEC_DST, xbmc.LOGDEBUG)
    if xbmcvfs.exists(AUTOEXEC_DST):
        xbmcvfs.delete(AUTOEXEC_DST)
    txt = addon.getLocalizedString(1071)
except:
    txt = addon.getLocalizedString(9031)

xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__addonname__, txt.encode(UTF8), 5000, __addonicon__))
