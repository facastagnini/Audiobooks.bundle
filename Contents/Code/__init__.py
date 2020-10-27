# Audiobooks (Audible)
# coding: utf-8
import re, types, traceback
import urllib
import Queue
import json

#from mutagen import File
#from mutagen.mp4 import MP4
#from mutagen.id3 import ID3
#from mutagen.flac import FLAC
#from mutagen.flac import Picture
#from mutagen.oggvorbis import OggVorbis

def json_decode(output):
  try:
    return json.loads(output,encoding="utf-8")
  except:
    return None


# URLs
VERSION_NO = '1.2020.04.15.1'

REQUEST_DELAY = 10       # Delay used when requesting HTML, may be good to have to prevent being banned from the site

INITIAL_SCORE = 100     # Starting value for score before deductions are taken.
GOOD_SCORE = 98         # Score required to short-circuit matching and stop searching.
IGNORE_SCORE = 45       # Any score lower than this will be ignored.

THREAD_MAX = 20

intl_sites={
    'en' : { 'url': 'www.audible.com'  , 'urltitle' : u'title='   , 'rel_date' : u'Release date'         , 'nar_by' : u'Narrated By'   , 'nar_by2': u'Narrated by'},
    'fr' : { 'url': 'www.audible.fr'   , 'urltitle' : u'title='   , 'rel_date' : u'Date de publication'  , 'nar_by' : u'Narrateur(s)'  , 'nar_by2': u'Lu par'},
    'de' : { 'url': 'www.audible.de'   , 'urltitle' : u'title='   , 'rel_date' : u'Erscheinungsdatum'    , 'nar_by' : u'Gesprochen von', 'rel_date2': u'Veröffentlicht'},
    'it' : { 'url': 'www.audible.it'   , 'urltitle' : u'title='   , 'rel_date' : u'Data di Pubblicazione', 'nar_by' : u'Narratore'     },
    }

sites_langs={
    'www.audible.com' : { 'lang' : 'en'     , 'url': 'www.audible.com'  },
    'www.audible.ca' : { 'lang' : 'en'      , 'url': 'www.audible.ca'   },
    'www.audible.co.uk' : { 'lang' : 'en'   , 'url': 'www.audible.co.uk'},
    'www.audible.com.au' : { 'lang' : 'en'  , 'url': 'www.audible.com.au'},
    'www.audible.fr' : { 'lang' : 'fr'      , 'url': 'www.audible.fr'   },
    'www.audible.de' : { 'lang' : 'de'      , 'url': 'www.audible.de'   },
    'www.audible.it' : { 'lang' : 'it'      , 'url': 'www.audible.it'   },
    }

