from pathlib import Path
import tempfile
import unittest

from gim_desktop.model import flatten_layers, load_gim, save_gim


class GimModelTests(unittest.TestCase):
    def test_load_and_flatten(self) -> None:
        doc = load_gim("sample.gim")
        self.assertEqual(doc.canvas_width, 960)
        self.assertEqual(doc.canvas_height, 540)
        self.assertEqual([layer.id for layer in flatten_layers(doc.layers)], ["bg-01", "group-01", "text-01"])

    def test_round_trip_save(self) -> None:
        doc = load_gim("sample.gim")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.gim"
            save_gim(out, doc)
            loaded = load_gim(out)
        self.assertEqual(loaded.to_dict(), doc.to_dict())


if __name__ == "__main__":
    unittest.main()
