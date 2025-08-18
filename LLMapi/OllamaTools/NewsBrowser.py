from LLMapi.iOllamaTool import OllamaTool
from dataclasses import dataclass
from ddgs import DDGS
import os
from LLMapi.OllamaTools.UrlParser import UrlParser
import logging as log

log.getLogger(__name__)

@dataclass
class NewsBrowser(OllamaTool):
    
    @staticmethod
    def _get_config_file_path():
        return os.path.splitext(os.path.relpath(__file__))[0] + '.json'
    
    @staticmethod
    def __perform_search(query: str,
                        region: str = "us-en",
                        safesearch: str = "moderate",
                        timelimit: str | None = None,
                        max_results: int | None = 10,
                        page: int = 1,
                        backend: str = "auto"):
        with DDGS() as ddgs:
            search_results = ddgs.news(query=query, region=region, safesearch=safesearch, timelimit=timelimit, max_results=max_results, page=page, backend=backend)
            log.info(f"Search results: {search_results}")
            results = []
            for r in search_results:
                results.append({
                    "title": r['title'],
                    "text": r['body'],
                    "source": r['source']
                })
            return results
    
    @classmethod
    def _main(cls, **kwargs):
        try:
            search_query = kwargs.get('query', '')
            max_results = kwargs.get('max_results', 10)
            
            return cls.__perform_search(search_query, max_results=max_results)
        except Exception as e:
            return {"error": f"Failed to perform search: {str(e)}", "query": kwargs.get('query', '')}