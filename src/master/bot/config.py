import yaml
import dotenv
from pathlib import Path

config_dir = Path(__file__).parent.parent.resolve() / "config"

# load yaml config
with open(config_dir / "config.yml", 'r') as f:
    config_yaml = yaml.safe_load(f)

# load .env config
config_env = dotenv.dotenv_values(config_dir / "config.env")

# config parameters
token = config_yaml["TELEGRAM_TOKEN"]

greeting_1_msg = config_yaml["GREETING_1_MSG"]
greeting_2_msg = config_yaml["GREETING_2_MSG"]
subscribe_msg = config_yaml["SUBSCRIBE_MSG"]
unsubscribe_msg = config_yaml["UNSUBSCRIBE_MSG"]
sorry_single_language_only = config_yaml["SORRY_SINGLE_LANG_ONLY"]
sorry_noreply = config_yaml["SORRY_NOREPLY"]

mongodb_uri = f"mongodb://mongo:{config_env['MONGODB_PORT']}"
mongodb_database = config_env['MONGODB_DATABASE']

base_server = config_yaml["MY_SERVER"]

seconds = config_yaml["SLEEP_SECONDS"]

magic_postfix = config_yaml["MAGIC_POSTFIX"]
