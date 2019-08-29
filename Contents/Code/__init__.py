#!/usr/bin/python
# -*- coding: utf-8 -*-

######################################################################################
#
#	Einthusan.com / Einthusan.ca
#
######################################################################################

import common, updater, urllib2, time, sys, random, re
import slimerjs, json, einthusan

TITLE = common.TITLE
PREFIX = common.PREFIX
ART = "art-default.jpg"
ICON = "icon-einthusan.png"
ICON_LIST = "icon-list.png"
ICON_COVER = "icon-cover.png"
ICON_SEARCH = "icon-search.png"
ICON_SEARCH_QUEUE = "icon-search-queue.png"
ICON_NEXT = "icon-next.png"
ICON_MOVIES = "icon-movies.png"
ICON_SERIES = "icon-series.png"
ICON_QUEUE = "icon-queue.png"
ICON_UPDATE = "icon-update.png"
ICON_UPDATE_NEW = "icon-update-new.png"
ICON_UNAV = "icon-unav.png"
ICON_PREFS = "icon-prefs.png"
ICON_LANG = "icon-lang.png"
ICON_SOURCES = "icon-sources.png"
BASE_URL = "https://einthusan.ca"
SEARCH_URL = "https://einthusan.ca/search/"
PROXY_URL = "https://ssl-proxy.my-addr.org/myaddrproxy.php/"
PROXY_PART = "/myaddrproxy.php/https/"
PROXY_PART_REPLACE = "//"
PROXY_PART2 = "/myaddrproxy.php/https/einthusan.ca/"
PROXY_PART2_REPLACE = "/"
LAST_PROCESSED_URL = []
VideoURL = {}
EINTHUSAN_SERVERS = ["Dallas","Washington","Los Angeles","London"]
EINTHUSAN_SERVER_INFO = {}

SLIMERJS_INIT = []
SERVER_OFFSET = []


######################################################################################
# Set global variables

def Start():

	ObjectContainer.title1 = TITLE
	ObjectContainer.art = R(ART)
	DirectoryObject.thumb = R(ICON_LIST)
	DirectoryObject.art = R(ART)
	VideoClipObject.thumb = R(ICON_MOVIES)
	VideoClipObject.art = R(ART)
	
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = common.USER_AGENT
	HTTP.Headers['Referer'] = BASE_URL
	
	LAST_PROCESSED_URL = []
	VideoURL = {}
	
	Log("Prefs:")
	Log("OS: " + sys.platform)
	firefox_dir = Prefs['firefox_dir']
	if firefox_dir == None:
		firefox_dir = ""
	Log("Firefox directory: " + str(firefox_dir))
	
	python_dir = Prefs['python_dir']
	if python_dir == None:
		python_dir = ""
	Log("Python directory: " + str(python_dir))
	Log(common.TITLE + ' v.' + common.VERSION)
	
	# Initialize Server Info Thread once
	Thread.Create(AddSourceInfo)
	
######################################################################################
# Menu hierarchy

