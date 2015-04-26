import os, sys, urllib, requests, urlparse, re, htmlentitydefs, hashlib, time
if sys.version < '2.7.3': #If crappy html.parser, use internal version. Using internal version on ATV2 crashes as of XBMC 12.2, so that's why we test version
    import HTMLParser #analysis:ignore
import bs4  # @UnresolvedImport

from xbmcswift2 import Plugin, xbmc
plugin = Plugin()

__version__ = plugin.addon.getAddonInfo('version')
T = plugin.addon.getLocalizedString
CACHE_PATH = xbmc.translatePath(os.path.join(plugin.addon.getAddonInfo('profile'),'cache'))
FANART_PATH = xbmc.translatePath(os.path.join(plugin.addon.getAddonInfo('profile'),'fanart'))
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)
if not os.path.exists(FANART_PATH): os.makedirs(FANART_PATH)
ADDON_PATH = xbmc.translatePath(plugin.addon.getAddonInfo('path'))
plugin_fanart = os.path.join(ADDON_PATH,'fanart.jpg')

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.57 Safari/537.17'
HEADERS = {'User-Agent':USER_AGENT}

def ERROR(msg):
    plugin.log.error('ERROR: {0}'.format(msg))
    import traceback
    traceback.print_exc()

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

def getPage(url,referer='http://geekandsundry.com'):
    headers = HEADERS.copy()
    headers['referer'] = referer
    return requests.get(url,headers=headers).text

def getSoup(html,default_parser="html5lib"):
    try:
        soup = bs4.BeautifulSoup(html, default_parser)
        plugin.log.info('Using: %s' % default_parser)
    except:
        soup = bs4.BeautifulSoup(html,"html.parser")
        plugin.log.info('Using: html.parser')
    return soup

@plugin.route('/')
def showMain():
    items = []
    items.append({'label':T(32100),'path':plugin.url_for('showNewest')})
    items.append({'label':T(32103),'path':plugin.url_for('showAllShows')})
#    items.append({'label':T(32105),'path':plugin.url_for('showVlogs')})
    return items

@plugin.route('/all/')
def showAllShows():
    url = 'http://geekandsundry.com/shows/'
    html = getCachedHTML('main',url)
    if not html:
        try:
            html = getPage(url)
            cacheHTML('main', url, html)
        except:
            ERROR('Failed getting main page')
            xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % ('Geek & Sundry',T(32101),3,plugin.addon.getAddonInfo('icon')))  # @UndefinedVariable #For xbmcswift2
            plugin.set_content('tvshows')
            return

    items = []

    soup = getSoup(html)
    div = soup.select('div.shelf')
    if not div: return
    anchors = div[0].findAll('a')
    for a in anchors:
        title = convertHTMLCodes(a.string)
#        if title.lower() == 'vlogs': continue
        url = a.get('href')
        fanart = createFanart(None,url)
        status = ''
#        statusdisp = status
#        if 'Air' in status:
#            statusdisp = '[COLOR green]{0}[/COLOR]'.format(status)
#        elif 'Hiatus' in status:
#            statusdisp = '[COLOR FFAAAA00]{0}[/COLOR]'.format(status)
#        plot = '{0}: [B]{1}[/B][CR][CR]{2}'.format(T(32102),statusdisp,idict.get('desc'))
        mode = 'showShow'
        items.append(   {   'label':title,
                            'path':plugin.url_for(mode,url=url),
                            'icon':'',
                            'properties':{'fanart_image':fanart},
                            'info':{'Plot':'','status':status}
                        }
        )

    plugin.set_content('tvshows')
    return items

@plugin.route('/vlogs/')
def showVlogs():
    url = 'http://www.geekandsundry.com/'
    html = getCachedHTML('main',url)
    if not html:
        html = getPage(url)
        cacheHTML('main', url, html)
    soup = getSoup(html,default_parser='html.parser')
    vlogs = soup.select('.subvlogs')
    if not vlogs: return
    items = []
    for a in vlogs[0].findAll('a'):
        url = a.get('href') or ''
        li = a.li
        if not li:
            continue
        icon = li.img.get('src') or ''
        fanart = ''
        try:
            fanart = createFanart(urlparse.urljoin(url,icon),url)
        except:
            plugin.log.info(str(sys.exc_info()[1]))
        span = li.span
        if not span:
            continue
        title = span.string or ''
        items.append(    {    'label':convertHTMLCodes(title),
                            'path':plugin.url_for('showShow',url=url),
                            'icon':icon,
                            'properties':{'fanart_image':fanart},
                        }
        )
    items.sort(key=lambda x: x['label'])
    return items

def getVlogVideos(html):
    try:
        soup = getSoup(html,default_parser="html.parser")
        shows = soup.select('.ui-carousel')
        if not shows: return None
        items = []
        for li in shows[0].findAll('li'):
            url = li.a.get('href','')
            icon = li.img.get('src','')
            fanart = createFanart(icon,url)
            title = li.h2.string
            ep = extractEpisode(title,icon)
            items.append(    {    'label':convertHTMLCodes(title),
                                'path':plugin.url_for('showVideoURL',url=url),
                                'icon':icon,
                                'properties':{'fanart_image':fanart},
                                'info':{'Episode':ep},
                                'is_playable': True
                            }
            )
        plugin.set_content('episodes')
        return items
    except:
        ERROR('getVlogVideos()')
        return None

