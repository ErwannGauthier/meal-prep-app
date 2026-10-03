import zipfile

from pipeline.sources.notion import extract_shortcodes, read_export

TEXT = """
Nom,Lien
Poulet satay,https://www.instagram.com/reel/C9xYz12AbC/?igsh=MWQ1ZGUxMzBkMg==
Nachos,https://instagram.com/p/DAbc_-123/
Doublon,https://www.instagram.com/reel/C9xYz12AbC/
Pluriel,https://www.instagram.com/reels/DXyz98765/
Avec pseudo,https://www.instagram.com/bourr_/reel/DPseudo111/
Autre site,https://www.youtube.com/watch?v=abc
Profil seul,https://www.instagram.com/bourr_/
"""


def test_extracts_all_reel_forms_once_in_order():
    assert extract_shortcodes(TEXT) == ["C9xYz12AbC", "DAbc_-123", "DXyz98765", "DPseudo111"]


def test_reads_a_single_csv_file(tmp_path):
    f = tmp_path / "export.csv"
    f.write_text(TEXT, encoding="utf-8")
    assert read_export(f)[0] == "C9xYz12AbC"


def test_reads_a_directory_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.md").write_text("[r](https://www.instagram.com/reel/AAAAA1/)")
    (tmp_path / "sub" / "b.md").write_text("https://www.instagram.com/reel/BBBBB2/")
    (tmp_path / "image.png").write_bytes(b"\x89PNG https://www.instagram.com/reel/IGNORE/")
    assert read_export(tmp_path) == ["AAAAA1", "BBBBB2"]


def test_reads_a_notion_zip(tmp_path):
    z = tmp_path / "export.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("Meal preps 123/page.md", "https://www.instagram.com/reel/ZIPPED1/")
        zf.writestr("Meal preps 123/table.csv", "x,https://www.instagram.com/p/ZIPPED2/")
    assert read_export(z) == ["ZIPPED1", "ZIPPED2"]
