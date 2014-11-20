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

	BASE_URL = 'http://www.masterani.me/api/animes'

	def getAnime(self, query = ""):
		try :
			return XML.ObjectFromURL(self.BASE_URL + query)
		except Exception:
			return None

class Video:

	def __init__(self, host_id, embed_id):
		self.host_id = host_id
		if self.host_id == 1:
			self.url = "http://mp4upload.com/embed-" + embed_id + ".html"
		elif self.host_id == 2:
			self.url = "http://arkvid.tv/player/?v=" + embed_id
		else:
			self.url = None

	def scrape(self, html, regex):
		found = regex.search(html)
		if found:
			return found.group(1)
		return None

	def get(self):
		Log.Info("[AnimeHD] - URL: " + self.url) 
		try:
			src = HTTP.Request(self.url).content
		except Exception:
			Log.Error("[AnimeHD][HTTP] - Could not crawl hosting website! " + self.host_id) 
			return None
		if src:
			if self.host_id == 1:
				vid = self.scrape(src, MP4UPLOAD[0])
				img = self.scrape(src, MP4UPLOAD[1])
			elif self.host_id == 2:
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

	def __init__(self, episode):
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
			thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
		)
	)
	return oc

def CreateLatestList(animes):
	oc = ObjectContainer(title1 = "Latest anime")
	for anime in animes.findall('latest'):
		episode_id = anime.find('episode_id').text
		name = anime.find('name').text
		name_episode = anime.find('episode').text
		cover = anime.find('cover').text
		new_title = name + " - ep. " + name_episode
		oc.add(DirectoryObject(
			key = Callback(WatchEpisode, episode = episode_id, title = new_title),
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
	episodes = Anime().getAnime("/" + anime + "/episodes")
	if episodes:
		oc = ObjectContainer(title1 = name + " - Episodes")
		for episode in episodes.findall('episode'):
			episode_id = episode.find('id').text
			episode = episode.find('name').text
			oc.add(DirectoryObject(
				key = Callback(WatchEpisode, episode = episode_id, title = name + " - ep. " + episode),
				title = episode,
				thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
			)
		)
		return oc
	else:
		Log.Error("Failed loading episodes for " + name)

@route(PREFIX + "/episode/mirrors", include_container=bool)
def CreateVideo(url, thumb, episode, resolution, host, include_container=False):
	rating_key = episode + "::" + host + "::" + resolution + "::animehd"
	video_object = VideoClipObject(
		key = Callback(CreateVideo, url=url, thumb=thumb, episode=episode, resolution=resolution, host=host, include_container=True),
		rating_key = rating_key,
		title = host + " - " + resolution + "p",
		thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-cover.png'),
		items = [
			MediaObject(
				parts = [PartObject(key=Callback(PlayVideo, url=url, unique=rating_key, episode=episode))],
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
					q_str = "TESTING"
					Log.Info("[AnimeHD][LastWatched] - " + q_str)
					del CURRENTLY_PLAYING[key]
			elif video.elapsed() >= 20000:
				Log.Debug("[AnimeHD][LastWatched] - Deleting video from CURRENTLY_PLAYING.")
				del CURRENTLY_PLAYING[key]
			Thread.Sleep(5)
	
@indirect
def PlayVideo(url, unique, episode):
	if Prefs["username"] and Prefs["password"]:
		if len(CURRENTLY_PLAYING) > 0:
			if unique in CURRENTLY_PLAYING:
				Log.Debug("[AnimeHD][LastWatched] - Already added video to CURRENTLY_PLAYING.")
			else:
				Log.Debug("[AnimeHD][LastWatched] - Adding video to CURRENTLY_PLAYING.")
				CURRENTLY_PLAYING[unique] = VideoSession(episode)
		else:
			CURRENTLY_PLAYING[unique] = VideoSession(episode)
			Thread.Create(add, globalize=True)
	return IndirectResponse(VideoClipObject, key=url)

@route(PREFIX + "/episode")
def WatchEpisode(episode, title):
	mirrors = Anime().getAnime("/episode/" + episode)
	if mirrors:
		oc = ObjectContainer(title1 = title)
		for mirror in mirrors.findall('mirror'):
			host = mirror.find('host_id').text
			host_id = int(host)
			if host == "1":
				host = "MP4Upload"
			elif host == "2":
				host = "Arkvid"
			if host_id != None and host_id <= 2:
				embed_id = mirror.find('embed_id').text
				quality = mirror.find('quality').text
				video = Video(host_id, embed_id)	
				url = video.get()
				if url:
					Log.Info("[AnimeHD][Success] - Loading: " + host + " - res.: " + quality)
					oc.add(CreateVideo(url[0], url[1], episode, quality, host))
				else:
					Log.Error("[AnimeHD][Failed] - Couldn't load video: " + host + ":" + quality)	
			else:
				Log.Info("[AnimeHD] - Host: " + host)
	else:
		Log.Error("Failed loading video(s) for ep. " + episode)
	return oc