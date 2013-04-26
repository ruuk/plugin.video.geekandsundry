import os, sys, urllib, urllib2, re, htmlentitydefs, md5, time
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

CACHE_PATH = xbmc.translatePath(os.path.join(xbmcaddon.Addon('plugin.video.geekandsundry').getAddonInfo('profile'),'cache'))
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)

def LOG(msg):
	print 'plugin.video.geekandsundry: %s' % msg 

charCodeFilter = re.compile('&#(\d{1,5});',re.I)
charNameFilter = re.compile('&(\w+?);')
		
def cUConvert(m): return unichr(int(m.group(1)))
def cTConvert(m):
	return unichr(htmlentitydefs.name2codepoint.get(m.group(1),32))
	
def convertHTMLCodes(html):
	try:
		html = charCodeFilter.sub(cUConvert,html)
		html = charNameFilter.sub(cTConvert,html)
	except:
		pass
	return html

def addDir(name,url,mode,iconimage,page=1,tot=0,playable=False,desc=''):
	name = convertHTMLCodes(name)
	u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&page="+str(page)+"&name="+urllib.quote_plus(name.encode('ascii','replace'))
	liz=xbmcgui.ListItem(name, 'test',iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo( type="Video", infoLabels={"Title": name} )
	if playable: liz.setProperty('IsPlayable', 'true')
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=not playable,totalItems=tot)

def get_params():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]
	else:
		param={}					
	return param

def showMain():
	url = 'http://www.geekandsundry.com/'
	html = getCachedHTML('main',url)
	if not html:
		html = urllib2.urlopen(url).read()
		cacheHTML('main', url, html)
	nhtml = html.split('<div class="new-shows">',1)[-1].split('<div class="clear">',1)[0]
	ohtml = html.split('<div class="old-shows">',1)[-1].split('<div class="clear">',1)[0]
	items = re.finditer("(?is)<a href='(?P<url>[^\"'>]+)'>.+?<img src=\"(?P<logo>[^\"'>]+)\" alt=\"(?P<title>[^\"]+)\".+?<p>(?P<desc>[^<]+)</p>.+?</a>",nhtml+ohtml)
	for i in items:
		idict = i.groupdict()
		addDir(idict.get('title',''),'http:' + idict.get('url',''),'show',idict.get('logo',''),desc=idict.get('desc'))

def showSeason(url):
	if not url: return False
	section,url = url.split(':',1)
	html = getCachedHTML('show',url)
	if not html:
		html = urllib2.urlopen(url).read()
		cacheHTML('show', url, html)
	items = re.finditer("(?is)<li class='episode-item-(?P<section>[^']+)'>\s+?<a href='(?P<url>[^']+)'.+?<img src=\"(?P<thumb>[^\"]+)\".+?<h2>(?P<title>[^<]+)</h2>.+?</li>",html)
	for i in items:
		idict = i.groupdict()
		currSection = idict.get('section','')
		if currSection == section:
			addDir(idict.get('title',''),url + idict.get('url',''),'video',idict.get('thumb',''),playable=True)
	return True

def showShow(url):
	if not url: return False
	html = getCachedHTML('show',url)
	if not html:
		html = urllib2.urlopen(url).read()
		cacheHTML('show', url, html)
	items = re.finditer("(?is)<li class='episode-item-(?P<section>[^']+)'>\s+?<a href='(?P<url>[^']+)'.+?<img src=\"(?P<thumb>[^\"]+)\".+?<h2>(?P<title>[^<]+)</h2>.+?</li>",html)
	sections = {}
	for i in items:
		idict = i.groupdict()
		section = idict.get('section','')
		if not section in sections:
			sections[section] = 1
			if section.startswith('episode-') or section.startswith('extras-'):
				display = section.split('-',1)[-1]
				num = re.search('\d+$',display)
				if num:
					display = re.sub('\d+$','',display) + ' ' + num.group(0)
				if section.startswith('extras-'): display += ' - Extras '
			else:
				display = section.replace('-',' ')
			display = display.title()
			addDir(display,section + ':' + url,'season',idict.get('thumb',''))
	return True

def showVideo(url):
	if not url: return False
	html = urllib2.urlopen(url).read()
	ID = re.search('(?is)<iframe.+?src="[^"]+?embed/(?P<id>[^/"]+)".+?</iframe>',html).group(1)
	url = 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + ID
	listitem = xbmcgui.ListItem(label='Video', path=url)
	listitem.setInfo(type='Video',infoLabels={"Title": 'Video'})
	xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=listitem)
	return True

def cacheHTML(prefix,url,html):
	fname = prefix + '.' + md5.md5(url).hexdigest()
	with open(os.path.join(CACHE_PATH,fname),'w') as f:
		f.write(str(time.time()) + '\n' + html)
		
def getCachedHTML(prefix,url):
	fname = prefix + '.' + md5.md5(url).hexdigest()
	path = os.path.join(CACHE_PATH,fname)
	if not os.path.exists(path): return None
	with open(path,'r') as f:
		data = f.read()
		last, html = data.split('\n',1)
	try:
		if time.time() - float(last) > 3600:
			LOG('Cached file expired. Getting new html...')
			return None
	except:
		LOG('Failed to process file cache time')
		return None
	
	LOG('Using cached HTML')
	return html

def doPlugin():
	success = True
	cache = True
	update_dir = False
	
	params=get_params()
	
	mode = params.get('mode')
	url = urllib.unquote_plus(params.get('url',''))
	if not mode:
		showMain()
	elif mode == 'season':
		success = showSeason(url)
	elif mode == 'show':
		success = showShow(url)
	elif mode == 'video':
		success = showVideo(url)
		if success: return
		
	if mode != 9999: xbmcplugin.endOfDirectory(int(sys.argv[1]),succeeded=success,updateListing=update_dir,cacheToDisc=cache)

if __name__ == '__main__':
	doPlugin()