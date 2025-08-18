from LLMapi.iOllamaTool import OllamaTool
from dataclasses import dataclass
from newspaper import Article
import os


@dataclass
class UrlParser(OllamaTool):
    
    @staticmethod
    def _get_config_file_path():
        return os.path.splitext(os.path.relpath(__file__))[0] + '.json'
    
    @staticmethod
    def _main(**kwargs):
        try:
            article = Article(kwargs['url'])
            article.download()
            article.parse()
            return {
                "title": article.title,
                "text": article.text,
                "url": kwargs['url']
            }
        except Exception as e:
            return {"error": f"Failed to parse URL: {str(e)}", "url": kwargs['url']}