# -*- coding: utf-8 -*-
# HKTV App 香港電視
# Written by chriskbchan

import urllib, urllib2, cookielib, json, uuid
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import os, time, sys

#UTF8 = 'utf-8'

#reload(sys)
#sys.setdefaultencoding(UTF8)

# Init Addon
addon = xbmcaddon.Addon()
hktvUser = addon.getSetting('username')
hktvPass = addon.getSetting('password')
videoLim = addon.getSetting('maxvideos')
__addonname__ = addon.getAddonInfo('name')
__addonicon__ = addon.getAddonInfo('icon')
__addonprofile__ = addon.getAddonInfo('profile')


def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def parse_argv():
    global mode, uid, tok, expy, pvid

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


def login(username=None, password=None):
    global cj

    loginURL = 'https://www.hktvmall.com/hktv/zh/j_spring_security_check'

    try:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(loginURL)
        payload = { 'j_username' : username, 'j_password' : password  }
        resp = opener.open(req, urllib.urlencode(payload))

        cj.save(COOKIE, ignore_discard=True)
        b = True
    except:
        b = False
    return b


def getToken():
    global cj, token
    global uid, tok, expy

    tokenURL = 'http://www.hktvmall.com/ott/token'

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(tokenURL)
    resp = opener.open(req)
    token = json.loads(resp.read())

    uid = token['user_id']
    tok = token['token']
    expy = token['expiry_date']


def getAllPlaylist(videoLim=20):
    global cj

    fListURL = 'http://ott-www.hktvmall.com/api/lists/getFeature'
    
    # Get all playlist
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(fListURL)
    payload = { 'lim' : videoLim, 'ofs' : '0' }
    resp = opener.open(req, urllib.urlencode(payload))
    fList = json.loads(resp.read())

    vList = []

    liveInfo = fList['promo_video']
    vList.append(
      { 'category' : liveInfo['category'],
        'v_level'  : liveInfo['video_level'],
        'vid'      : liveInfo['video_id'],
        'p_vid'    : liveInfo['video_id'],
        'title'    : liveInfo['title'],
        'thumbnail': liveInfo['thumbnail'],
        'duration' : liveInfo['duration']
      })
    
    dramaInfo = fList['videos']
    for d1 in range (0, dramaInfo.__len__()):
      vList.append(
        { 'category' : dramaInfo[d1]['category'],
          'v_level'  : dramaInfo[d1]['video_level'],
          'vid'      : dramaInfo[d1]['video_id'],
          'p_vid'    : dramaInfo[d1]['video_id'],
          'title'    : dramaInfo[d1]['title'],
          'thumbnail': dramaInfo[d1]['thumbnail'],
          'duration' : dramaInfo[d1]['duration']
        })
      dramaChildInfo = dramaInfo[d1]['child_nodes']
      parentVID = dramaInfo[d1]['video_id']
      for d2 in range (0, dramaChildInfo.__len__()):
        vList.append(
          { 'category' : dramaChildInfo[d2]['category'],
            'v_level'  : dramaChildInfo[d2]['video_level'],
            'vid'      : dramaChildInfo[d2]['video_id'],
            'p_vid'    : parentVID,
            'title'    : dramaChildInfo[d2]['title'],
            'thumbnail': dramaChildInfo[d2]['thumbnail'],
            'duration' : dramaChildInfo[d2]['duration']
          })

    return vList
    
def getVideoPlaylist(vid):
    global uid, tok, expy, UDID

    pListURL = 'http://ott-www.hktvmall.com/api/playlist/request'

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

###

# Init variables
UDID = str(uuid.uuid1())
videoList = []

cj = cookielib.LWPCookieJar()
COOKIE = xbmc.translatePath(__addonprofile__)
COOKIE = os.path.join(COOKIE, 'cookie.txt')

# Start
baseURL = sys.argv[0]
addonHandle = int(sys.argv[1])

xbmcplugin.setContent(addonHandle, 'tvshows')

# Load Cookies
try:
    cj.load(COOKIE, ignore_discard=True)
except Exception as e:
    log('Error loading '+ COOKIE +', err='+ str(e))

parse_argv()

log("Mode: "+str(mode))
log('args[uid,tok,expy,pvid] = '+ ','.join([uid,tok,expy,pvid]))
if mode == None:

    # Login
    if uid == '1':
        login(hktvUser, hktvPass)
        getToken()
        log("User ID: "+ uid)
    
    # Retrieve Playlist
    videoList = getAllPlaylist(videoLim)
    
    # Generate Playlist
    for i in range(0, videoList.__len__()):
       v = videoList[i]
       #log("Generate Playlist"+ v['vid'])

       if v['category'] == 'LIVE':
           pList = getVideoPlaylist(int(v['vid']))
           playURL = pList['m3u8']
           li = xbmcgui.ListItem(v['title'], iconImage=__addonicon__, thumbnailImage=v['thumbnail'])
           li.addStreamInfo('video', { 'duration': v['duration'] })
           li.setProperty('IsPlayable', 'true')
           li.setProperty('fanart_image', v['thumbnail'])
           xbmcplugin.addDirectoryItem(handle=addonHandle, url=playURL, listitem=li, isFolder=False)
       elif v['category'] == 'DRAMA' and v['v_level'] == '1':  # Parent
           payload = { 'mode' : '1',
                       'uid'  : str(uid), 't'    : str(tok), 'expy' : str(expy), 'pvid' : str(v['p_vid']) }
           url = baseURL +'?'+ urllib.urlencode(payload)
           #log('vid='+v['vid']+', url='+url)
           li = xbmcgui.ListItem(v['title'], iconImage=__addonicon__, thumbnailImage=v['thumbnail'])
           li.addStreamInfo('video', { 'duration': v['duration'] })
           li.setProperty('fanart_image', v['thumbnail'])
           xbmcplugin.addDirectoryItem(handle=addonHandle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle=addonHandle)

elif mode == 1:

    log("Selected Parent VID:" + pvid)

    # Retrieve Playlist
    videoList = getAllPlaylist(videoLim)

    dPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    dPlaylist.clear()

    for i in range(0, videoList.__len__()):
       v = videoList[i]
       #log(str(i) + "-" + ','.join([v['vid'], v['category'], v['v_level'], v['p_vid']]))
       if v['category'] == 'DRAMA' and v['p_vid'] == pvid:
           if v['v_level'] == '1':
               dIndex = 0
           if v['v_level'] == '0':
               li = xbmcgui.ListItem(v['title'], thumbnailImage=v['thumbnail'])
               li.addStreamInfo('video', { 'duration': v['duration'] })
               pList = getVideoPlaylist(int(v['vid']))
               playURL = pList['m3u8']
               dPlaylist.add(url=playURL, listitem=li, index=dIndex)
               log("Playlist:"+ str(dIndex) +"-"+ ','.join([v['vid'], v['category'], v['v_level'], v['p_vid']]))
               dIndex += 1

    xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(dPlaylist, startpos=0)

