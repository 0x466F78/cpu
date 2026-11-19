import unittest

from sw.asm import Assembler


class AsmTestCase(unittest.TestCase):
    """Dasar semua test assembler: merakit source kecil langsung dari string."""

    def assemble_ok(self, source):
        result = Assembler().assemble(source)
        if not result.ok:
            pesan = [d.message for d in result.diagnostics.errors]
            self.fail(f"assembler gagal: {pesan}")
        return result

    def words(self, source):
        return self.assemble_ok(source).words

    def assert_error(self, source, potongan_pesan):
        """Source harus gagal, dan salah satu pesan error memuat potongan_pesan."""
        result = Assembler().assemble(source)
        self.assertFalse(result.ok, "seharusnya error, tapi berhasil dirakit")
        pesan = [d.message for d in result.diagnostics.errors]
        self.assertTrue(
            any(potongan_pesan in p for p in pesan),
            f"'{potongan_pesan}' tidak ada di pesan error: {pesan}",
        )
