# CPU

Prosesor sederhana yang dirancang khusus untuk tujuan **edukasi** dan **pembelajaran arsitektur komputer**, dibangun menggunakan **simulator rangkaian digital**.

- **RISC 16-bit** — Kumpulan instruksi ringkas, seragam, dan berukuran jalur data 16-bit.
- **Harvard** — Pemisahan fisik antara memori instruksi (**ROM**) dan memori data (**RAM**) untuk menghindari konflik jalur akses.
- **Single-Cycle** — Setiap instruksi dieksekusi sepenuhnya dalam satu siklus *clock*.
- **8 Register** — Register internal **`r0`** hingga **`r7`** berukuran 16-bit untuk penyimpanan data sementara.

## 1. Format Instruksi

### 1.1 R-format (Register-to-Register)

Digunakan untuk operasi antar-register (aritmetika, logika, dan akses memori).

```text
Bit:   |  15 - 12  |  11 - 8  |  7 - 4  |  3 - 0  |
Field: |  OpCode   |   Dst    |    X    |    Y    |
```

- **`OpCode` (4-bit)** — Kode instruksi.
- **`Dst` (4-bit)** — Register tujuan hasil operasi.
- **`X`, `Y` (masing-masing 4-bit)** — Register sumber data.

### 1.2 I-format (Immediate)

Digunakan untuk konstanta langsung atau lompatan alamat (*branch*).

```text
Bit:   |  15 - 12  |  11 - 8  |      7 - 0      |
Field: |  OpCode   |   Dst    |       imm       |
```

- **`OpCode` (4-bit)** — Kode instruksi.
- **`Dst` (4-bit)** — Register tujuan / register yang diuji kondisinya.
- **`imm` (8-bit)** — Nilai konstanta atau *offset* alamat lompatan.

## 2. Instruction Set Architecture (ISA)

### 2.1 Aritmetika & Logika

| Hex | Biner | Instruksi | Operasi | Penjelasan |
| --- | --- | --- | --- | --- |
| **`0`** | `0000` | `add` | `Dst <- X + Y` | Penjumlahan nilai register `X` dan `Y`. |
| **`1`** | `0001` | `sub` | `Dst <- X - Y` | Pengurangan nilai `X` dikurangi `Y`. |
| **`2`** | `0010` | `mul` | `Dst <- X * Y` | Perkalian nilai `X` dan `Y`. |
| **`3`** | `0011` | `div` | `Dst <- X / Y` | Pembagian bilangan bulat `X` oleh `Y`. |
| **`7`** | `0111` | `rem` | `Dst <- X % Y` | Sisa hasil bagi (modulo) `X` oleh `Y`. |
| **`A`** | `1010` | `andn` | `Dst <- X AND ¬Y` | Operasi *bitwise* `X` AND kebalikan dari `Y`. |
| **`B`** | `1011` | `xor` | `Dst <- X XOR Y` | Operasi *bitwise* Exclusive-OR. |

### 2.2 Memori & Immediate

| Hex | Biner | Instruksi | Tipe | Operasi | Penjelasan |
| --- | --- | --- | --- | --- | --- |
| **`5`** | `0101` | `sw` | R | `Y -> [X]` | Simpan isi register `Y` ke alamat memori `X`. |
| **`6`** | `0110` | `lw` | R | `Dst <- [X]` | Muat data dari memori `X` ke register `Dst`. |
| **`8`** | `1000` | `lhi` | I | `Dst[15:8] <- imm` | Isi 8-bit atas register `Dst` dengan `imm`. |
| **`9`** | `1001` | `lli` | I | `Dst <- imm` | Isi register `Dst` dengan `imm` (*sign-extended*). |

### 2.3 Control Flow (Percabangan & Lompatan)

| Hex | Biner | Instruksi | Tipe | Operasi | Penjelasan |
| --- | --- | --- | --- | --- | --- |
| **`4`** | `0100` | `jalr` | R | `PC <- X+Y; Dst <- PC+1` | Lompat ke `X+Y`, simpan alamat kembali ke `Dst`. |
| **`D`** | `1101` | `bnz` | I | `if Dst != 0, PC <- PC+imm` | Lompat jika `Dst` tidak sama dengan nol. |
| **`E`** | `1110` | `bz` | I | `if Dst == 0, PC <- PC+imm` | Lompat jika `Dst` bernilai nol. |
| **`F`** | `1111` | `bltz` | I | `if Dst < 0, PC <- PC+imm` | Lompat jika `Dst` bernilai negatif. |

> **Catatan:** Kode **`C`** (`1100`) dibiarkan kosong (*unused*) untuk ekstensi instruksi kustom.

## 3. Sinyal Kontrol

