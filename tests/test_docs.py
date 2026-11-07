from src.report.docs import NOTICE, load_docs, required_documents
from src.report.explain import FORBIDDEN


def test_only_credits_in_total_get_documents():
    res = {"credits": [
        {"id": "integrated_employment", "status": "computed", "in_total": True},
        {"id": "rnd_credit", "status": "not_applicable", "in_total": True},
        {"id": "startup_sme_exemption", "status": "computed", "in_total": False}]}
    assert [d["id"] for d in required_documents(res)] == ["integrated_employment"]


def test_every_entry_has_source_flag_and_no_forbidden_words():
    data = load_docs()
    for k, v in data.items():
        if k == "meta":
            continue
        assert v["documents"] and v["timing"] and v["evidence"] and isinstance(v["verified"], bool), k
        text = " ".join(v["documents"]) + v["timing"] + v["name"]
        assert not [w for w in FORBIDDEN if w in text], k
    assert "확인하세요" in NOTICE
