from elkron_client import ElkronClient

class ElkronAlarm:

    def __init__(self, elkronClient):
        self.elkronClient = elkronClient
        self.zones = []

    @classmethod
    def withClient(cls, username, password, host):
        client = ElkronClient(username, password, host)
        return cls(client)
