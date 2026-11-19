import contextlib
import io
import os
import tempfile
import unittest

from sw.asm import Assembler
from sw.asm.cli import main
from sw.asm.output import write_memfile

from .helpers import AsmTestCase

TUTORIAL_ASM = """
lli r1, 3
lli r2, 6
add r3, r1, r2

lli r4, 0x00
lhi r4, 0x20
sw  r3, (r4)

lw  r5, (r4)
lli r6, 48
add r5, r5, r6

lli r7, 0x00
lhi r7, 0x40
sw  r5, (r7)

bz  r0, 0
"""

TUTORIAL_WORDS = [
    0x9103, 0x9206, 0x0312, 0x9400, 0x8420, 0x5043, 0x6540,
    0x9630, 0x0556, 0x9700, 0x8740, 0x5075, 0xE000,
]


class TestTutorial(AsmTestCase):
    def test_kode_mesin_sama_dengan_readme(self):
        self.assertEqual(self.words(TUTORIAL_ASM), TUTORIAL_WORDS)

    def test_tutorial_tanpa_peringatan(self):
        self.assertEqual(self.assemble_ok(TUTORIAL_ASM).warnings, [])


class TestResult(AsmTestCase):
    def test_berhasil(self):
        result = self.assemble_ok("nop")
        self.assertTrue(result.ok)
        self.assertEqual(result.words, [0x0000])

    def test_gagal_tidak_punya_kata(self):
        result = Assembler().assemble("foo")
        self.assertFalse(result.ok)
        self.assertEqual(result.words, [])


class TestMemfile(unittest.TestCase):
    def tulis(self, words):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.mem")
            write_memfile(path, words)
            with open(path, encoding="utf-8") as f:
                return f.read()

    def test_format_logisim(self):
        self.assertEqual(self.tulis([0x9103, 0x0312]), "v2.0 raw\n9103 0312\n")

    def test_delapan_kata_per_baris(self):
        baris = self.tulis([1] * 10).splitlines()
        self.assertEqual(len(baris), 3)
        self.assertEqual(len(baris[1].split()), 8)
        self.assertEqual(len(baris[2].split()), 2)


class TestCli(unittest.TestCase):
    def jalankan(self, isi_asm):
        """Jalankan CLI di folder sementara. Return (kode_keluar, isi_.mem atau None)."""
        with tempfile.TemporaryDirectory() as folder:
            sumber = os.path.join(folder, "prog.asm")
            keluaran = os.path.join(folder, "prog.mem")
            with open(sumber, "w", encoding="utf-8") as f:
                f.write(isi_asm)
            with contextlib.redirect_stderr(io.StringIO()):
                kode = main([sumber, "-o", keluaran, "-q"])
            isi = None
            if os.path.exists(keluaran):
                with open(keluaran, encoding="utf-8") as f:
                    isi = f.read()
            return kode, isi

    def test_berhasil(self):
        kode, isi = self.jalankan("lli r1, 3\n")
        self.assertEqual(kode, 0)
        self.assertEqual(isi, "v2.0 raw\n9103\n")

    def test_gagal_tidak_menulis_berkas(self):
        kode, isi = self.jalankan("foo\n")
        self.assertEqual(kode, 1)
        self.assertIsNone(isi)

    def test_berkas_tidak_ada(self):
        with contextlib.redirect_stderr(io.StringIO()):
            kode = main(["/tidak/ada/prog.asm", "-q"])
        self.assertEqual(kode, 1)
