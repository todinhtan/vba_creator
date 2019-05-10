import yaml

class AppConfig(object):
    def __init__(self):
        with open('config.yml', 'r') as config:
            cfg = yaml.load(config)
        self.withdraw = cfg['withdraw']