@plugin.route('/season/<url>')
def showSeason(url):
    if not url: return False
    section,url = url.split(':',1)
    html = getCachedHTML('show',url)
    if not html:
        html = getPage(url)
        cacheHTML('show', url, html)
    results = re.finditer("(?is)<li class='episode-item-(?P<section>[^']+)'>\s+?<a href='(?P<url>[^']+)'.+?<img src=\"(?P<thumb>[^\"]*)\".+?<h2>(?P<title>[^<]+)</h2>.+?</li>",html)
    try:
        fanart = 'http://www.geekandsundry.com' + re.search('<div id="show-banner"[^>]*url\(\'(?P<url>[^\']*)\'',html).group(1)
        fanart = createFanart(fanart,url)
    except:
        fanart = ''
    items = []
    for i in results:
        idict = i.groupdict()
        currSection = idict.get('section','')
        if currSection == section:
            ep = extractEpisode(idict.get('title',''),idict.get('thumb',''))
            items.append(    {  'label':convertHTMLCodes(idict.get('title','')),
                                'path':plugin.url_for('showVideoURL',url=urlparse.urljoin(url,idict.get('url',''))),
                                'icon':idict.get('thumb',''),
                                'properties':{'fanart_image':fanart},
                                'info':{'Episode':ep},
                                'is_playable': True
                            }
            )
    plugin.set_content('episodes')
    return items

@plugin.route('/show/<url>')
def showShow(url):
    if not url: return False
    html = getCachedHTML('show',url)
    if not html:
        html = getPage(url)
        cacheHTML('show', url, html)
    soup = getSoup(html)
    pages = soup.select('a.page-numbers')
    lastPage = 1
    if pages:
        try:
            lastPage = int(pages[-1].string)
        except:
            pass
    if 'vlogger' in url: return getVlogVideos(html)
#    try:
#        fanart = urlparse.urljoin('http://www.geekandsundry.com',re.search('<div id="show-banner"[^>]*url\(\'(?P<url>[^\']*)\'',html).group(1))
#        fanart = createFanart(fanart,url)
#    except:
#        fanart = ''
    items = []
    for page in range(1,lastPage+1):
        if not soup:
            pageURL = url + 'page/{0}/'.format(page)
            html = getCachedHTML('show',pageURL)
            if not html:
                html = getPage(pageURL,referer=url)
                cacheHTML('show', pageURL, html)
            soup = getSoup(html)

        for a in soup.select('a.post'):
            contentDiv = a.select('div.content-type')
            if contentDiv:
                content = contentDiv[0].string.strip()
                if not content.lower() == 'show':
                    continue
            title = a.h2.contents[0].strip()
            icon = ''
            imgdiv = a.select('div.grid_image')
            if imgdiv:
                icon = imgdiv[0].get('data-2x2') or ''

            epURL = a.get('href') or ''
            items.append(    {  'label':convertHTMLCodes(title),
                                'path':plugin.url_for('showVideoURL',url=epURL),
                                'icon':icon,
                                'properties':{'fanart_image':icon,},
                                'is_playable': True
                            }
            )

        soup = None
    plugin.set_content('episodes')
    return items

@plugin.route('/newest/')
def showNewest():
    items = []
    url = 'http://www.youtube.com/user/geekandsundry/videos'
    html = getCachedHTML('newest',url)
    if not html:
        html = getPage(url)
        cacheHTML('newest', url, html)
    soup = getSoup(html)
    results = soup.findAll('h3')
    for i in results:
        if not i.get('class'): continue
        a = i.find('a')
        if not a: continue

        href = a.get('href') or ''
        ID = href.split('=',1)[-1]
        thumb = 'http://i1.ytimg.com/vi/%s/0.jpg' % ID
        items.append(    {  'label':convertHTMLCodes(a.get('title','')),
                            'path':plugin.url_for('showVideo',ID=ID),
                            'icon':thumb,
                            'is_playable': True
                        }
        )
    return items

@plugin.route('/play_url/<url>')
def showVideoURL(url):
    if not url:
        plugin.set_resolved_url(None)
        return
    html = getPage(url)

    try:
        soup = getSoup(html)
        vidDiv = soup.select('div.video-wrapper')[0]
        vidScript = vidDiv.script
        if vidScript and vidScript.get('src'):
            ID = vidDiv.video.get('data-video-id')
            src = 'http:' + vidScript.get('src')
            return showBrightcoveVideo(ID,src)
    except IndexError:
        pass

    try:
        ID = re.search('(?is)<iframe.+?src="[^"]+?embed/(?P<id>[^/"]+)".+?</iframe>',html).group(1)
    except:
        ID = re.search('href="http://youtu.be/(?P<id>\w+)"',html).group(1)
    showVideo(ID)

@plugin.route('/play/<ID>')
def showVideo(ID):
    url = 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + ID
    plugin.set_resolved_url({'path':url,'info':{'type':'Video'}})

