import configparser
import os

class ConfigHelper:
    _instance = None
    _config = None

    @classmethod
    def load_config(cls, file_path="config/config.ini"):
        if cls._config is None:
            cls._config = configparser.ConfigParser()
            if os.path.exists(file_path):
                cls._config.read(file_path)
            else:
                print(f"Warning: config file '{file_path}' not found.")
        return cls._config

    @classmethod
    def get(cls, section, key, fallback=None):
        cls.load_config()
        try:
            return cls._config.get(section, key, fallback=fallback)
        except Exception as e:
            print(f"Config error: [{section}] {key} — {e}")
            return fallback
