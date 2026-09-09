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
        audio = load_script("06_audio.py")
        words = [{"id": "backofen", "lemma": "Backofen", "level": "A1"}]
        sentences = [{"id": "s123", "de": "Guten Tag!", "level": "A1"}]
        self.assertEqual(
            list(audio.work_items(words, sentences, {"a1"})),
            [("backofen", "Backofen", True), ("s123", "Guten Tag!", False)],
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


if __name__ == "__main__":
    unittest.main()
