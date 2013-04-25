import sys, urllib, urllib2, re, htmlentitydefs, xbmcgui, xbmcplugin

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
	html = urllib2.urlopen('http://www.geekandsundry.com/').read()
	nhtml = html.split('<div class="new-shows">',1)[-1].split('<div class="clear">',1)[0]
	ohtml = html.split('<div class="old-shows">',1)[-1].split('<div class="clear">',1)[0]
	items = re.finditer("(?is)<a href='(?P<url>[^\"'>]+)'>.+?<img src=\"(?P<logo>[^\"'>]+)\" alt=\"(?P<title>[^\"]+)\".+?<p>(?P<desc>[^<]+)</p>.+?</a>",nhtml+ohtml)
	for i in items:
		idict = i.groupdict()
		addDir(idict.get('title',''),'http:' + idict.get('url',''),'show',idict.get('logo',''),desc=idict.get('desc'))

def showShow(url):
	if not url: return False
	html = urllib2.urlopen(url).read()
	items = re.finditer("(?is)<li class='episode-item-(?P<section>[^']+)'>\s+?<a href='(?P<url>[^']+)'.+?<img src=\"(?P<thumb>[^\"]+)\".+?<h2>(?P<title>[^<]+)</h2>.+?</li>",html)
	for i in items:
		idict = i.groupdict()
		addDir(idict.get('title',''),url + idict.get('url',''),'video',idict.get('thumb',''),playable=True)
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

def doPlugin():
	success = True
	cache = True
	update_dir = False
	
	params=get_params()
	
	mode = params.get('mode')
	url = urllib.unquote_plus(params.get('url',''))
	if not mode:
		showMain()
	elif mode == 'show':
		success = showShow(url)
	elif mode == 'video':
		success = showVideo(url)
		if success: return
		
	if mode != 9999: xbmcplugin.endOfDirectory(int(sys.argv[1]),succeeded=success,updateListing=update_dir,cacheToDisc=cache)

if __name__ == '__main__':
	doPlugin()