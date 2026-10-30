"""Check the published feed with the frozen client in an isolated, silent profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.version import APP_VERSION


def main():
	profile = ROOT / "data/temp" / ("update-feed-" + str(time.time_ns()))
	(profile / "config").mkdir(parents=True)
	(profile / "config/config.json").write_text(json.dumps({
		"sounds": {"enabled": False},
		"updates": {"check_on_startup": True},
		"general": {"anunciar_arranque": False, "iniciar_en_bandeja": True},
	}), encoding="utf-8")
	exe = ROOT / "build" / ("VixClient-" + APP_VERSION) / "VixClient.exe"
	process = subprocess.Popen([str(exe)], env={**os.environ, "APP_DATA_DIR": str(profile)})
	try:
		end = time.monotonic() + 35
		while time.monotonic() < end:
			logs = "\n".join(p.read_text(encoding="utf-8") for p in (profile / "logs").glob("sesion*.log"))
			if "Firma del manifiesto verificada" in logs and "No hay versión nueva" in logs:
				assert "ERROR" not in logs and "CRITICAL" not in logs
				print("FROZEN CLIENT: LIVE GITHUB MANIFEST SIGNATURE VERIFIED; CURRENT VERSION RECOGNIZED")
				return
			if process.poll() is not None:
				raise RuntimeError("El cliente de prueba se cerró antes de verificar el manifiesto.")
			time.sleep(.2)
		raise RuntimeError("No se confirmó la firma del manifiesto publicado; consulte " + str(profile / "logs"))
	finally:
		# Only the process created by THIS test, using a separate, disposable profile.
		if process.poll() is None:
			process.terminate()
		process.wait(timeout=10)


if __name__ == "__main__":
	main()
