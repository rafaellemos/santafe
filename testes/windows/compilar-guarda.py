from pathlib import Path
import subprocess, sys
from recursos import compile_resource
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
resource=compile_resource(out/'recursos-guarda','instalador-guarda.dll','Santafé instalador',dll=True)
subprocess.run(['gcc','-std=gnu99','-O2','-Wall','-Wextra','-shared',str(Path(__file__).with_name('instalador-guarda.c')),str(resource),'-lmsi','-o',str(out/'instalador-guarda.dll')],check=True)
