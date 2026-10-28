#!/usr/bin/env python3
"""Extensão restrita para configurações DNS; nenhuma chave privada permitida."""
from pathlib import Path
import tempfile, unittest
from transacao import Transacao, Recusa

class Tests(unittest.TestCase):
    def test_destinos_dns(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();root.chmod(0o700)
            (root/'.replica-iba3').write_text('REPLICA_ISOLADA_SEM_PRODUCAO\n')
            tx=Transacao(root,None,None)
            for folder in ('santafe-dns','santafe-nomes'):
                self.assertEqual(tx.target('etc/'+folder+'/zonas.fé'),root/'etc'/folder/'zonas.fé')
                self.assertEqual(tx.target('etc/'+folder+'/dns.env'),root/'etc'/folder/'dns.env')
                for name in ('chave.pem','banco.sql','certificado.crt'):
                    with self.assertRaises(Recusa):tx.target('etc/'+folder+'/'+name)
            for name in ('etc/letsencrypt/chave.pem','etc/systemd/system/teste.service','var/lib/correio/a','usr/local/lib/mariadb/a'):
                with self.assertRaises(Recusa):tx.target(name)

if __name__=='__main__':unittest.main(verbosity=2)
