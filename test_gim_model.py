from pathlib import Path
import tempfile
import unittest
import zipfile

from gim_desktop.model import (
    PropertyDocument,
    can_preview_as_text,
    load_gim_package,
    parse_obj_vertices_edges,
    parse_property_document,
)


class GimPackageTests(unittest.TestCase):
    def test_parse_property_for_all_property_files(self) -> None:
        text = """[设计参数]\nVoltageLevel=电压等级=10\n电网工程标识系统编码=电网工程标识系统编码=30ATD01GL1015\n"""
        for ext in [".fam", ".cbm", ".dev", ".phm"]:
            doc = parse_property_document(f"a{ext}", text)
            self.assertIsNotNone(doc)
            assert doc is not None
            self.assertEqual(doc.sections[0].name, "设计参数")
            self.assertEqual(doc.sections[0].properties[0].key, "VoltageLevel")

    def test_load_from_directory_and_export_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "example_gim"
            (root / "DEV").mkdir(parents=True)
            (root / "DEV" / "node.fam").write_text("[设计参数]\nA=B=1\n", encoding="utf-8")
            (root / "MOD").mkdir(parents=True)
            (root / "MOD" / "node.mod").write_bytes(b"binary")

            pkg = load_gim_package(root)
            self.assertIn("DEV/node.fam", pkg.file_paths())
            self.assertIn("MOD/node.mod", pkg.file_paths())

            out = Path(tmp) / "out.gim"
            pkg.save_as_gim_zip(out)
            with zipfile.ZipFile(out, "r") as zf:
                names = set(zf.namelist())
            self.assertIn("DEV/node.fam", names)

    def test_non_zip_gim_fallback_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gim = Path(tmp) / "raw.gim"
            gim.write_text("not a zip", encoding="utf-8")
            pkg = load_gim_package(gim)
            self.assertIn("raw.gim", pkg.file_paths())
            self.assertEqual(pkg.read_text("raw.gim"), "not a zip")

    def test_obj_parse_for_render(self) -> None:
        obj = """v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n"""
        verts, edges = parse_obj_vertices_edges(obj)
        self.assertEqual(len(verts), 4)
        self.assertGreaterEqual(len(edges), 4)

    def test_text_preview_detection(self) -> None:
        self.assertTrue(can_preview_as_text("a.dev", b"A=B=1"))
        self.assertFalse(can_preview_as_text("a.bin", b"\x00\x01\x02\x03"))


if __name__ == "__main__":
    unittest.main()
