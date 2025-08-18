import os
from logging import log
from typing import Optional


class FileManagement(object):
    @staticmethod
    def get_dir_from_filepath(path: str) -> str:
        """
        Given any path (either to a file or a directory), returns the parent 
        directory if it is a file, or itself if it is a directory.

        Args:
            path (str): Path

        Returns:
            str: Path to directory
        """
        _path = path[:]
        if "." in path[path.rfind("/"):]:
            _path = path[:path.rfind('/')]
        return _path

    @classmethod
    def create_dir_if_not_exists(cls, dir_path: str) -> str:
        """
        Given a path, creates a directory if it doesn't exists. 
        If the path provided is to a file and not a directory, 
        it creates what would be the parent directory to that file
        
        Args:
            dir_path (str): Path to file or directory

        Returns:
            str: Path to generated path, None if it fails
        """        
        _path = cls.get_dir_from_filepath(dir_path)
        if not os.path.exists(_path):
            try:
                os.makedirs(_path, exist_ok=True)
                log.debug(f"Created '{_path}' directory.")
            except Exception as ex:
                log.error(f"Failed creating '{_path}' ({ex})")
                return None
        log.debug(f"Directory '{_path}' already existed.")
        return _path
    
    @staticmethod
    def path_to_python(path: str):
        """
        Converts a windows-formatted path to a python-compatible path

        Args
            path (str): File/Directory path
        
        Returns:
            (str) Same path with assured compatibility with python
        """
        _path = path[:]
        _path = _path.replace("\\", "/")
        if _path.endswith("/"):
            _path = _path[:-1]
        return _path
    
    @staticmethod
    def isFile(path:str) -> tuple[bool, int]:
        if "/" in path:
            _final_dir = path.split("/")[-1]
        elif "\\" in path:
            _final_dir = path.split("\\")[-1]
        else: return(False, -1)
        
        if not os.path.exists(path):
            return (False, -1)
        
        if "." in _final_dir:
            return True, 0
        else: return False, 0
    
    @classmethod
    def isFolder(cls, path:str) -> tuple[bool, int]:
        return os.path.isdir(path)
   
    @classmethod
    def getFileExtension(cls, path) -> Optional[str]:
        if not cls.isFile(path)[0]:
            log.warning("Passed path is not a file")
            return None
        
        file = ""
        if "/" in path:
            file = path.split("/")[-1]
        elif "\\" in path:
            file = path.split("\\")[-1]
        else: 
            file = path
        
        return file.split(".")[-1] 
    
    @classmethod
    def validateFileExtension(cls, path, validExtensions):
        """
        For a said file, and list of valid extensions, simply check if file passed has an extension that's in the valid extensions list

        Args:
            path (str): Path to file
            validExtensions (list[str]): List of valid extensions

        Returns:
            bool: True if it is valid, false if it isn't
        """        
        log.debug(f"Validating file extension for {path}")
        if cls.getFileExtension(path) in validExtensions:
            return True
        else:
            return False       
