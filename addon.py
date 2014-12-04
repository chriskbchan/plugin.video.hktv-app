# -*- coding: utf-8 -*-
# HKTV App 香港電視
# Written by chriskbchan

import urllib, urllib2, cookielib, json, uuid
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import os, time, sys

UTF8 = 'utf-8'

# Init Addon
addon = xbmcaddon.Addon()
hktvUser = addon.getSetting('username')
hktvPass = addon.getSetting('password')
videoLim = addon.getSetting('maxvideos')
autoLive = addon.getSetting('autolive')
cacheSec = int(addon.getSetting('cachesec'))
__addonname__ = addon.getAddonInfo('name')
__addonicon__ = addon.getAddonInfo('icon')
__addonpath__ = addon.getAddonInfo('path')
__addonprofile__ = addon.getAddonInfo('profile')
__addonversion__ = addon.getAddonInfo('version')

# URLs
loginURL = 'https://www.hktvmall.com/hktv/zh/j_spring_security_check'
tokenURL = 'http://www.hktvmall.com/ott/token'
fListURL = 'http://ott-www.hktvmall.com/api/lists/getFeature'
aListURL = 'http://ott-www.hktvmall.com/api/lists/getProgram'
pListURL = 'http://ott-www.hktvmall.com/api/playlist/request'
vInfoURL = 'http://ott-www.hktvmall.com/api/video/details'


def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def parse_argv():
    global mode, uid, tok, expy, pvid, pgid

    params = {}
    try:
        params = dict( arg.split( "=" ) for arg in ((sys.argv[2][1:]).split( "&" )) )
    except:
        params = {}

    mode = dequote(params.get('mode', None))
    uid  = dequote(params.get('uid' , '1'))
    tok  = dequote(params.get('t'   , ''))
    expy = dequote(params.get('expy', str(int(time.time())+604800)))
    pvid = dequote(params.get('pvid', '1'))
    pgid = dequote(params.get('pgid', '1'))

    try:
       mode = int(params.get('mode', None ))
    except:
       mode = None


def dequote(u):
    try:
        u = urllib.unquote_plus(u)
    except:
        pass
    return u


def popup(txt):
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__addonname__, txt.encode(UTF8), 5000, __addonicon__))


def cacheSave(fn, data, forceClear=False):
    log('Save cache: ' + fn)
    if xbmcvfs.exists(fn):
        eTime = int(xbmcvfs.Stat(fn).st_mtime()) + cacheSec
        cTime = int(time.time())
        log('cTime=' + str(cTime) + ', eTime=' + str(eTime))
        if cTime > eTime:
            log('Cache reset: expired')
            xbmcvfs.delete(fn)
        elif forceClear:
            log('Cache reset: force clear')
            xbmcvfs.delete(fn)

    try:
        fh = xbmcvfs.File(fn, 'w')
        fh.write(data)
        fh.close()
        log('Cache saved')
    except Exception as e:
        log('Error saving cache '+ fn +', err='+ str(e))


def cacheLoad(fn):
    log('Load cache: ' + fn)
    data = None
    if xbmcvfs.exists(fn):
        eTime = int(xbmcvfs.Stat(fn).st_mtime()) + cacheSec
        cTime = int(time.time())
        log('cTime=' + str(cTime) + ', eTime=' + str(eTime))
        if cTime > eTime:
            log('Cache reset: expired')
            xbmcvfs.delete(fn)
        else:
            fh = xbmcvfs.File(fn)
            data = fh.read()
            fh.close()

    return data


def login(username=None, password=None):
    global cj

    log('user length: ' + str(username.__len__()))
    log('pass length: ' + str(password.__len__()))
    try:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(loginURL)
        payload = { 'j_username' : username, 'j_password' : password  }
        resp = opener.open(req, urllib.urlencode(payload))

        log('Save cookie: ' + COOKIE)
        cj.save(COOKIE, ignore_discard=True)
    except:
        popup(addon.getLocalizedString(9010))


