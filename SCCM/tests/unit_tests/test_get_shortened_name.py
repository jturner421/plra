from bin.convert_to_excel import get_shortened_name
import pytest
@pytest.mark.parametrize("name, expected", [("Romelo Bob Russel Booker", "Romelo B Russel"),
                                            ("Sovereignty Joseph Helmueller Sovereign", "S Helmueller")])
def test_shortened_name_with_four_parts(name, expected):
    result = get_shortened_name(name)
    assert result == expected, f"Expected {expected} but got {result}"



def test_shortened_name_with_three_parts():
    result = get_shortened_name("Jonathan Dwayne Smith")
    assert result == "Jonathan D Smith", "Expected 'John D. Smith' but got {}".format(result)


def test_shortened_name_with_two_parts():
    result = get_shortened_name("John Doe")
    assert result == "John Doe", "Expected 'John Doe' but got {}".format(result)


def test_shortened_name_with_hyphenation():
    result = get_shortened_name("Helson Pabon-Gonzalez")
    assert result == "Helson P-Gonzalez", "Expected 'Helson P.-Gonzalez' but got {}".format(result)


def test_shortened_name_with_single_word():
    result = get_shortened_name("John")
    assert result == "John", "Expected 'John' but got {}".format(result)



