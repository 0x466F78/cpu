from .helpers import AsmTestCase


class TestData(AsmTestCase):
    def test_word(self):
        self.assertEqual(self.words(".word 1, 2, 0xFFFF"), [1, 2, 0xFFFF])

    def test_string_diakhiri_nol(self):
        self.assertEqual(self.words('.string "Hi"'), [72, 105, 0])
        self.assertEqual(self.words('.asciz "A"'), [65, 0])

    def test_ascii_tanpa_nol(self):
        self.assertEqual(self.words('.ascii "Hi"'), [72, 105])

    def test_escape_di_string(self):
        self.assertEqual(self.words('.ascii "a\\n"'), [97, 10])

    def test_space_dan_zero(self):
        self.assertEqual(self.words(".space 3"), [0, 0, 0])
        self.assertEqual(self.words(".zero 2"), [0, 0])


class TestLayout(AsmTestCase):
    def test_org_mengisi_celah_dengan_nol(self):
        source = """
        lli r1, 1
        .org 3
        lli r2, 2
        """
        self.assertEqual(self.words(source), [0x9101, 0, 0, 0x9202])

    def test_org_tidak_boleh_mundur(self):
        self.assert_error("nop\nnop\n.org 1\n", "mundur")

    def test_org_di_luar_rom(self):
        self.assert_error(".org 0x1000", "di luar ROM")

    def test_align(self):
        source = """
        lli r1, 1
        .align 2
        lli r2, 2
        """
        self.assertEqual(self.words(source), [0x9101, 0, 0, 0, 0x9202])

    def test_label_tidak_boleh_menempel_pada_org(self):
        self.assert_error("x: .org 4\n", "tidak boleh menempel")

    def test_program_tepat_sebesar_rom(self):
        self.assertEqual(len(self.words(".space 4096")), 4096)

    def test_program_melebihi_rom(self):
        self.assert_error(".space 4097", "melebihi ROM")


class TestSyntaxErrors(AsmTestCase):
    def test_mnemonic_tidak_dikenal(self):
        self.assert_error("foo r1\n", "mnemonic tidak dikenal")

    def test_direktif_tidak_dikenal(self):
        self.assert_error(".foo\n", "direktif tidak dikenal")

    def test_register_di_luar_r0_sampai_r7(self):
        self.assert_error("add r1, r2, r8\n", "bukan register")

    def test_koma_hilang(self):
        self.assert_error("add r1 r2, r3\n", "diharapkan ','")

    def test_string_tidak_ditutup(self):
        self.assert_error('.string "abc\n', "tidak ditutup")

    def test_string_tidak_ditutup_di_akhir_berkas(self):
        self.assert_error('.string "abc', "tidak ditutup")

    def test_komentar_diabaikan(self):
        source = """
        ; komentar penuh
        nop   # komentar di ujung baris
        """
        self.assertEqual(self.words(source), [0x0000])
