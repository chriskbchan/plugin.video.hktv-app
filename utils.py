# -*- coding: utf-8 -*-

import xbmc, xbmcaddon, xbmcvfs
import os, time, datetime, sys, json

UTF8 = 'utf-8'

addon = xbmcaddon.Addon()
__addonid__   = addon.getAddonInfo('id')
__addonname__ = addon.getAddonInfo('name')
__addonicon__ = addon.getAddonInfo('icon')
cacheSec = int(addon.getSetting('cachesec'))


def log(level, txt):
    message = '[%s]: %s' % (__addonid__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=level)


def dequote(u):
    try:
        u = urllib.unquote_plus(u)
    except:
        pass
    return u


def popup(txt):
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__addonname__, txt.encode(UTF8), 5000, __addonicon__))


def cacheSave(fn, data, forceClear=False):
    log(xbmc.LOGDEBUG, 'Save cache: ' + fn)
    if xbmcvfs.exists(fn):
        eTime = int(xbmcvfs.Stat(fn).st_mtime()) + cacheSec
        cTime = int(time.time())
        log(xbmc.LOGDEBUG, 'cTime=' + str(cTime) + ', eTime=' + str(eTime))
        if cTime > eTime:
            log(xbmc.LOGDEBUG, 'Cache reset: expired')
            xbmcvfs.delete(fn)
        elif forceClear:
            log(xbmc.LOGDEBUG, 'Cache reset: force clear')
            xbmcvfs.delete(fn)

    try:
        fh = xbmcvfs.File(fn, 'w')
        fh.write(data)
        fh.close()
        log(xbmc.LOGDEBUG, 'Cache saved')
    except Exception as e:
        log(xbmc.LOGERROR, 'Error saving cache '+ fn +', err='+ str(e))


def cacheLoad(fn):
    log(xbmc.LOGDEBUG, 'Load cache: ' + fn)
    data = None
    if xbmcvfs.exists(fn):
        eTime = int(xbmcvfs.Stat(fn).st_mtime()) + cacheSec
        cTime = int(time.time())
        log(xbmc.LOGDEBUG, 'cTime=' + str(cTime) + ', eTime=' + str(eTime))
        if cTime > eTime:
            log(xbmc.LOGDEBUG, 'Cache reset: expired')
            xbmcvfs.delete(fn)
        else:
            fh = xbmcvfs.File(fn)
            data = fh.read()
            fh.close()

    return data


def xbmcJsonRequest(params):
    data = json.dumps(params)
    req = xbmc.executeJSONRPC(data)
    resp = json.loads(req)

    try:
        if 'result' in resp:
            return resp['result']
        return None
    except KeyError:
        log(xbmc.LOGERROR, '[%s] %s' % (params['method'], resp['error']['message']))
        return None


def secondSinceEpoch(dtime):
    epoch = datetime.datetime(1970,1,1,8,0,0)       # assume HK GMT+8
    td = dtime - epoch
    if sys.version_info >= (2, 7):
       t = td.total_seconds()
    else:
       t = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    return int(t)

