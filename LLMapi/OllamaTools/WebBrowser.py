from LLMapi.iOllamaTool import OllamaTool
from dataclasses import dataclass
from ddgs import DDGS
import os
from LLMapi.OllamaTools.UrlParser import UrlParser
import logging as log

log.getLogger(__name__)


@dataclass
class WebBrowser(OllamaTool):
    
    @staticmethod
    def _get_config_file_path():
        return os.path.splitext(os.path.relpath(__file__))[0] + '.json'
    
    @staticmethod
    def __perform_search(query, results_num: int = 4):
        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results=results_num)
            log.info(f"Search results: {search_results}")
            results = []
            for r in search_results:
                results.append({
                    "title": r['title'],
                    "url": r['href']
                })
            return results
    
    @classmethod
    def _main(cls, **kwargs):
        try:
            search_query = kwargs.get('query', '')
            num_results = kwargs.get('num_results', 10)
            
            search_result = cls.__perform_search(search_query, num_results)
        except Exception as e:
            return {"error": f"Failed to perform search: {str(e)}", "query": kwargs.get('query', '')}
    
        results = []
        for result in search_result:
            results.append(UrlParser._main(url=result['url']))
            
        return results