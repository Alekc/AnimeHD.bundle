import time

PLEX_URL = "http://"+ Network.Address +":32400";
PREFIX = "/video/animehd"
NAME = "AnimeHD"
ART = "art-default.jpg"
ICON = "icon-default.png"
START_MENU = [["Latest anime", "latest"], ["Ongoing anime", "ongoing"], ["All anime", "all"]]
MP4UPLOAD = [
	Regex('url: \'(http\:\/\/.*?\/video\.mp4.*?)\''),
	Regex('\'image\': \'(http\://.*?\.jpg)\'')
]
ARKVID = [
	Regex('source src="(http:\/\/.*?)"'), 
	Regex('poster="(http:\/\/.*?)"')
]

CURRENTLY_PLAYING = {}

class Anime:

	BASE_URL = 'http://www.masterani.me/api/anime'

	def getAnime(self, query = ""):
		try :
			return XML.ObjectFromURL(self.BASE_URL + query)
		except Exception:
			return None

class Video:

	def __init__(self, url):
		self.url = url

	def scrape(self, html, regex):
		found = regex.search(html)
		if found:
			return found.group(1)
		return None

	def get(self, host):
		try:
			src = HTTP.Request(self.url).content
		except Exception:
			Log.Error("[AnimeHD][HTTP] - Could not crawl website") 
			return None
		if src and host:
			if host == "MP4Upload":
				vid = self.scrape(src, MP4UPLOAD[0])
				img = self.scrape(src, MP4UPLOAD[1])
			elif host == "Arkvid":
				vid = self.scrape(src, ARKVID[0])
				img = self.scrape(src, ARKVID[1])

			if vid: 
				return [vid, img]
		return None

class Masterani:

	BASE_URL = "http://www.masterani.me/api/anime/account"

	def auth(self, username, password):
		try:
			request = HTTP.Request(self.BASE_URL + "/validate", {'username': username, 'password': password})
		except:
			Log.Error("[AnimeHD][HTTP] - Could not validate user!") 
			return None
		return request.content

	def lastwatched(self, username, password, anime, episode):
		try:
			request = HTTP.Request(self.BASE_URL + "/lastwatched", {'username': username, 'password': password, 'id': anime, 'episode': episode})
		except:
			Log.Error("[AnimeHD][HTTP] - Could not add anime to lastwatched database!") 
			return None
		return request.content

class PMSSession:

	BASE_PATH = PLEX_URL + "/status/sessions";

	def getContainerSize(self, xml):
		return int(xml.xpath('//MediaContainer/@size')[0])

	def getContainer(self, xml, key):
		try:
			return xml.xpath("//Video[@ratingKey='" + key + "']")[0]
		except:
			return None

	def getElapsedVideo(self, xml, key):
		try:
			time_elapsed = xml.xpath("//Video[@ratingKey='" + key + "']/@viewOffset")
		except:
			return 0
		if len(time_elapsed) > 0:
			return int(time_elapsed[0])
		return 0

	def getSession(self):
		try:
			return XML.ObjectFromURL(self.BASE_PATH, cacheTime=4)
		except Exception:
			Log.Info("[AnimeHD][LastWatched] - Could not open sessions: Make sure you are LOGGED IN (Requires Plex pass)!")
		return None

class VideoSession:

	def __init__(self, anime, episode):
		self.anime = anime
		self.episode = episode
		self.total = self.getCurrentTime()

	def getCurrentTime(self):
		return int(round(time.time() * 1000))

	def elapsed(self):
		return int(self.total - self.getCurrentTime())

	
	
def Start():
	ObjectContainer.art = R(ART)
	HTTP.CacheTime = 180

def ValidatePrefs():
	if Prefs["username"] and Prefs["password"]:
		data = Masterani().auth(Prefs["username"], Prefs["password"])
		if data:
			Log.Info("[AnimeHD][Account] - " + data)
			if data != "User validated.":
				Log.Info("[AnimeHD][Account] - resetting prefs.")
				url = PLEX_URL + "/video/animehd/:/prefs/set?username=";
				HTTP.Request(url)
				
@handler(PREFIX, NAME, thumb=ICON)
def MainMenu():
	oc = ObjectContainer()
	for menu in START_MENU:
		oc.add(DirectoryObject(key = Callback(AnimeList, category = menu[1]), title = menu[0]))
	oc.add(InputDirectoryObject(key = Callback(SearchAnimeList), title = "Search AnimeHD", prompt = "Search for anime?"))
	return oc

def CreateAnimeList(animes, title = "All anime"):
	oc = ObjectContainer(title1 = title)
	for anime in animes.findall('anime'):
		name = anime.find('name').text
		anime_id = anime.find('id').text
		cover = anime.find('cover').text
		oc.add(DirectoryObject(
			key = Callback(EpisodeList, anime = anime_id, cover = cover, name = name),
			title = name,
			summary = "www.masterani.me",
			thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
		)
	)
	return oc

def CreateLatestList(animes):
	oc = ObjectContainer(title1 = "Latest anime")
	for anime in animes.findall('latest'):
		anime_id = anime.find('anime_id').text
		episode_id = anime.find('episode_id').text
		name = anime.find('name').text
		host = anime.find('host').text
		if host == "masterani":
			cover = "http://www.masterani.me/" + anime.find('thumbnail').text
		else:
			cover = anime.find('thumbnail').text
		new_title = name + " - ep. " + episode_id
		oc.add(DirectoryObject(
			key = Callback(WatchEpisode, anime = anime_id, episode = episode_id, title = new_title),
			title = new_title,
			thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
			)
		)
	return oc


