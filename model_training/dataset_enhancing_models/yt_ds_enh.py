import yt_dlp

def search_and_download(query, out_path="downloads/"):
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "default_search": "ytsearch1",
        "outtmpl": f"{out_path}%(title)s.%(ext)s",
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([query])

if __name__ == "__main__":
    search_and_download("Daft Punk Get Lucky audio")