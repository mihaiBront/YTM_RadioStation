from Models.TTS.Prompt import PromptMaker

prompt_maker = PromptMaker()

prompt = prompt_maker.make_prompt(
    previous_song_name="Candy Rain",
    previous_song_artist="Soul For Real",
    next_song_name="1 Thing",
    next_song_artist="Amerie"
)

print(prompt)