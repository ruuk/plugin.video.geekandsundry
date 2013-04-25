import sys, urllib, urllib2, re, xbmcgui, xbmcplugin

def addLink(self,name,url,iconimage,tot=0,contextMenu=None,ltype='image'):
	#u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&name="+urllib.quote_plus(name)
	liz=xbmcgui.ListItem(name, iconImage="DefaultImage.png", thumbnailImage=iconimage)
	liz.setInfo( type=ltype, infoLabels={ "Title": name } )
	liz.setProperty( "sharing","handled" )
	if contextMenu: liz.addContextMenuItems(contextMenu)
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz,isFolder=False,totalItems=tot)

def addDir(self,name,url,mode,iconimage,page=1,tot=0,userid='',desc=''):
	if userid: userid = "&userid="+urllib.quote_plus(userid)
	u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&page="+str(page)+userid+"&name="+urllib.quote_plus(name.encode('ascii','replace'))
	liz=xbmcgui.ListItem(name, 'test',iconImage="DefaultFolder.png", thumbnailImage=iconimage)
	liz.setInfo( type="image", infoLabels={"Title": name} )
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True,totalItems=tot)

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
		addDir(idict.get('title',''),'http:' + idict.get('url',''),idict.get('logo',''),desc=idict.get('desc'))

def showShow(url):
	if not url: return False
	html = urllib2.urlopen(url).read()
	items = re.finditer("(?is)<li class='episode-item-(?P<section>[^']+)'>.+?<a href='(?P<url>[^']+)'.+?<img src=\"(?P<thumb>[^\"]+)\".+?</li>.+?<h2>(?P<title>[^<]+)</h2>",html)
	for i in items:
		idict = i.groupdict()
		addDir(idict.get('title',''),url + idict.get('url',''),idict.get('thumb',''))
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
	if not mode:
		showMain()
	elif mode == 'show':
		success = showShow(params.get('url'))
	elif mode == 'video':
		success = showVideo(params.get('url'))
		if success: return
		
	if mode != 9999: xbmcplugin.endOfDirectory(int(sys.argv[1]),succeeded=success,updateListing=update_dir,cacheToDisc=cache)

if __name__ == '__main__':
	doPlugin()