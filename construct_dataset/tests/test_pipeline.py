from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ids import sentence_id, unique_sentences, word_id  # noqa: E402
from llm import run_chunks  # noqa: E402


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IdTests(unittest.TestCase):
    def test_word_id_keeps_the_existing_rules(self):
        self.assertEqual(word_id("Vater"), "vater")
        self.assertEqual(word_id("Straße"), "strasse")
        self.assertEqual(word_id("Frühstück"), "fruehstueck")
        self.assertEqual(word_id("E-Mail"), "e-mail")
        self.assertEqual(word_id("Backofen"), "backofen")

    def test_sentence_id_distinguishes_punctuation(self):
        self.assertNotEqual(sentence_id("Auf Wiedersehen!"), sentence_id("Auf Wiedersehen."))
        self.assertRegex(sentence_id("Auf Wiedersehen!"), r"^s[0-9a-f]{10}$")

    def test_checked_in_word_ids_are_unchanged_and_unique(self):
        words = [json.loads(line) for line in (ROOT / "data" / "wordlist.jsonl").read_text().splitlines()]
        seen = Counter()
        expected = []
        for word in words:
            base = word_id(word["lemma"])
            seen[base] += 1
            expected.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
        actual = [word["id"] for word in words]
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), len(set(actual)))

    def test_sentence_dataset_counts_and_ids(self):
        words = [json.loads(line) for line in (ROOT / "data" / "wordlist.jsonl").read_text().splitlines()]
        sentences = unique_sentences(words)
        self.assertEqual(len(sentences), 6417)
        self.assertEqual(Counter(row["level"] for row in sentences), {"a1": 2585, "a2": 1639, "b1": 2193})
        self.assertEqual(len({row["id"] for row in sentences}), len(sentences))


class AudioTests(unittest.TestCase):
    def test_work_items_uses_dataset_ids_and_word_lemmas(self):
        audio = load_script("07_audio.py")
        words = [{"id": "backofen", "lemma": "Backofen", "level": "A1"}]
        sentences = [{"id": "s123", "de": "Guten Tag!", "level": "A1"}]
        # 단어와 예문은 일부러 다른 속도를 쓴다
        self.assertEqual(
            list(audio.work_items(words, sentences, {"a1"},
                                  word_scale=1.25, slow=1.8, sentence_scale=1.6)),
            [("backofen", "Backofen", (1.25, 1.8)), ("s123", "Guten Tag!", (1.6,))],
        )
        # 예문 속도만 바꿨을 때 단어까지 다시 만들지 않기 위한 것
        self.assertEqual(
            [row[0] for row in audio.work_items(words, sentences, {"a1"}, only="sentences")],
            ["s123"],
        )

    def test_final_word_examples_reference_sentences(self):
        words_path = ROOT / "data" / "words.json"
        sentences_path = ROOT / "data" / "sentences.json"
        if not words_path.exists() or not sentences_path.exists():
            self.skipTest("run make merge first")
        words = json.loads(words_path.read_text(encoding="utf-8"))
        sentences = json.loads(sentences_path.read_text(encoding="utf-8"))
        sentence_ids = {sentence["id"] for sentence in sentences}
        referenced = {example["id"] for word in words for example in word["examples"]}
        self.assertEqual(referenced, sentence_ids)


class LlmTests(unittest.TestCase):
    def test_missing_items_are_retried_once_and_duplicate_outputs_are_ignored(self):
        class Item(BaseModel):
            id: str
            ko: str

        class Batch(BaseModel):
            items: list[Item]

        responses = [
            (Batch(items=[Item(id="a", ko="가"), Item(id="a", ko="중복")]), "model"),
            (Batch(items=[Item(id="b", ko="나")]), "model"),
        ]
        saved = []
        with patch("llm.call_cli", side_effect=responses) as call:
            run_chunks(
                [{"id": "a"}, {"id": "b"}],
                label="test",
                system="system",
                build_prompt=lambda entries: str(entries),
                batch_type=Batch,
                valid_item=lambda item: bool(item.ko),
                save=lambda items, _model: saved.extend((item.id, item.ko) for item in items),
                backend="cli",
                model=None,
                sdk_model="unused",
                effort="low",
                workers=1,
                chunk_size=2,
            )
        self.assertEqual(call.call_count, 2)
        self.assertEqual(saved, [("a", "가"), ("b", "나")])


class GlossTests(unittest.TestCase):
    def test_span_counts_must_cover_every_german_word(self):
        glosses = load_script("05_glosses.py")
        sentence = {"de": "Ab morgen muss ich arbeiten."}
        valid = glosses.GlossItem(
            id="s1",
            g=[
                {"n": 1, "ko": "~부터"}, {"n": 1, "ko": "내일"},
                {"n": 1, "ko": "~해야 한다"}, {"n": 1, "ko": "나는"},
                {"n": 1, "ko": "일하다"},
            ],
        )
        short = glosses.GlossItem(id="s1", g=[{"n": 2, "ko": "내일부터"}, {"n": 1, "ko": "~해야 한다"}])
        self.assertTrue(glosses.valid_gloss(valid, sentence))
        self.assertFalse(glosses.valid_gloss(short, sentence))

    def test_prompt_reuses_translation_without_repeating_metadata(self):
        glosses = load_script("05_glosses.py")
        prompt = glosses.build_prompt([{
            "id": "s1",
            "de": "Ab morgen muss ich arbeiten.",
            "ko": "내일부터 일해야 해요.",
            "en": "I have to work starting tomorrow.",
            "level": "a1",
        }])
        self.assertIn("s1\tAb morgen muss ich arbeiten.\t내일부터 일해야 해요.", prompt)
        self.assertNotIn("I have to work", prompt)
        self.assertNotIn("a1", prompt)

    def test_merge_rejects_invalid_spans_and_flags_multiword_groups(self):
        merge = load_script("06_merge.py")
        sentence = {"de": "Wie geht es Ihnen?"}
        self.assertEqual(merge.gloss_reasons(sentence, {"g": [[1, "어떻게"]]}), ["span_mismatch=1/4"])
        self.assertEqual(merge.gloss_reasons(sentence, {"g": [[1, "어떻게"], [2, "지내세요"], [1, "선생님은"]]}), ["multiword"])

    def test_numbers_are_counted_as_visible_gloss_tokens(self):
        glosses = load_script("05_glosses.py")
        item = glosses.GlossItem(id="s1", g=[
            {"n": 3, "ko": "요금은"}, {"n": 2, "ko": "함부르크부터"},
            {"n": 1, "ko": "200"}, {"n": 1, "ko": "유로"},
        ])
        self.assertTrue(glosses.valid_gloss(item, {"de": "Die Fahrt kostet ab Hamburg 200 Euro."}))

    def test_long_clause_groups_are_rejected(self):
        glosses = load_script("05_glosses.py")
        item = glosses.GlossItem(id="s1", g=[{"n": 4, "ko": "혼자 해낼 수 있다"}])
        self.assertFalse(glosses.valid_gloss(item, {"de": "Ich schaffe das allein."}))

    def test_workbook_alternatives_count_as_one_token(self):
        glosses = load_script("05_glosses.py")
        self.assertEqual(glosses.word_count("Sonst noch (et)was per E-Mail?"), 5)
        self.assertEqual(glosses.word_count("Soll ich Ihnen/dir helfen?"), 4)


if __name__ == "__main__":
    unittest.main()
