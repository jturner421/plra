from SCCM.config.config_model import PLRASettings
from SCCM.data.db_session import DbSession

config_file = '../config/dev.env'
settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')
DbSession.global_init(f"{settings.db_base_directory}{settings.db_file}")
