from pathlib import Path
from pydantic import BaseSettings, Field, SecretStr
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
    reconciliation_path: str = Field(..., env='RECONCILIATION_FILE_PATH')
    ccam_username: str = Field(..., env='CCAM_USERNAME')
    ccam_password: SecretStr = Field(..., env='CCAM_PASSWORD')
    base_url: str = Field(..., env='BASE_URL')
    ccam_url: str = Field(..., env='CCAM_URL')
    cert_file: str = Field(..., env='CERT_FILE')
    class Config:
        # env_file = env_file
        # env_file_encoding = 'uft-8'
        case_sensitive = False
