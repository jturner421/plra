import configparser


def initialize_config(config_file):
    """
    Reads variables from config.ini file
    :return: dictionary of key value pairs for all attributes
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def get_dev_vars(config, section):
    """
    Gets variables for dev environments
    :param config: dictionary of key value pairs
    :param section: identifier values to get
    :return: dictionary of key value pairs for dev environments
    """
    dev_vars = config[section]
    return dev_vars


def get_db_vars(config, section):
    """
    Gets variables for dev DB connections
    :param config: dictionary of key value pairs
    :param section: identifier values to get
    :return: dictionary of key value pairs to populate Oracle connection string
    """
    db_vars = config[section]
    return db_vars

def get_reconciliation_vars(confiig, section):
    reconciliation_vars = confiig[section]
    return reconciliation_vars

def get_prod_vars(config, section):
    """
    Gets variables for prod DB connections
    :param config: dictionary of key value pairs
    :param section: identifier values to get
    :return: dictionary of key value pairs to populate Oracle connection string
    """
    prod_vars = config[section]
    return prod_vars
