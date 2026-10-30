"""Genera campanitas originales suaves; no descarga recursos ni voces."""
from array import array
import math
from pathlib import Path
import wave

NOTES = {
	"startup": [(523.25, 0), (659.25, .12), (783.99, .24)],
	"open": [(659.25, 0), (783.99, .08)],
	"back": [(659.25, 0), (523.25, .08)],
	"top": [(880, 0), (1046.5, .07)],
	"bottom": [(523.25, 0), (392, .08)],
	"ready": [(783.99, 0)],
	"error": [(392, 0), (349.23, .09)],
}


def generate(folder):
	folder.mkdir(parents=True, exist_ok=True)
	for name, notes in NOTES.items():
		rate = 22050
		duration = max(start for _, start in notes) + .38
		samples = array("h")
		for i in range(int(duration * rate)):
			time = i / rate
			value = 0
			for frequency, start in notes:
				t = time - start
				if t >= 0:
					envelope = min(1, t / .018) * math.exp(-t * 12)
					value += envelope * (math.sin(2 * math.pi * frequency * t) + .13 * math.sin(4 * math.pi * frequency * t))
			value *= min(1, max(0, (duration - time) / .03))
			samples.append(round(32767 * .16 * value))
		with wave.open(str(folder / (name + ".wav")), "wb") as output:
			output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
			output.writeframes(samples.tobytes())


if __name__ == "__main__":
	generate(Path(__file__).resolve().parents[1] / "data/sounds")
