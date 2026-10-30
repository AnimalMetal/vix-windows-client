"""Release bundles are signed and contain resources, never runtime data or keys."""
import json
import zipfile

import pytest

from app.services import actualizador
from tools import publicar_version as release
from tools.firmar_version import generar


@pytest.fixture
def bundle(tmp_path, monkeypatch):
	key = tmp_path / "keys/sign.key"
	public = generar(key)
	monkeypatch.setattr(actualizador, "CLAVES_PUBLICAS_ED25519", (public,))
	folder = tmp_path / "build"
	folder.mkdir()
	(folder / "VixClient.exe").write_bytes(b"test executable")
	(folder / "data/docs").mkdir(parents=True)
	(folder / "data/docs/manual.md").write_text("manual")
	return folder, tmp_path / "dist", key, public


def test_signed_release_round_trip(bundle):
	folder, output, key, public = bundle
	archive, manifest, notes = release.empaquetar(folder, output, key)
	data = json.loads(manifest.read_text(encoding="utf-8"))
	actualizador.verificar_firma(data, (public,))
	assert data["url"].endswith(archive.name) and "/releases/download/v" in data["url"]
	with zipfile.ZipFile(archive) as zipped:
		assert set(zipped.namelist()) == {"VixClient/VixClient.exe", "VixClient/data/docs/manual.md"}
	assert notes


@pytest.mark.parametrize("filename", ["data/config/config.json", "data/sessions/cookie", "secret.key", "secret.pem"])
def test_dirty_build_is_not_published(bundle, filename):
	folder, output, key, public = bundle
	path = folder / filename
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text("private")
	with pytest.raises(ValueError):
		release.empaquetar(folder, output, key)
	assert not list(output.glob("*.zip"))
