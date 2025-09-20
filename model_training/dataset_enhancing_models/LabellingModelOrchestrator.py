from dataclasses import dataclass
from dis import disco
from essentia.standard import MonoLoader, TensorflowPredictTempoCNN, TensorflowPredictEffnetDiscogs, TensorflowPredict2D
import essentia
import numpy as np
import os
import logging
import concurrent.futures
import time
import multiprocessing
import json

# Suppress Essentia logs
essentia.log.infoActive = False
essentia.log.warningActive = False
essentia.log.errorActive = False

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 0=all, 1=info, 2=warnings, 3=errors
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations logging # 0=all, 1=info, 2=warnings, 3=errors
import tensorflow as tf
tf.get_logger().setLevel('ERROR')

# Optional: Suppress warnings module
import warnings
warnings.filterwarnings('ignore')

labelling_model_orchestrator = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PB_PATHS = {
    "tempo_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "deeptemp-k16-3.pb"),
    "discogs_embeddings_extractor": os.path.join(SCRIPT_DIR, "essentia_pb", "discogs-effnet-bs64-1.pb"),
    "discogs_approach_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "approachability_2c-discogs-effnet-1.pb"),
    "discogs_engagement_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "engagement_2c-discogs-effnet-1.pb"),
    "discogs_danceability_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "danceability-discogs-effnet-1.pb"),
    "discogs_mood_acousticness_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_acoustic-discogs-effnet-1.pb"),
    "discogs_mood_agressiveness_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_aggressive-discogs-effnet-1.pb"),
    "discogs_mood_electronicness_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_electronic-discogs-effnet-1.pb"),
    "discogs_mood_happy_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_happy-discogs-effnet-1.pb"),
    "discogs_mood_relaxed_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_relaxed-discogs-effnet-1.pb"),
    "discogs_mood_sad_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_sad-discogs-effnet-1.pb"),
    "discogs_mood_party_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_party-discogs-effnet-1.pb")
}

# Verify all PB files exist
for key, value in PB_PATHS.items():
    if not os.path.exists(value):
        print(f"PB file {value} not found")
        print(f"Script directory: {SCRIPT_DIR}")
        print(f"Looking for: {value}")
        exit()

