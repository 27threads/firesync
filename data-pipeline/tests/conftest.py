import sys
from pathlib import Path

# os módulos do pipeline (pipeline.py, agregar.py, job_nrt.py) ficam na pasta acima
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
