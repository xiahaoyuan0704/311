from pathlib import Path
import tempfile
import unittest
import zipfile

from gim_desktop.model import FamDocument, load_gim_package


class GimPackageTests(unittest.TestCase):
    def test_parse_fam_properties(self) -> None:
        text = """[设计参数]\nVoltageLevel=电压等级=10\n电网工程标识系统编码=电网工程标识系统编码=30ATD01GL1015\n"""
        fam = FamDocument.parse(text)
        self.assertEqual(fam.sections[0].name, "设计参数")
        self.assertEqual(fam.sections[0].properties[0].key, "VoltageLevel")
        self.assertEqual(fam.sections[0].properties[0].label, "电压等级")
        self.assertEqual(fam.sections[0].properties[0].value, "10")

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
            self.assertIn("MOD/node.mod", names)

    def test_load_from_gim_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gim = Path(tmp) / "sample.gim"
            with zipfile.ZipFile(gim, "w") as zf:
                zf.writestr("PHM/a.phm", "k=v=1")
            pkg = load_gim_package(gim)
            self.assertEqual(pkg.read_text("PHM/a.phm"), "k=v=1")


if __name__ == "__main__":
    unittest.main()
