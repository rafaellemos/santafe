#!/usr/bin/env python3
"""Gera lançador verificável para os dois pacotes 2.0.3 já produzidos."""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
hashes = {name: hashlib.sha256((dist / name).read_bytes()).hexdigest()
          for name in ("santafe-2.0.3.tar.gz", "santafe-2.0.3.zip")}
checks = "\n".join(f"printf '%s  %s\\n' '{digest}' \"$PACOTES/{name}\" | sha256sum -c -"
                   for name, digest in hashes.items())
launcher = '''#!/usr/bin/env bash
set -Eeuo pipefail
PACOTES="$(cd -- "$(dirname -- "$0")" && pwd)"
''' + checks + '''
TRABALHO="$(mktemp -d /tmp/santafe-fechamento-2.0.3.XXXXXXXX)"
# Recusa caminhos perigosos e links antes de extrair o pacote conferido.
python3 - "$PACOTES/santafe-2.0.3.tar.gz" <<'PY'
import sys, tarfile
from pathlib import PurePosixPath
with tarfile.open(sys.argv[1]) as archive:
    for item in archive.getmembers():
        path = PurePosixPath(item.name)
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'santafe-2.0.3' or not (item.isfile() or item.isdir()):
            raise SystemExit('Membro inseguro: ' + item.name)
PY
tar --no-same-owner -xzf "$PACOTES/santafe-2.0.3.tar.gz" -C "$TRABALHO"
export SANTAFE_PACOTES_FECHAMENTO="$PACOTES"
exec bash "$TRABALHO/santafe-2.0.3/operação/publicar-fechamento-2.0.3.sh" "${1:-publicar}"
'''
target = dist / "publicar-fechamento-santafe-2.0.3.sh"
target.write_text(launcher, encoding="utf-8")
target.chmod(0o755)
print(target)
