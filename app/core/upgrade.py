"""Copia datos de la versión anterior sin modificarla ni copiar un perfil en uso."""
import ctypes
from ctypes import wintypes
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import re

from app.core import paths
from app.core.version import APP_VERSION

log = logging.getLogger(__name__)


def process_alive(pid):
	if not sys.platform.startswith("win"):
		return False
	api = ctypes.WinDLL("kernel32", use_last_error=True)
	api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
	api.OpenProcess.restype = wintypes.HANDLE
	api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
	api.GetExitCodeProcess.restype = wintypes.BOOL
	api.CloseHandle.argtypes = [wintypes.HANDLE]
	api.CloseHandle.restype = wintypes.BOOL
	process = api.OpenProcess(0x1000, False, pid)
	if not process:
		return ctypes.get_last_error() == 5
	try:
		code = wintypes.DWORD()
		return not api.GetExitCodeProcess(process, ctypes.byref(code)) or code.value == 259
	finally:
		api.CloseHandle(process)


def copy_previous_data(previous: Path, current: Path):
	old_profile = previous / "sessions"
	new_profile = current / "sessions"
	if old_profile.exists() and not new_profile.exists():
		metadata = previous / "temp/instancia/instancia.json"
		try:
			pid = int(json.loads(metadata.read_text(encoding="utf-8")).get("pid", 0)) if metadata.exists() else 0
		except (OSError, ValueError, TypeError):
			pid = 0
		if pid and process_alive(pid):
			raise RuntimeError("Para conservar su sesión de ViX, cierre la versión anterior y vuelva a abrir esta actualización.")
		staging = current / "sessions-upgrade"
		shutil.copytree(old_profile, staging, dirs_exist_ok=True, ignore=shutil.ignore_patterns("Cache", "Code Cache", "GPUCache", "Crashpad", "ShaderCache", "GrShaderCache"))
		os.replace(staging, new_profile)
	old_config = previous / "config/config.json"
	new_config = current / "config/config.json"
	if old_config.is_file() and not new_config.exists():
		new_config.parent.mkdir(parents=True, exist_ok=True)
		staging = new_config.with_suffix(".upgrade")
		shutil.copy2(old_config, staging)
		os.replace(staging, new_config)


def import_previous_version():
	if not paths.CONGELADA or os.environ.get(paths.VARIABLE_DATA):
		return
	base = paths.ruta_base()
	current_version = tuple(map(int, APP_VERSION.split(".")))
	candidates = []
	for folder in base.parent.glob("VixClient-*"):
		match = re.fullmatch(r"VixClient-(\d+)\.(\d+)\.(\d+)", folder.name)
		if match:
			version = tuple(map(int, match.groups()))
			if version < current_version:
				candidates.append((version, folder / "data"))
	for _, previous in sorted(candidates, reverse=True):
		if ((previous / "sessions").exists() or (previous / "config/config.json").is_file()) and previous.resolve() != paths.ruta_datos().resolve():
			copy_previous_data(previous, paths.ruta_datos())
			break
