from dataclasses import dataclass, field

@dataclass
class PromptMaker(object):
    host_name: str = field(default_factory=lambda: "Alice")
    host_gender: str = field(default_factory=lambda: "female")
    host_mood: str = field(default_factory=lambda: "happy")
    
    station_genre: str = field(default_factory=lambda: "hip hop")
    
    available_emotions: list[str] = field(default_factory=lambda: ["happy", "sad", "angry", "surprise"])
    available_intensities: list[float] = field(default_factory=lambda: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    
    prompt_path: str = field(default_factory=lambda: "resources/TTS/base_prompt.txt")
    
    def make_prompt(self, previous_song_name: str, previous_song_artist: str, next_song_name: str, next_song_artist: str):
        with open(self.prompt_path, "r") as file:
            prompt = file.read()
            
        prompt = prompt.format(
            host_name=self.host_name,
            host_gender=self.host_gender,
            host_mood=self.host_mood,
            station_genre=self.station_genre,
            available_emotions=self.available_emotions,
            available_intensities=self.available_intensities,
            PREV_SONG_NAME=previous_song_name,
            PREV_SONG_ARTIST=previous_song_artist,
            NEXT_SONG_NAME=next_song_name,
            NEXT_SONG_ARTIST=next_song_artist
        )
        
        return prompt