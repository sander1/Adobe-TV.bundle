# -*- coding: utf-8 -*-
import re

NAME = 'Adobe TV'
BASE_URL = 'http://tv.adobe.com'
ART = 'art-default.jpg'
ICON = 'icon-default.png'

SHOWS_BY_PRODUCT = 'http://tv.adobe.com/api/v4/Show/index/?product_id=%s&maxresults=1000'
SHOWS_BY_CATEGORY = 'http://tv.adobe.com/api/v4/Show/index/?category_id=%s&maxresults=1000'
EPISODES = 'http://tv.adobe.com/api/v4/Episode/index/?show_id=%s&maxresults=1000'

###################################################################################################
def Start():

	Plugin.AddPrefixHandler('/video/adobetv', MainMenu, NAME, ICON, ART)
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

	ObjectContainer.title1 = NAME
	ObjectContainer.view_group = 'InfoList'
	ObjectContainer.art = R(ART)

	DirectoryObject.thumb = R(ICON)
	VideoClipObject.thumb = R(ICON)

	HTTP.CacheTime = CACHE_1DAY
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/534.53.11 (KHTML, like Gecko) Version/5.1.3 Safari/534.53.10'

###################################################################################################
def MainMenu():

	oc = ObjectContainer(view_group='List')
	oc.add(DirectoryObject(key = Callback(Channels), title='Channels'))
	oc.add(DirectoryObject(key = Callback(Products), title='Products'))
	return oc

####################################################################################################
def Channels():

	oc = ObjectContainer(title2='Channels', view_group='List')
	i = 0

	for channel in HTML.ElementFromURL('%s/channels/' % BASE_URL).xpath('//div[@id="channels"]//div[contains(@class, "channel")]'):
		title = channel.xpath('./h3/a/text()')[0].strip()

		# If a channel has subchannels we create an extra menu
		if len( channel.xpath('./ul/li/a') ) > 0:
			oc.add(DirectoryObject(key=Callback(SubChannels, title=title, i=i), title=title))
		else:
			url = channel.xpath('./h3/a')[0].get('href')
			oc.add(DirectoryObject(key=Callback(Shows, title=title, url=url), title=title))

		i += 1

	return oc

####################################################################################################
def SubChannels(title, i):

	oc = ObjectContainer(title2=title, view_group='List')
	channels = HTML.ElementFromURL('%s/channels/' % BASE_URL).xpath('//div[@id="channels"]//div[contains(@class, "channel")]')

	for subchannel in channels[i].xpath('./ul/li/a'):
		title = subchannel.text.strip()
		url = subchannel.get('href')
		oc.add(DirectoryObject(key=Callback(Shows, title=title, url=url), title=title))

	return oc

####################################################################################################
def Products():

	oc = ObjectContainer(title2='Products')
	json = GetJson('%s/products/' % BASE_URL)

	if json:
		for product in json['products']['en']:
			product_id = str( product['id'] )
			title = product['product_name']
			summary = product['product_description']
			thumb = product['large_logo']['url']

			if thumb.startswith('//'):
				thumb = 'http:%s' % thumb

			oc.add(DirectoryObject(key=Callback(Shows, title=title, product_id=product_id), title=title, summary=summary, thumb=Callback(GetThumb, url=thumb)))

	return oc

####################################################################################################
def Shows(title, product_id=None, url=None):

	oc = ObjectContainer(title2=title)
	show_url = None

	if product_id:
		show_url = SHOWS_BY_PRODUCT % product_id
	elif url:
		# Find the category id
		page = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
		category = re.search('"categories":\[.+?' + title + '","id":([0-9]+),', page)

		if category:
			category_id = category.group(1)
			Log('%s: %s' % (title, category_id))
			show_url = SHOWS_BY_CATEGORY % category_id

	if show_url:
		for show in JSON.ObjectFromURL(show_url)['data']:
			show_id = str( show['id'] )
			title = show['show_name']
			summary = show['show_description']
			thumb = show['large_logo']['url']

			oc.add(DirectoryObject(key=Callback(Episodes, title=title, show_id=show_id), title=title, summary=summary, thumb=Callback(GetThumb, url=thumb)))

	if len(oc) == 0:
		return MessageContainer("Empty", "There aren't any shows for this product or channel")
	else:
		return oc

####################################################################################################
def Episodes(title, show_id):

	oc = ObjectContainer(title2=title)

	for episode in JSON.ObjectFromURL(EPISODES % show_id)['data']:
		video = VideoClipObject()

		video.url = episode['url']
		video.title = episode['title']
		video.summary = episode['description']
		video.thumb = episode['thumbnail']

		if 'rating_cache' in episode:
			video.rating = episode['rating_cache'] * 2

		if 'duration' in episode:
			video.duration = TimeToMs(episode['duration'])

		oc.add(video)

	if len(oc) == 0:
		return MessageContainer("Empty", "There aren't episodes for this show")
	else:
		return oc

####################################################################################################
def GetThumb(url):

	try:
		if url and url[0:4] == 'http':
			if url.endswith('.png'):
				mimetype = 'image/png'
			else:
				mimetype = 'image/jpeg'

			data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
			return DataObject(data, mimetype)
	except:
		pass

	return Redirect(R(ICON))

####################################################################################################
def GetJson(url):

	html = HTTP.Request(url).content

	# Extract the relevant JSON part
	pattern = re.compile('data\s:\s(\{.+\})')
	result = pattern.search(html)

	if result:
		json_string = result.group(1).replace("\\\\/", "/").replace("\\/", "/").replace('\\"', '"').replace('"[', '[').replace(']"', ']').replace("'client_JSON'", '"client_JSON"')
		json = JSON.ObjectFromString(json_string)['client_JSON']

		return json
	else:
		return None

####################################################################################################
def TimeToMs(timecode):

	seconds = 0

	try:
		duration = timecode.split(':')
		duration.reverse()

		for i in range(0, len(duration)):
			seconds += int(duration[i]) * (60**i)
	except:
		pass

	return seconds * 1000
