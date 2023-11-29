from typing import List


class Host:
    def __init__(self, name: str, majority: str):
        self.name = name
        self.majority = majority


class XVM:
    def __init__(self, name: str, hosts: dict):
        hosts_objects = list()
        for host in hosts:
            hosts_objects.append(Host(host.get('name'), host.get('majority')))
        self._name = name
        self._hosts = hosts_objects

    @property
    def name(self) -> str:
        return self._name

    @property
    def hosts(self) -> List[Host]:
        return self._hosts

