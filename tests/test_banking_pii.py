from swaybench.pii.detect import detect_pii


def test_detect_routing_with_keyword_and_checksum():
    # 021000021 is a commonly used example routing number that passes ABA checksum.
    text = "My routing number is 021000021 and my account number is 123456789012."
    spans = detect_pii(text)
    types = {s.entity_type for s in spans}
    assert "ROUTING_NUMBER" in types
    assert "BANK_ACCOUNT" in types

