lli r1, 0x00
lhi r1, 0x40

lli r2, 0x48       ; 'H'
sw  r2, (r1)

lli r2, 0x69       ; 'i'
sw  r2, (r1)

bz  r0, 0
