# -*- coding: utf-8 -*-
# HKTV App 香港電視
# Written by chriskbchan

import urllib, urllib2, cookielib, json, uuid
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import os, time, datetime, sys
from xml.etree import ElementTree
from utils import *


# Init Addon
addon = xbmcaddon.Addon()
hktvUser = addon.getSetting('username')
hktvPass = addon.getSetting('password')
videoLim = addon.getSetting('maxvideos')
vshopLim = addon.getSetting('maxshops')
autoLive = addon.getSetting('autolive')
showEpg  = addon.getSetting('showepg')
showShop = addon.getSetting('showshop')
showFeat = addon.getSetting('showfeat')
showProg = addon.getSetting('showprog')
#cacheSec = int(addon.getSetting('cachesec'))
__addonname__ = addon.getAddonInfo('name')
__addonicon__ = addon.getAddonInfo('icon')
__addonpath__ = addon.getAddonInfo('path')
__addonprofile__ = addon.getAddonInfo('profile')
__addonversion__ = addon.getAddonInfo('version')

# URLs
loginURL = 'https://www.hktvmall.com/hktv/zh/j_spring_security_check'
tokenURL = 'http://www.hktvmall.com/ott/token'
fListURL = 'http://ott-www.hktvmall.com/api/lists/getFeature'
pListURL = 'http://ott-www.hktvmall.com/api/lists/getProgram'
sListURL = 'http://ott-www.hktvmall.com/api/lists/getProduct'
tvEpgURL = 'http://ott-www.hktvmall.com/api/lists/getEpg'
plReqURL = 'http://ott-www.hktvmall.com/api/playlist/request'
vInfoURL = 'http://ott-www.hktvmall.com/api/video/details'
mListURL = 'http://ott-www.hktvmall.com/api/preroll/getList'


def parse_argv():
    global mode, uid, muid, tok, expy, pvid, pgid

    params = {}
    try:
        params = dict( arg.split( "=" ) for arg in ((sys.argv[2][1:]).split( "&" )) )
    except:
        params = {}

    mode = dequote(params.get('mode', None))
    uid  = dequote(params.get('uid' , '1'))
    muid = dequote(params.get('muid', '1'))
    tok  = dequote(params.get('t'   , ''))
    expy = dequote(params.get('expy', str(int(time.time())+604800)))
    pvid = dequote(params.get('pvid', '1'))
    pgid = dequote(params.get('pgid', '1'))

    try:
       mode = int(params.get('mode', None ))
    except:
       mode = None


def login(username=None, password=None):
    global cj

    log('user length: %s' % username.__len__())
    log('pass length: %s' % password.__len__())
    try:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(loginURL)
        payload = { 'j_username' : username, 'j_password' : password  }
        resp = opener.open(req, urllib.urlencode(payload))

        log('Save cookie: %s' % COOKIE)
        cj.save(COOKIE, ignore_discard=True)
    except:
        popup(addon.getLocalizedString(9010))


def getToken():
    global cj, token
    global uid, muid, tok, expy

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(tokenURL)
    resp = opener.open(req)
    token = json.loads(resp.read())

    uid = token['user_id']
    muid = token['mallUid']
    tok = token['token']
    expy = token['expiry_date']


def flattenJsonInfo(dInfo, progID=0):
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
    for c in range(dChildInfo.__len__()):
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


def getEpg():
    global cj
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    # Get EPG
    cache = cacheLoad(EPG_CACHE)
    if cache is None:
        log('EPG loading...')
        req = urllib2.Request(tvEpgURL)
        resp = opener.open(req)
        eJson = json.loads(resp.read())
        cacheSave(EPG_CACHE, json.dumps(eJson))
    else:
        log('EPG using cache')
        eJson = json.loads(cache.decode(UTF8))

    return eJson