def showBrightcoveVideo(ID,src):
    script = getPage(src)
    baseURLMatch = re.search('baseUrl:"([^"]*)"',script)
    accountID = re.search('accountId:"([^"]*)"',script).group(1)
    policyKey = re.search('policyKey:"([^"]*)"',script).group(1)

    if baseURLMatch:
        baseURL = baseURLMatch.group(1)
        plugin.log.info('Using parsed baseURL')
    else:
        baseURL = 'https://edge.api.brightcove.com/playback/v1/'

    url = '{0}{1}/{2}/{3}/{4}'.format(baseURL,'accounts',accountID,'videos',ID)
    headers = HEADERS.copy()
    headers['BCOV-Policy'] = policyKey
    data = requests.get(url,headers=headers).json()
    maxHeight = 0
    url = ''
    alt = ''
    for source in data['sources']:
        if source.get('container') == 'M2TS' and not alt:
            alt = source['src']
        if 'src' in source and 'height' in source and maxHeight < source['height']: #Only sources with src are mp4 files, others are rtmp
            url = source['src']
            maxHeight = source['height']
    if not url: return
    if 'uds.ak.o' in url: url = alt
    #rtmp://[wowza-ip-address]:[port]/[application]/[appInstance]/[prefix]:[path1]/[path2]/[streamName]



    url += '|User-Agent={0}'.format(urllib.quote(USER_AGENT))
    plugin.set_resolved_url({'path':url,'info':{'type':'Video'}})

def hasPIL():
    try:
        import PIL #@analysis:ignore
        return True
    except:
        return False

def createFanart(url,page_url):
    if not hasPIL(): return url
    if '/vlogger/' in page_url or '/vlogs/' in page_url:
        outname = page_url.rsplit('/',1)[-1]
    else:
        outname = page_url.rsplit('/',1)[-1] + '.png'

    outfile = os.path.join(FANART_PATH,outname)
    if os.path.exists(outfile): return outfile
    if not url: return ''
    workfile = os.path.join(CACHE_PATH,'work.gif')
    urllib.urlretrieve(url, workfile)
    if '/vlogger/' in page_url or '/vlogs/' in page_url:
        try:
            img = tileImage(640,360,workfile)
            img.save(outfile,'PNG')
            return outfile
        except ImportError:
            pass
        except:
            ERROR('')
        return url

    try:
        from PIL import Image,ImageOps # @UnresolvedImport
        img = Image.open(workfile).convert('RGB')
        h = img.histogram()
        rgb = tuple([b.index(max(b)) for b in [ h[i*256:(i+1)*256] for i in range(3) ]])
        if img.size[0] == 60:
            img2 = ImageOps.expand(img,border=(580,150),fill=rgb)
        else:
            img2 = ImageOps.expand(img,border=(0,120),fill=rgb)
        img2.save(outfile,'PNG')
        return outfile
    except ImportError:
        pass
    except:
        ERROR('')
    return url

def tileImage(w,h,source):
    from PIL import Image # @UnresolvedImport
    source = Image.open(source).convert('RGBA')
    sw,sh = source.size
    target = Image.new('RGBA',(w,h),(0,0,0,255))
    x = 10
    y = 0
    switch = False
    while x < w:
        while y < h:
            nx = x  # @UnusedVariable
            ny = y
            nw = sw
            nh = sh
            paste = source
            if x + sw > w or y + sh > h or y < 0 or x < 0:
                if x + sw > w: nw = sw - (w - x)
                if y + sh > h: nh = sh - (h - y)
                if x < 0: nx = abs(x)  #@analysis:ignore
                if y < 0: ny = abs(y)
                paste = source.copy()
                paste.crop((0,ny,nw,nh))
            target.paste(paste,(x,y),paste)
            y+= sh + 15
        switch = not switch
        if switch:
            y = int(sw/2) * -1
        else:
            y = 0
        x+=sw + 10
    return target

def extractEpisode(title,url):
    test = re.search('(?i)(?:ep|#)(\d+)',title)
    if not test: test = re.search('(?i)_E(\d+)\.',url)
    if not test: test = re.search('[_\.]\d*(\d\d)\.',url)
    if test: return test.group(1)
    return ''

def cacheHTML(prefix,url,html):
    fname = prefix + '.' + hashlib.md5(url).hexdigest()
    with open(os.path.join(CACHE_PATH,fname),'w') as f:
        f.write(str(time.time()) + '\n' + html.encode('utf-8'))

def getCachedHTML(prefix,url):
    fname = prefix + '.' + hashlib.md5(url).hexdigest()
    path = os.path.join(CACHE_PATH,fname)
    if not os.path.exists(path): return None
    with open(path,'r') as f:
        data = f.read()
        try:
            last, html = data.split('\n',1)
        except:
            plugin.log.info('Cached file corrupt!')
    try:
        if time.time() - float(last) > 3600:
            plugin.log.info('Cached file expired. Getting new html...')
            return None
    except:
        plugin.log.info('Failed to process file cache time')
        return None

    plugin.log.info('Using cached HTML')
    return html.decode('utf-8')

if __name__ == '__main__':
    plugin.run()