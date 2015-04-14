import unittest
from biicode.client.dev.python.python_dynlib_adapter_generator import clean_preprocessor_directives


class CleanPreprocessorDirectivesTest(unittest.TestCase):
    def test_clean_preprocessor_directives(self):
        text = r'''#include "test.h"
#include <iostream>'''
        result = clean_preprocessor_directives(text)
        self.assertEqual(result, "")

    def test_with_functions(self):
        text = r'''#include "test.h"
        int main();
        '''
        result = clean_preprocessor_directives(text)
        self.assertEqual(result, '\n        int main();')

    def test_with_functions_and_comments(self):
        text = r'''#include "test.h"
#include a
int main();  /* #sadasdasasd */
#endif'''
        result = clean_preprocessor_directives(text)
        self.assertEqual(result, '\n\nint main();  /* #sadasdasasd */')