def getToken():
    global cj, token
    global uid, tok, expy

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(tokenURL)
    resp = opener.open(req)
    token = json.loads(resp.read())

    uid = token['user_id']
    tok = token['token']
    expy = token['expiry_date']


def flattenDramaInfo(dInfo, progID=0):
    dList = []

    dList.append(
      { 'category' : dInfo['category'],
        'v_level'  : dInfo['video_level'],
        'pgid'     : str(progID),
        'vid'      : dInfo['video_id'],
        'pvid'     : dInfo['video_id'],
        'title'    : dInfo['title'].encode(UTF8),
        'thumbnail': dInfo['thumbnail'],
        'duration' : dInfo['duration']
      })
    dChildInfo = dInfo['child_nodes']
    parentVID = dInfo['video_id']
    for c in range (0, dChildInfo.__len__()):
      dList.append(
        { 'category' : dChildInfo[c]['category'],
          'v_level'  : dChildInfo[c]['video_level'],
          'pgid'     : str(progID),
          'vid'      : dChildInfo[c]['video_id'],
          'pvid'     : parentVID,
          'title'    : dChildInfo[c]['title'].encode(UTF8),
          'thumbnail': dChildInfo[c]['thumbnail'],
          'duration' : dChildInfo[c]['duration']
        })

    return dList


def getAllPlaylist(videoLim=20, clearCache=False):
    global cj
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    vList = []  # feature video list
    pList = []  # program video list (program level)
    aList = []  # program video list (video level)

    # Get feature playlist
    cache = cacheLoad(FEATURE_CACHE)
    if cache is None:
        log('Feature list loading...')
        req = urllib2.Request(fListURL)
        payload = { 'lim' : videoLim, 'ofs' : '0' }
        resp = opener.open(req, urllib.urlencode(payload))
        fJson = json.loads(resp.read())
        cacheSave(FEATURE_CACHE, json.dumps(fJson))
    else:
        log('Feature list using cache')
        fJson = json.loads(cache.decode(UTF8))

    if 'promo_video' in fJson:
        liveInfo = fJson['promo_video']
        vList.append(
          { 'category' : liveInfo['category'],
            'v_level'  : liveInfo['video_level'],
            'pgid'     : liveInfo['video_id'],
            'vid'      : liveInfo['video_id'],
            'pvid'     : liveInfo['video_id'],
            'title'    : liveInfo['title'].encode(UTF8),
            'thumbnail': liveInfo['thumbnail'],
            'duration' : liveInfo['duration']
          })
    
    if 'videos' in fJson:
        dramaInfo = fJson['videos']
        for d in range (0, dramaInfo.__len__()):
            di = flattenDramaInfo(dramaInfo[d])
            for v in range (0, di.__len__()):
                vList.append(di[v])

    # Get program playlist
    cache = cacheLoad(PROGRAM_CACHE)
    if cache is None:
        log('Program list loading...')
        req = urllib2.Request(aListURL)
        payload = { 'lim' : videoLim, 'ofs' : '0' }
        resp = opener.open(req, urllib.urlencode(payload))
        aJson = json.loads(resp.read())
        cacheSave(PROGRAM_CACHE, json.dumps(aJson))
    else:
        log('Program list using cache')
        aJson = json.loads(cache.decode(UTF8))

    if 'videos' in aJson:
        progInfo = aJson['videos']
        for p in range (0, progInfo.__len__()):
            pList.append(
                { 'category' : progInfo[p]['category'],
                  'v_level'  : progInfo[p]['video_level'],
                  'pgid'     : progInfo[p]['video_id'],
                  'vid'      : progInfo[p]['video_id'],
                  'title'    : progInfo[p]['title'].encode(UTF8),
                  'thumbnail': progInfo[p]['thumbnail']
                })
            dramaInfo = progInfo[p]['child_nodes']
            for p2 in range (0, dramaInfo.__len__()):
                di = flattenDramaInfo(dramaInfo[p2], int(progInfo[p]['video_id']))
                for v in range (0, di.__len__()):
                    aList.append(di[v])

    return (vList, pList, aList)