def SetupUrls(sitetype, base, lang='en'):
    Log('Library/Search language is : %s', lang)
    ctx=dict()
    if sitetype:
      Log('Manual Site Selection Enabled : %s', base)
      Log('Language being ignored due to manual site selection')
      if base in sites_langs :
        Log('Pulling language from sites array')
        lang=sites_langs[base]['lang']
        if lang in intl_sites :
          base=sites_langs[base]['url']
          urlsearchtitle=intl_sites[lang]['urltitle']
          ctx['REL_DATE']=intl_sites[lang]['rel_date']
          ctx['NAR_BY'  ]=intl_sites[lang]['nar_by']
          if 'rel_date2' in intl_sites[lang]:
              ctx['REL_DATE_INFO']=intl_sites[lang]['rel_date2']
          else:
              ctx['REL_DATE_INFO']=ctx['REL_DATE']
          if 'nar_by2' in intl_sites[lang]:
              ctx['NAR_BY_INFO' ]=intl_sites[lang]['nar_by2']
          else:
              ctx['NAR_BY_INFO' ]=ctx['NAR_BY'  ]
        else:
          ctx['REL_DATE'     ]='Release date'
          ctx['REL_DATE_INFO']=ctx['REL_DATE']
          ctx['NAR_BY'       ]='Narrated By'
          ctx['NAR_BY_INFO'  ]='Narrated by'		        
      Log('Sites language is : %s', lang)
      Log('/******************************LANG DEBUGGING************************************/')
      Log('/* REL_DATE = %s', ctx['REL_DATE'])
      Log('/* REL_DATE_INFO = %s', ctx['REL_DATE_INFO'])
      Log('/* NAR_BY = %s', ctx['NAR_BY'])
      Log('/* NAR_BY_INFO = %s', ctx['NAR_BY_INFO'])
      Log('/********************************************************************************/')
    else:
      Log('Audible site will be chosen by library language')
      Log('Library Language is %s', lang)
      if base is None:
          base='www.audible.com'
      if lang in intl_sites :
        base=intl_sites[lang]['url']
        urlsearchtitle=intl_sites[lang]['urltitle']
        ctx['REL_DATE']=intl_sites[lang]['rel_date']
        ctx['NAR_BY'  ]=intl_sites[lang]['nar_by']
        if 'rel_date2' in intl_sites[lang]:
            ctx['REL_DATE_INFO']=intl_sites[lang]['rel_date2']
        else:
            ctx['REL_DATE_INFO']=ctx['REL_DATE']
        if 'nar_by2' in intl_sites[lang]:
            ctx['NAR_BY_INFO' ]=intl_sites[lang]['nar_by2']
        else:
            ctx['NAR_BY_INFO' ]=ctx['NAR_BY'  ]
      else:
        ctx['REL_DATE'     ]='Release date'
        ctx['REL_DATE_INFO']=ctx['REL_DATE']
        ctx['NAR_BY'       ]='Narrated By'
        ctx['NAR_BY_INFO'  ]='Narrated by'


    AUD_BASE_URL='https://' + str(base) + '/'
    AUD_TITLE_URL=urlsearchtitle
    ctx['AUD_BOOK_INFO'         ]=AUD_BASE_URL + 'pd/%s?ipRedirectOverride=true'
    ctx['AUD_ARTIST_SEARCH_URL' ]=AUD_BASE_URL + 'search?searchAuthor=%s&ipRedirectOverride=true'
    ctx['AUD_ALBUM_SEARCH_URL'  ]=AUD_BASE_URL + 'search?' + AUD_TITLE_URL + '%s&x=41&ipRedirectOverride=true'
    ctx['AUD_KEYWORD_SEARCH_URL']=AUD_BASE_URL + 'search?filterby=field-keywords&advsearchKeywords=%s&x=41&ipRedirectOverride=true'
    ctx['AUD_SEARCH_URL'        ]=AUD_BASE_URL + 'search?' + AUD_TITLE_URL + '{0}&searchAuthor={1}&x=41&ipRedirectOverride=true'
    return ctx


def Start():
    #HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'
    HTTP.Headers['Accept-Encoding'] = 'gzip'

