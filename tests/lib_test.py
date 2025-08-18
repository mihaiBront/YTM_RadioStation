from unittest import TestCase

from newspaper import Article
from LLMapi.OllamaTools.UrlParser import UrlParser
import coloredlogs
from LLMapi.OllamaTools.WebBrowser import WebBrowser
from LLMapi.OllamaTools.NewsBrowser import NewsBrowser

coloredlogs.install(level='DEBUG', fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TestNewspaper(TestCase):
    def test_newspaper(self):
        article = Article('https://www.youtube.com')
        article.download()
        article.parse()
        print(article.text)
        
class TestURLParser(TestCase):
    def test_url_parser(self):
        url_parser = UrlParser.autoload()
        print(url_parser.run(url="https://www.wikipedia.org/wiki/fiat"))
        
class TestWebBrowser(TestCase):
    def test_web_browser(self):
        web_browser = WebBrowser.autoload()
        res = web_browser.run(query="fiat car info", num_results=2)
        print(res)
        
class TestNewsBrowser(TestCase):
    def test_news_browser(self):
        news_browser = NewsBrowser.autoload()
        res = news_browser.run(query="Kendrick Lamar", max_results=2)
        print(res)