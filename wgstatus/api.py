from typing import List

import aiohttp

from .cluster import Cluster
from .xvm import XVM


class WGStatusAPI:
    def __init__(self):
        self._url = 'https://api.wgstatus.com/api/data/wot'
        self._data: dict = {}
        self._clusters: List[Cluster] = []
        self._xvm = None

    async def _get_data(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self._url) as response:
                d = await response.json()
                self._data = d.get('results')[0]

    def _create_clusters(self, cluster: dict):
        self._clusters.append(Cluster(
            title=cluster.get('title'),
            servers=cluster.get('servers'),
            version=cluster.get('version'),
            version_updated_at=cluster.get('version_updated_at'),
            flag=cluster.get('flag'),
            online=cluster.get('online')
        ))

    def _create_xvm(self, item: dict):
        self._xvm = XVM(item['title'], item['hosts'])

    @property
    def raw_data(self) -> dict:
        return self._data

    @property
    def clusters(self) -> List[Cluster]:
        return self._clusters

    @property
    def xvm(self) -> XVM:
        return self._xvm

    @classmethod
    async def create(cls):
        instance = cls()
        await instance._get_data()
        for item in instance._data:
            if item.get('type') == 'cluster':
                instance._create_clusters(item.get('data'))
            elif item.get('type') == 'http':
                instance._create_xvm(item.get('data'))
        return instance
