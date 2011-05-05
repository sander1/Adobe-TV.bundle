# -*- coding: utf-8 -*-
###################################################################################################
#
# Adobe TV (tv.adobe.com) plugin for Plex (by sander1)
# http://wiki.plexapp.com/index.php/Adobe_TV

import re

TITLE    = 'Adobe TV'
BASE_URL = 'http://tv.adobe.com'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'

PREF_MAP = {'720p':'HD', 'Medium':'MED', 'Low':'LOW'}
ORDER = ['HD', 'MED', 'LOW']

###################################################################################################

def Start():
  Plugin.AddPrefixHandler('/video/adobetv', MainMenu, TITLE, ICON, ART)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

  MediaContainer.title1    = TITLE
  MediaContainer.viewGroup = 'InfoList'
  MediaContainer.art       = R(ART)
  MediaContainer.userAgent = ''

  DirectoryItem.thumb = R(ICON)
  VideoItem.thumb = R(ICON)

  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.16) Gecko/20110319 Firefox/3.6.16'

###################################################################################################

def MainMenu():
  dir = MediaContainer(viewGroup='List')
  dir.Append(Function(DirectoryItem(Products, title='Products')))
  dir.Append(Function(DirectoryItem(Channels, title='Channels')))
  dir.Append(PrefsItem('Preferences', thumb=R('icon-prefs.png')))
  return dir

####################################################################################################

def Products(sender):
  dir = MediaContainer(title2=sender.itemTitle)
  resultDict = {}

  @parallelize
  def GetProducts():
    products = HTML.ElementFromURL(BASE_URL + '/products/', errors='ignore').xpath('//div[@id="products"]//li')

    for num in range(len(products)):
      product = products[num]

      @task
      def GetProduct(num=num, resultDict=resultDict, product=product):
        title = product.xpath('./a/text()')[0].strip()
        url = BASE_URL + product.xpath('./a')[0].get('href')

        # The ?c=l added to the url below doesn't do anything. It just makes the urls unique so we can use different
        # cache times for this url (long for here, 'normal' in other functions).
        details = HTML.ElementFromURL(url + '?c=l', errors='ignore', cacheTime=CACHE_1MONTH).xpath('//div[@class="masthead"]')[0]

        summary = details.xpath('./h2')[0].text
        if not summary:
          summary = ''

        thumb = details.xpath('./img')[0].get('src')

        resultDict[num] = DirectoryItem(Function(Shows, url=url), title=title, summary=summary, thumb=Function(GetThumb, url=thumb))

  keys = resultDict.keys()
  keys.sort()
  for key in keys:
    dir.Append(resultDict[key])

  return dir

####################################################################################################

def Channels(sender):
  dir = MediaContainer(viewGroup='List', title2=sender.itemTitle)
  i = 0

  for channel in HTML.ElementFromURL(BASE_URL + '/channels/', errors='ignore').xpath('//div[@id="channels"]//div[@class="channel"]'):
    title = channel.xpath('./h3//text()')[0].strip()

    # If a channel has subchannels we get an extra menu
    if len( channel.xpath('./ul/li/a') ) > 0:
      dir.Append(Function(DirectoryItem(SubChannels, title=title), i=i))
    else:
      url = BASE_URL + channel.xpath('./h3/a')[0].get('href')
      dir.Append(Function(DirectoryItem(Shows, title=title), url=url))

    i += 1

  return dir

####################################################################################################

def SubChannels(sender, i):
  dir = MediaContainer(viewGroup='List', title2=sender.itemTitle)

  channels = HTML.ElementFromURL(BASE_URL + '/channels/', errors='ignore').xpath('//div[@id="channels"]//div[@class="channel"]')
  for subchannel in channels[i].xpath('./ul/li/a'):
    title = subchannel.text.strip()
    url = BASE_URL + subchannel.get('href')
    dir.Append(Function(DirectoryItem(Shows, title=title), url=url))

  return dir

####################################################################################################

def Shows(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)

  for show in HTML.ElementFromURL(url, errors='ignore').xpath('//div[contains(@class, "page all")]/div/div[@class="top"]'):
    title = show.xpath('./img')[0].get('alt').strip()
    summary = show.xpath('./p')[0].text
    thumb = show.xpath('./img')[0].get('src').replace('50.jpg','100.jpg')
    url = BASE_URL + show.xpath('./h3/a')[0].get('href')
    dir.Append(Function(DirectoryItem(Episodes, title=title, summary=summary, thumb=Function(GetThumb, url=thumb)), url=url))

  if len(dir) == 0:
    return MessageContainer("Empty", "There aren't any items")
  else:
    return dir

####################################################################################################

