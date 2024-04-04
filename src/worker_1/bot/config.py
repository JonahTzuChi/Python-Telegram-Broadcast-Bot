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
master = config_yaml["MASTER_TELEGRAM_TOKEN"]
bot_id = config_yaml["MY_ID"]
worker = config_yaml["TELEGRAM_TOKEN"]

sysadmin_tid = config_yaml["SYSADMIN_ID"]
allowed_tid = config_yaml["ALLOWED_TELEGRAM_ID"]
allowed_username = config_yaml["ALLOWED_USERNAME"]

x_api_key = config_yaml["X_API_KEY"]
weather_api_key = config_yaml["WEATHER_API_KEY"]
base_server = config_yaml["MY_SERVER"]

magic_postfix = config_yaml["MAGIC_POSTFIX"]

seconds = config_yaml["SLEEP_SECONDS"]
use_multiproc = config_yaml["USE_MULTI_PROCESS"] == 1
use_nproc = config_yaml["USE_NPROC"]
db_find_limit = config_yaml["DB_FIND_LIMIT"]

media_types = config_yaml["MEDIA_TYPES"]

mongodb_uri = f"mongodb://mongo:{config_env['MONGODB_PORT']}"
mongodb_database = config_env["MONGODB_DATABASE"]