| Hex | Instruksi | ArithCode | Xsel | Ysel | Pcsel | ImmExt | SrcSel | Dsel | MemW | MemR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`0-3`** | `add` – `div` | `0.OpCode[1:0]` | `X` | `Y` | `0` | `-` | `0` | `Dst` | `0` | `0` |
| **`4`** | `jalr` | `0.OpCode[1:0]` | `X` | `Y` | `10` | `-` | `11` | `Dst` | `0` | `0` |
| **`5`** | `sw` | `-` | `X` | `Y` | `0` | `-` | `-` | `0` | `1` | `0` |
| **`6`** | `lw` | `-` | `-` | `Y` | `0` | `-` | `1` | `Dst` | `0` | `1` |
| **`7`** | `rem` | `1.OpCode[1:0]` | `X` | `Y` | `0` | `-` | `0` | `Dst` | `0` | `0` |
| **`8`** | `lhi` | `0.OpCode[1:0]` | `Dst` | `0` | `0` | `0` | `10` | `Dst` | `0` | `0` |
| **`9`** | `lli` | `-` | `-` | `-` | `0` | `1` | `10` | `Dst` | `0` | `0` |
| **`A`** | `andn` | `100` | `X` | `Y` | `0` | `-` | `0` | `Dst` | `0` | `0` |
| **`B`** | `xor` | `101` | `X` | `Y` | `0` | `-` | `0` | `Dst` | `0` | `0` |
| **`D`** | `bnz` | `-` | `Dst` | `0` | `~XeqY` | `-` | `-` | `0` | `0` | `0` |
| **`E`** | `bz` | `-` | `Dst` | `0` | `XeqY` | `-` | `-` | `0` | `0` | `0` |
| **`F`** | `bltz` | `-` | `Dst` | `0` | `XltY` | `-` | `-` | `0` | `0` | `0` |

## 4. Peta Memori (Memory Map)

| Rentang Alamat | Perangkat | Fungsi & Keterangan |
| --- | --- | --- |
| `0x0000` – `0x0FFF` | **ROM** | Menyimpan kode program utama (kapasitas 4K *words*). |
| `0x2000` – `0x2FFF` | **RAM** | Menyimpan data variabel sementara (kapasitas 4K *words*). |
| `0x4000` | **Layar (TTY)** | Menulis karakter ASCII akan menampilkan huruf di layar TTY. |
| `0x4001` | **Status Keyboard** | Bernilai selain `0` jika ada tombol ditekan dan siap dibaca. |
| `0x4002` | **Data Keyboard** | Kode ASCII tombol yang ditekan (membaca alamat ini membersihkan antrean). |

## 5. Tutorial Pemrograman

Contoh program sederhana untuk melakukan penjumlahan `3 + 6 = 9`, menyimpannya ke RAM, lalu menampilkannya ke layar TTY sebagai karakter ASCII.

### Kode Assembly (`demo/add.asm`)

```assembly
; 1. Operasi Aritmetika
lli r1, 3
lli r2, 6
add r3, r1, r2      ; r3 = 3 + 6 = 9

; 2. Simpan ke RAM (0x2000)
lli r4, 0x00
lhi r4, 0x20        ; r4 = 0x2000 (alamat RAM)
sw  r3, (r4)        ; RAM[0x2000] = r3

; 3. Baca dari RAM dan Konversi ke ASCII ('9' = 57 / 0x39)
lw  r5, (r4)        ; r5 = RAM[0x2000]
lli r6, 48          ; konstanta ASCII '0'
add r5, r5, r6      ; r5 = 9 + 48 = 57

; 4. Tampilkan ke Layar TTY (0x4000)
lli r7, 0x00
lhi r7, 0x40        ; r7 = 0x4000 (alamat TTY)
sw  r5, (r7)        ; cetak karakter ke layar

; 5. Hentikan Program (Halt Loop)
bz  r0, 0
```

## 6. Kompilasi

Jalankan skrip *assembler* dari direktori *root* proyek:

```bash
./build.sh <isi nama file>
./build.sh all
```

Hasil kompilasi akan disimpan di dalam folder `sw/demo/build/<nama_program>/`:

- **`.mem`** — Format `v2.0 raw` untuk ROM Logisim.
- **`.lst`** — Berkas *listing* instruksi dan alamat.
- **`cpu_memory.txt`** — Ringkasan peta memori & simbol.

### Utilitas

```bash
./build.sh test   # Menjalankan seluruh unit test
./build.sh tidy   # Membersihkan file sampah/cache Python
./build.sh clean  # Menghapus seluruh hasil build di sw/demo/build/
```

## 7. Simulasi

1. **Buka Rangkaian** — Jalankan aplikasi **Logisim-evolution**, lalu buka berkas `hw/cpu.circ`.
2. **Muat ROM** — Klik kanan pada komponen **`Program_ROM`**, pilih **Load Image...**, dan arahkan ke berkas `.mem` hasil kompilasi.
3. **Reset CPU** — Tekan `Ctrl + R` (`Cmd + R` di macOS) untuk mereset register dan *Program Counter* ke `0x0000`.
4. **Eksekusi**
   - **Manual (Step-by-step)** — Tekan `Ctrl + T` berulang kali untuk memicu satu detak *clock*.
   - **Otomatis** — Tekan `Ctrl + K` untuk menjalankan simulasi secara kontinu.