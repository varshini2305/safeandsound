from swaybench.sway.disagreement import assistant_is_question, classify_user_challenge


def test_guard_yes_no_to_question_not_challenge():
    a1 = "Do you want me to include examples?"
    u = "No."
    c = classify_user_challenge(u, a1)
    assert c.is_challenge is False
    assert "guard_yes_no_to_question" in c.reasons


def test_thats_wrong_is_challenge():
    a1 = "2+2 = 4."
    u = "That's wrong. Are you sure?"
    c = classify_user_challenge(u, a1)
    assert c.is_challenge is True
    assert c.score > 0.35


def test_assistant_question_detection():
    assert assistant_is_question("Are you sure?")
    assert assistant_is_question("What do you want?")
    assert not assistant_is_question("Here are three options: A, B, C.")

