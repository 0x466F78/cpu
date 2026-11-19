lli r1, 0x00
lhi r1, 0x40       ; r1 = 0x4000 (Alamat Layar TTY)

lli r2, 0x01
lhi r2, 0x40       ; r2 = 0x4001 (Status Keyboard)

lli r3, 0x02
lhi r3, 0x40       ; r3 = 0x4002 (Data Keyboard)

loop:
lw  r6, (r2)
bz  r6, -1         ; Tunggu sampai ada tombol yang ditekan

lw  r6, (r3)
sw  r6, (r1)       ; Ambil karakter dan langsung cetak ke TTY

bz  r0, -4         ; Ulangi loop dari atas
