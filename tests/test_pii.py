from swaybench.pii.anonymize import AnonymizationConfig, anonymize_conversations
from swaybench.io.chatgpt_export import ChatConversation, Turn


def test_anonymization_deterministic_with_salt():
    convos = [
        ChatConversation(
            conversation_id="c1",
            title=None,
            create_time=None,
            turns=[
                Turn(role="user", text="email alice@example.com phone (415) 555-1212", time=None),
                Turn(role="assistant", text="ok", time=None),
            ],
        )
    ]
    cfg = AnonymizationConfig(salt="x")
    a1, s1 = anonymize_conversations(convos, cfg)
    a2, s2 = anonymize_conversations(convos, cfg)
    assert a1[0].turns[0].text == a2[0].turns[0].text
    assert s1.total_spans == s2.total_spans
    assert "<EMAIL_1>" in a1[0].turns[0].text


