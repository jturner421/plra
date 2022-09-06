from SCCM.services.db_session import DbSession
from SCCM.config.config_model import PLRASettings

config_file = 'SCCM/config/dev.env'
settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')

db_path = f'{settings.db_base_directory}{settings.db_file}'
DbSession.global_init(db_path)

