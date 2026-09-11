from src.analysis.cache import AnalysisCache


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, *, Key):
        item = self.items.get(Key["transactionId"])
        return {"Item": item} if item else {}

    def put_item(self, *, Item):
        self.items[Item["transactionId"]] = Item


def test_cache_returns_saved_analysis_and_persists_new_analysis():
    cache = AnalysisCache(table=FakeTable())

    assert cache.get("txn-1") is None
    saved = cache.save("txn-1", "SUSPICIOUS", "Repeated pattern", [])

    assert cache.get("txn-1") == saved
    assert saved["reasoning"] == "Repeated pattern"
    assert saved["analyzedAt"]