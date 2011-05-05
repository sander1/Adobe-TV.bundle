# -*- coding: utf-8 -*-
###################################################################################################
# Adobe TV (tv.adobe.com) plugin for Plex (by sander1)
# http://wiki.plexapp.com/index.php/Adobe_TV

import re

TITLE    = 'Adobe TV'
BASE_URL = 'http://tv.adobe.com'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'

###################################################################################################
def Start():
  Plugin.AddPrefixHandler('/video/adobetv', MainMenu, TITLE, ICON, ART)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

  ObjectContainer.title1 = TITLE
  ObjectContainer.art = R(ART)
  ObjectContainer.user_agent = ''

  DirectoryObject.thumb = R(ICON)
  VideoClipObject.thumb = R(ICON)

  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.16) Gecko/20110319 Firefox/3.6.16'

###################################################################################################
def MainMenu():
  oc = ObjectContainer(view_group='List')
  oc.add(DirectoryObject(key=Callback(Products, title='Products'), title='Products'))
  oc.add(DirectoryObject(key=Callback(Channels, title='Channels'), title='Channels'))
  oc.add(PrefsObject(title='Preferences', thumb=R('icon-prefs.png')))
  return oc

####################################################################################################
def Products(title):
  oc = ObjectContainer(title2=title, view_group='InfoList')
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

        resultDict[num] = DirectoryObject(key=Callback(Shows, title=title, url=url), title=title, summary=summary, thumb=Callback(GetThumb, url=thumb))

  keys = resultDict.keys()
  keys.sort()
  for key in keys:
    oc.add(resultDict[key])

  return oc

####################################################################################################
def Channels(title):
  oc = ObjectContainer(title2=title, view_group='List')
  i = 0

  for channel in HTML.ElementFromURL(BASE_URL + '/channels/', errors='ignore').xpath('//div[@id="channels"]//div[@class="channel"]'):
    title = channel.xpath('./h3//text()')[0].strip()

    # If a channel has subchannels we get an extra menu
    if len( channel.xpath('./ul/li/a') ) > 0:
      oc.add(DirectoryObject(key=Callback(SubChannels, title=title, i=i), title=title))
    else:
      url = BASE_URL + channel.xpath('./h3/a')[0].get('href')
      oc.add(DirectoryObject(key=Callback(Shows, title=title, url=url), title=title))

    i += 1

  return oc

####################################################################################################
def SubChannels(title, i):
  oc = ObjectContainer(title2=title, view_group='List')

  channels = HTML.ElementFromURL(BASE_URL + '/channels/', errors='ignore').xpath('//div[@id="channels"]//div[@class="channel"]')
  for subchannel in channels[i].xpath('./ul/li/a'):
    title = subchannel.text.strip()
    url = BASE_URL + subchannel.get('href')
    oc.add(DirectoryObject(key=Callback(Shows, title=title, url=url), title=title))

  return oc

####################################################################################################
def Shows(title, url):
  oc = ObjectContainer(title2=title, view_group='InfoList')

  for show in HTML.ElementFromURL(url, errors='ignore').xpath('//div[contains(@class, "page all")]/div/div[@class="top"]'):
    title = show.xpath('./img')[0].get('alt').strip()
    summary = show.xpath('./p')[0].text
    thumb = show.xpath('./img')[0].get('src').replace('50.jpg','100.jpg')
    url = BASE_URL + show.xpath('./h3/a')[0].get('href')
    oc.add(DirectoryObject(key=Callback(Episodes, title=title, url=url), title=title, summary=summary, thumb=Callback(GetThumb, url=thumb)))

  if len(oc) == 0:
    return MessageContainer("Empty", "There aren't any items")
  else:
    return oc

####################################################################################################
def Episodes(title, url):
  oc = ObjectContainer(title2=title, view_group='InfoList')
  tagline = title

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
      rating = re.search('width: ([0-9]+)%').group(1)
      if int(rating) > 0:
        rating = int(rating) / 10
      else:
        rating = None
    except:
      rating = None

    date = episode.xpath('./td//span[@class="added"]')[0].text
    date = re.search('Added : (.+)$', date).group(1)
    originally_available_at = Datetime.ParseDate(date).date()

    url = BASE_URL + episode.xpath('./td/a')[0].get('href')

    oc.add(VideoClipObject(url=url, title=title, tagline=tagline, summary=summary, duration=duration, rating=rating, originally_available_at=originally_available_at, thumb=Callback(GetEpisodeThumb, url=url)))

  if len(oc) == 0:
    return MessageContainer("Empty", "There aren't any items")
  else:
    return oc

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