@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def MainMenu(**kwargs):

	if Prefs["use_slimerjs"] and len(SLIMERJS_INIT) == 0:
		# Initialize SlimerJS module once for faster load times
		Thread.Create(initSlimerJS)
		SLIMERJS_INIT.append('True')
	
	defaultLang = Prefs['langPref']
	
	oc = ObjectContainer(title2=TITLE)

	oc.add(DirectoryObject(key = Callback(SortMenu, lang = defaultLang), title = defaultLang.title() + ' Movies', thumb = R(ICON_MOVIES)))
	#oc.add(DirectoryObject(key = Callback(SortMenu, lang = defaultLang), title = defaultLang.title() + ' Music Videos', thumb = R(ICON_MOVIES)))
	
	oc.add(DirectoryObject(key = Callback(SetLanguage), title = 'Movies (Language Menu)', thumb = R(ICON_LANG)))
	
	oc.add(DirectoryObject(key = Callback(Bookmarks, title="My Movie Bookmarks"), title = "Bookmarks", thumb = R(ICON_QUEUE)))
	
	oc.add(InputDirectoryObject(key = Callback(Search, lang = defaultLang, page_count=1), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
	oc.add(DirectoryObject(key = Callback(SearchQueueMenu, title = 'Search Queue'), title = 'Search Queue', summary='Search using saved search terms', thumb = R(ICON_SEARCH_QUEUE)))
	oc.add(PrefsObject(title = 'Preferences', thumb = R(ICON_PREFS)))
	if updater.update_available()[0]:
		oc.add(DirectoryObject(key = Callback(updater.menu, title='Update Plugin'), title = 'Update (New Available)', thumb = R(ICON_UPDATE_NEW)))
	else:
		oc.add(DirectoryObject(key = Callback(updater.menu, title='Update Plugin'), title = 'Update (Running Latest)', thumb = R(ICON_UPDATE)))
	
	return oc
	
@route(PREFIX + "/setlanguage")
def SetLanguage(**kwargs):
	
	oc = ObjectContainer(title2='Select Language')
	
	page_elems = common.GetPageElements(BASE_URL + "/intro/")
	if page_elems == None and Prefs["use_https_alt"]:
		return ObjectContainer(header=title, message='Page was not retrieved. SSL Alternate method not compatible. Try using Proxy method.')
		
	if page_elems == None and Prefs["use_proxy"]: 
		return ObjectContainer(header=title, message='Page was not retrieved. Proxy did not work.')
		
	if page_elems == None: 
		return ObjectContainer(header=title, message='Page was not retrieved. Try enabling SSL Alternate method.')
	
	blocks = page_elems.xpath(".//div[@class='block1']//ul")
	for block in blocks:
		langblock = block.xpath(".//li")
		for langsq in langblock:
			lang = langsq.xpath(".//p//text()")[0]
			try:
				lang_img = "http:" + langsq.xpath(".//img//@src")[0]
			except:
				lang_img = "http:" + langsq.xpath(".//img//@data-src")[0]
			oc.add(DirectoryObject(key = Callback(SortMenu, lang = lang.lower()), title = lang, thumb = Resource.ContentsOfURLWithFallback(url = lang_img, fallback='MoviePosterUnavailable.jpg')))
	
	return oc

@route(PREFIX + "/sortMenu")
def SortMenu(lang, **kwargs):

	page_elems = common.GetPageElements(BASE_URL + "/intro/")
	if page_elems == None and Prefs["use_https_alt"]:
		return ObjectContainer(header='SortMenu', message='Page was not retrieved. SSL Alternate method not compatible. Try using Proxy method.')
		
	if page_elems == None and Prefs["use_proxy"]: 
		return ObjectContainer(header='SortMenu', message='Page was not retrieved. Proxy did not work.')
		
	if page_elems == None: 
		return ObjectContainer(header='SortMenu', message='Page was not retrieved. Try enabling SSL Alternate method.')

	cats1 = ['Hot Picks']
	cats2 = ['Staff Picks', 'Recently Added']
	cats2b = ['Genre']
	cats3 = ['Number or Alphabet']
	cats4 = ['Year']
	cats4b = ['Cast']
	cats5 = ['Coming Soon','Regional Hits']
	oc = ObjectContainer(title2='Sort ' + lang.title() + ' Movies By')
	for cat in cats1:
		oc.add(DirectoryObject(key = Callback(SortMenuHotPicks, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
	for cat in cats2:
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
	for cat in cats2b:
		oc.add(DirectoryObject(key = Callback(GenreMenu, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
	for cat in cats3:
		oc.add(DirectoryObject(key = Callback(SortMenuAlphabets, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
	for cat in cats4:
		oc.add(DirectoryObject(key = Callback(SortMenuYears, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
	for cat in cats4b:
		oc.add(DirectoryObject(key = Callback(SortMenuCast, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
	for cat in cats5:
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat), title = cat, thumb = R(ICON_LIST)))
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc	

@route(PREFIX + "/genreMenu")
def GenreMenu(lang, cat, **kwargs):

	oc = ObjectContainer(title2=cat.title())
	choices = ['action','comedy','romance','storyline','performance']
	for filter in choices:
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat, filter=filter), title = filter.title()))
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc
	
@route(PREFIX + "/sortmenuhotpicks")
def SortMenuHotPicks(lang, cat, **kwargs):

	oc = ObjectContainer(title2=cat.title())
		
	page_elems = common.GetPageElements(BASE_URL + "/movie/browse/?lang=" + lang)
	
	tabs = page_elems.xpath(".//section[@id='UIFeaturedFilms']//div[@class='tabview']")
	for block in tabs:
		loc = BASE_URL + block.xpath(".//div[@class='block1']//@href")[0]
		try:
			thumb = "http:" + block.xpath(".//div[@class='block1']//@src")[0]
		except:
			thumb = "http:" + block.xpath(".//div[@class='block1']//@data-src")[0]
		title = block.xpath(".//div[@class='block2']//a[@class='title']//text()")[0]
		summary = "Synopsis currently unavailable."
		oc.add(DirectoryObject(key = Callback(EpisodeDetail, title=title, url=loc), title = title, summary=summary, thumb = Resource.ContentsOfURLWithFallback(url = thumb, fallback='MoviePosterUnavailable.jpg')))
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc
	
@route(PREFIX + "/sortmenualphabets")
def SortMenuAlphabets(lang, cat, **kwargs):

	oc = ObjectContainer(title2=cat.title())
	
	page_elems = common.GetPageElements(BASE_URL + "/movie/browse/?lang="+lang)
	
	tabs = page_elems.xpath(".//section[@id='UIMovieFinder']//div[@class='tabview'][1]//div[@class='innertab simpletext']//a")
	for block in tabs:
		url = BASE_URL + block.xpath(".//@href")[0]
		title = block.xpath(".//text()")[0]
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat, key=title), title = title))
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc
	
@route(PREFIX + "/sortmenuyears")
def SortMenuYears(lang, cat, **kwargs):

	oc = ObjectContainer(title2=cat.title())
	
	page_elems = common.GetPageElements(BASE_URL + "/movie/browse/?lang="+lang)
	
	tabs = page_elems.xpath(".//section[@id='UIMovieFinder']//div[@class='tabview'][2]//div[@class='innertab simpletext'][position()>1]//a")
	for block in tabs:
		url = BASE_URL + block.xpath(".//@href")[0]
		title = block.xpath(".//text()")[0]
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat, key=title), title = title))
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc
	
@route(PREFIX + "/sortmenucast")
def SortMenuCast(lang, cat, **kwargs):

	oc = ObjectContainer(title2=cat.title())
	
	page_elems = common.GetPageElements(BASE_URL + "/movie/browse/?lang="+lang)
	
	tabs = page_elems.xpath(".//section[@id='UIMovieFinder']//div[@class='tabview'][3]//div[@class='innertab'][position()<3]//a")
	
	for block in tabs:
		url = BASE_URL + block.xpath(".//@href")[0]
		title = block.xpath(".//label//text()")[0]
		try:
			thumb = "http:" + block.xpath(".//@src")[0]
		except:
			thumb = "http:" + block.xpath(".//@data-src")[0]
		id = re.findall(r'id=(.*?)&', url)[0]
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat, key=id), title = title, thumb = Resource.ContentsOfURLWithFallback(url = thumb, fallback='MoviePosterUnavailable.jpg')))
		
	if len(oc) > 0:
		oc.objects.sort(key=lambda obj: obj.title, reverse=False)
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc

######################################################################################

@route(PREFIX + "/pagedetail")
def PageDetail(cat, lang, key="none", filter="", page_count="1", **kwargs):

	cat2title = filter
	if cat == 'Staff Picks':
		url = BASE_URL + "/movie/results/?find=StaffPick&lang="+lang+"&page="+page_count
	elif cat == 'Recently Added':
		url = BASE_URL + "/movie/results/?find=Recent&lang="+lang+"&page="+page_count
	elif cat == 'Regional Hits':
		url = BASE_URL + "/movie/results/?find=RegionalHit&lang="+lang+"&page="+page_count
	elif cat == 'Coming Soon':
		url = BASE_URL + "/movie/results/?find=ComingSoon&lang="+lang+"&page="+page_count
	elif cat == 'Number or Alphabet':
		if key == 'Number':
			url = BASE_URL + "/movie/results/?find=Numbers&lang="+lang+"&page="+page_count
		else:
			url = BASE_URL + "/movie/results/?find=Alphabets&lang="+lang+"&alpha="+key+"&page="+page_count
	elif cat == 'Year':
		url = BASE_URL + "/movie/results/?find=Year&lang="+lang+"&year="+key+"&page="+page_count
	elif cat == 'Cast':
		url = BASE_URL + "/movie/results/?find=Cast&lang="+lang+"&id="+key+"&page="+page_count+"&role="
	elif cat == 'Genre':
		if filter == 'action':
			find_filter = "&find=Rating&action=4&comedy=1&romance=1&storyline=1&performance=1&ratecount=5"
		elif filter == 'comedy':
			find_filter = "&find=Rating&action=1&comedy=4&romance=1&storyline=1&performance=1&ratecount=5"
		elif filter == 'romance':
			find_filter = "&find=Rating&action=1&comedy=1&romance=4&storyline=1&performance=1&ratecount=5"
		elif filter == 'storyline':
			find_filter = "&find=Rating&action=1&comedy=1&romance=1&storyline=4&performance=1&ratecount=5"
		elif filter == 'performance':
			find_filter = "&find=Rating&action=1&comedy=1&romance=1&storyline=1&performance=4&ratecount=5"
		
		cat2title = "-%s" % filter.title()
		url = BASE_URL + "/movie/results/?lang="+lang+find_filter+"&page="+page_count
	
	oc = ObjectContainer(title2="%s%s" % (cat.title(), cat2title) + " (Page" + page_count + ")")
	
	page_elems = common.GetPageElements(url)
	
	movies = page_elems.xpath(".//section[@id='UIMovieSummary']/ul/li")
	for block in movies:
		loc = BASE_URL + block.xpath(".//div[@class='block1']//@href")[0]
		try:
			thumb = "http:" + block.xpath(".//div[@class='block1']//@src")[0]
		except:
			thumb = "http:" + block.xpath(".//div[@class='block1']//@data-src")[0]
		title = block.xpath(".//div[@class='block2']//a[@class='title']//text()")[0]
		try:
			summary = block.xpath(".//p[@class='synopsis']//text()")[0]
			if summary == None or summary == "":
				summary = "Synopsis currently unavailable."
		except:
			summary = "Synopsis currently unavailable."
		try:
			profs = block.xpath(".//div[@class='professionals']//div[@class='prof']")
			for prof in profs:
				summary += "\n "
				summary += prof.xpath(".//label//text()")[0] + " : " + prof.xpath(".//p//text()")[0]
		except:
			pass
		if cat == 'Coming Soon':
			oc.add(DirectoryObject(key = Callback(ComingSoon, title=title), title = title, summary=summary, thumb = Resource.ContentsOfURLWithFallback(url = thumb, fallback='MoviePosterUnavailable.jpg')))
		else:
			oc.add(DirectoryObject(key = Callback(EpisodeDetail, title=title, url=loc), title = title, summary=summary, thumb = Resource.ContentsOfURLWithFallback(url = thumb, fallback='MoviePosterUnavailable.jpg')))
		
	curr_page = int(page_elems.xpath(".//div[@class='pagination']//span[@class='active']//text()")[0])
	last_page = int(page_elems.xpath("(.//div[@class='pagination']//span//text())[last()]")[0])
	if last_page > curr_page:
		oc.add(DirectoryObject(key = Callback(PageDetail, lang=lang, cat=cat, key=key, filter=filter, page_count=int(page_count)+1), title = "Next Page >>", thumb = R(ICON_NEXT)))
		
	oc.add(InputDirectoryObject(key = Callback(Search, lang = lang), title='Search', summary='Search Movies', prompt='Search for...', thumb = R(ICON_SEARCH)))
		
	return oc

@route(PREFIX + "/comingsoon")
def ComingSoon(title, **kwargs):
	return ObjectContainer(header=title, message=title + ' will be Available Soon')

@route(PREFIX + "/episodedetail")
def EpisodeDetail(title, url, **kwargs):
	
	
	Thread.Create(GetVideoUrl,{},url)
	
	page_elems = common.GetPageElements(url)
	
	try:
		try:
			thumb = "http:" + page_elems.xpath(".//section[@id='UIMovieSummary']//div[@class='block1']//@src")[0]
		except:
			thumb = "http:" + page_elems.xpath(".//section[@id='UIMovieSummary']//div[@class='block1']//@data-src")[0]
	except:
		thumb = None
	try:
		summary = page_elems.xpath(".//section[@id='UIMovieSummary']//p[@class='synopsis']//text()")[0]
	except:
		summary = "Synopsis currently unavailable."
	try:
		year = str(page_elems.xpath(".//section[@id='UIMovieSummary']//div[@class='info']//p[1]//text()")[0])
	except:
		year = 0000
	try:
		ratings = page_elems.xpath(".//section[@id='UIMovieSummary']//ul[@class='average-rating']//p//text()")
		rating = float(0.0)
		for rate in ratings:
			rating += float(rate)
		rating = rating * 10/25
	except:
		rating = float(0.0)
	try:
		profs = page_elems.xpath(".//section[@id='UIMovieSummary']//div[@class='professionals']//div[@class='prof']")
		for prof in profs:
			summary += "\n "
			summary += prof.xpath(".//label//text()")[0] + " : " + prof.xpath(".//p//text()")[0]
	except:
		pass
		
	trailer_urls = page_elems.xpath(".//section[@id='UIMovieSummary']//div[@class='extras']//@href")
	for trailer_u in trailer_urls:
		if 'youtube' in trailer_u:
			trailer = trailer_u.replace("/myaddrproxy.php/https/", "http://")
	
	title = title
	oc = ObjectContainer(title1 = unicode(title), art=thumb)
	art = thumb
	
	timer = 0
	while VideoURL['GetVideoUrlComplete'] == 'False':
		time.sleep(1)
		timer += 1
		if timer > 20: # using 20 sec. timeout
			return ObjectContainer(header=title, message=title + ' : Timeout error occurred !')
	
		
	furl = VideoURL['GetVideoUrlComplete']
	datacenter = VideoURL['GetVideoUrlDatacenter']
	# fix San Jose datacenter label
	if datacenter == 'San':
		datacenter = 'San Jose'
	
	if 'error-fail' in furl:
		return ObjectContainer(header=title, message=title + ' could not be fetched !')
		
	try:
		oc.add(VideoClipObject(
			url = trailer,
			art = art,
			title = title + " (Trailer)",
			thumb = Resource.ContentsOfURLWithFallback(url = thumb, fallback='MoviePosterUnavailable.jpg'),
			summary = summary
			)
		)
	except:
		trailer = ""
		
	server_n = DetermineCurrentServer(furl, datacenter)
	try:
		oc.add(VideoClipObject(
			url = "einthusan://" + E(JSON.StringFromObject({"url":furl, "title": title, "summary": summary, "thumb": thumb, "year": year, "rating": rating})),
			art = art,
			title = title + " (via " + datacenter + " Server ID:" + server_n + ")",
			thumb = thumb,
			summary = summary
			)
		)
	except:
		url = ""
		
	furl2, server_n2, ret_code = AvailableSourceFrom(furl, Prefs["locationPref"])
	if ret_code == "200":
		#server_n2 = DetermineCurrentServer(furl2, Prefs["locationPref"])
		try:
			oc.add(VideoClipObject(
				url = "einthusan://" + E(JSON.StringFromObject({"url":furl2, "title": title, "summary": summary, "thumb": thumb, "year": year, "rating": rating})),
				art = art,
				title = title + " (via " + Prefs["locationPref"] + " Server ID:" + server_n2 + ")",
				thumb = thumb,
				summary = summary
				)
			)
		except:
			url = ""
		
	oc.add(DirectoryObject(
			key = Callback(AllAvailableSources, furl=furl, title=title, summary=summary, thumb=thumb, year=year, rating=rating, art=art),
			title = "Other Servers Available",
			art = art,
			summary = "Play using a different server",
			thumb = R(ICON_SOURCES)
		)
	)
	
	if Check(title=title,url=url):
		oc.add(DirectoryObject(
			key = Callback(RemoveBookmark, title = title, url = url),
			title = "Remove Bookmark",
			art = art,
			summary = 'Removes the current movie from the Boomark que',
			thumb = R(ICON_QUEUE)
		)
	)
	else:
		oc.add(DirectoryObject(
			key = Callback(AddBookmark, title = title, url = url),
			title = "Bookmark Video",
			summary = 'Adds the current movie to the Boomark que',
			art = art,
			thumb = R(ICON_QUEUE)
		)
	)

	return oc
		
# Initialize SlimerJS and dependencies at startup for faster load time later in use	
def initSlimerJS():		
	Log("Initializing SlimerJS")
	firefox_dir = Prefs['firefox_dir']
	if firefox_dir == None:
		firefox_dir = ""
	python_dir = Prefs['python_dir']
	if python_dir == None:
		python_dir = ""
	
	res = slimerjs.einthusan(python_dir=python_dir, firefox_dir=firefox_dir, url="https://einthusan.ca")
	if res == "":
		res = "Success"
	Log("Initialized SlimerJS: " + res)
	
@route(PREFIX + "/GetVideoUrl")
def GetVideoUrl(url, **kwargs):

	VideoURL['GetVideoUrlComplete'] = 'False'
	furl = 'error-fail'
	datacenter = 'Unknown'
	debug = Prefs['use_debug']
	
	if url not in LAST_PROCESSED_URL:
		del LAST_PROCESSED_URL[:]
		
		if Prefs["use_slimerjs"]:
			if debug:
				Log("Running SlimerJS routine for : " + url)
			firefox_dir = Prefs['firefox_dir']
			python_dir = Prefs['python_dir']
			res = slimerjs.einthusan(python_dir=python_dir, firefox_dir=firefox_dir, url=url, debug=debug)
			out = "{" + find_between( out, "{", "}" ) + "}"
		else:
			if debug:
				Log("Internal routine for : %s" % url)
			out = einthusan.GetEinthusanData(url=url, debug=debug)
			
		if 'error-fail' not in out and 'MP4Link' in out:
			try:
				res2 = json.loads(out)
				furl = res2['MP4Link']
				datacenter = res2["Datacenter"]
				#Log("vidfile: " + furl)
				LAST_PROCESSED_URL.append(url)
				LAST_PROCESSED_URL.append(furl)
				LAST_PROCESSED_URL.append(datacenter)
				if debug:
					Log("Output: %s" % out)
			except:
				Log("Error: No Video link. Output: %s" % out)
		else:
			Log("Output: %s" % out)
	else:
		furl = LAST_PROCESSED_URL[1]
		datacenter = LAST_PROCESSED_URL[2]
		
	# fix San Jose datacenter label
	if datacenter == 'San':
		datacenter = 'San Jose'
	VideoURL['GetVideoUrlComplete'] = furl
	VideoURL['GetVideoUrlDatacenter'] = datacenter

@route(PREFIX + "/AllAvailableSources")
def AllAvailableSources(furl, title, summary, thumb, year, rating, art, **kwargs):
	
	oc = ObjectContainer(title1 = unicode(title), art=thumb)	

	for location in EINTHUSAN_SERVERS:
		location_with_state_country = location
		if EINTHUSAN_SERVER_INFO[location]["State"] != "":
			location_with_state_country += " (" + EINTHUSAN_SERVER_INFO[location]["State"] + ") - " + EINTHUSAN_SERVER_INFO[location]["Country"]
		else:
			location_with_state_country += " - " + EINTHUSAN_SERVER_INFO[location]["Country"]
		oc.add(DirectoryObject(
			key = Callback(AllAvailableSources2, furl=furl, title=title, summary=summary, thumb=thumb, year=year, rating=rating, art=art, location=location),
			title = location_with_state_country,
			art = art,
			summary = "Play using " + location_with_state_country + " server",
			thumb = R(EINTHUSAN_SERVER_INFO[location]["Flag"])
			)
		)
		
	return oc	
	
@route(PREFIX + "/AllAvailableSources2")
def AllAvailableSources2(furl, title, summary, thumb, year, rating, art, location, **kwargs):
	
	oc = ObjectContainer(title1 = unicode(title), art=thumb)	
	vidpath = furl.split('.io/')[1]

	for idx in EINTHUSAN_SERVER_INFO[location]["Servers"]:
		furl = ("https://cdn" + str(idx+SERVER_OFFSET[0]) + ".einthusan.io/" + vidpath)
		ret_code = GetHttpStatus(url=furl)
		if ret_code == "200":
			oc.add(VideoClipObject(
				url = "einthusan://" + E(JSON.StringFromObject({"url":furl, "title": title, "summary": summary, "thumb": thumb, "year": year, "rating": rating})),
				art = art,
				title = unicode(title + " (Server ID:" + str(idx+SERVER_OFFSET[0]) + ")"),
				thumb = thumb,
				summary = summary
				)
			)
	return oc
	
@route(PREFIX + "/AvailableSourceFrom")
def AvailableSourceFrom(furl, location, **kwargs):

	# fix San Jose datacenter label
	if location == 'San':
		location = 'San Jose'
	
	try:
		vidpath = furl.split('.io/')[1]
		choice_str = str(random.choice(EINTHUSAN_SERVER_INFO[location]["Servers"]) + SERVER_OFFSET[0])
	except:
		choice_str = '1'
		
	url = ("https://cdn" + choice_str + ".einthusan.io/" + vidpath)
	ret_code = GetHttpStatus(url=url)
	
	return url, choice_str, ret_code

@route(PREFIX + "/DetermineCurrentServer")
def DetermineCurrentServer(furl, location, **kwargs):
	server_n = furl.split('.einthusan.io')[0].strip('https://cdn')
	
	del SERVER_OFFSET[:]
	if int(server_n) > 100:
		SERVER_OFFSET.append(100)
	else:
		SERVER_OFFSET.append(0)
	
	# fix San Jose datacenter label
	if location == 'San':
		location = 'San Jose'
	
	try:
		for idx in EINTHUSAN_SERVER_INFO[location]["Servers"]:
			if (int(idx) + int(SERVER_OFFSET[0])) == int(server_n):
				return str(int(idx)+int(SERVER_OFFSET[0]))
	except:
		pass
	
	Log("Unknown Server: Wrong assignment in constant EINTHUSAN_SERVER_INFO")
	Log(location)	
	Log(server_n)
	return server_n
	
def AddSourceInfo():
	US_FLAG = "icon-us.png"
	UK_FLAG = "icon-uk.png"
	CAN_FLAG = "icon-can.png"
	AUS_FLAG = "icon-aus.png"
	
	EINTHUSAN_SERVER_INFO["Dallas"] = {}
	EINTHUSAN_SERVER_INFO["Dallas"]["Servers"]=[2]
	EINTHUSAN_SERVER_INFO["Dallas"]["Country"]="US"
	EINTHUSAN_SERVER_INFO["Dallas"]["State"]="TX"
	EINTHUSAN_SERVER_INFO["Dallas"]["Flag"]=US_FLAG
	
	EINTHUSAN_SERVER_INFO["Washington"] = {}
	EINTHUSAN_SERVER_INFO["Washington"]["Servers"]=[1]
	EINTHUSAN_SERVER_INFO["Washington"]["Country"]="US"
	EINTHUSAN_SERVER_INFO["Washington"]["State"]="D.C."
	EINTHUSAN_SERVER_INFO["Washington"]["Flag"]=US_FLAG
	
	EINTHUSAN_SERVER_INFO["Los Angeles"] = {}
	EINTHUSAN_SERVER_INFO["Los Angeles"]["Servers"] = [3]
	EINTHUSAN_SERVER_INFO["Los Angeles"]["Country"] = "US"
	EINTHUSAN_SERVER_INFO["Los Angeles"]["State"] = "CA"
	EINTHUSAN_SERVER_INFO["Los Angeles"]["Flag"] = US_FLAG
    
    EINTHUSAN_SERVER_INFO["London"] = {}
    EINTHUSAN_SERVER_INFO["London"]["Servers"] = [4]
    EINTHUSAN_SERVER_INFO["London"]["Country"] = "UK"
    EINTHUSAN_SERVER_INFO["London"]["State"] = ""
    EINTHUSAN_SERVER_INFO["London"]["Flag"] = UK_FLAG

def find_between( s, first, last ):
    try:
        start = s.rindex( first ) + len( first )
        end = s.rindex( last, start )
        return s[start:end]
    except ValueError:
        return ""

######################################################################################
# Loads bookmarked shows from Dict.  Titles are used as keys to store the show urls.

@route(PREFIX + "/bookmarks")	
def Bookmarks(title, **kwargs):

	oc = ObjectContainer(title1 = title)
	
	for each in Dict:
		url = Dict[each]
		#Log("url-----------" + url)
		if url.find(TITLE.lower()) != -1 and 'http' in url and '.mp4' not in url:
			if 'einthusan.ca' in url:
				url = GetRedirector(url)
				Dict[each] = url
			oc.add(DirectoryObject(
				key = Callback(EpisodeDetail, title = each, url = url),
				title = each,
				thumb = R(ICON_MOVIES)
				)
			)
		elif '.mp4' in url:
			Dict[each] = ""
	
	Dict.Save()
	
	#add a way to clear bookmarks list
	oc.add(DirectoryObject(
		key = Callback(ClearBookmarks),
		title = "Clear Bookmarks",
		thumb = R(ICON_QUEUE),
		summary = "CAUTION! This will clear your entire bookmark list!"
		)
	)
	
	if len(oc) == 1:
		return ObjectContainer(header=title, message='No Bookmarked Videos Available')
	return oc

######################################################################################
# Checks a show to the bookmarks list using the title as a key for the url
@route(PREFIX + "/checkbookmark")	
def Check(title, url, **kwargs):
	bool = False
	url = Dict[title]
	#Log("url-----------" + url)
	if url != None and (url.lower()).find(TITLE.lower()) != -1:
		bool = True
	
	return bool

######################################################################################
# Adds a show to the bookmarks list using the title as a key for the url
	
@route(PREFIX + "/addbookmark")
def AddBookmark(title, url, **kwargs):
	
	Dict[title] = url
	Dict.Save()
	return ObjectContainer(header=title, message='This movie has been added to your bookmarks.')
######################################################################################
# Removes a show to the bookmarks list using the title as a key for the url
	
@route(PREFIX + "/removebookmark")
def RemoveBookmark(title, url, **kwargs):
	
	Dict[title] = 'removed'
	Dict.Save()
	return ObjectContainer(header=title, message='This movie has been removed from your bookmarks.')	
######################################################################################
# Clears the Dict that stores the bookmarks list
	
@route(PREFIX + "/clearbookmarks")
def ClearBookmarks(**kwargs):

	for each in Dict:
		if each.find(TITLE.lower()) != -1 and 'http' in each:
			Dict[each] = 'removed'
	Dict.Save()
	return ObjectContainer(header="Bookmarks", message='Your bookmark list will be cleared soon.')

######################################################################################
# Clears the Dict that stores the search list
	
@route(PREFIX + "/clearsearches")
def ClearSearches(**kwargs):

	for each in Dict:
		if each.find(TITLE.lower()) != -1 and 'MyCustomSearch' in each:
			Dict[each] = 'removed'
	Dict.Save()
	return ObjectContainer(header="Search Queue", message='Your Search Queue list will be cleared soon.')
	
####################################################################################################
@route(PREFIX + "/search")
def Search(query, lang, page_count='1', **kwargs):
	
	title = query
	Dict[TITLE.lower() +'MyCustomSearch'+query] = query
	Dict[TITLE.lower() +'MyCustomSLang'+query] = lang
	Dict.Save()
	oc = ObjectContainer(title2='Search Results')
	
	url = (BASE_URL + '/movie/results/' + '?lang='+ lang + '&page=' + page_count + '&query=%s' % String.Quote(query, usePlus=True))
	page_elems = common.GetPageElements(url)

	movies = page_elems.xpath(".//section[@id='UIMovieSummary']/ul/li")
	for block in movies:
		loc = BASE_URL + block.xpath(".//div[@class='block1']//@href")[0]
		try:
			thumb = "http:" + block.xpath(".//div[@class='block1']//@src")[0]
		except:
			thumb = "http:" + block.xpath(".//div[@class='block1']//@data-src")[0]
		title = block.xpath(".//div[@class='block2']//a[@class='title']//text()")[0]
		try:
			summary = block.xpath(".//p[@class='synopsis']//text()")[0]
			if summary == None or summary == "":
				summary = "Synopsis currently unavailable."
		except:
			summary = "Synopsis currently unavailable."
		try:
			profs = block.xpath(".//div[@class='professionals']//div[@class='prof']")
			for prof in profs:
				summary += "\n "
				summary += prof.xpath(".//label//text()")[0] + " : " + prof.xpath(".//p//text()")[0]
		except:
			pass
		oc.add(DirectoryObject(key = Callback(EpisodeDetail, title=title, url=loc), title = title, summary=summary, thumb = Resource.ContentsOfURLWithFallback(url = thumb, fallback='MoviePosterUnavailable.jpg')))
		
	curr_page = int(page_elems.xpath(".//div[@class='pagination']//span[@class='active']//text()")[0])
	last_page = int(page_elems.xpath("(.//div[@class='pagination']//span//text())[last()]")[0])
	if last_page > curr_page:
		oc.add(DirectoryObject(key = Callback(Search, lang=lang, query=query, page_count=int(page_count)+1), title = "Next Page >>", thumb = R(ICON_NEXT)))
		
	if len(oc) == 0:
		return ObjectContainer(header=title, message='No Videos Available')
	return oc
	

@route(PREFIX + "/searchQueueMenu")
def SearchQueueMenu(title, **kwargs):
	oc2 = ObjectContainer(title2='Search Using Term')
	#add a way to clear bookmarks list
	oc2.add(DirectoryObject(
		key = Callback(ClearSearches),
		title = "Clear Search Queue",
		thumb = R(ICON_SEARCH_QUEUE),
		summary = "CAUTION! This will clear your entire search queue list!"
		)
	)
	for each in Dict:
		query = Dict[each]
		#Log("each-----------" + each)
		#Log("query-----------" + query)
		if each.find(TITLE.lower()) != -1 and 'MyCustomSearch' in each and query != 'removed':
			lang = Dict[TITLE.lower() +'MyCustomSLang'+query]
			if lang == None or lang == '':
				lang = Prefs['langPref']
			oc2.add(DirectoryObject(key = Callback(Search, query = query, lang = lang), title = query, thumb = R(ICON_SEARCH))
		)

	return oc2
####################################################################################################
@route(PREFIX + '/getredirector')
def GetRedirector(url, **kwargs):

	redirectUrl = url
	try:
		page = urllib2.urlopen(url)
		redirectUrl = page.geturl()
	except:
		redirectUrl = url
			
	#Log("Redirecting url ----- : " + redirectUrl)
	return redirectUrl
		
####################################################################################################
# Get HTTP response code (200 == good)
@route(PREFIX + '/gethttpstatus')
def GetHttpStatus(url, **kwargs):
	try:
		if Prefs["use_https_alt"]:
			resp = einthusan.requestWithHeaders(url, output='responsecode')
		else:
			headers = {'User-Agent': common.USER_AGENT,
			   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
			   'Accept-Encoding': 'none',
			   'Accept-Language': 'en-US,en;q=0.8',
			   'Connection': 'keep-alive',
			   'Referer': url}
		   
			if '|' in url:
				url_split = url.split('|')
				url = url_split[0]
				headers['Referer'] = url
				for params in url_split:
					if '=' in params:
						param_split = params.split('=')
						param = param_split[0].strip()
						param_val = urllib2.quote(param_split[1].strip(), safe='/=&')
						headers[param] = param_val

			if 'http://' in url or 'https://' in url:
				req = urllib2.Request(url, headers=headers)
				conn = urllib2.urlopen(req, timeout=10)
				resp = str(conn.getcode())
			else:
				resp = '200'
	except Exception as e:
		resp = '0'
		if Prefs['use_debug']:
			Log('Error > GetHttpStatus: ' + str(e))
			Log(url +' : HTTPResponse = '+ resp)
	return resp