class AudiobookArtist(Agent.Artist):
    name = 'Audiobooks'
    languages = [Locale.Language.English, 'de', 'fr', 'it']
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0
	

    def Log(self, message, *args):
        if Prefs['debug']:
            Log(message, *args)

    def getDateFromString(self, string):
        try:
            return Datetime.ParseDate(string).date()
        except:
            return None

    def getStringContentFromXPath(self, source, query):
        return source.xpath('string(' + query + ')')

    def getAnchorUrlFromXPath(self, source, query):
        anchor = source.xpath(query)

        if len(anchor) == 0:
            return None

        return anchor[0].get('href')

    def getImageUrlFromXPath(self, source, query):
        img = source.xpath(query)

        if len(img) == 0:
            return None

        return img[0].get('src')

    def doSearch(self, url, ctx):
	
	  
		
        html = HTML.ElementFromURL(url, sleep=REQUEST_DELAY)

        found = []
		
        for r in html.xpath('//div[a/img[@class="yborder"]]'):
            date = self.getDateFromString(self.getStringContentFromXPath(r, 'text()[1]'))
            title = self.getStringContentFromXPath(r, 'a[2]')
            murl = self.getAnchorUrlFromXPath(r, 'a[2]')
            thumb = self.getImageUrlFromXPath(r, 'a/img')

            found.append({'url': murl, 'title': title, 'date': date, 'thumb': thumb})

        return found

    def search(self, results, media, lang, manual=False):
	
	    # Author data is pulling from last.fm automatically.
		# This will probably never be built out unless a good
		# author source is identified.
	
	
	    #Log some stuff
        self.Log('---------------------------------ARTIST SEARCH--------------------------------------------------')
        self.Log('* Album:           %s', media.album)
        self.Log('* Artist:           %s', media.artist)
        self.Log('****************************************Not Ready For Artist Search Yet*************************')
        self.Log('------------------------------------------------------------------------------------------------')
        
        '''
        We can get the id from the search results with the right xpath
        <a class="bc-link bc-color-link" tabindex="0" href="/author/Cixin-Liu/B007JP96JU?ref=a_search_c3_lAuthor_1_1_1&amp;pf_rd_p=e81b7c27-6880-467a-b5a7-13cef5d729fe&amp;pf_rd_r=0A2J9TTD5NYVNKMKG12Y">Cixin Liu</a>
        
        Then we can use the id to visit the author's bio page

        author_page = 'http://www.audible.com/author/B007JP96JU'

        search_results = 'http://www.audible.com/search?keywords=cixin+liu?ipRedirectOverride=true'

        html = HTML.ElementFromURL(search_results, sleep=REQUEST_DELAY)
        for r in html.xpath('/html/body/div[1]/div[5]/div[3]/div/div[2]/div[4]/div/span/ul/div/li[1]/div/div[1]/div'):
            id = self.getStringContentFromXPath(r, '/html/body/div[1]/div[5]/div[3]/div/div[2]/div[4]/div/span/ul/div/li[1]/div/div[1]/div/div[2]/div/div/span/ul/li[2]/span/a[1]')        
            self.Log('***************ID: %s, ', id)
        return
        '''

        author_bio = 'http://www.audible.com/author/B007JP96JU'
        html = HTML.ElementFromURL(author_bio, sleep=REQUEST_DELAY)
        self.Log('-----------------------------ABOUT TO TRY XPATH--------------------------')
        for r in html.xpath('//*[@id="center-1"]'):            
            self.Log('---------------------------------------XPATH SEARCH HIT-----------------------------------------------')
            # try to get the author bio and pic
            thumb = self.getImageUrlFromXPath(r, '/html/body/div[1]/div[8]/div[2]/div[2]/div/div/div/div/div/div[1]/img')
            artist_Bio = self.getStringContentFromXPath(r, '/html/body/div[1]/div[8]/div[2]/div[2]/div/div/div/div/div/div[6]/div/div/p[1]')
            
            # display the results
            self.Log('***************BIO: %s, ', artist_Bio)
            self.Log('***************THUMB: %s, ', thumb)
        return
	
		
    def update(self, metadata, media, lang, force=False):
        return

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try: func(*args, **kargs)
                except Exception, e: self.Log(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))


