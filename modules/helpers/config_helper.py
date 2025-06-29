import configparser
import os

class ConfigHelper:
    _instance = None
    _config = None

    @classmethod
    def load_config(cls, file_path="config/config.ini"):
        """Load the configuration from ``file_path`` if it hasn't been loaded."""
        if cls._config is None:
            cls._config = configparser.ConfigParser()
            if os.path.exists(file_path):
                cls._config.read(file_path)
            else:
                print(f"Warning: config file '{file_path}' not found.")
        return cls._config

    @classmethod
    def get(cls, section, key, fallback=None):
        if cls._config is None:
            cls.load_config()
        try:
            return cls._config.get(section, key, fallback=fallback)
        except Exception as e:
            print(f"Config error: [{section}] {key} — {e}")
            return fallback

    def set(section, key, value, file_path="config/config.ini"):
        config = configparser.ConfigParser()
        if os.path.exists(file_path):
            config.read(file_path)

        if not config.has_section(section):
            config.add_section(section)

        config.set(section, key, str(value))

        with open(file_path, "w", encoding="utf-8") as configfile:
            config.write(configfile)

    @classmethod
    def get_campaign_dir(cls):
        """Return the directory containing the configured database file."""
        db_path = cls.get("Database", "path", fallback="default_campaign.db")
        return os.path.abspath(os.path.dirname(db_path))


