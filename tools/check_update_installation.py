"""Exercise the real compiled updater on a separate copy; never touches a user's app."""
from pathlib import Path
import json
import os
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.version import APP_VERSION
from app.services import actualizador


def main():
	# Unique target, checked inside the workspace before creating or copying files.
	area = (ROOT / "data/temp" / ("update-install-" + str(time.time_ns()))).resolve()
	assert area.is_relative_to((ROOT / "data/temp").resolve())
	installation = area / "ViX Client"
	candidates = [p for p in (ROOT / "build").glob("VixClient-*") if p.is_dir() and actualizador.comparar_versiones(p.name.removeprefix("VixClient-"), APP_VERSION) < 0]
	previous = max(candidates, key=lambda p: actualizador.clave_version(p.name.removeprefix("VixClient-")))
	previous_version = previous.name.removeprefix("VixClient-")
	def ignore_personal_data(folder, names):
		return [n for n in names if n not in actualizador.DATA_ACTUALIZABLE] if Path(folder) == previous / "data" else []
	shutil.copytree(previous, installation, ignore=ignore_personal_data)
	os.environ["APP_DATA_DIR"] = str(installation / "data")
	from app.core.config import Configuracion
	settings = Configuracion()
	settings.establecer("updates.check_on_startup", False)
	settings.establecer("sounds.enabled", False)
	settings.establecer("general.anunciar_arranque", False)
	settings.establecer("vix.favorites", [{"title": "Preserved favorite"}])
	settings.guardar()
	session = installation / "data/sessions/test-session.bin"
	session.parent.mkdir(parents=True, exist_ok=True)
	session.write_bytes(b"preserved session bytes")
	config = actualizador.Configuracion(previous_version, installation, comando=[str(installation / "VixClient.exe"), "--comprobar-actualizacion"], permitir_desde_codigo=True, pid_a_esperar=2147483647)
	manifest = json.loads((ROOT / "dist" / APP_VERSION / "version.json").read_text(encoding="utf-8"))
	actualizador.verificar_firma(manifest, config.claves_publicas)
	info = actualizador._info_desde_manifiesto(config, manifest, config.url_manifiesto)
	archive = ROOT / "dist" / APP_VERSION / info.archivo
	# Verify a private copy because failed verification deletes the rejected archive.
	config.carpeta_trabajo.mkdir(parents=True)
	local = config.carpeta_trabajo / info.archivo
	shutil.copy2(archive, local)
	actualizador.verificar_paquete(local, info)
	actualizador.extraer_seguro(local, config.carpeta_trabajo / "nueva", config)
	script = actualizador.preparar_sustitucion(config, info)
	process = actualizador.lanzar_sustitucion(script)
	process.wait(timeout=100)
	result = dict(line.split("=", 1) for line in config.archivo_resultado.read_text(encoding="utf-8").splitlines())
	assert result["estado"] == "correcta", config.registro_script.read_text(errors="replace")
	# The new compiled app exits after its real main-loop/health check.
	time.sleep(5)
	assert actualizador.leer_estado(config)["version_confirmada"] == APP_VERSION
	assert session.read_bytes() == b"preserved session bytes"
	assert Configuracion().obtener("vix.favorites") == [{"title": "Preserved favorite"}]
	assert Configuracion().obtener("updates.check_on_startup") is False
	logs = "\n".join(p.read_text(encoding="utf-8") for p in (installation / "data/logs").glob("sesion*.log"))
	assert "Marcador de salud escrito" in logs and "Cierre normal" in logs
	assert "CRITICAL" not in logs and "ERROR" not in logs
	print("COMPILED IN-PLACE UPDATE OK:", result["anterior"], "->", result["version"])
	print("SETTINGS, FAVORITES AND SESSION PRESERVED; HEALTH CONFIRMED; NORMAL EXIT")
	print("Isolated installation:", installation)


if __name__ == "__main__":
	main()
