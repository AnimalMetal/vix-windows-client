"""Build, sign and publish a portable release. The signing key never leaves this PC.

python tools/publicar_version.py                 # tests, build, ZIP and signature
python tools/publicar_version.py --publicar      # also publish a GitHub Release
python tools/publicar_version.py --solo-paquete  # reuse a clean, verified build
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.version import APP_VERSION, ID_APLICACION
from app.services import actualizador
from tools.firmar_version import CLAVE_POR_DEFECTO, cargar_privada, clave_publica_hex, firmar, verificar

REPO = "AnimalMetal/vix-windows-client"
API = "https://api.github.com/repos/" + REPO


def notas_version(version=APP_VERSION):
	text = (ROOT / "data/docs/novedades.md").read_text(encoding="utf-8-sig")
	match = re.search(r"^## " + re.escape(version) + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
	if not match or not match[1].strip():
		raise ValueError("Faltan novedades para " + version)
	return match[1].strip()


def empaquetar(carpeta, salida, clave, version=APP_VERSION):
	carpeta, salida, clave = Path(carpeta), Path(salida), Path(clave)
	publica = clave_publica_hex(cargar_privada(clave))
	if publica not in actualizador.CLAVES_PUBLICAS_ED25519:
		raise ValueError("La clave de firma no coincide con la clave pública del cliente.")
	if not (carpeta / actualizador.EJECUTABLE).is_file():
		raise ValueError("Falta el ejecutable compilado.")
	archivos = []
	for ruta in sorted(carpeta.rglob("*")):
		if ruta.is_symlink() or ruta.is_junction():
			raise ValueError("La compilación contiene enlaces.")
		if not ruta.is_file():
			continue
		relativa = ruta.relative_to(carpeta)
		if relativa.parts[0].lower() == "data" and (len(relativa.parts) < 3 or relativa.parts[1].lower() not in actualizador.DATA_ACTUALIZABLE):
			raise ValueError("La compilación contiene datos personales: " + str(relativa))
		if ruta.suffix.lower() in {".key", ".pem", ".pfx", ".p12", ".log"} or any(p in {".git", "claves", "__pycache__"} for p in relativa.parts):
			raise ValueError("Archivo no distribuible: " + str(relativa))
		archivos.append((ruta, relativa))
	salida.mkdir(parents=True, exist_ok=True)
	paquete = salida / f"{ID_APLICACION}-{version}-windows-x64.zip"
	with zipfile.ZipFile(paquete, "w", zipfile.ZIP_DEFLATED) as archivo:
		for ruta, relativa in archivos:
			archivo.write(ruta, ID_APLICACION + "/" + relativa.as_posix())
	notas = notas_version(version)
	manifiesto = salida / "version.json"
	manifiesto.write_text(json.dumps({
		"app": ID_APLICACION, "version": version, "file": paquete.name,
		"url": f"https://github.com/{REPO}/releases/download/v{version}/{paquete.name}",
		"size": paquete.stat().st_size, "sha256": actualizador.sha256_de(paquete),
		"date": datetime.now(timezone.utc).date().isoformat(), "novedades": notas,
	}, ensure_ascii=False, indent=2), encoding="utf-8")
	firmar(clave, manifiesto)
	problemas = verificar(manifiesto, [publica])
	if problemas:
		raise ValueError("; ".join(problemas))
	return paquete, manifiesto, notas


def credencial_github():
	"""Reuse Git's credential manager without displaying or storing the token."""
	token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
	if token:
		return token
	resultado = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True, check=True)
	datos = dict(line.split("=", 1) for line in resultado.stdout.splitlines() if "=" in line)
	if not datos.get("password"):
		raise ValueError("No hay credenciales de GitHub. Inicie sesión con Git Credential Manager.")
	return datos["password"]


def peticion(url, token, datos=None, metodo="GET", tipo="application/json"):
	contenido = datos if isinstance(datos, bytes) else json.dumps(datos).encode() if datos is not None else None
	solicitud = urllib.request.Request(url, data=contenido, method=metodo, headers={
		"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
		"Content-Type": tipo, "User-Agent": "VixClient-release",
		"X-GitHub-Api-Version": "2022-11-28",
	})
	with urllib.request.urlopen(solicitud, timeout=180) as respuesta:
		return json.load(respuesta)


def publicar(paquete, manifiesto, notas, commit):
	token = credencial_github()
	# A draft keeps the old feed available until BOTH verified assets are uploaded.
	release = peticion(API + "/releases", token, {
		"tag_name": "v" + APP_VERSION, "target_commitish": commit,
		"name": "ViX Client " + APP_VERSION, "body": notas,
		"draft": True, "prerelease": False,
	}, "POST")
	for archivo in (paquete, manifiesto):
		url = release["upload_url"].split("{", 1)[0] + "?name=" + urllib.parse.quote(archivo.name)
		peticion(url, token, archivo.read_bytes(), "POST", "application/zip" if archivo.suffix == ".zip" else "application/json")
	release = peticion(release["url"], token, {"draft": False, "make_latest": "true"}, "PATCH")
	return release["html_url"]


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--publicar", action="store_true")
	parser.add_argument("--solo-paquete", action="store_true")
	parser.add_argument("--clave", type=Path, default=CLAVE_POR_DEFECTO)
	args = parser.parse_args()
	carpeta = ROOT / "build" / (ID_APLICACION + "-" + APP_VERSION)
	if not args.solo_paquete:
		if carpeta.exists():
			raise ValueError("Ya existe la compilación. Use una versión nueva o --solo-paquete tras verificarla; no se borran compilaciones utilizadas.")
		subprocess.run([sys.executable, "-m", "pytest"], cwd=ROOT, check=True)
		subprocess.run([sys.executable, "setup_cx.py", "build"], cwd=ROOT, check=True)
	paquete, manifiesto, notas = empaquetar(carpeta, ROOT / "dist" / APP_VERSION, args.clave)
	print("Paquete verificado:", paquete)
	if args.publicar:
		if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
			raise ValueError("Guarde y suba los cambios antes de publicar.")
		commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
		remoto = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/main"], cwd=ROOT, text=True).split()[0]
		if remoto != commit:
			raise ValueError("La versión local debe estar subida a main antes de publicar.")
		print("Publicado:", publicar(paquete, manifiesto, notas, commit))


if __name__ == "__main__":
	try:
		main()
	except (ValueError, OSError, subprocess.SubprocessError, urllib.error.URLError) as error:
		print("No se pudo preparar/publicar la versión:", str(error), file=sys.stderr)
		sys.exit(1)