def Episodes(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)

  for episode in HTML.ElementFromURL(url, errors='ignore').xpath('//div[@id="episodes"]/table/tbody/tr'):
    title = episode.xpath('./td//span[@class="title"]')[0].text.strip()
    summary = episode.xpath('./td//span[@class="description"]')[0].text

    try:
      duration = episode.xpath('./td//span[@class="runtime"]')[0].text
      duration = CalculateDuration(duration)
    except:
      duration = None

    try:
      rating = episode.xpath('./td//span[@class="rating-stars"]/span')[0].get('style')
      rating = re.search('width:([0-9]+)%', rating).group(1)
      if int(rating) > 0:
        rating = int(rating) / 10
      else:
        rating = None
    except:
      rating = None

    date = episode.xpath('./td//span[@class="added"]')[0].text
    date = re.search('Added : (.+)$', date).group(1)

    url = BASE_URL + episode.xpath('./td/a')[0].get('href')

    dir.Append(Function(VideoItem(PlayVideo, title=title, subtitle=date, summary=summary, duration=duration, rating=rating, thumb=Function(GetEpisodeThumb, url=url)), url=url))

  if len(dir) == 0:
    return MessageContainer("Empty", "There aren't any items")
  else:
    return dir

####################################################################################################

def CalculateDuration(timecode):
  milliseconds = 0
  d = re.search('([0-9]{2}):([0-9]{2}):([0-9]{2})', timecode)
  milliseconds += int( d.group(1) ) * 60 * 60 * 1000
  milliseconds += int( d.group(2) ) * 60 * 1000
  milliseconds += int( d.group(3) ) * 1000
  return milliseconds

####################################################################################################

def GetThumb(url):
  try:
    if url and url[0:4] == 'http':
      data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
      return DataObject(data, 'image/jpeg')
  except:
    pass
  return Redirect(R(ICON))

####################################################################################################

def GetEpisodeThumb(url):
  try:
    thumb = HTML.ElementFromURL(url, errors='ignore', cacheTime=CACHE_1MONTH).xpath('//head/link[@rel="image_src"]')[0].get('href')
  except:
    thumb = None
  return GetThumb(thumb)

####################################################################################################

def PlayVideo(sender, url):
  video_src = HTML.ElementFromURL(url, errors='ignore', cacheTime=CACHE_1MONTH).xpath('//head/link[@rel="video_src"]')[0].get('href')
  vid = re.search('fileID=([0-9]+).+context=([0-9]+)', video_src)
  fileID = int(vid.group(1))
  context = int(vid.group(2))

  url = DoAmfRequest(fileID, context)

  if url[0:4] == 'http':
    return Redirect(url)
  elif url[0:4] == 'rtmp':
    if url.find('edgeboss') != -1:
      content = XML.ElementFromURL(url, errors='ignore', cacheTime=CACHE_1MONTH).xpath('/FLVPlayerConfig/stream/entry')[0]
      serverName = content.xpath('./serverName')[0].text
      appName = content.xpath('./appName')[0].text
      streamName = content.xpath('./streamName')[0].text
      streamer = 'rtmp://' + serverName + '/' + appName
      return Redirect(RTMPVideoItem(url=streamer, clip=streamName))
    elif url[0:4] == 'rtmp':
      (streamer, file) = url.split('/ondemand/')
      streamer += '/ondemand'
      if file.find('.mp4') != -1:
        file = 'mp4:' + file[:-4]
      elif file.find('.flv') != -1:
        file = file[:-4]
      return Redirect(RTMPVideoItem(url=streamer, clip=file))
  else:
    return

####################################################################################################

def DoAmfRequest(fileID, context):
  client = AMF.RemotingService('http://tv.adobe.com/flashservices/gateway', amf_version=3, user_agent='Shockwave Flash')
  service = client.getService('services.player')
  result = service.load(fileID, False, context)

  # If there are multiple videos to select from...
  if 'VIDEOS' in result:
    user_quality = Prefs['video_quality']
    pref_value = PREF_MAP[user_quality]
    available = {}

    for version in result['VIDEOS']:
      # Prefer http over rtmp
      if 'PROGRESSIVE' in version:
        video_url = version['PROGRESSIVE']
      elif 'CDNURL' in version:
        video_url = version['CDNURL']

      q = version['QUALITY']
      if q in ORDER:
        available[q] = video_url

    for i in range(ORDER.index(pref_value), len(ORDER)):
      quality = ORDER[i]
      if quality in available:
        return available[quality]

  # ...or if there is just one version available (prefer http over rtmp)
  elif 'PROGRESSIVE' in result:
    return result['PROGRESSIVE']
  elif 'CDNURL' in result:
    return result['CDNURL']
  else:
    return