def getAllPlaylist(lim=20, clearCache=False):
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
        payload = { 'lim' : lim, 'ofs' : '0' }
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
        for d in range(dramaInfo.__len__()):
            di = flattenJsonInfo(dramaInfo[d])
            for v in range(di.__len__()):
                vList.append(di[v])

    # Get program playlist
    cache = cacheLoad(PROGRAM_CACHE)
    if cache is None:
        log('Program list loading...')
        req = urllib2.Request(pListURL)
        payload = { 'lim' : lim, 'ofs' : '0' }
        resp = opener.open(req, urllib.urlencode(payload))
        aJson = json.loads(resp.read())
        cacheSave(PROGRAM_CACHE, json.dumps(aJson))
    else:
        log('Program list using cache')
        aJson = json.loads(cache.decode(UTF8))

    if 'videos' in aJson:
        progInfo = aJson['videos']
        for p in range(progInfo.__len__()):
            pList.append(
                { 'category' : progInfo[p]['category'],
                  'v_level'  : progInfo[p]['video_level'],
                  'pgid'     : progInfo[p]['video_id'],
                  'vid'      : progInfo[p]['video_id'],
                  'title'    : progInfo[p]['title'].encode(UTF8),
                  'thumbnail': progInfo[p]['thumbnail']
                })
            dramaInfo = progInfo[p]['child_nodes']
            for p2 in range(dramaInfo.__len__()):
                di = flattenJsonInfo(dramaInfo[p2], int(progInfo[p]['video_id']))
                for v in range(di.__len__()):
                    aList.append(di[v])

    return (vList, pList, aList)


def getShopPlaylist(lim=50, clearCache=False):
    global cj
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    sList = []  # shopping video list

    # Get shopping playlist
    cache = cacheLoad(SHOPPING_CACHE)
    if cache is None:
        log('Shopping list loading...')
        req = urllib2.Request(sListURL)
        payload = { 'lim' : lim, 'ofs' : '0' }
        resp = opener.open(req, urllib.urlencode(payload))
        sJson = json.loads(resp.read())
        cacheSave(SHOPPING_CACHE, json.dumps(sJson))
    else:
        log('Shopping list using cache')
        sJson = json.loads(cache.decode(UTF8))

    if 'videos' in sJson:
        prodInfo = sJson['videos']
        for p in range(prodInfo.__len__()):
            sList.append(
                { 'category' : prodInfo[p]['category'],
                  'v_level'  : prodInfo[p]['video_level'],
                  'pgid'     : prodInfo[p]['video_id'],
                  'vid'      : prodInfo[p]['video_id'],
                  'title'    : prodInfo[p]['title'].encode(UTF8),
                  'thumbnail': prodInfo[p]['thumbnail'],
                  'duration' : prodInfo[p]['duration']
                })

    return sList


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
    req = urllib2.Request(plReqURL)
    payload = { 'uid'  : uid,
                'vid'  : str(vid),
                'udid' : UDID,
                't'    : tok,
                'ppos' : '0',
                '_'    : expy   }
    resp = opener.open(req, urllib.urlencode(payload))
    pList = json.loads(resp.read())
    
    return pList


def parseAds(xml):
    try:
        tree = ElementTree.fromstring(xml)
        ads = []

        for Ad in tree.findall('.//Ad'):
            id = int(Ad.get('id'))
            seq = int(Ad.get('sequence'))
            idx = seq - 1
            ads.append( {'id' : id, 'seq' : seq} )
        
            imList = []
            for Imp in Ad.findall('.//Impression'):
                url = str.strip(Imp.text)
                if url:
                    imList.append(url)
            ads[idx]['imp'] = imList
        
            for Dur in Ad.findall('.//Duration'):
                st = time.strptime(str.strip(Dur.text), '%H:%M:%S')
                totalSec = st.tm_min * 60 + st.tm_sec
            ads[idx]['dur'] = totalSec
        
            for Media in Ad.findall('.//MediaFile'):
                url = str.strip(Media.text)
            ads[idx]['media'] = url
        
            tkList = [ [], [] ]
            tkNext = 0
            for Track in Ad.findall('.//Tracking'):
                url = str.strip(Track.text)
                tkList[tkNext].append(url)
                tkNext = (tkNext + 1) % 2
            ads[idx]['track'] = tkList

    except Exception as e:
        logerr('Error parsing Ads, err=%s' % e)

    return ads