@route(PREFIX + "/anime")
def AnimeList(category = None):
	Log.Info("[AnimeHD] - Category: " + category)
	if category == None:
		Log.Info("[AnimeHD] - No category has been set.")
	elif category == "all":
		animes = Anime().getAnime("/all")
		if animes:
			Log.Info("[AnimeHD] - Creating all anime list.")
			return CreateAnimeList(animes)
		else:
			Log.Error("Failed loading anime.")
	elif category == "ongoing":
		animes = Anime().getAnime("/ongoing")
		if animes:
			Log.Info("[AnimeHD] - Creating ongoing list.")
			return CreateAnimeList(animes, "Ongoing anime")
		else:
			Log.Error("Failed loading anime.")
	elif category == "latest":
		animes = Anime().getAnime("/latest")
		if animes:
			Log.Info("[AnimeHD] - Creating latest list.")
			return CreateLatestList(animes)
		else:
			Log.Error("Failed loading anime.")
	else:
		Log.Error("[AnimeHD] - No defined category.")

@route(PREFIX + "/anime/search")
def SearchAnimeList(query):
	if query:
		animes = Anime().getAnime("/search/" + query)
		if animes:
			return CreateAnimeList(animes, "Search results: " + query)
		else:
			return ObjectContainer(header="Search result", message="Nothing found! Try something less specific or request anime titles at www.masterani.me") 
	else:
		Log.Error("[AnimeHD] - Must set search query.")

@route(PREFIX + "/episodes")
def EpisodeList(anime , cover, name):
	episodes = Anime().getAnime("/" + anime)
	if episodes:
		oc = ObjectContainer(title1 = name + " - Episodes")
		for episode in episodes.findall('episode'):
			episode_id = episode.find('id').text
			oc.add(DirectoryObject(
				key = Callback(WatchEpisode, anime = anime, episode = episode_id, title = name + " - ep. " + episode_id),
				title = episode_id,
				thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
			)
		)
		return oc
	else:
		Log.Error("Failed loading episodes for " + name)

@route(PREFIX + "/episode/mirrors", include_container=bool)
def CreateVideo(url, thumb, anime, episode, resolution, host, include_container=False):
	rating_key = anime + "::" + episode + "::" + host + "::" + resolution + "::animehd"
	video_object = VideoClipObject(
		key = Callback(CreateVideo, url=url, thumb=thumb, anime=anime, episode=episode, resolution=resolution, host=host, include_container=True),
		rating_key = rating_key,
		title = host + " - " + resolution + "p",
		thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-cover.png'),
		items = [
			MediaObject(
				parts = [PartObject(key=Callback(PlayVideo, url=url, unique=rating_key, anime=anime, episode=episode))],
				optimized_for_streaming = True,
				container = Container.MP4,
				audio_channels = 2,
				audio_codec = AudioCodec.AAC,
				video_resolution = resolution
				)
			]
		)
	if include_container:
		return ObjectContainer(objects=[video_object])
	else:
		return video_object

def add():
	session = PMSSession()
	while len(CURRENTLY_PLAYING) > 0:
		for key, video in CURRENTLY_PLAYING.items():
			xml = session.getSession()
			container = session.getContainer(xml, key)
			if container != None:
				video_time = session.getElapsedVideo(xml, key)
				Log.Debug("[AnimeHD][LastWatched] - Time elapsed: " + str(video_time))
				if video_time > 60000:
					q_str = Masterani().lastwatched(Prefs["username"], Prefs["password"], video.anime, video.episode)
					Log.Info("[AnimeHD][LastWatched] - " + q_str)
					del CURRENTLY_PLAYING[key]
			elif video.elapsed() >= 20000:
				Log.Debug("[AnimeHD][LastWatched] - Deleting video from CURRENTLY_PLAYING.")
				del CURRENTLY_PLAYING[key]
			Thread.Sleep(5)
	
@indirect
def PlayVideo(url, unique, anime, episode):
	if Prefs["username"] and Prefs["password"]:
		if len(CURRENTLY_PLAYING) > 0:
			if unique in CURRENTLY_PLAYING:
				Log.Debug("[AnimeHD][LastWatched] - Already added video to CURRENTLY_PLAYING.")
			else:
				Log.Debug("[AnimeHD][LastWatched] - Adding video to CURRENTLY_PLAYING.")
				CURRENTLY_PLAYING[unique] = VideoSession(anime, episode)
		else:
			CURRENTLY_PLAYING[unique] = VideoSession(anime, episode)
			Thread.Create(add, globalize=True)
	return IndirectResponse(VideoClipObject, key=url)

@route(PREFIX + "/episode")
def WatchEpisode(anime, episode, title):
	mirrors = Anime().getAnime("/" + anime + "/" + episode)
	if mirrors:
		oc = ObjectContainer(title1 = title)
		for mirror in mirrors.findall('mirror'):
			host = mirror.find('host').text
			video = Video(mirror.find('url').text)	
			url = video.get(host)
			quality = mirror.find('quality').text
			if url:
				Log.Info("[AnimeHD][Success] - Loading: " + host + " - res.: " + quality)
				oc.add(CreateVideo(url[0], url[1], anime, episode, quality, host))
			else:
				Log.Error("[AnimeHD][Failed] - Couldn't load video: " + host + ":" + quality)	
	else:
		Log.Error("Failed loading video(s) for " + name + " ep. " + episode)
	return oc