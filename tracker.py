# -*- coding: utf-8 -*-
#

import xbmc
import time, threading, urllib2, json
from utils import *

TRACKER = 'hktvTracker'


def goURL(url):
    log('[%s] Go URL %s' % (TRACKER, url))
    try:
        resp = urllib2.urlopen(url)
        log('[%s] HTTP status code = %s' % (TRACKER, resp.getcode()))
        return
    except Exception as e:
        logerr('[%s] goURL err=%s' % (TRACKER, e))
        return


class adsTimer(threading.Thread):

    def __init__(self, second, trackers):
        super(adsTimer, self).__init__()
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0
        self.timer = second
        self.trackers = trackers
        log('[%s] [%s] timer for %d sec' % (TRACKER, self.getName(), self.timer))

    def run(self):
        log('[%s] [%s] timer started' % (TRACKER, self.getName()))
        sCount = 0
        intv = [ 0, self.timer / 4, self.timer / 2, self.timer / 4 * 3, self.timer ]
        tkList = map(list, zip(*self.trackers))

        while not self._stopevent.isSet() and sCount <= self.timer:
            for i in range(intv.__len__()):
                interval = int(intv[i])
                #log('[%s] [%s] i=%d, intv=%d, sCount=%s' % (TRACKER, self.getName(), i, intv[i], sCount))
                if sCount == interval:
                    #log('[%s] [%s] match interval' % (TRACKER, self.getName()))
                    for t in range(tkList[i].__len__()):  # per trackers
                        log('[%s] [%s] interval %d - tracking - %s' % (TRACKER, self.getName(), i, tkList[i][t]))
                        goURL(tkList[i][t])
            sCount += 1
            if sCount < self.timer:
                self._stopevent.wait(self._sleepperiod)

        log('[%s] [%s] timer completed' % (TRACKER, self.getName()))

    def join(self, timeout=None):
        log('[%s] [%s] timer stopping' % (TRACKER, self.getName()))
        self._stopevent.set()
        threading.Thread.join(self, timeout)


class hktvTracker(xbmc.Player):

    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.playing = False
        self.adTrack = None
        self.url = ''
        self.playTime = 0

    def onPlayBackStarted(self):
        xbmc.sleep(100)
        if self.isPlayingVideo():
            try:
                self.url = self.getPlayingFile()
                self.playTime = self.getTotalTime()
                adInfoJson = xbmc.getInfoLabel('VideoPlayer.Plot')
                videoType = xbmc.getInfoLabel('VideoPlayer.PlotOutline')
                #log('[%s] adInfoJson=%s' % (TRACKER, adInfoJson))
                #log('[%s] videoType=%s' % (TRACKER, videoType))
                if adInfoJson:
                    adInfo = json.loads(adInfoJson)
                    if 'track' in adInfo:
                        log('[%s] playing - %s' % (TRACKER, self.url))
                        # get Ad info
                        if 'imp' in adInfo:
                            imList = adInfo['imp']
                            for i in range(imList.__len__()):
                                log('[%s] impression=%s' % (TRACKER, imList[i]))
                                goURL(imList[i])
                        tkList = None
                        #tkList = [ ['1A', '1B', '1C', '1D', '1E'],
                        #           ['2A', '2B', '2C', '2D', '2E'] ]
                        if 'track' in adInfo:
                            tkList = adInfo['track']
                        # tracker
                        #if self.playTime > 1 and self.playTime < 60:
                        if videoType == 'ADS':
                            if tkList:
                                self.adTrack = adsTimer(self.playTime, tkList)
                                self.adTrack.start()
                        self.playing = True
                return
            except Exception as e:
                logerr('[%s] onPlayBackStarted err=%s' % (TRACKER, e))
                return

    def onPlayBackEnded(self):
        try:
            if self.playing:
                log('[%s] ended %s' % (TRACKER, self.url))
                self.adTrack.join()
                self.playing = False
            return
        except Exception as e:
            logerr('[%s] onPlayBackEnded err=%s' % (TRACKER, e))
            return

    def onPlayBackStopped(self):
        try:
            if self.playing:
                log('[%s] stopping %s' % (TRACKER, self.url))
                self.adTrack.join()
                self.playing = False
            return
        except Exception as e:
            logerr('[%s] onPlayBackStopped err=%s' % (TRACKER, e))
            return


# Starting tracker

loginfo('[%s] Loading HKTV Tracker' % TRACKER)

player = hktvTracker()

while not xbmc.abortRequested:
    xbmc.sleep(1000)

loginfo('[%s] Shutting down ...' % TRACKER)

#
#   They tried to bury us.
#   They didn't know we were seeds.
#                 - Mexican Proverb
#