def getAds(muid, uid, ads_cat, tok, vid, vn, vt):
    global cj

    ads = ''
    try:
        ads_list = ','.join(ads_cat)
        ads_list = ads_list.join(['{','}'])

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(mListURL)
        payload = { 'muid' : muid,
                    'uid'  : uid,
                    'rt'   : 'WEB',
                    'ec'   : ads_list,
                    't'    : tok,
                    'vid'  : vid,
                    'vn'   : vn,
                    'vt'   : vt   }
        log('getAds:%s' % urllib.urlencode(payload))
        resp = opener.open(req, urllib.urlencode(payload))
        mXML = resp.read()
        #log('mXML:%s' % mXML)

        ads = parseAds(mXML)
        return ads
    except Exception as e:
        logerr('Error loading Ads, err=%s' % e)
        return ads


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

cj = cookielib.LWPCookieJar()
USERDATAPATH = xbmc.translatePath(__addonprofile__)
if not xbmcvfs.exists(USERDATAPATH):
     xbmcvfs.mkdir(USERDATAPATH)
COOKIE = os.path.join(USERDATAPATH, 'cookie.txt')
FEATURE_CACHE = os.path.join(USERDATAPATH, 'feature.json')
PROGRAM_CACHE = os.path.join(USERDATAPATH, 'program.json')
SHOPPING_CACHE = os.path.join(USERDATAPATH, 'shopping.json')
EPG_CACHE = os.path.join(USERDATAPATH, 'epg.json')


# Start
loginfo('### Start HKTV App version %s' % __addonversion__)
baseURL = sys.argv[0]
addonHandle = int(sys.argv[1])

xbmcplugin.setContent(addonHandle, 'tvshows')

# Load Cookies
try:
    log('Load cookie: %s' % COOKIE)
    cj.load(COOKIE, ignore_discard=True)
except Exception as e:
    logerr('Error loading %s, err=%s' % (COOKIE, e))

parse_argv()

