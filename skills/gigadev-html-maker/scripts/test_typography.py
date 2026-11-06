"""Focused safety tests for build-time Russian typography."""
import importlib.util
import inspect
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('typography',ROOT/'typography.py')
typography=importlib.util.module_from_spec(spec);spec.loader.exec_module(typography)

class TypographyTests(unittest.TestCase):
    def test_safe_quote_dash_spacing_and_punctuation(self):
        source='Он сказал "важное решение"  — это важно . Данные  готовы'
        result=typography.normalize(source)
        self.assertEqual(result,'Он сказал «важное решение» — это важно. Данные готовы')

    def test_idempotent(self):
        result=typography.normalize('Фраза "для теста"  - это факт')
        self.assertEqual(typography.normalize(result),result)

    def test_protects_technical_and_numeric_strings(self):
        values=['https://example.com/a-b?x="тест"', 'www.example.com', 'a@b.ru',
                'v1.2.3', 'GPT-6.1', '10 - 20', 'C++', 'foo_bar', '<tag>']
        for value in values:
            with self.subTest(value=value):self.assertEqual(typography.normalize(value),value)

    def test_inline_markup_and_links_are_left_intact(self):
        markup='<p data-source-id="s1-o2">Текст <a href="https://example.com">"ссылка"</a></p>'
        out,changes=typography.prepare(markup,set(),True)
        self.assertEqual(out,markup);self.assertEqual(changes,[])

    def test_records_exact_source_and_honors_exclusions(self):
        markup='<p data-source-id="s1-o2">"фраза"  - это верно</p><p data-source-id="s1-o3">"оставить"</p>'
        out,changes=typography.prepare(markup,{'s1-o3'},True)
        self.assertIn('«фраза» — это верно',out)
        self.assertEqual(changes,[{'sourceId':'s1-o2','before':'"фраза"  - это верно','after':'«фраза» — это верно'}])

    def test_review_records_without_applying(self):
        markup='<p data-source-id="s1-o2">"фраза"  - это верно</p>'
        out,changes=typography.prepare(markup,set(),False)
        self.assertEqual(out,markup);self.assertEqual(len(changes),1)

    def test_emphasis_keeps_markup_and_normalizes_text_nodes(self):
        markup='<p data-source-id="s1-o2">"фраза" - это <strong>важно</strong> , верно.</p>'
        out, changes=typography.prepare(markup,set(),True)
        self.assertIn('«фраза» — это <strong>важно</strong>',out)
        self.assertEqual(len(changes),1)
        self.assertNotIn('<strong>',changes[0]['after'])
        self.assertEqual(typography.prepare(out,set(),True)[1],[])

    def test_short_preposition_stays_with_following_word(self):
        self.assertEqual(typography.normalize('Работа в команде и проверка'), 'Работа в\u00a0команде и\u00a0проверка')

    def test_default_build_mode_is_apply_and_modes_remain_explicit(self):
        build=ROOT/'build.py'
        text=build.read_text()
        self.assertIn('typography="apply"',text)
        self.assertIn("choices=['off','review','apply'],default='apply'",text)

if __name__=='__main__':unittest.main()
