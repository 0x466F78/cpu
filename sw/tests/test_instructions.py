from .helpers import AsmTestCase


class TestRFormat(AsmTestCase):
    def test_aritmetika_dan_logika(self):
        kasus = {
            "add  r3, r1, r2": 0x0312,
            "sub  r1, r2, r3": 0x1123,
            "mul  r4, r5, r6": 0x2456,
            "div  r1, r2, r3": 0x3123,
            "jalr r1, r2, r3": 0x4123,
            "rem  r1, r2, r3": 0x7123,
            "andn r1, r2, r3": 0xA123,
            "xor  r1, r2, r3": 0xB123,
        }
        for baris, hasil in kasus.items():
            with self.subTest(baris):
                self.assertEqual(self.words(baris), [hasil])

    def test_sw_dan_lw(self):
        self.assertEqual(self.words("sw r3, (r4)"), [0x5043])
        self.assertEqual(self.words("lw r5, (r4)"), [0x6540])

    def test_mnemonic_dan_register_tidak_peka_huruf_besar(self):
        self.assertEqual(self.words("ADD R1, R2, R3"), [0x0123])


class TestImmediate(AsmTestCase):
    def test_lli_dan_lhi(self):
        self.assertEqual(self.words("lli r1, 3"), [0x9103])
        self.assertEqual(self.words("lhi r4, 0x20"), [0x8420])

    def test_lli_negatif(self):
        self.assertEqual(self.words("lli r1, -1"), [0x91FF])

    def test_lli_hex_boleh_sampai_ff(self):
        self.assertEqual(self.words("lli r1, 0xC8"), [0x91C8])

    def test_lli_desimal_128_sampai_255_ditolak(self):
        self.assert_error("lli r1, 200", "sign-extend")

    def test_saran_li_menyebut_register(self):
        self.assert_error("lli r1, 200", "li r1, 200")

    def test_lli_di_luar_jangkauan(self):
        self.assert_error("lli r1, 300", "di luar jangkauan")


class TestPseudo(AsmTestCase):
    def test_nop(self):
        self.assertEqual(self.words("nop"), [0x0000])

    def test_mov(self):
        self.assertEqual(self.words("mov r2, r1"), [0x0210])

    def test_li_menjadi_dua_kata(self):
        self.assertEqual(self.words("li r1, 0x1234"), [0x9134, 0x8112])

    def test_li_negatif_sama_dengan_ffff(self):
        self.assertEqual(self.words("li r1, -1"), [0x91FF, 0x81FF])
        self.assertEqual(self.words("li r1, 65535"), [0x91FF, 0x81FF])

    def test_li_di_luar_16_bit(self):
        self.assert_error("li r1, 70000", "di luar jangkauan")


class TestBranch(AsmTestCase):
    def test_offset_angka_dipakai_apa_adanya(self):
        self.assertEqual(self.words("bz   r1, 3"), [0xE103])
        self.assertEqual(self.words("bnz  r2, -2"), [0xD2FE])
        self.assertEqual(self.words("bltz r3, -2"), [0xF3FE])

    def test_label_mundur(self):
        source = """
        start: nop
               b start
        """
        self.assertEqual(self.words(source), [0x0000, 0xE0FF])

    def test_label_maju(self):
        source = """
               bnz r2, end
               nop
        end:   nop
        """
        self.assertEqual(self.words(source), [0xD202, 0x0000, 0x0000])

    def test_li_memakai_dua_alamat(self):
        # li makan 2 kata, jadi label sesudahnya bergeser satu
        source = """
               li r1, 0x1234
        target: nop
               b target
        """
        self.assertEqual(self.words(source), [0x9134, 0x8112, 0x0000, 0xE0FF])

    def test_offset_terlalu_jauh(self):
        self.assert_error("bz r1, 200", "offset cabang")


class TestWarnings(AsmTestCase):
    def test_menulis_ke_r0_memberi_peringatan(self):
        result = self.assemble_ok("add r0, r1, r2")
        self.assertEqual(len(result.warnings), 1)

    def test_jalr_ke_r0_tanpa_peringatan(self):
        result = self.assemble_ok("jalr r0, r1, r2")
        self.assertEqual(len(result.warnings), 0)
