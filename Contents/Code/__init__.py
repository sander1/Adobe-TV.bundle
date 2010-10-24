# -*- coding: utf-8 -*-
###################################################################################################
#
# Adobe TV (tv.adobe.com) plugin for Plex (by sander1)
# http://wiki.plexapp.com/index.php/Adobe_TV

import re

###################################################################################################

PLUGIN_TITLE               = 'Adobe TV'
PLUGIN_PREFIX              = '/video/adobetv'
BASE_URL                   = 'http://tv.adobe.com'

# Default artwork and icon(s)
PLUGIN_ARTWORK             = 'art-default.jpg'
PLUGIN_ICON_DEFAULT        = 'icon-default.png'

###################################################################################################

def Start():
  Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, PLUGIN_TITLE, PLUGIN_ICON_DEFAULT, PLUGIN_ARTWORK)
  Plugin.AddViewGroup('_List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('_InfoList', viewMode='InfoList', mediaType='items')

  # Set the default MediaContainer attributes
  MediaContainer.title1    = PLUGIN_TITLE
  MediaContainer.viewGroup = '_InfoList'
  MediaContainer.art       = R(PLUGIN_ARTWORK)
  MediaContainer.userAgent = ''

  # Set the default thumb
  DirectoryItem.thumb = R(PLUGIN_ICON_DEFAULT)
  WebVideoItem.thumb = R(PLUGIN_ICON_DEFAULT)

  # Set HTTP headers
  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6'

###################################################################################################

def MainMenu():
  dir = MediaContainer(viewGroup='_List')
  dir.Append(Function(DirectoryItem(Products, title='Products')))
  dir.Append(Function(DirectoryItem(Channels, title='Channels')))
  return dir

####################################################################################################

def Products(sender):
  dir = MediaContainer(title2=sender.itemTitle)

  url = BASE_URL + '/products/'
  xp = '/html/body//div[@id="products"]//li/a'
  products = HTML.ElementFromURL(url, errors='ignore').xpath(xp)

  for p in products:
    url = BASE_URL + p.get('href')
    xp = '/html/body//div[@class="masthead"]'
    details = HTML.ElementFromURL(url, errors='ignore').xpath(xp)[0]

    title = details.xpath('./h1')[0].text.replace('Adobe','').strip()
    summary = details.xpath('./h2')[0].text
    thumb = details.xpath('./img')[0].get('src')
    dir.Append(Function(DirectoryItem(Shows, title=title, summary=summary, thumb=Function(GetThumb, url=thumb)), url=url))

  return dir

####################################################################################################

def Channels(sender):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  url = BASE_URL + '/channels/'
  xp = '/html/body//div[@id="channels"]//div[@class="channel"]'
  channels = HTML.ElementFromURL(url, errors='ignore').xpath(xp)
  i = 0

  for c in channels:
    title = c.xpath('./h3//text()')[0].strip()
    dir.Append(Function(DirectoryItem(SubChannels, title=title), i=i))
    i += 1

  return dir

####################################################################################################

def SubChannels(sender, i):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  url = BASE_URL + '/channels/'
  xp = '/html/body//div[@id="channels"]//div[@class="channel"]'
  channels = HTML.ElementFromURL(url, errors='ignore').xpath(xp)

  # 'Main' item
  title = channels[i].xpath('./h3//text()')[0].strip()
  url = BASE_URL + channels[i].xpath('./h3/a')[0].get('href')
  dir.Append(Function(DirectoryItem(Shows, title=title), url=url))

  # Sub
  subchannels = channels[i].xpath('./ul/li/a')
  for s in subchannels:
    title = s.text.strip()
    url = BASE_URL + s.get('href')
    dir.Append(Function(DirectoryItem(Shows, title=title), url=url))

  return dir

####################################################################################################

def Shows(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)

  xp = '/html/body//div[contains(@class, "page all")]/div/div[@class="top"]'
  shows = HTML.ElementFromURL(url, errors='ignore').xpath(xp)

  for s in shows:
    title = s.xpath('./img')[0].get('alt').strip()
    summary = s.xpath('./p')[0].text
    thumb = s.xpath('./img')[0].get('src').replace('50.jpg','100.jpg')
    url = BASE_URL + s.xpath('./h3/a')[0].get('href')
    dir.Append(Function(DirectoryItem(Episodes, title=title, summary=summary, thumb=Function(GetThumb, url=thumb)), url=url))

  return dir

####################################################################################################

def Episodes(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)

  xp = '/html/body//div[@id="episodes"]/table/tbody/tr'
  episodes = HTML.ElementFromURL(url, errors='ignore').xpath(xp)

  for e in episodes:
    title = e.xpath('./td//span[@class="title"]')[0].text.strip()
    summary = e.xpath('./td//span[@class="description"]')[0].text
    duration = e.xpath('./td//span[@class="runtime"]')[0].text
    duration = CalculateDuration(duration)

    try:
      rating = e.xpath('./td//span[@class="rating-stars"]/span')[0].get('style')
      rating = re.search('width: ([0-9]+)%').group(1)
      if int(rating) > 0:
        rating = int(rating) / 10
      else:
        rating = None
    except:
      rating = None

    date = e.xpath('./td//span[@class="added"]')[0].text
    date = re.search('Added : (.+)$', date).group(1)

    url = BASE_URL + e.xpath('./td/a')[0].get('href')

    try:
      thumb_xp = '/html/head/link[@rel="image_src"]'
      thumb = HTML.ElementFromURL(url, errors='ignore', cacheTime=CACHE_1MONTH).xpath(thumb_xp)[0].get('href')
    except:
      thumb = None

    dir.Append(Function(WebVideoItem(PlayVideo, title=title, subtitle=date, summary=summary, duration=duration, rating=rating, thumb=Function(GetThumb, url=thumb)), url=url))

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
    if url != None and url[0:4] == 'http':
      data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
      return DataObject(data, 'image/jpeg')
  except:
    pass
  return Redirect(R(PLUGIN_ICON_DEFAULT))

####################################################################################################

def PlayVideo(sender, url):
  xp = '/html/head/link[@rel="video_src"]'
  video_src = HTML.ElementFromURL(url, errors='ignore', cacheTime=CACHE_1MONTH).xpath(xp)[0].get('href')
  vid = re.search('fileID=([0-9]+).+context=([0-9]+)', video_src)
  fileID = int(vid.group(1))
  context = int(vid.group(2))

  url = DoAmfRequest(fileID, context)

  if url.find('edgeboss') != -1:
    xp = '/FLVPlayerConfig/stream/entry'
    content = XML.ElementFromURL(url, errors='ignore', cacheTime=CACHE_1MONTH).xpath(xp)[0]
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

  return None

####################################################################################################

def DoAmfRequest(fileID, context):
  client = AMF.RemotingService('http://tv.adobe.com/flashservices/gateway', amf_version=3, user_agent='Shockwave Flash')
  service = client.getService('services.player')
  result = service.load(fileID, False, context)

  return result['CDNURL']
