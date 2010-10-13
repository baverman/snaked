import sys
import os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__))) 

from snaked.plugins.edit_and_select.pairs_parser import get_brackets, find_closing_quote_pos

def test_bracket_matcher():
    assert get_brackets('foo(1,2, boo(a, b))', 13) == ('(', 13, 18)
    assert get_brackets('foo(1,2, boo(a, b))', 12) == ('(', 4, 19)

    assert get_brackets('foo(a[sas])', 6) == ('[', 6, 10)
    assert get_brackets('foo(a[sas])', 7) == ('[', 6, 10)
    assert get_brackets('foo(a[sas])', 9) == ('[', 6, 10)
    assert get_brackets('foo(a[sas])', 10) == ('(', 4, 11)

    assert get_brackets('foo() = boo()', 5) == (None, None, None)
    assert get_brackets('foo() = boo()', 6) == (None, None, None)
    assert get_brackets('foo() = boo()', 11) == (None, None, None)
    assert get_brackets('foo() = boo()', 12) == ('(', 12, 13)

def test_quotes_matcher():
    assert get_brackets(r'foo(")(\")")', 4) == ('(', 4, 12)
    assert get_brackets(r'foo(")(\")")', 11) == ('(', 4, 12)

    assert get_brackets(r'foo(")(\")")', 5) == ('"', 5, 11)
    assert get_brackets(r'foo(")(\")")', 6) == ('"', 5, 11)
    assert get_brackets(r"foo(')(\')')", 10) == ("'", 5, 11)

def test_triple_quotes_matcher():
    assert get_brackets(r'foo("""()""")', 4) == ('(', 4, 13)
    assert get_brackets(r'foo("""()""")', 7) == ('"""', 7, 12)
    assert get_brackets(r"foo('''()''')", 9) == ("'''", 7, 12)

def test_close_quote():
    assert find_closing_quote_pos("'", "sss '' ddd '", 5) == 6
    