class AudiobookAlbum(Agent.Album):
    name = 'Audiobooks'
    languages = [Locale.Language.English, 'de', 'fr', 'it']
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0
    
    def Log(self, message, *args):
        if Prefs['debug']:
            Log(message, *args)

    def getDateFromString(self, string):
        try:
            return Datetime.ParseDate(string).date()
        except:
            return None

    def getStringContentFromXPath(self, source, query):
        return source.xpath('string(' + query + ')')

    def getAnchorUrlFromXPath(self, source, query):
        anchor = source.xpath(query)

        if len(anchor) == 0:
            return None

        return anchor[0].get('href')

    def getImageUrlFromXPath(self, source, query):
        img = source.xpath(query)

        if len(img) == 0:
            return None

        return img[0].get('src')

    def doSearch(self, url, ctx):
        """This method implements the web scraping xpath rules for the search page"""
        html = HTML.ElementFromURL(url, sleep=REQUEST_DELAY)
        found = []
        subtitle = ''
        self.Log('-----------------------------ABOUT TO TRY XPATH--------------------------')
        for r in html.xpath('//ul//li[contains(@class,"productListItem")]'):
            self.Log('---------------------------------------XPATH SEARCH HIT-----------------------------------------------')
            datetext = self.getStringContentFromXPath(r, 'div/div/div/div/div/div/span/ul/li[contains (@class,"releaseDateLabel")]/span'.decode('utf-8'))
            datetext=re.sub(r'[^0-9\-]', '',datetext)
            date=self.getDateFromString(datetext)
            title = self.getStringContentFromXPath(r, 'div/div/div/div/div/div/span/ul//a[contains (@class,"bc-link")][1]')
            subtitle = self.getStringContentFromXPath(r, 'div/div/div/div/div/div/span/ul/li[contains (@class,"subtitle")]/span')
            murl = self.getAnchorUrlFromXPath(r, 'div/div/div/div/div/div/span/ul/li/h3//a[1]')
            thumb = self.getImageUrlFromXPath(r, 'div/div/div/div/div/div/div[contains(@class,"responsive-product-square")]/div/a/img')
            author = self.getStringContentFromXPath(r, 'div/div/div/div/div/div/span/ul/li[contains (@class,"authorLabel")]/span/a[1]')
            narrator = self.getStringContentFromXPath(r, 'div/div/div/div/div/div/span/ul/li[contains (@class,"narratorLabel")]/span//a[1]'.format(ctx['NAR_BY']).decode('utf-8'))
            series = self.getStringContentFromXPath(r, 'div/div/div/div/div/div/span/ul/li[contains (@class,"seriesLabel")]/span/a[1]')


            # store the results
            found.append({'url': murl, 'title': title, 'subtitle': subtitle, 'date': date, 'thumb': thumb, 'author': author, 'narrator': narrator, 'series': series})

        return found

    def search(self, results, media, lang, manual):
        ctx=SetupUrls(Prefs['sitetype'], Prefs['site'], lang)
        LCL_IGNORE_SCORE=IGNORE_SCORE
        
        # Handle a couple of edge cases where album search will give bad results.
        if media.album is None and not manual:
          self.Log('Album Title is NULL on an automatic search.  Returning')
          return	  
        if media.album == '[Unknown Album]' and not manual:
          self.Log('Album Title is [Unknown Album] on an automatic search.  Returning')
          return	

        # Handle a case in newer Plex versions where media.name is sometimes None
        if media.name is None:
          media.name = media.title
	    
        if manual:
          Log('You clicked \'fix match\'. This may have returned no useful results because it\'s searching using the title of the first track.')
          Log('There\'s not currently a way around this initial failure. But clicking \'Search Options\' and entering the title works just fine.')
          Log('This message will appear during the initial search and the actual manual search.')
          # If this is a custom search, use the user-entered name instead of the scanner hint.
          Log('Custom album search for: ' + media.name)
          #media.title = media.name
          media.album = media.name
        else:
          Log('Album search: ' + media.title)

		# Log some stuff for troubleshooting detail
        self.Log('-----------------------------------------------------------------------')
        self.Log('* ID:              %s', media.parent_metadata.id)
        self.Log('* Title:           %s', media.title)
        self.Log('* Name:            %s', media.name)
        self.Log('* Artist:          %s', media.artist)
        self.Log('-----------------------------------------------------------------------')
        
        # Normalize the name
        normalizedName = String.StripDiacritics(media.album)
        if len(normalizedName) == 0:
            normalizedName = media.album
        Log('normalizedName = %s', normalizedName)

		# Chop off "unabridged"
        normalizedName = re.sub(r"[\(\[].*?[\)\]]", "", normalizedName)
        Log('chopping bracketed text = %s', normalizedName)
        normalizedName = normalizedName.strip()
        Log('normalizedName stripped = %s', normalizedName)

        self.Log('***** SEARCHING FOR "%s" - AUDIBLE v.%s *****', normalizedName, VERSION_NO)

        # Make the URL
        match = re.search("(?P<book_title>.*?)\[(?P<source>(audible))-(?P<guid>B[a-zA-Z0-9]{9,9})\]", media.title, re.IGNORECASE)
        if match:  ###metadata id provided
          Log('Looks like you went through the trouble of adding the audible ID to the Book title...')
          searchUrl = ctx['AUD_KEYWORD_SEARCH_URL'] % (String.Quote((match.group('guid')).encode('utf-8'), usePlus=True))
          LCL_IGNORE_SCORE=0
        elif media.artist is not None:
          searchUrl = ctx['AUD_SEARCH_URL'].format((String.Quote((normalizedName).encode('utf-8'), usePlus=True)), (String.Quote((media.artist).encode('utf-8'), usePlus=True)))
        else:
          searchUrl = ctx['AUD_ALBUM_SEARCH_URL'] % (String.Quote((normalizedName).encode('utf-8'), usePlus=True))
        found = self.doSearch(searchUrl, ctx)

        # Write search result status to log
        if len(found) == 0:
            self.Log('No results found for query "%s"', normalizedName)
            return
        else:
            self.Log('Found %s result(s) for query "%s"', len(found), normalizedName)
            i = 1
            for f in found:
                self.Log('    %s. (title) %s (author) %s (url)[%s] (date)(%s) (thumb){%s}', i, f['title'], f['author'], f['url'], str(f['date']), f['thumb'])
                i += 1

        self.Log('-----------------------------------------------------------------------')
        # Walk the found items and gather extended information
        info = []
        i = 1
        for f in found:
            url = f['url']
            self.Log('URL For Breakdown: %s', url)

            # Get the id
            for itemId in url.split('/') :
                if re.match(r'^[0-9A-Z]{10,10}', itemId):  # IDs No longer start with just 'B0'
                    break
                itemId=None

		    #New Search results contain question marks after the ID
            for itemId in itemId.split('?') :
                if re.match(r'^[0-9A-Z]{10,10}', itemId):  # IDs No longer start with just 'B0'
                    break

            if len(itemId) == 0:
                Log('No Match: %s', url)
                continue

            self.Log('* ID is                 %s', itemId)

            title    = f['title']
            subtitle = f['subtitle']
            thumb    = f['thumb']
            date     = f['date']
            year     = ''
            author   = f['author']
            series   = f['series']
            narrator = f['narrator']

            if date is not None:
                year = date.year

            # Score the album name
            scorebase1 = media.album
            scorebase2 = title.encode('utf-8')
            #self.Log('scorebase1:    %s', scorebase1)
            #self.Log('scorebase2:    %s', scorebase2)

            score = INITIAL_SCORE - Util.LevenshteinDistance(scorebase1, scorebase2)

            if media.artist:
              scorebase3 = media.artist
              scorebase4 = author
              #self.Log('scorebase3:    %s', scorebase3)
              #self.Log('scorebase4:    %s', scorebase4)
              score = INITIAL_SCORE - Util.LevenshteinDistance(scorebase3, scorebase4)


            self.Log('* Title is              %s', title)
            self.Log('* Author is             %s', author)
            self.Log('* Narrator is           %s', narrator)
            self.Log('* Series is             %s', series)
            self.Log('* Date is               %s', str(date))
            self.Log('* Score is              %s', str(score))
            self.Log('* Thumb is              %s', thumb)

            if score >= LCL_IGNORE_SCORE:
                info.append({'id': itemId, 'title': title, 'year': year, 'date': date, 'score': score, 'thumb': thumb, 'artist' : author})
            else:
                self.Log('# Score is below ignore boundary (%s)... Skipping!', LCL_IGNORE_SCORE)

            if i != len(found):
                self.Log('-----------------------------------------------------------------------')

            i += 1

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)

        # Output the final results.
        self.Log('***********************************************************************')
        self.Log('Final result:')
        i = 1
        for r in info:
            self.Log('    [%s]    %s. %s (%s) %s {%s} [%s]', r['score'], i, r['title'], r['year'], r['artist'], r['id'], r['thumb'])
            results.Append(MetadataSearchResult(id = r['id'], name  = r['title'], year = r['year'], score = r['score'], thumb = r['thumb'], lang = lang))

            # If there are more than one result, and this one has a score that is >= GOOD SCORE, then ignore the rest of the results
            if not manual and len(info) > 1 and r['score'] >= GOOD_SCORE:
                self.Log('            *** The score for these results are great, so we will use them, and ignore the rest. ***')
                break
            i += 1

    def update(self, metadata, media, lang, force=False):
        self.Log('***** UPDATING "%s" ID: %s - AUDIBLE v.%s *****', media.title, metadata.id, VERSION_NO)
        ctx=SetupUrls(Prefs['sitetype'], Prefs['site'], lang)
		  
        # Make url
        url = ctx['AUD_BOOK_INFO'] % metadata.id

        try:
            html = HTML.ElementFromURL(url, sleep=REQUEST_DELAY)
        except NetworkError:
            pass
        
        date=None
        rating=None
        series=''
        genre1=None
        genre2=None
        subtitle = ''


        # there is a json at the bottom of the page with a lot of the information we want
        for r in html.xpath('//script[contains (@type, "application/ld+json")]'):
            page_content = r.text_content()
            page_content = page_content.replace('\n', '')
            #page_content = page_content.replace('\'', '\\\'')
            #page_content = re.sub(r'\\(?![bfnrtv\'\"\\])', '', page_content)  
			# Remove any backslashes that aren't escaping a character JSON needs escaped
            remove_inv_json_esc=re.compile(r'([^\\])(\\(?![bfnrt\'\"\\/]|u[A-Fa-f0-9]{4}))')
            page_content=remove_inv_json_esc.sub(r'\1\\\2', page_content)
            self.Log(page_content)
            json_data=json_decode(page_content)
            for json_data in json_data:
                if 'datePublished' in json_data:
                    #for key in json_data:
                    #    Log('{0}:{1}'.format(key, json_data[key]))
                    date=self.getDateFromString(json_data['datePublished'])
                    title=json_data['name']
                    thumb=json_data['image']
                    rating=json_data['aggregateRating']['ratingValue']
                    author=''
                    counter=0
                    for c in json_data['author'] :
                        counter+=1
                        if counter > 1 :  
                            author+=', '
                        author+=c['name']
                    narrator=''
                    counter=0
                    for c in json_data['readBy'] :
                        counter+=1
                        if counter > 1 :  
                            narrator+=','
                        narrator+=c['name']
                    studio=json_data['publisher']
                    synopsis=json_data['description']
                if 'itemListElement' in json_data:
                    # debug
                    # for key in json_data:
                    #     Log('{0}:{1}'.format(key, json_data[key]))
                    # [0] is a tag called 'home', we skip it
                    genre1=json_data['itemListElement'][1]['item']['name']
                    try:
                        genre2=json_data['itemListElement'][2]['item']['name']
                    except:
                        continue


        # the series are not included in the mentioned json
        # we need to get it from the html
        for r in html.xpath('//*[contains (@class, "seriesLabel")]'):
            series = self.getStringContentFromXPath(r, 'a[1]')
            self.Log('seriesLabel matched: %s', series)


        # the subtitle is not present in the mentioned json
        # we need to scrape it from the html
        for r in html.xpath('//*[contains (@class, "subtitle")]'):
            # li[contains (@class,"subtitle")]/span
            # #center-1 > div > div > div > div.bc-col-responsive.bc-col-5 > span > ul > li.bc-list-item.subtitle.bc-spacing-s2.bc-size-medium
            # subtitle = self.getStringContentFromXPath(r, '')
            subtitle = r
            self.Log('subtitle matched: %s', subtitle)
        
		
        #cleanup synopsis
        synopsis = synopsis.replace("<i>", "")
        synopsis = synopsis.replace("</i>", "")
        synopsis = synopsis.replace("<em>", "")
        synopsis = synopsis.replace("</em>", "")
        synopsis = synopsis.replace("<u>", "")
        synopsis = synopsis.replace("</u>", "")
        synopsis = synopsis.replace("<b>", "")
        synopsis = synopsis.replace("</b>", "")
        synopsis = synopsis.replace("<strong>", "")
        synopsis = synopsis.replace("</strong>", "")
        synopsis = synopsis.replace("<ul>", "")
        synopsis = synopsis.replace("</ul>", "\n")
        synopsis = synopsis.replace("<ol>", "")
        synopsis = synopsis.replace("</ol>", "\n")
        synopsis = synopsis.replace("<li>", " • ")
        synopsis = synopsis.replace("</li>", "\n")
        synopsis = synopsis.replace("<br />", "")
        synopsis = synopsis.replace("<p>", "")
        synopsis = synopsis.replace("</p>", "\n")
		
		
        self.Log('date:        %s', date)
        self.Log('title:       %s', title)
        self.Log('subtitle:    %s', subtitle)
        self.Log('author:      %s', author)
        self.Log('series:      %s', series)
        self.Log('narrator:    %s', narrator)
        self.Log('studio:      %s', studio)
        self.Log('thumb:       %s', thumb)
        self.Log('rating:      %s', rating)
        self.Log('genres:      %s, %s', genre1, genre2)
        self.Log('synopsis:    %s', synopsis)
		
		# Set the date and year if found.
        if date is not None:
          metadata.originally_available_at = date

		# Add the genres
        metadata.genres.clear()
        metadata.genres.add(series)
        narrators_list = narrator.split(",")
        for narrators in narrators_list:
            metadata.genres.add(narrators)
        metadata.genres.add(genre1)
        metadata.genres.add(genre2)
		
		# other metadata
        metadata.title = title
        metadata.title_sort = subtitle + ' - ' + title if (subtitle != '' ) else title
        metadata.studio = studio
        metadata.summary = synopsis
        metadata.posters[1] = Proxy.Media(HTTP.Request(thumb))
        metadata.posters.validate_keys(thumb)
        metadata.rating = float(rating) * 2

        # Add the collection tag
        metadata.collections.clear()
        series_list = series.split(",")
        for sl in series_list:
            metadata.collections.add(sl)

        media.artist = author
		
        self.writeInfo('New data', url, metadata)

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try: func(*args, **kargs)
                except Exception, e: self.Log(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))

   
    

    ### Writes metadata information to log.
    def writeInfo(self, header, url, metadata):
        self.Log(header)
        self.Log('-----------------------------------------------------------------------')
        self.Log('* ID:              %s', metadata.id)
        self.Log('* URL:             %s', url)
        self.Log('* Title:           %s', metadata.title)
        self.Log('* Release date:    %s', str(metadata.originally_available_at))
        self.Log('* Studio:          %s', metadata.studio)
        self.Log('* Summary:         %s', metadata.summary)

        if len(metadata.collections) > 0:
            self.Log('|\\')
            for i in range(len(metadata.collections)):
                self.Log('| * Collection:    %s', metadata.collections[i])

        if len(metadata.genres) > 0:
            self.Log('|\\')
            for i in range(len(metadata.genres)):
                self.Log('| * Genre:         %s', metadata.genres[i])

        if len(metadata.posters) > 0:
            self.Log('|\\')
            for poster in metadata.posters.keys():
                self.Log('| * Poster URL:    %s', poster)

        if len(metadata.art) > 0:
            self.Log('|\\')
            for art in metadata.art.keys():
                self.Log('| * Fan art URL:   %s', art)

        self.Log('***********************************************************************')

def safe_unicode(s, encoding='utf-8'):
    if s is None:
        return None
    if isinstance(s, basestring):
        if isinstance(s, types.UnicodeType):
            return s
        else:
            return s.decode(encoding)
    else:
        return str(s).decode(encoding)
