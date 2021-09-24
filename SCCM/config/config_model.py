from pydantic import BaseSettings, Field
from dotenv import load_dotenv


class PLRASettings(BaseSettings):
    """
    Pydantic model for managing application settings
    """
    network_base_directory: str = Field(..., env='NETWORK_BASE_DIR')
    db_base_directory: str = Field(..., env='NETWORK_DB_BASE_DIR')
    db_backup_directory: str = Field(..., env='NETWORK_DB_BACKUP_DIR')
    db_file: str = Field(..., env='DATABASE_SQLite')
    reconciliation_path: str = Field(..., env='RECONCILIATION_FILE_PATH')

    class Config:
        case_sensitive = False

