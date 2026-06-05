from cummand.generator import generate_code, validate_code, COLORS, ADJECTIVES, ANIMALS, NOUNS


def test_word_list_sizes():
    assert len(COLORS) == 100, f"Expected 100 colors, got {len(COLORS)}"
    assert len(ADJECTIVES) == 100, f"Expected 100 adjectives, got {len(ADJECTIVES)}"
    assert len(ANIMALS) == 100, f"Expected 100 animals, got {len(ANIMALS)}"
    assert len(NOUNS) == 100, f"Expected 100 nouns, got {len(NOUNS)}"


def test_generate_code_format():
    for _ in range(100):
        code = generate_code()
        parts = code.split("-")
        assert len(parts) == 4, f"Expected 4 parts, got {len(parts)}: {code}"
        color, adj, animal, noun = parts
        assert color in COLORS, f"Unknown color: {color}"
        assert adj in ADJECTIVES, f"Unknown adjective: {adj}"
        assert animal in ANIMALS, f"Unknown animal: {animal}"
        assert noun in NOUNS, f"Unknown noun: {noun}"


def test_generate_code_unique():
    codes = {generate_code() for _ in range(1000)}
    assert len(codes) > 900, f"Too many duplicates: {len(codes)} unique out of 1000"


def test_validate_code_valid():
    code = "crimson-swift-falcon-river"
    assert validate_code(code)


def test_validate_code_invalid():
    assert not validate_code("not-a-real-code")
    assert not validate_code("too-many-parts-here-now-yeah")
    assert not validate_code("")
