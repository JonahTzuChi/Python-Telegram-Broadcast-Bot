import yaml
import dotenv
from pathlib import Path

shared_config_dir = Path(__file__).parent.parent.resolve() / "shared_config"
with open(shared_config_dir / "bot_line.production.yml", 'r') as f:
    bot_line = yaml.safe_load(f)

with open(shared_config_dir / "general.production.yml", 'r') as f:
    general_config_yaml = yaml.safe_load(f)
# Extracting `general_config_yaml`
seconds: float = general_config_yaml["SLEEP_SECONDS"]
max_retry: int = general_config_yaml["MAX_RETRY"]
# use_multi_process: bool = general_config_yaml["USE_MULTI_PROCESS"]
# use_nproc: int = general_config_yaml["USE_NPROC"]
# broadcast_types: list[str] = general_config_yaml["BROADCAST_TYPES"]
# upload_types: list[str] = general_config_yaml["UPLOAD_TYPES"]

magic_postfix = general_config_yaml["MAGIC_POSTFIX"]
# db_find_limit: int = general_config_yaml["DB_FIND_LIMIT"]

# Load access control list
with open(shared_config_dir / "access.production.yml", 'r') as f:
    acl_config_yaml = yaml.safe_load(f)
# sysadmin_tid: list[int] = acl_config_yaml["SYSADMIN_TID"]
# dummy_id: int = acl_config_yaml["DUMMY_ID"]
token: str = acl_config_yaml["MASTER_TOKEN"]

# Load environmental variables
shared_config_env = dotenv.dotenv_values(shared_config_dir / "config.production.env")
db_host = shared_config_env["MONGODB_HOST"]
db_port = shared_config_env["MONGODB_PORT"]
db_name = shared_config_env["MONGODB_DATABASE"]
mongodb_uri = f"mongodb://{db_host}:{db_port}"

project_name: str = shared_config_env["PROJECT_NAME"]