TEMPO_CNN_MIN_MAX_BINS = {
    "min": 30,
    "max": 286,
    "bins": 256
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

    
def interpret_discogs_output(output, isreverted=False):
    reduced = np.mean(output, axis=0)
    if isreverted:
        reduced = np.flip(reduced)
    if len(reduced) == 3:
        return {"low": float(reduced[0]), "medium": float(reduced[1]), "high": float(reduced[2])}
    elif len(reduced) == 2:
        return {"low": float(reduced[0]), "high": float(reduced[1])}
    if len(reduced) > 3:
        return np.argmax([o[0] for o in output]) 
    
    return output
    

@dataclass
class LabellingModelOrchestrator(object):
    tempo_predictor: TensorflowPredictTempoCNN = TensorflowPredictTempoCNN(
        graphFilename=PB_PATHS["tempo_predictor"])
    discogs_embeddings_extractor: TensorflowPredictEffnetDiscogs = TensorflowPredictEffnetDiscogs(
        graphFilename=PB_PATHS["discogs_embeddings_extractor"], output="PartitionedCall:1")
    discogs_approach_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_approach_predictor"], output="model/Softmax")
    discogs_engagement_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_engagement_predictor"], output="model/Softmax")
    discogs_danceability_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_danceability_predictor"], output="model/Softmax")
    discogs_mood_acousticness_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_acousticness_predictor"], output="model/Softmax")
    discogs_mood_agressiveness_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_agressiveness_predictor"], output="model/Softmax")
    discogs_mood_electronicness_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_electronicness_predictor"], output="model/Softmax")
    discogs_mood_happy_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_happy_predictor"], output="model/Softmax")
    discogs_mood_party_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_party_predictor"], output="model/Softmax")
    discogs_mood_relaxed_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_relaxed_predictor"], output="model/Softmax")
    discogs_mood_sad_predictor: TensorflowPredict2D = TensorflowPredict2D(
        graphFilename=PB_PATHS["discogs_mood_sad_predictor"], output="model/Softmax")
    
    # Audio storage
    __audio = None
        
    
    def __load_audio(self, audio_path: str):
        self.__audio = MonoLoader(filename=audio_path, sampleRate=11025, resampleQuality=4)()
    
    def load_audio_from_path(self, audio_path: str):
        return MonoLoader(filename=audio_path, sampleRate=11025, resampleQuality=4)()
    
    def __get_music_tempo(self, audio):
        def interpret_output(output):
            global_vector = np.mean(output, axis=0)  # shape (256,)
            bpm_bin_index = np.argmax(global_vector)
            bpm = TEMPO_CNN_MIN_MAX_BINS["min"] + (bpm_bin_index / (TEMPO_CNN_MIN_MAX_BINS["bins"] - 1)) * (TEMPO_CNN_MIN_MAX_BINS["max"] - TEMPO_CNN_MIN_MAX_BINS["min"])
            return bpm, global_vector[np.argmax(global_vector)]
        
        labelling = self.tempo_predictor(audio)
        bpm, confidence = interpret_output(labelling)
        
        return float(bpm), float(confidence)
    
    def __extract_discoges_embeddings(self, audio):
        embeddings = self.discogs_embeddings_extractor(audio)
        return embeddings
    
    def __predict_approachability_2d(self, embeddings) -> dict[str, float] | float:
        approachability = self.discogs_approach_predictor(embeddings)
        return interpret_discogs_output(approachability)
    
    def __predict_engagement_2d(self, embeddings):
        engagement = self.discogs_engagement_predictor(embeddings)
        return interpret_discogs_output(engagement)
    
    def __predict_danceability_2d(self, embeddings):
        danceability = self.discogs_danceability_predictor(embeddings)
        return interpret_discogs_output(danceability, True)
    
    def __predict_acousticness_2d(self, embeddings):
        acousticness = self.discogs_mood_acousticness_predictor(embeddings)
        return interpret_discogs_output(acousticness, True)
    
    def __predict_agressiveness_2d(self, embeddings):
        agressiveness = self.discogs_mood_agressiveness_predictor(embeddings)
        return interpret_discogs_output(agressiveness, True)
    
    def __predict_electronicness_2d(self, embeddings):
        electronicness = self.discogs_mood_electronicness_predictor(embeddings)
        return interpret_discogs_output(electronicness, True)
    
    def __predict_happy_2d(self, embeddings):
        happy = self.discogs_mood_happy_predictor(embeddings)
        return interpret_discogs_output(happy, True)
    
    def __predict_party_2d(self, embeddings):
        party = self.discogs_mood_party_predictor(embeddings)
        return interpret_discogs_output(party, True)
    
    def __predict_relaxed_2d(self, embeddings):
        relaxed = self.discogs_mood_relaxed_predictor(embeddings)
        return interpret_discogs_output(relaxed, True)
    
    def __predict_sad_2d(self, embeddings):
        sad = self.discogs_mood_sad_predictor(embeddings)
        return interpret_discogs_output(sad, True)
    
    
    
    def label_audio_serial(self, audio_path: str):
        """
        Simple sequential processing - no threading to avoid locks
        This is the fastest approach for single file processing
        """
        # Load audio
        audio = self.load_audio_from_path(audio_path)
        
        # Process sequentially - no threading issues
        bpm = self.__get_music_tempo(audio)
        embeddings = self.__extract_discoges_embeddings(audio)
        
        # Return all results
        return {
            "bpm": bpm,
            "approachability": self.__predict_approachability_2d(embeddings),
            "engagement": self.__predict_engagement_2d(embeddings),
            "danceability": self.__predict_danceability_2d(embeddings),
            "acousticness": self.__predict_acousticness_2d(embeddings),
            "agressiveness": self.__predict_agressiveness_2d(embeddings),
            "electronicness": self.__predict_electronicness_2d(embeddings),
            "happy": self.__predict_happy_2d(embeddings),
            "party": self.__predict_party_2d(embeddings),
            "relaxed": self.__predict_relaxed_2d(embeddings),
            "sad": self.__predict_sad_2d(embeddings)
        }
    
    def batch_process_files_multiprocessing(self, audio_paths: list[str], max_workers: int = 4):
        """
        Use multiprocessing.Pool with spawn method for better isolation
        This works better with TensorFlow than ProcessPoolExecutor
        """
        # Set spawn method for clean process isolation
        ctx = multiprocessing.get_context('spawn')
        
        with ctx.Pool(processes=max_workers) as pool:
            try:
                results_list = pool.map(process_single_file, audio_paths)
                # Convert to dictionary
                results = {path: result for path, result in zip(audio_paths, results_list)}
                return results
            except Exception as e:
                logger.error(f"Error in multiprocessing pool: {e}")
                return {}
    
    def batch_process_files(self, audio_paths: list[str], max_workers: int = 4):
        """
        Process multiple files using process pools for true parallelism
        Each process gets its own model instances and GPU context
        """
        # Try multiprocessing first (better for TensorFlow)
        try:
            return self.batch_process_files_multiprocessing(audio_paths, max_workers)
        except Exception as e:
            logger.error(f"Multiprocessing failed, falling back to ProcessPoolExecutor: {e}")
            
            # Fallback to ProcessPoolExecutor
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    path: executor.submit(process_single_file, path)
                    for path in audio_paths
                }
                
                results = {}
                for path, future in futures.items():
                    try:
                        results[path] = future.result()
                    except Exception as e:
                        logger.error(f"Error processing {path}: {e}")
                        results[path] = None
                
                return results

    def batch_process_files_external(self, audio_paths: list[str], max_workers: int = 4):
        """
        Use external Python processes - most reliable for TensorFlow
        """
        import subprocess
        import sys
        
        results = {}
        script_path = os.path.abspath(__file__)
        
        # Process files in batches to limit concurrent processes
        for i in range(0, len(audio_paths), max_workers):
            batch = audio_paths[i:i + max_workers]
            processes = []
            
            # Start processes for this batch
            for audio_path in batch:
                cmd = [
                    sys.executable, '-c',
                    f'''
import sys
sys.path.append("{os.path.dirname(script_path)}")
from LabellingModelOrchestrator import process_single_file
import json
result = process_single_file("{audio_path}")
print(json.dumps(result) if result else "null")
'''
                ]
                
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                processes.append((audio_path, proc))
            
            # Collect results
            for audio_path, proc in processes:
                try:
                    stdout, stderr = proc.communicate(timeout=300)  # 5 min timeout
                    if proc.returncode == 0 and stdout.strip():
                        import json
                        result = json.loads(stdout.strip())
                        results[audio_path] = result
                    else:
                        print(f"Process failed for {audio_path}: {stderr}")
                        results[audio_path] = None
                except subprocess.TimeoutExpired:
                    proc.kill()
                    print(f"Timeout processing {audio_path}")
                    results[audio_path] = None
                except Exception as e:
                    print(f"Error processing {audio_path}: {e}")
                    results[audio_path] = None
        
        return results
            

