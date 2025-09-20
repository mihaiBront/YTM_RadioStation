from dataclasses import dataclass, field
import yt_dlp
import concurrent.futures
import os
import logging
import json
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Query:
    id: int
    name: str
    artist: str
    out_path: str = ""
    info: dict = field(default_factory=dict)

@dataclass
class YT_DLP_wrapper:
    out_path: str = "temp/"
    ydl_opts: dict = field(default_factory=lambda: {
        "format": "bestaudio/best",
        "noplaylist": True,
        "default_search": "ytsearch1",
        "outtmpl": f"downloads/%(title)s.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    })
    
    def __post_init__(self):
        self.ydl_opts["outtmpl"] = f"{self.out_path}%(title)s.%(ext)s"
        
    def download_single_query(self,query: Query):
            logger.debug(f"Downloading {query.name} {query.artist} audio")
            search_term = f"{query.name} {query.artist} audio"
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(search_term, download=True)
                    logger.info(f"Downloaded {query.name} {query.artist} audio")
                    info = info["entries"][0]
                    query.out_path = os.path.join(self.out_path, info["requested_downloads"][0]["filename"])
                    query.info = info
                    logger.info(f"Saved {query.name} {query.artist} audio")
                    return query
                except Exception as e:
                    logger.error(f"Error downloading {search_term}: {str(e)}")
                    return None
        
    def download_queries(self, list_of_queries: list[Query], max_workers: int = None):
        # Create output directory if it doesn't exist
        os.makedirs(self.out_path, exist_ok=True)

        if max_workers is None:
            max_workers = min(len(list_of_queries), os.cpu_count() or 1)

        # Use ThreadPoolExecutor for parallel downloads
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as process_pool:
            
            # Submit all audio processing tasks
            futures = {
                i: process_pool.submit(self.download_single_query, query)
                for i, query in enumerate(list_of_queries)
            }
            
            # Collect results as they complete
            results = []
            for future in concurrent.futures.as_completed(futures.values()):
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing query: {e}")
                
            return results
            
if __name__ == "__main__":
    time_start = time.time()
    yt_dlp_wrapper = YT_DLP_wrapper()
    downloaded_queries = yt_dlp_wrapper.download_queries([
            Query(id=1, name="Daft Punk Get Lucky", artist="Daft Punk"), 
            Query(id=2, name="Baby Come Back", artist="Player"),
            Query(id=3, name="Don't Stop Believin'", artist="Journey"), 
            Query(id=4, name="Billie Jean", artist="Michael Jackson"),
            Query(id=5, name="Bohemian Rhapsody", artist="Queen"),
            Query(id=6, name="Hotel California", artist="Eagles"),
            Query(id=7, name="I Want to Hold Your Hand", artist="The Beatles"),
            Query(id=8, name="Hey Jude", artist="The Beatles"),
            Query(id=9, name="Purple Rain", artist="Prince"),
            Query(id=10, name="Sweet Child o' Mine", artist="Guns N' Roses"),
            Query(id=11, name="Stairway to Heaven", artist="Led Zeppelin"),
            Query(id=12, name="Like a Rolling Stone", artist="Bob Dylan"),
            Query(id=13, name="Smells Like Teen Spirit", artist="Nirvana"),
            Query(id=14, name="Yesterday", artist="The Beatles"),
            Query(id=15, name="Respect", artist="Aretha Franklin"),
            Query(id=16, name="Born to Run", artist="Bruce Springsteen"),
            Query(id=17, name="Johnny B. Goode", artist="Chuck Berry"),
            Query(id=18, name="Good Vibrations", artist="The Beach Boys"),
            Query(id=19, name="Light My Fire", artist="The Doors"),
            Query(id=20, name="What's Going On", artist="Marvin Gaye"),
            Query(id=21, name="Like a Prayer", artist="Madonna"),
            Query(id=22, name="Sweet Dreams (Are Made of This)", artist="Eurythmics"),
            Query(id=23, name="I Will Always Love You", artist="Whitney Houston"),
            Query(id=24, name="Imagine", artist="John Lennon"),
            Query(id=25, name="Dancing Queen", artist="ABBA"),
            Query(id=26, name="Bridge Over Troubled Water", artist="Simon & Garfunkel"),
            Query(id=27, name="I Want It That Way", artist="Backstreet Boys"),
            Query(id=28, name="Sweet Home Alabama", artist="Lynyrd Skynyrd"),
            Query(id=29, name="Every Breath You Take", artist="The Police"),
            Query(id=30, name="Beat It", artist="Michael Jackson"),
            Query(id=31, name="Sweet Caroline", artist="Neil Diamond"),
            Query(id=32, name="American Woman", artist="The Guess Who"),
            Query(id=33, name="Dream On", artist="Aerosmith"),
            Query(id=34, name="Piano Man", artist="Billy Joel"),
            Query(id=35, name="Stayin' Alive", artist="Bee Gees"),
            Query(id=36, name="Wonderwall", artist="Oasis"),
            Query(id=37, name="Sweet Dreams", artist="Beyoncé"),
            Query(id=38, name="Livin' on a Prayer", artist="Bon Jovi"),
            Query(id=39, name="Sweet Emotion", artist="Aerosmith"),
            Query(id=40, name="California Dreamin'", artist="The Mamas & The Papas"),
            Query(id=41, name="Sweet Home Chicago", artist="Blues Brothers"),
            Query(id=42, name="Roxanne", artist="The Police"), 
            Query(id=43, name="Sweet Dreams (Are Made of This)", artist="Marilyn Manson"),
            Query(id=44, name="Brown Eyed Girl", artist="Van Morrison"),
            Query(id=45, name="Sweet Surrender", artist="Sarah McLachlan"),
            Query(id=46, name="All Along the Watchtower", artist="Jimi Hendrix"),
            Query(id=47, name="Sweet Thing", artist="Van Morrison"),
            Query(id=48, name="Paint It Black", artist="The Rolling Stones"),
            Query(id=49, name="Sweet Jane", artist="Lou Reed"),
            Query(id=50, name="Layla", artist="Eric Clapton"),
            Query(id=51, name="Sweet Disposition", artist="The Temper Trap"),
            Query(id=52, name="Satisfaction", artist="The Rolling Stones"),
            Query(id=53, name="Sweet Love", artist="Anita Baker"),
            Query(id=54, name="Hallelujah", artist="Jeff Buckley"),
            Query(id=55, name="Sweet Dreams Baby", artist="Roy Orbison"),
            Query(id=56, name="London Calling", artist="The Clash"),
            Query(id=57, name="Sweet City Woman", artist="The Stampeders"),
            Query(id=58, name="Purple Haze", artist="Jimi Hendrix"),
            Query(id=59, name="Sweet Baby James", artist="James Taylor"),
            Query(id=60, name="American Girl", artist="Tom Petty"),
            Query(id=61, name="Sweet Sixteen", artist="B.B. King"),
            Query(id=62, name="Born to Be Wild", artist="Steppenwolf"),
            Query(id=63, name="Sweet Soul Music", artist="Arthur Conley"),
            Query(id=64, name="Black Dog", artist="Led Zeppelin"),
            Query(id=65, name="Sweet Georgia Brown", artist="Brother Bones"),
            Query(id=66, name="Sympathy for the Devil", artist="The Rolling Stones"),
            Query(id=67, name="Sweet Talkin' Woman", artist="Electric Light Orchestra"),
            Query(id=68, name="Superstition", artist="Stevie Wonder"),
            Query(id=69, name="Sweet Little Sixteen", artist="Chuck Berry"),
            Query(id=70, name="Gimme Shelter", artist="The Rolling Stones"),
            Query(id=71, name="Sweet Emotion", artist="Aerosmith"),
            Query(id=72, name="Proud Mary", artist="Creedence Clearwater Revival"),
            Query(id=73, name="Sweet Music", artist="Van Morrison"),
            Query(id=74, name="Kashmir", artist="Led Zeppelin"),
            Query(id=75, name="Sweet Freedom", artist="Michael McDonald"),
            Query(id=76, name="Fortunate Son", artist="Creedence Clearwater Revival"),
            Query(id=77, name="Sweet Leaf", artist="Black Sabbath"),
            Query(id=78, name="Freebird", artist="Lynyrd Skynyrd"),
            Query(id=79, name="Sweet Thing", artist="Rufus"),
            Query(id=80, name="All Right Now", artist="Free"),
            Query(id=81, name="Sweet Seasons", artist="Carole King"),
            Query(id=82, name="Smoke on the Water", artist="Deep Purple"),
            Query(id=83, name="Sweet Talking Woman", artist="Electric Light Orchestra"),
            Query(id=84, name="Sunshine of Your Love", artist="Cream"),
            Query(id=85, name="Sweet Surrender", artist="John Denver"),
            Query(id=86, name="Won't Get Fooled Again", artist="The Who"),
            Query(id=87, name="Sweet Love", artist="Commodores"),
            Query(id=88, name="Whole Lotta Love", artist="Led Zeppelin"),
            Query(id=89, name="Sweet Dreams", artist="Air Supply"),
            Query(id=90, name="Paranoid", artist="Black Sabbath"),
            Query(id=91, name="Sweet Thing", artist="Chaka Khan"),
            Query(id=92, name="Baba O'Riley", artist="The Who"),
            Query(id=93, name="Sweet Pea", artist="Tommy Roe"),
            Query(id=94, name="Back in Black", artist="AC/DC"),
            Query(id=95, name="Sweet Inspiration", artist="The Sweet Inspirations"),
            Query(id=96, name="Dream On", artist="Aerosmith"),
            Query(id=97, name="Sweet Nothin's", artist="Brenda Lee"),
            Query(id=98, name="Heartbreaker", artist="Led Zeppelin"),
            Query(id=99, name="Sweet Love", artist="Gladys Knight & The Pips"),
            Query(id=100, name="Roadhouse Blues", artist="The Doors")
        ])
    time_end = time.time()
    print(f"Time taken: {time_end - time_start} seconds")
    # print(sorted(downloaded_queries, key=lambda x: x.id))