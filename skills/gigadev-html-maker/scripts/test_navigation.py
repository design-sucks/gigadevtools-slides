import copy
import unittest
from navigation import resolve, equivalent

class NavigationTests(unittest.TestCase):
    def test_dividers_inherit_and_reset(self):
        pages=[{'id':'s1','title':'Раздел А','navigationRole':'divider'}, {'id':'s2','title':'Факты'}, {'id':'s3','title':'Раздел Б','composition':{'id':'divider'}}, {'id':'s4','title':'Выводы'}]
        nav=resolve(pages)
        self.assertEqual(nav['s2']['section'],'Раздел А')
        self.assertEqual(nav['s4']['section'],'Раздел Б')
        self.assertEqual(nav['s1']['section'],'')
        self.assertEqual(nav['s1']['navigationSection'],'Раздел А')
        self.assertEqual(nav['s2']['sectionSourceId'],'s1')

    def test_actual_authored_heading_beats_stale_title(self):
        nav=resolve([{'id':'s1','title':'Старый заголовок','topic':'Новый — это «результат»','html':'<h2>НОВЫЙ - это <em>"результат"</em></h2>'}])
        self.assertEqual(nav['s1']['topic'],'')

    def test_custom_topic_and_sidebar_label(self):
        nav=resolve([{'id':'s1','title':'Большой полный заголовок','section':'Выбор','navigationLabel':'Критерии','navigationTopic':'Стоимость и скорость'}])
        self.assertEqual(nav['s1']['label'],'Критерии')
        self.assertEqual(nav['s1']['topic'],'Стоимость и скорость')
        self.assertEqual(nav['s1']['section'],'Выбор')

    def test_explicit_empty_and_section_duplicate(self):
        nav=resolve([{'id':'s1','title':'Выводы','section':'Итог','navigationTopic':''},{'id':'s2','title':'Выводы','section':'Итог','topic':'ИТОГ!'}])
        self.assertEqual(nav['s1']['topic'],'')
        self.assertEqual(nav['s2']['topic'],'')
        self.assertEqual(nav['s2']['section'],'Итог')

    def test_words_and_numbers_are_not_collapsed(self):
        for left,right in [('версия 2.1','версия 21'),('проект А Б','проект АБ'),('рост 10%','рост 20%')]:
            self.assertFalse(equivalent(left,right))

    def test_no_speculative_divider_and_no_input_mutation(self):
        pages=[{'id':'s1','title':'Короткий заголовок'},{'id':'s2','title':'Следующий'}];before=copy.deepcopy(pages)
        nav=resolve(pages)
        self.assertEqual(nav['s2']['section'],'')
        self.assertEqual(pages,before)

    def test_explicit_section_and_clear(self):
        nav=resolve([{'id':'s1','title':'Раздел','navigationRole':'divider'},{'id':'s2','title':'Страница','navigationSection':''},{'id':'s3','title':'Страница','section':'Особый контекст'},{'id':'s4','title':'Конец'}])
        self.assertEqual(nav['s2']['section'],'')
        self.assertEqual(nav['s3']['section'],'Особый контекст')
        self.assertEqual(nav['s4']['section'],'Раздел')

    def test_prefix_and_stable_id(self):
        nav=resolve([{'id':'s20','sourceNumber':20,'title':'20 / Выбор','topic':'Выбор','navigationRole':'divider'},{'id':'s3','sourceNumber':3,'title':'3. Факты','topic':'Факты'}])
        self.assertEqual(nav['s3']['section'],'Выбор')
        self.assertEqual(nav['s3']['topic'],'')
        self.assertEqual(nav['s3']['label'],'Факты')

    def test_invalid_metadata_refuses(self):
        for page in [{'id':'s1','navigationRole':'maybe'},{'id':'s1','navigationTopic':[]},{'id':'s1','navigationRole':'divider'}]:
            with self.assertRaises(ValueError):resolve([page])

if __name__=='__main__':unittest.main()