log('Mode: %s, args[uid,muid,tok,expy,pvid,pgid] = %s' % (mode, ','.join([uid,muid,tok,expy,pvid,pgid])))
log('Addon Profile: %s' % __addonprofile__)
if mode == None:

    loginfo('Selected Main Menu')

    # Login
    if uid == '1':
        login(hktvUser, hktvPass)
        getToken()
        if uid == '1' and hktvUser:
            popup(addon.getLocalizedString(9000))
        elif not hktvUser:
            popup(addon.getLocalizedString(8000))
            addon.openSettings()
        log('User ID: %s' % uid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    defaultThumbnail = ''   # default thumbnail
    failCount = 0           # fail count to get link
    
    # Generate Playlist
    # Live
    liveURL = None
    liveItem = None
    for i in range(videoList.__len__()):
        v = videoList[i]
        if v['category'] == 'LIVE':
            pList = getVideoPlaylist(int(v['vid']))
            if 'm3u8' in pList:
                liveURL = pList['m3u8']
                liveTitle = '[COLOR %s]%s[/COLOR]' % ('red', v['title'])
                defaultThumbnail = v['thumbnail']    # for undefined thumbnail
            else:
                liveURL = baseURL
                liveTitle = v['title']
                failCount += 1
            liveItem = createListItem(liveTitle, v['thumbnail'], liveURL, v['duration'], '', playable='true', folder=False)

    if showEpg == 'true':
        epgText = 'HKTV '+addon.getLocalizedString(1030)
        payload = { 'mode' : '10' }
        epgURL = baseURL +'?'+ urllib.urlencode(payload)
        createListItem(epgText, defaultThumbnail, epgURL , '0', epgText, playable='false', folder=True)

    # Shopping
    if showShop == 'true':
        shopText = 'HKTV '+addon.getLocalizedString(1005)
        payload = { 'mode' : '20', 'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy) }
        shopURL = baseURL +'?'+ urllib.urlencode(payload)
        createListItem(shopText, defaultThumbnail, shopURL , '0', shopText, playable='false', folder=True)

    # Feature
    if showFeat == 'true':
        for i in range(videoList.__len__()):
            v = videoList[i]
            if v['category'] == 'DRAMA' and v['v_level'] == '1':  # Episode Parent
                payload = { 'mode' : v['v_level'], 'muid' : muid,
                            'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pvid' : str(v['pvid']),
                            'pgid' : str(v['pgid']) }
                playURL = baseURL +'?'+ urllib.urlencode(payload)
                log('Episode: pvid=%s, vid=%s, playURL=%s' % (v['pvid'], v['vid'], playURL))
                #vd = getVideoDetail(int(v['vid']))
                #if 'synopsis' in vd:
                #    desc = vd['synopsis']
                videoTitle = '[COLOR white][%s][/COLOR] %s' % (addon.getLocalizedString(1011).encode(UTF8), v['title'])
                createListItem(videoTitle, v['thumbnail'], playURL, v['duration'], '', playable='true', folder=True)

    # Program
    if showProg == 'true':
        for i in range(progList.__len__()):
            p = progList[i]
            if p['category'] == 'DRAMA' and p['v_level'] == '2':  # Program Parent
                payload = { 'mode' : p['v_level'], 'muid' : muid,
                            'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pgid' : str(p['pgid']) }
                playURL = baseURL +'?'+ urllib.urlencode(payload)
                log('Program: pgid=%s, vid=%s, playURL=%s' % (p['pgid'], p['vid'], playURL))
                #pd = getVideoDetail(int(p['vid']))
                #if 'synopsis' in pd:
                #    desc = pd['synopsis']
                createListItem(p['title'], p['thumbnail'], playURL, '0', '', playable='false', folder=True)

    xbmcplugin.endOfDirectory(handle=addonHandle)

    log('Auto Live: %s' % autoLive)
    if autoLive == 'true' and liveURL:
        popup(addon.getLocalizedString(1000))
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(liveURL, liveItem)

    if failCount > 0:
        popup(addon.getLocalizedString(9020))

    loginfo('Finished Main Menu')

elif mode == 1:

    loginfo('Selected Parent VID: %s' % pvid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    failCount = 0

    dPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    dPlaylist.clear()

    for i in range(videoList.__len__()):
        v = videoList[i]
        if v['category'] == 'DRAMA' and v['pvid'] == pvid:
            if v['v_level'] == '1':
                dIndex = 0
            if v['v_level'] == '0':
                pList = getVideoPlaylist(int(v['vid']))
                # insert Ads
                if 'ads_cat' in pList:
                    adInfo = getAds(muid, uid, pList['ads_cat'], tok, v['vid'], v['title'], v['category'])
                    #log('AdInfo: %s'+ adInfo)
                    for ad in range(adInfo.__len__()):
                        if 'media' in adInfo[ad]:
                           ai = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
                           adInfoJson = json.dumps(adInfo[ad])
                           #log('adInfoJson:%s-%s' % (dIndex, adInfoJson))
                           ai.setInfo(type='video', infoLabels={ 'Plot': adInfoJson })      # plot as metadata
                           ai.setInfo(type='video', infoLabels={ 'PlotOutline': 'ADS' })
                           mediaURL = adInfo[ad]['media']
                           dPlaylist.add(url=mediaURL, listitem=ai, index=dIndex)
                           log('Playlist: %s-%s' % (dIndex, mediaURL))
                           dIndex += 1
                # insert video
                li = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
                li.addStreamInfo('video', { 'duration': v['duration'] })
                if 'm3u8' in pList:
                    playURL = pList['m3u8']
                    li.setInfo(type='video', infoLabels={ 'PlotOutline': v['category'] })
                    dPlaylist.add(url=playURL, listitem=li, index=dIndex)
                    log('Playlist:%s-%s' % (dIndex, ','.join([v['vid'], v['category'], v['v_level'], v['pvid']])))
                    dIndex += 1
                else:
                    failCount += 1

    if failCount > 0:
        popup(addon.getLocalizedString(9020))
    else:
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(dPlaylist)

    loginfo('Finished Parent VID: %s' % pvid)

elif mode == 2:

    loginfo('Selected Program VID: %s' % pgid)

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    for i in range(allList.__len__()):
        v = allList[i]
        if v['category'] == 'DRAMA' and v['pgid'] == pgid:
            if v['v_level'] == '1':
                payload = { 'mode' : str(mode + int(v['v_level'])), 'muid' : muid,
                            'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pvid' : str(v['pvid']),
                            'pgid' : str(v['pgid']) }
                playURL = baseURL +'?'+ urllib.urlencode(payload)
                log('Program: pgid=%s, vid=%s, playURL=%s' % (v['pgid'], v['vid'], playURL))
                #vd = getVideoDetail(int(v['vid']))
                #if 'synopsis' in vd:
                #    desc = vd['synopsis']
                createListItem(v['title'], v['thumbnail'], playURL, v['duration'], '', playable='true', folder=True)

    xbmcplugin.endOfDirectory(handle=addonHandle)

    loginfo('Finished Program VID: %s' % pgid)

elif mode == 3:

    loginfo('Selected Program / Parent VID : %s / %s' % (pgid, pvid))

    # Retrieve Playlist
    (videoList, progList, allList) = getAllPlaylist(videoLim)

    failCount = 0

    dPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    dPlaylist.clear()

    for i in range(allList.__len__()):
        v = allList[i]
        if v['category'] == 'DRAMA' and v['pvid'] == pvid:
            if v['v_level'] == '1':
                dIndex = 0
            if v['v_level'] == '0':
                pList = getVideoPlaylist(int(v['vid']))
                # insert Ads
                if 'ads_cat' in pList:
                    adInfo = getAds(muid, uid, pList['ads_cat'], tok, v['vid'], v['title'], v['category'])
                    #log('AdInfo:%s' % adInfo)
                    for ad in range(adInfo.__len__()):
                        if 'media' in adInfo[ad]:
                           ai = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
                           adInfoJson = json.dumps(adInfo[ad])
                           #log('adInfoJson:%s-%s' % (dIndex, adInfoJson))
                           ai.setInfo(type='video', infoLabels={ 'Plot': adInfoJson })      # plot as metadata
                           ai.setInfo(type='video', infoLabels={ 'PlotOutline': 'ADS' })
                           mediaURL = adInfo[ad]['media']
                           dPlaylist.add(url=mediaURL, listitem=ai, index=dIndex)
                           log('Playlist:%s-%s' % (dIndex, mediaURL))
                           dIndex += 1
                # insert video
                li = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
                li.addStreamInfo('video', { 'duration': v['duration'] })
                if 'm3u8' in pList:
                    playURL = pList['m3u8']
                    li.setInfo(type='video', infoLabels={ 'PlotOutline': v['category'] })
                    dPlaylist.add(url=playURL, listitem=li, index=dIndex)
                    log('Playlist:%s-%s' % (dIndex, ','.join([v['vid'], v['category'], v['v_level'], v['pvid']])))
                    dIndex += 1
                else:
                    failCount += 1

    if failCount > 0:
        popup(addon.getLocalizedString(9020))
    else:
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(dPlaylist)

    loginfo('Finished Program / Parent VID : %s / %s' % (pgid, pvid))

elif mode == 10:

    loginfo('Selected EPG')

    today = datetime.datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)
    tmw   = today + datetime.timedelta(days=1)
    dat   = today + datetime.timedelta(days=2)
    datt  = today + datetime.timedelta(days=3)
    t0  = secondSinceEpoch(today)# + 21600
    t1  = secondSinceEpoch(tmw)
    t2  = secondSinceEpoch(dat)
    t3  = secondSinceEpoch(datt)
    t0Text = addon.getLocalizedString(1040)
    t1Text = addon.getLocalizedString(1041)
    t2Text = addon.getLocalizedString(1042)
    epgLineForm = '[COLOR %s][%s][/COLOR] [B]%s[/B] - %s'
    epgLineLive = '%s [COLOR red](%s)[/COLOR]' % (epgLineForm, addon.getLocalizedString(1050))

    try:
        epgJson = getEpg()
        epgListEnrich = []

        prevTime = 0
        if 'epg' in epgJson:
            epgList = epgJson['epg']
            for e in epgList:
                if prevTime == 0:
                    prevTitle = e['title']
                    prevTime  = int(e['start_time'])
                else:
                    showTime  = int(e['start_time'])
                    # add previous show
                    epgListEnrich.append({'start':prevTime, 'end':showTime, 'title':prevTitle})
                    prevTitle = e['title']
                    prevTime  = showTime
    
        now = int(time.time())
        for e in epgListEnrich:
            stTime = e['start']
            enTime = e['end']
            eTime = datetime.datetime.fromtimestamp(stTime)
            if stTime <= t1 and stTime > t0:
                textColor = 'orange'
                dayText = t0Text
            elif stTime <= t2 and stTime > t1:
                textColor = 'green'
                dayText = t1Text
            elif stTime <= t3 and stTime > t2:
                textColor = 'magenta'
                dayText = t2Text
            else:
                textColor = dayText = ''
            if textColor and dayText:
                if now > stTime and now <= enTime:
                    epgLine = epgLineLive % (textColor, dayText, eTime.strftime('%H:%M'), e['title'])
                else:
                    epgLine = epgLineForm % (textColor, dayText, eTime.strftime('%H:%M'), e['title'])
                createListItem(epgLine, '', baseURL , '0', '', playable='false', folder=False)
    except Exception as e:
        logerr('EPG err=%s' % e)

    xbmcplugin.endOfDirectory(handle=addonHandle)

    loginfo('Finished EPG')

elif mode == 20:

    loginfo('Selected Shopping List')

    # Retrieve Playlist
    shopList = getShopPlaylist(vshopLim)

    for i in range(shopList.__len__()):
        v = shopList[i]
        if v['category'] == 'PRODUCT':
            payload = { 'mode' : '21', 'muid' : muid,
                        'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pvid' : str(v['vid']),
                        'pgid' : str(v['vid']) }
            playURL = baseURL +'?'+ urllib.urlencode(payload)
            log('Shopping: vid=%s, playURL=%s' % (v['vid'], playURL))
            createListItem(v['title'], v['thumbnail'], playURL, v['duration'], '', playable='true', folder=True)

    xbmcplugin.endOfDirectory(handle=addonHandle)

    loginfo('Finished Shopping List')

elif mode == 21:

    loginfo('Selected Shopping VID: %s' % pvid)

    pList = getVideoPlaylist(int(pvid))
    if 'm3u8' in pList:
        shopURL = pList['m3u8']
        vd = getVideoDetail(int(pvid))
        if 'title' in vd:
            shopItem = createListItem(vd['title'], vd['thumbnail'], shopURL, vd['duration'], '', playable='true', folder=False)
        else:
            shopItem = createListItem('', '', shopURL, '', '', playable='true', folder=False)
        xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(shopURL, shopItem)
    else:
        popup(addon.getLocalizedString(9020))

    loginfo('Finished Shopping VID: %s' % pvid)

#
#   Do not go gentle into that good night,
#   Old age should burn and rave at close of day;
#   Rage, rage against the dying of the light.  
#                      - Dylan Thomas (1914-1953)
#
