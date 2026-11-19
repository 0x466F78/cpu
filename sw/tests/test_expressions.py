from .helpers import AsmTestCase


class TestExpressions(AsmTestCase):
    def test_nilai_ekspresi(self):
        kasus = [
            ("1 + 2 * 3", 7),
            ("(1 + 2) * 3", 9),
            ("10 / 3", 3),
            ("10 % 3", 1),
            ("-7 / 2", 0xFFFD),          # dibulatkan ke nol: -3
            ("1 << 4", 16),
            ("0xFF >> 4", 0x0F),
            ("0xFF & 0x0F", 0x0F),
            ("0xF0 | 0x0F", 0xFF),
            ("0xFF ^ 0x0F", 0xF0),
            ("~0", 0xFFFF),
            ("-1", 0xFFFF),
            ("0b101", 5),
            ("0o17", 15),
            ("0x1F", 31),
            ("'A'", 65),
            ("'A' + 1", 66),
            ("0x1234[15:8]", 0x12),
            ("0x1234[7:0]", 0x34),
        ]
        for ekspresi, hasil in kasus:
            with self.subTest(ekspresi):
                self.assertEqual(self.words(f".word {ekspresi}"), [hasil])

    def test_pembagian_dengan_nol(self):
        self.assert_error(".word 1 / 0", "pembagian dengan nol")


class TestSymbols(AsmTestCase):
    def test_equ(self):
        source = """
        .equ SIZE, 4
        .word SIZE * 2
        """
        self.assertEqual(self.words(source), [8])

    def test_label_boleh_dipakai_sebelum_didefinisikan(self):
        source = """
        .word end
        end: nop
        """
        self.assertEqual(self.words(source), [1, 0])

    def test_tanda_dolar_adalah_alamat_saat_ini(self):
        source = """
        nop
        .word $
        """
        self.assertEqual(self.words(source), [0, 1])

    def test_simbol_tak_terdefinisi(self):
        self.assert_error("b nowhere", "tak terdefinisi")

    def test_label_duplikat(self):
        self.assert_error("x: nop\nx: nop\n", "label duplikat")

    def test_label_tidak_boleh_bernama_register(self):
        self.assert_error("r1: nop\n", "dipesan")