def getVideoDetail(vid):
    # Video details
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(vInfoURL)
    payload = { 'vid'  : str(vid) }
    resp = opener.open(req, urllib.urlencode(payload))
    vInfo = json.loads(resp.read())

    return vInfo


def getVideoPlaylist(vid):
    # Video playlist
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(pListURL)
    payload = { 'uid'  : uid,
                'vid'  : str(vid),
                'udid' : UDID,
                't'    : tok,
                'ppos' : '0',
                '_'    : expy   }
    resp = opener.open(req, urllib.urlencode(payload))
    pList = json.loads(resp.read())
    
    return pList


def createListItem(title, thumbnail, url, duration, desc, playable, folder):
    li = xbmcgui.ListItem(title, iconImage=__addonicon__, thumbnailImage=thumbnail)
    li.setInfo(type='video', infoLabels={ 'Title': title })
    li.setInfo(type='video', infoLabels={ 'Plot': desc })
    li.setProperty('IsPlayable', playable)
    li.setProperty('fanart_image', thumbnail)

    if not folder:
        li.addStreamInfo('video', { 'duration': duration })

    xbmcplugin.addDirectoryItem(handle=addonHandle, url=url, listitem=li, isFolder=folder)

    return li


###

# Init variables
UDID = str(uuid.uuid1())
videoList = []
progList = []

cj = cookielib.LWPCookieJar()
USERDATAPATH = xbmc.translatePath(__addonprofile__)
if not xbmcvfs.exists(USERDATAPATH):
     xbmcvfs.mkdir(USERDATAPATH)
COOKIE = os.path.join(USERDATAPATH, 'cookie.txt')
FEATURE_CACHE = os.path.join(USERDATAPATH, 'feature.json')
PROGRAM_CACHE = os.path.join(USERDATAPATH, 'program.json')


# Start
log('### Start HKTV App version ' + __addonversion__)
baseURL = sys.argv[0]
addonHandle = int(sys.argv[1])

xbmcplugin.setContent(addonHandle, 'tvshows')

# Load Cookies
try:
    log('Load cookie: ' + COOKIE)
    cj.load(COOKIE, ignore_discard=True)
except Exception as e:
    log('Error loading '+ COOKIE +', err='+ str(e))

parse_argv()

