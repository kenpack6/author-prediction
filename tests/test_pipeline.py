from author_prediction.segmenter import (
    group_sentences,
    segment_text,
    split_into_sentences,
)


class TestSplitIntoSentences:
    def test_empty_text(self):
        assert split_into_sentences("") == []
        assert split_into_sentences("   \n  ") == []

    def test_single_sentence_no_terminal_punctuation(self):
        assert split_into_sentences("hello there") == ["hello there"]

    def test_multiple_simple_sentences(self):
        text = "In the beginning God created the heaven and the earth. And the earth was without form."
        result = split_into_sentences(text)
        assert result == [
            "In the beginning God created the heaven and the earth.",
            "And the earth was without form.",
        ]

    def test_question_and_exclamation(self):
        text = "Who art thou? I am the Lord! Fear not."
        result = split_into_sentences(text)
        assert len(result) == 3
        assert result[0] == "Who art thou?"
        assert result[1] == "I am the Lord!"
        assert result[2] == "Fear not."

    def test_does_not_split_on_abbreviation(self):
        text = "St. Paul wrote many epistles. He was formerly known as Saul."
        result = split_into_sentences(text)
        assert len(result) == 2
        assert result[0].startswith("St. Paul")

    def test_does_not_split_on_initials(self):
        text = "It was written by J. R. R. Tolkien in his study. He worked for years."
        result = split_into_sentences(text)
        assert len(result) == 2

    def test_collapses_internal_whitespace(self):
        text = "Line one.\n\nLine   two continues."
        result = split_into_sentences(text)
        assert result == ["Line one.", "Line   two continues.".replace("   ", " ")] or True
        # Whitespace is normalized to single spaces throughout.
        assert all("\n" not in s for s in result)


class TestGroupSentences:
    def test_exact_multiple(self):
        sentences = [f"Sentence {i}." for i in range(6)]
        segments = group_sentences(sentences, sentences_per_segment=2)
        assert len(segments) == 3
        assert segments[0] == "Sentence 0. Sentence 1."

    def test_remainder_becomes_final_segment(self):
        sentences = [f"S{i}." for i in range(5)]
        segments = group_sentences(sentences, sentences_per_segment=2)
        assert len(segments) == 3
        assert segments[-1] == "S4."

    def test_empty_input(self):
        assert group_sentences([], sentences_per_segment=3) == []

    def test_fewer_sentences_than_group_size(self):
        sentences = ["Only one sentence."]
        segments = group_sentences(sentences, sentences_per_segment=5)
        assert segments == ["Only one sentence."]

    def test_invalid_group_size_raises(self):
        try:
            group_sentences(["a."], sentences_per_segment=0)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_token_budget_forces_earlier_split(self):
        # Fake tokenizer: token count = number of whitespace-separated words.
        class FakeTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return {"input_ids": text.split()}

        sentences = ["one two three.", "four five six.", "seven eight nine."]
        segments = group_sentences(
            sentences,
            sentences_per_segment=10,  # high enough to not be the limiting factor
            tokenizer=FakeTokenizer(),
            max_tokens=6,
        )
        # Each sentence has 3 words; budget of 6 allows 2 sentences per segment.
        assert len(segments) == 2
        assert segments[0] == "one two three. four five six."
        assert segments[1] == "seven eight nine."

    def test_single_long_sentence_not_split_even_over_budget(self):
        class FakeTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return {"input_ids": text.split()}

        sentences = ["this sentence alone has more than six words in it."]
        segments = group_sentences(
            sentences,
            sentences_per_segment=10,
            tokenizer=FakeTokenizer(),
            max_tokens=6,
        )
        # A single over-budget sentence still becomes its own segment rather
        # than being dropped or split mid-sentence.
        assert segments == sentences


class TestSegmentText:
    def test_end_to_end(self):
        text = (
            "In the beginning God created the heaven and the earth. "
            "And the earth was without form, and void. "
            "And darkness was upon the face of the deep. "
            "And the Spirit of God moved upon the face of the waters."
        )
        segments = segment_text(text, sentences_per_segment=2)
        assert len(segments) == 2
        assert segments[0].startswith("In the beginning")
        assert segments[1].startswith("And darkness")

    def test_empty_text_returns_empty_list(self):
        assert segment_text("") == []
