from pathlib import Path
import tempfile
import unittest
import zipfile

from gim_desktop.model import (
    can_preview_as_text,
    decode_bytes_auto,
    load_gim_package,
    parse_obj_vertices_edges,
    parse_property_document,
    parse_property_from_bytes,
)


class GimPackageTests(unittest.TestCase):
    def test_parse_property_for_all_property_files(self) -> None:
        text = """[设计参数]\nVoltageLevel=电压等级=10\n电网工程标识系统编码=电网工程标识系统编码=30ATD01GL1015\n"""
        for ext in [".fam", ".cbm", ".dev", ".phm", ".gim"]:
            doc = parse_property_document(f"a{ext}", text)
            self.assertIsNotNone(doc)
            assert doc is not None
            self.assertEqual(doc.sections[0].name, "设计参数")
            self.assertEqual(doc.sections[0].properties[0].key, "VoltageLevel")

    def test_non_zip_gim_fallback_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gim = Path(tmp) / "raw.gim"
            gim.write_text("[设计参数]\nA=A=1\n", encoding="utf-8")
            pkg = load_gim_package(gim)
            self.assertIn("raw.gim", pkg.file_paths())

    def test_gbk_binary_property_extract(self) -> None:
        text = "[设计参数]\nVoltageLevel=电压等级=10\n"
        data = text.encode("gb18030")
        doc = parse_property_from_bytes("a.bin", data)
        self.assertIsNotNone(doc)
        assert doc is not None
        self.assertEqual(doc.sections[0].properties[0].value, "10")

    def test_load_from_directory_and_export_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "example_gim"
            (root / "DEV").mkdir(parents=True)
            (root / "DEV" / "node.fam").write_text("[设计参数]\nA=B=1\n", encoding="utf-8")
            out = Path(tmp) / "out.gim"
            pkg = load_gim_package(root)
            pkg.save_as_gim_zip(out)
            with zipfile.ZipFile(out, "r") as zf:
                self.assertIn("DEV/node.fam", zf.namelist())

    def test_obj_parse_for_render(self) -> None:
        obj = """v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n"""
        verts, edges = parse_obj_vertices_edges(obj)
        self.assertEqual(len(verts), 4)
        self.assertGreaterEqual(len(edges), 4)

    def test_text_preview_detection(self) -> None:
        self.assertTrue(can_preview_as_text("a.dev", b"A=B=1"))
        self.assertFalse(can_preview_as_text("a.bin", b"\x00\x01\x02\x03"))

    def test_decode_bytes_auto(self) -> None:
        raw = "电压等级=10".encode("gb18030")
        self.assertIn("电压等级", decode_bytes_auto(raw))


if __name__ == "__main__":
    unittest.main()
