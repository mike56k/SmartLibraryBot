from cassandra.cluster import Cluster


class CassandraSession:
    _cluster = None
    _session = None

    @classmethod
    def get_session(cls):
        if not cls._session:
            cls._cluster = Cluster(["db"])
            cls._session = cls._cluster.connect()
        return cls._session

    @classmethod
    def shutdown(cls):
        if cls._cluster:
            cls._cluster.shutdown()
