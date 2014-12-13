# -*- coding: utf-8 -*-
#

import xbmc
import time, threading, urllib2, json
from utils import *

TRACKER = 'hktvTracker'


def goURL(url):
    log(xbmc.LOGDEBUG, '[%s] Go URL %s' % (TRACKER, url))
    try:
        resp = urllib2.urlopen(url)
        log(xbmc.LOGDEBUG, '[%s] HTTP status code = %s' % (TRACKER, resp.getcode()))
    except Exception as e:
        log(xbmc.LOGERROR, '[%s] goURL err=%s' % (TRACKER, str(e)))
        return


class adsTimer(threading.Thread):

    def __init__(self, second, trackers):
        super(adsTimer, self).__init__()
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0
        self.timer = second
        self.trackers = trackers
        log(xbmc.LOGDEBUG, '[%s] [%s] timer for %d sec' % (TRACKER, self.getName(), self.timer))

    def run(self):
        log(xbmc.LOGDEBUG, '[%s] [%s] timer started' % (TRACKER, self.getName()))
        sCount = 0
        intv = [ 0, self.timer / 4, self.timer / 2, self.timer / 4 * 3, self.timer ]
        tkList = map(list, zip(*self.trackers))

        while not self._stopevent.isSet() and sCount <= self.timer:
            for i in range(intv.__len__()):
                interval = int(intv[i])
                #log(xbmc.LOGDEBUG, '[%s] [%s] i=%d, intv=%d, sCount=%s' % (TRACKER, self.getName(), i, intv[i], sCount))
                if sCount == interval:
                    #log(xbmc.LOGDEBUG, '[%s] [%s] match interval' % (TRACKER, self.getName()))
                    for t in range(tkList[i].__len__()):  # per trackers
                        log(xbmc.LOGDEBUG, '[%s] [%s] interval %d - tracking - %s' % (TRACKER, self.getName(), i, tkList[i][t]))
                        goURL(tkList[i][t])
            sCount += 1
            self._stopevent.wait(self._sleepperiod)

        log(xbmc.LOGDEBUG, '[%s] [%s] timer completed' % (TRACKER, self.getName()))

    def join(self, timeout=None):
        log(xbmc.LOGDEBUG, '[%s] [%s] timer stopping' % (TRACKER, self.getName()))
        self._stopevent.set()
        threading.Thread.join(self, timeout)


class hktvTracker(xbmc.Player):

    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.adTrack = None
        self.url = ''
        self.playTime = 0

    def onPlayBackStarted(self):
        xbmc.sleep(100)
        if self.isPlayingVideo():
            try:
                self.url = self.getPlayingFile()
                self.playTime = self.getTotalTime()
                log(xbmc.LOGDEBUG, '[%s] playing - %s' % (TRACKER, self.url))
                adInfoJson = xbmc.getInfoLabel('VideoPlayer.Plot')
                log(xbmc.LOGDEBUG, '[%s] adInfoJson=%s' % (TRACKER, adInfoJson))
                if adInfoJson:
                    adInfo = json.loads(adInfoJson)
                    # get Ad info
                    if 'imp' in adInfo:
                        imList = adInfo['imp']
                        for i in range(imList.__len__()):
                            log(xbmc.LOGDEBUG, '[%s] impression=%s' % (TRACKER, imList[i]))
                            goURL(imList[i])
                    tkList = None
                    #tkList = [ ['1A', '1B', '1C', '1D', '1E'],
                    #           ['2A', '2B', '2C', '2D', '2E'] ]
                    if 'track' in adInfo:
                        tkList = adInfo['track']
                    # tracker
                    if self.playTime > 1 and self.playTime < 60:
                        if tkList:
                            self.adTrack = adsTimer(self.playTime, tkList)
                            self.adTrack.start()
            except Exception as e:
                log(xbmc.LOGERROR, '[%s] onPlayBackStarted err=%s' % (TRACKER, str(e)))
                return

    def onPlayBackStopped(self):
        xbmc.sleep(100)
        try:
            log(xbmc.LOGDEBUG, '[%s] stopping %s' % (TRACKER, self.url))
            self.adTrack.join()
        except Exception as e:
            log(xbmc.LOGERROR, '[%s] onPlayBackStopped err=%s' % (TRACKER, str(e)))
            return


log(xbmc.LOGINFO, '[%s] Loading HKTV Tracker' % TRACKER)

player = hktvTracker()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

log(xbmc.LOGINFO, '[%s] Shutting down ...' % TRACKER)

#
#   They tried to bury us.
#   They didn't know we were seeds.
#                 - Mexican Proverb
#