# Standalone function for process pools - needed to avoid pickle issues
def process_single_file(audio_path: str):
    """
    Process a single audio file in a separate process
    This creates fresh model instances to avoid pickle issues
    """
    try:
        # Configure TensorFlow for WSL2 process pools
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'  # Allow GPU memory growth
        os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'  # Private GPU threads
        
        import tensorflow as tf
        tf.get_logger().setLevel('ERROR')
        
        # Configure GPU memory growth if GPU is available
        try:
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError:
            pass  # GPU configuration can only be set at startup
        
        # Create a new orchestrator instance in this process
        orchestrator = LabellingModelOrchestrator()
        # Process the file sequentially
        result = orchestrator.label_audio_serial(audio_path)
        # Clean up
        del orchestrator
        return result
    except Exception as e:
        logger.error(f"Error in process_single_file for {audio_path}: {e}")
        return None
    

if __name__ == "__main__":
    # Test files
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
    test_files = [
        os.path.join(PARENT_DIR, "temp", "[I Can't Get No] Satisfaction (Mono).mp3"),
        os.path.join(PARENT_DIR, "temp", "1949 HITS ARCHIVE： Sweet Georgia Brown - Brother Bones (Harlem Globetrotters theme).mp3"),
        os.path.join(PARENT_DIR, "temp", "ABBA - Dancing Queen (Official Lyric Video).mp3"),
        os.path.join(PARENT_DIR, "temp", "AC⧸DC - Back In Black.mp3"),
        os.path.join(PARENT_DIR, "temp", "Aerosmith - Dream On (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Aerosmith - Sweet Emotion (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "All Right Now.mp3"),
        os.path.join(PARENT_DIR, "temp", "American Girl.mp3"),
        os.path.join(PARENT_DIR, "temp", "Aretha Franklin - Respect (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Arthur Conley ~ Sweet Soul Music  (1967).mp3"),
        os.path.join(PARENT_DIR, "temp", "B.B. King - Sweet Sixteen .wmv.mp3"),
        os.path.join(PARENT_DIR, "temp", "Beat It.mp3"),
        os.path.join(PARENT_DIR, "temp", "Bee Gees - Staying Alive (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Beyoncé - Sweet Dreams.mp3"),
        os.path.join(PARENT_DIR, "temp", "Billie Jean.mp3"),
        os.path.join(PARENT_DIR, "temp", "Billy Joel - Piano Man (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Black Sabbath - Paranoid (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Black Sabbath - Sweet Leaf [High Quality].mp3"),
        os.path.join(PARENT_DIR, "temp", "Bob Dylan - Like a Rolling Stone (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Bohemian Rhapsody (Remastered 2011).mp3"),
        os.path.join(PARENT_DIR, "temp", "Bon Jovi - Livin' On A Prayer.mp3"),
        os.path.join(PARENT_DIR, "temp", "Born To Be Wild.mp3"),
        os.path.join(PARENT_DIR, "temp", "Born to Run.mp3"),
        os.path.join(PARENT_DIR, "temp", "Carole King - Sweet Seasons (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Creedence Clearwater Revival - Proud Mary (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Daft Punk - Get Lucky (Official Audio) ft. Pharrell Williams, Nile Rodgers.mp3"),
        os.path.join(PARENT_DIR, "temp", "Dream Baby (How Long Must I Dream).mp3"),
        os.path.join(PARENT_DIR, "temp", "Eagles - Hotel California (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Electric Light Orchestra - Sweet Talkin' Woman (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Eurythmics - Sweet Dreams (Lyrics).mp3"),
        os.path.join(PARENT_DIR, "temp", "Every Breath You Take.mp3"),
        os.path.join(PARENT_DIR, "temp", "Fortunate Son.mp3"),
        os.path.join(PARENT_DIR, "temp", "Gimme Shelter (Remastered 2019).mp3"),
        os.path.join(PARENT_DIR, "temp", "Gladys Knight & The Pips - Taste of Bitter Love.mp3"),
        os.path.join(PARENT_DIR, "temp", "Good Vibrations (Stereo).mp3"),
        os.path.join(PARENT_DIR, "temp", "Guns N' Roses - Sweet Child O' Mine (Official Audio HQ).mp3"),
        os.path.join(PARENT_DIR, "temp", "Hey Jude (Remastered 2015).mp3"),
        os.path.join(PARENT_DIR, "temp", "I Want It That Way.mp3"),
        os.path.join(PARENT_DIR, "temp", "I Want To Hold Your Hand (Remastered 2015).mp3"),
        os.path.join(PARENT_DIR, "temp", "Jeff Buckley - Hallelujah (Original Studio Version).mp3"),
        os.path.join(PARENT_DIR, "temp", "John Denver： Sweet Surrender.mp3"),
        os.path.join(PARENT_DIR, "temp", "John Lennon - Imagine (Remastered 2020).mp3"),
        os.path.join(PARENT_DIR, "temp", "Johnny Be Goode.mp3"),
        os.path.join(PARENT_DIR, "temp", "Journey - Don't Stop Believin' (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Kashmir (Remaster).mp3"),
        os.path.join(PARENT_DIR, "temp", "Layla.mp3"),
        os.path.join(PARENT_DIR, "temp", "Led Zeppelin - Black Dog (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Led Zeppelin - Heartbreaker (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Led Zeppelin - Stairway To Heaven (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Led Zeppelin - Whole Lotta Love (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Light My Fire (2017 Remaster).mp3"),
        os.path.join(PARENT_DIR, "temp", "Like a Prayer.mp3"),
        os.path.join(PARENT_DIR, "temp", "London Calling.mp3"),
        os.path.join(PARENT_DIR, "temp", "Lou Reed - Sweet Jane (Official Audio from Walk On The Wild Side).mp3"),
        os.path.join(PARENT_DIR, "temp", "Lynyrd Skynyrd - Free Bird (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Lynyrd Skynyrd - Sweet Home Alabama (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Marilyn Manson - Sweet Dreams ( Are Made Of This ) - Official Audio HD.mp3"),
        os.path.join(PARENT_DIR, "temp", "Marvin Gaye - What's Going On.mp3"),
        os.path.join(PARENT_DIR, "temp", "Neil Diamond - Sweet Caroline (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Nirvana - Smells Like Teen Spirit [Nevermind] [HQ Sound].mp3"),
        os.path.join(PARENT_DIR, "temp", "Paint It, Black.mp3"),
        os.path.join(PARENT_DIR, "temp", "Player - Player Baby Come Back (HQ).mp3"),
        os.path.join(PARENT_DIR, "temp", "Purple Rain.mp3"),
        os.path.join(PARENT_DIR, "temp", "Roadhouse Blues.mp3"),
        os.path.join(PARENT_DIR, "temp", "Roxanne.mp3"),
        os.path.join(PARENT_DIR, "temp", "Simon & Garfunkel - Bridge Over Troubled Water (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Smoke On The Water (2024 Remastered).mp3"),
        os.path.join(PARENT_DIR, "temp", "Sunshine Of Your Love.mp3"),
        os.path.join(PARENT_DIR, "temp", "Superstition.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Baby James.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet City Woman.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Dreams - Air Supply (High Quality Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Freedom.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Inspiration.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Little Sixteen.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Love.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Nothin's.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Surrender.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Thing (2015 Remaster).mp3"),
        os.path.join(PARENT_DIR, "temp", "Sweet Thing.mp3"),
        os.path.join(PARENT_DIR, "temp", "Sympathy For The Devil.mp3"),
        os.path.join(PARENT_DIR, "temp", "The Blues Brothers - Sweet Home Chicago (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "The Guess Who - American Woman (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "The Jimi Hendrix Experience - All Along The Watchtower (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "The Jimi Hendrix Experience - Purple Haze (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "The Mama's and The Papa's - California Dreamin' [Remastered] (Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "The Temper Trap- Sweet Disposition (HQ).mp3"),
        os.path.join(PARENT_DIR, "temp", "The Who - Baba O'Riley (Lyric Video).mp3"),
        os.path.join(PARENT_DIR, "temp", "Tommy Roe - Sweet Pea.mp3"),
        os.path.join(PARENT_DIR, "temp", "Van Morrison - Brown Eyed Girl (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Whitney Houston - I Will Always Love You (Official Audio).mp3"),
        os.path.join(PARENT_DIR, "temp", "Won't Get Fooled Again (Remastered 2022).mp3"),
        os.path.join(PARENT_DIR, "temp", "Wonderwall (Remastered).mp3"),
        os.path.join(PARENT_DIR, "temp", "Yesterday (Remastered 2009).mp3")
    ]
    
    # Verify files exist before processing
    existing_files = []
    for file_path in test_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
        else:
            print(f"File not found: {file_path}")
    
    print(f"Found {len(existing_files)}/{len(test_files)} files to process")
    
    if existing_files:
        # Create orchestrator for testing
        labelling_model_orchestrator = LabellingModelOrchestrator()
        
        print("\n=== Testing Sequential Processing ===")
        start_time = time.time()
        if existing_files:  # Test with just one file first
            print(f"Processing: {os.path.basename(existing_files[0])}")
            result = labelling_model_orchestrator.label_audio_serial(existing_files[0])
            print(f"BPM: {result['bpm'][0]:.1f}, Danceability: {result['danceability']}")
        sequential_time = time.time() - start_time
        print(f"Sequential time for 1 file: {sequential_time:.2f}s")
        
        print("\n=== Testing Multiprocessing Pool ===")
        start_time = time.time()
        batch_results = labelling_model_orchestrator.batch_process_files_multiprocessing(existing_files[:3], max_workers=3)
        mp_time = time.time() - start_time
        
        successful_results = len([r for r in batch_results.values() if r is not None])
        print(f"Multiprocessing time for {len(existing_files[:3])} files: {mp_time:.2f}s")
        print(f"Successfully processed: {successful_results}/{len(existing_files[:3])} files")
        
        if successful_results == 0:
            print("\n=== Trying External Processes ===")
            start_time = time.time()
            batch_results = labelling_model_orchestrator.batch_process_files_external(existing_files[:3], max_workers=3)
            ext_time = time.time() - start_time
            
            successful_results = len([r for r in batch_results.values() if r is not None])
            print(f"External processes time for {len(existing_files[:3])} files: {ext_time:.2f}s")
            print(f"Successfully processed: {successful_results}/{len(existing_files[:3])} files")
            process_pool_time = ext_time
        else:
            process_pool_time = mp_time
        
        if sequential_time > 0:
            print(f"\nSpeedup: {sequential_time * len(existing_files[:3]) / process_pool_time:.1f}x")
        
        # Clean up
        del labelling_model_orchestrator
    else:
        print("No files found to process!")
    