log('Mode: '+ str(mode) +', args[uid,tok,expy,pvid,pgid] = '+ ','.join([uid,tok,expy,pvid,pgid]))
log('Addon Profile: '+ __addonprofile__)
if mode == None:

    # Login
    if uid == '1':
        login(hktvUser, hktvPass)
        getToken()
        if uid == '1' and hktvUser:
            popup(addon.getLocalizedString(9000))
        elif not hktvUser:
            popup(addon.getLocalizedString(8000))
        log('User ID: '+ uid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    defaultThumbnail = ''
    
    # Generate Playlist
    # Live
    liveURL = None
    liveItem = None
    for i in range (0, videoList.__len__()):
        v = videoList[i]
        if v['category'] == 'LIVE':
            pList = getVideoPlaylist(int(v['vid']))
            liveURL = pList['m3u8']
            defaultThumbnail = v['thumbnail']    # for undefined thumbnail
            liveItem = createListItem(v['title'], v['thumbnail'], liveURL, v['duration'], '', playable='true', folder=False)

    sepText = '--- '+addon.getLocalizedString(1010)+' ---'
    createListItem(sepText, defaultThumbnail, baseURL , '0', '', playable='false', folder=False)

    # Feature
    for i in range (0, videoList.__len__()):
        v = videoList[i]
        if v['category'] == 'DRAMA' and v['v_level'] == '1':  # Episode Parent
            payload = { 'mode' : v['v_level'],
                        'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pvid' : str(v['pvid']),
                        'pgid' : str(v['pgid']) }
            playURL = baseURL +'?'+ urllib.urlencode(payload)
            log('Episode: pvid='+v['pvid']+', vid='+v['vid']+', playURL='+playURL)
            #vd = getVideoDetail(int(v['vid']))
            #if 'synopsis' in vd:
            #    desc = vd['synopsis']
            createListItem(v['title'], v['thumbnail'], playURL, v['duration'], '', playable='true', folder=True)

    sepText = '--- '+addon.getLocalizedString(1020)+' ---'
    createListItem(sepText, defaultThumbnail, baseURL , '0', '', playable='false', folder=False)

    # Program
    for i in range (0, progList.__len__()):
        p = progList[i]
        if p['category'] == 'DRAMA' and p['v_level'] == '2':  # Program Parent
            payload = { 'mode' : p['v_level'],
                        'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pgid' : str(p['pgid']) }
            playURL = baseURL +'?'+ urllib.urlencode(payload)
            log('Program: pgid='+p['pgid']+', vid='+p['vid']+', playURL='+playURL)
            #pd = getVideoDetail(int(p['vid']))
            #if 'synopsis' in pd:
            #    desc = pd['synopsis']
            createListItem(p['title'], p['thumbnail'], playURL, '0', '', playable='false', folder=True)

    xbmcplugin.endOfDirectory(handle=addonHandle)

    log('Auto Live: '+ autoLive)
    if autoLive == 'true' and liveURL:
        popup(addon.getLocalizedString(1000))
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(liveURL, liveItem)


elif mode == 1:

    log('Selected Parent VID: ' + pvid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    dPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    dPlaylist.clear()

    for i in range (0, videoList.__len__()):
        v = videoList[i]
        if v['category'] == 'DRAMA' and v['pvid'] == pvid:
            if v['v_level'] == '1':
                dIndex = 0
            if v['v_level'] == '0':
                li = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
                li.addStreamInfo('video', { 'duration': v['duration'] })
                pList = getVideoPlaylist(int(v['vid']))
                playURL = pList['m3u8']
                dPlaylist.add(url=playURL, listitem=li, index=dIndex)
                log('Playlist:'+ str(dIndex) +'-'+ ','.join([v['vid'], v['category'], v['v_level'], v['pvid']]))
                dIndex += 1

    xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(dPlaylist)

elif mode == 2:

    log('Selected Program VID: ' + pgid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    for i in range (0, allList.__len__()):
        v = allList[i]
        if v['category'] == 'DRAMA' and v['pgid'] == pgid:
            if v['v_level'] == '1':
                payload = { 'mode' : str(mode + int(v['v_level'])),
                            'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pvid' : str(v['pvid']),
                            'pgid' : str(v['pgid']) }
                playURL = baseURL +'?'+ urllib.urlencode(payload)
                log('Program: pgid='+v['pgid']+', vid='+v['vid']+', playURL='+playURL)
                #vd = getVideoDetail(int(v['vid']))
                #if 'synopsis' in vd:
                #    desc = vd['synopsis']
                createListItem(v['title'], v['thumbnail'], playURL, v['duration'], '', playable='true', folder=True)

    xbmcplugin.endOfDirectory(handle=addonHandle)

elif mode == 3:

    log('Selected Program / Parent VID : ' + pgid + '/' + pvid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    dPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    dPlaylist.clear()

    for i in range (0, allList.__len__()):
        v = allList[i]
        if v['category'] == 'DRAMA' and v['pvid'] == pvid:
            if v['v_level'] == '1':
                dIndex = 0
            if v['v_level'] == '0':
                li = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
                li.addStreamInfo('video', { 'duration': v['duration'] })
                pList = getVideoPlaylist(int(v['vid']))
                playURL = pList['m3u8']
                dPlaylist.add(url=playURL, listitem=li, index=dIndex)
                log('Playlist:'+ str(dIndex) +'-'+ ','.join([v['vid'], v['category'], v['v_level'], v['pvid']]))
                dIndex += 1

    xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(dPlaylist)

