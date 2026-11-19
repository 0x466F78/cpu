#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SW_DIR="$ROOT/sw"
DEMO_DIR="$SW_DIR/demo"
BUILD_DIR="$DEMO_DIR/build"

usage() {
  cat <<'EOF'
RISC16 assembler build helper

Usage:
  ./build.sh <program>    Compile sw/demo/<program>.asm
  ./build.sh all          Compile every .asm file in sw/demo/
  ./build.sh test         Run the complete unittest suite
  ./build.sh tidy         Remove only known temporary files and Python caches
  ./build.sh clean        Remove generated sw/demo/build/ outputs

Examples:
  ./build.sh add
  ./build.sh echo
  ./build.sh hi
  ./build.sh all
EOF
}

require_project() {
  if [[ ! -f "$SW_DIR/__main__.py" || ! -d "$SW_DIR/asm" || ! -d "$DEMO_DIR" ]]; then
    echo "ERROR: struktur proyek tidak lengkap di $ROOT" >&2
    exit 2
  fi
}

build_one() {
  local name="$1"
  local source="$DEMO_DIR/$name.asm"
  local destination="$BUILD_DIR/$name"
  local stage backup

  if [[ ! "$name" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "ERROR: nama program tidak valid: $name" >&2
    return 2
  fi
  if [[ ! -f "$source" ]]; then
    echo "ERROR: sumber tidak ditemukan: sw/demo/$name.asm" >&2
    return 2
  fi

  mkdir -p "$BUILD_DIR"
  stage="$(mktemp -d "$BUILD_DIR/.${name}.tmp.XXXXXX")"

  # Simpan ketiga artefak di staging directory agar build gagal tidak
  # meninggalkan keluaran setengah jadi atau merusak build sebelumnya.
  if ! (
    cd "$ROOT"
    python3 -m sw "sw/demo/$name.asm" \
      --output "$stage/$name.mem" \
      --listing "$stage/$name.lst" \
      --memory-map "$stage/cpu_memory.txt" \
      --quiet
  ); then
    rm -rf -- "$stage"
    echo "GAGAL: $name.asm; hasil sebelumnya (jika ada) tidak diubah." >&2
    return 1
  fi

  if [[ ! -s "$stage/$name.mem" || ! -f "$stage/$name.lst" || ! -f "$stage/cpu_memory.txt" ]]; then
    rm -rf -- "$stage"
    echo "ERROR: assembler tidak menghasilkan seluruh berkas keluaran untuk $name.asm" >&2
    return 1
  fi

  # Ganti folder hasil hanya setelah semua output baru berhasil dibuat.
  backup=""
  if [[ -e "$destination" ]]; then
    backup="$(mktemp -d "$BUILD_DIR/.${name}.old.XXXXXX")"
    rmdir -- "$backup"
    mv -- "$destination" "$backup"
  fi

  if mv -- "$stage" "$destination"; then
    [[ -z "$backup" ]] || rm -rf -- "$backup"
  else
    [[ -z "$backup" ]] || mv -- "$backup" "$destination"
    rm -rf -- "$stage"
    echo "ERROR: tidak dapat memasang hasil build $name." >&2
    return 1
  fi

  printf 'OK: %s.asm berhasil dirakit\n' "$name"
  printf '    %s\n' "${destination#"$ROOT"/}/$name.mem" \
                 "${destination#"$ROOT"/}/$name.lst" \
                 "${destination#"$ROOT"/}/cpu_memory.txt"
}

require_project

command="${1:-}"
case "$command" in
  "")
    usage
    exit 2
    ;;
  all)
    shopt -s nullglob
    sources=("$DEMO_DIR"/*.asm)
    if (( ${#sources[@]} == 0 )); then
      echo "Tidak ada berkas .asm di sw/demo/." >&2
      exit 1
    fi
    for source in "${sources[@]}"; do
      build_one "$(basename -- "$source" .asm)"
    done
    ;;
  test)
    cd "$ROOT"
    python3 -m unittest -v
    ;;
  tidy)
    find "$SW_DIR" -type d -name '__pycache__' -prune -exec rm -rf -- {} +
    find "$SW_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.py.bak' \) -delete
    rm -f -- "$ROOT/fix_sw_package_layout.py"
    echo "File backup dan cache Python yang dikenal sudah dibersihkan. Source, demo, test, dan hasil build tidak dihapus."
    ;;
  clean)
    rm -rf -- "$BUILD_DIR"
    echo "Hasil build di sw/demo/build/ sudah dihapus. Source ASM tetap aman."
    ;;
  *)
    if (( $# != 1 )); then
      echo "ERROR: berikan tepat satu nama program." >&2
      usage
      exit 2
    fi
    build_one "$command"
    ;;
esac
