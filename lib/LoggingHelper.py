import coloredlogs
import logging as log

class LoggingHelper(object):
    @staticmethod
    def init_logger(level: str = 'INFO', theme="light"):
        """
        Returns a coloredlogs type logger with the specified level

        Args:
            level (str, optional): Minimum level to be logged 
                [DEBUG > INFO > WARNING > ERROR > FATAL]. 
                Defaults to 'INFO'.

        Returns:
            log: Created logger
        """
        
        timestampColor = "black"
        if theme == "dark":
            timestampColor = "white"
        
        return coloredlogs.install(level=level,
                                   fmt='[%(asctime)s]\t%(levelname)s\t(%(filename)s:%(lineno)d/%(funcName)s)\t%(message)s',
                                   level_styles={
                                       'critical': {'bold': True, 'color': 'red'},
                                       'debug': {'color': 'black'},
                                       'error': {'color': 'red'},
                                       'info': {'color': 'cyan'},
                                       'notice': {'color': 'magenta'},
                                       'spam': {'color': 'green', 'faint': True},
                                       'success': {'bold': True, 'color': 'green'},
                                       'verbose': {'color': 'blue'},
                                       'warning': {'color': 'yellow'}
                                       },
                                   field_styles={
                                       'asctime': {'bold': True, 'color': timestampColor},
                                       'hostname': {'color': 'magenta'},
                                       'levelname': {'bold': True, 'color': timestampColor},
                                       'name': {'bold': True, 'color': timestampColor},
                                       'programname': {'bold': True, 'color': timestampColor},
                                       'username': {'color': 'yellow'},
                                       'funcName': {'bold': True, 'color': timestampColor}
                                       },
                                   isatty=True
                                   )  
