import pandas as pd
import json
from dataclasses import dataclass, Field
import os
import argparse
from pathlib import Path
from typing import Optional
    
@dataclass
class DF_INTERFACE(object):
    output_file_path: Optional[str] = None
    
    __dataframe = None
    __current_mix_id = 0
    
    def __post_init__(self):
        self.__dataframe = pd.DataFrame()
        self.__initialize_columns()
        self.__generate_csv()
        
    def __initialize_columns(self):
        self.__dataframe = pd.DataFrame(columns=[
            'mix_id',
            'mix_title', 
            'mix_url',
            'dj_name',
            'mix_date',
            'mix_duration',
            'mix_genre',
            'track_number',
            'track_title',
            'track_artist', 
            'track_start_time',
            'track_time_position',
        ])
        
    def __generate_csv(self):
        if Path(self.output_file_path).exists():
            Path(self.output_file_path).unlink()
        self.__dataframe.to_csv(self.output_file_path)
    
    def add_mix(self, mix: dict):
        # print(f"Adding mix {self.__current_mix_id} to dataframe {self.output_file_path} with {len(mix['tracks'])} tracks")
        for song_id, track in enumerate(mix['tracks']):
            # print(f"Adding track {song_id} to dataframe {self.output_file_path}")
            new_row = {
                'mix_id': self.__current_mix_id,
                'mix_title': mix["title"],
                'mix_url': mix['url'],
                'dj_name': mix['dj_name'],
                'mix_date': mix['date'],
                'mix_duration': mix['duration'],
                'mix_genre': mix['genres'][0],
                'track_number': track['track_number'],
                'track_title': track['title'],
                'track_artist': track['artist'],
                'track_start_time': track['start_time'],
                'track_time_position': track['time_position'],
            }
            self.__dataframe = pd.concat([self.__dataframe, pd.DataFrame([new_row])], ignore_index=True)
            
    def pipe_json(self, json_data: dict):
        num_mixes = len(json_data['mixes'])
        print(f"Converting {num_mixes} mixes to CSV format...")
        from tqdm import tqdm
        pbar = tqdm(total=num_mixes, desc="Processing mixes")
        
        batch_size = 100
        for i in range(0, num_mixes, batch_size):
            batch_end = min(i + batch_size, num_mixes)
            for mix in json_data['mixes'][i:batch_end]:
                pbar.update(1)
                self.add_mix(mix)
                self.__current_mix_id += 1
                
            # Save batch to CSV, append mode after first batch
            self.__dataframe.to_csv(self.output_file_path, mode='a', header=False, index=False)

            # if self.__current_mix_id > 5: exit()
            
            # Clear dataframe to free memory
            self.__dataframe = self.__dataframe.iloc[0:0]
        pbar.close()
    

def load_json(file_path: str) -> list:
    print(f"Loading JSON from {file_path}")
    
    with open(file_path, 'r') as file:
        return json.load(file)
    

def main(input_file_path: Path, mode: str):
    if mode == "file":
        output_file_path = input_file_path.with_suffix(".csv")
    elif mode == "folder":
        output_file_path = input_file_path / "scrapped_combo.csv"
    
    df_interface = DF_INTERFACE(output_file_path=output_file_path)
    
    if mode == "file":
        print(f"Processing file: {input_file_path}")
        df_interface.pipe_json(load_json(input_file_path))
    elif mode == "folder":
        print(f"Processing folder: {input_file_path}")
        for file in input_file_path.glob("*.json"):
            print(f"Processing file: {file}")
            df_interface.pipe_json(load_json(file))
    
if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument("--mode", type=str, default="file", choices=["file", "folder"])
    args.add_argument("--input", type=Path, required=True)
    args = args.parse_args()
    
    input_file_path = None
    
    if args.mode == "file":
        if not args.input.is_file():
            raise FileNotFoundError(f"File {args.input} not found")
        input_file_path = args.input
    elif args.mode == "folder":
        if not args.input.is_dir():
            raise FileNotFoundError(f"Folder {args.input} not found")
        input_file_path = args.input
        
    if not args.input.exists():
            raise FileNotFoundError(f"Folder {args.input} not found")
    
    main(input_file_path, args.mode)