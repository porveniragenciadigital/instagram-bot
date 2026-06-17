"""
Reads current_post.json, generates a caption with Claude,
and sends the post to Instagram via Make webhook.
"""
import json
import os
from pathlib import Path

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

BRAND_SYSTEM = """Eres el community manager de Porvenir Agencia Digital.
Fundadora: Teresa Rodriguez, Ingeniera de Software con Master en UX, Ciudad Real (Espana).
Servicios: Diseno Web & UX, IA & Automatizacion, Chatbots, Agentes de Voz (Ley 10/2025), Apps Moviles iOS/Android, Auditorias UX/WCAG, Formacion IA.

Voz de marca:
- Autoridad tecnica, no agencia generica
- Directa, sin rodeos, sin relleno
- Primera persona o imperativa
- Espanol de Espana
- Sin em dash (—)
- Usa 3-4 emojis distribuidos naturalmente en el texto
- El emoji va SIEMPRE al final de la frase, pegado a la ultima palabra con un espacio: "ultima palabra 🚀" — sin punto, coma ni ningun signo de puntuacion antes del emoji
- Formato correcto: "Reserva en el link de la bio 🚀" — Formato INCORRECTO: "Reserva en el link de la bio. 🚀" o "🚀 Reserva en el link"
- Nunca uses viñetas con punto (•) delante de emojis
- Nunca describas la web como "emocional"
- Los botones y CTAs van en primera persona o accion directa"""

CAPTION_PROMPT = """Genera un caption de Instagram para el siguiente post.

Tipo de post: {post_type}
Datos del post:
{data}

Formato de respuesta (respeta exactamente este formato):

CAPTION:
[80-150 palabras. Primera linea que engancha sin leerlo todo. Desarrolla el valor. Cierra con CTA concreta como "Agenda tu consultoria gratis en el link de la bio."]

HASHTAGS:
[25 hashtags. Mezcla grandes (#ia #diseno) con nicho (#agenciaCiudadReal #chatbotIA #leyIA). En una sola linea separados por espacios.]"""

POST_TYPE_LABELS = {
    "service_feature": "presentacion de servicio con caracteristicas",
    "hook_text": "post de enganche: problema -> solucion",
    "numbered_steps": "post de proceso paso a paso",
    "split_concept": "contraste entre dos conceptos",
}


def generate_caption(topic: dict) -> tuple[str, str]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    post_type = POST_TYPE_LABELS.get(topic["template"], topic["template"])
    prompt = CAPTION_PROMPT.format(
        post_type=post_type,
        data=json.dumps(topic["data"], ensure_ascii=False, indent=2),
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system=BRAND_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    parts = text.split("HASHTAGS:")
    caption = parts[0].replace("CAPTION:", "").strip()
    hashtags = parts[1].strip() if len(parts) > 1 else ""
    return caption, hashtags


CAPTION_FOOTER = "📲 porveniragenciadigital.com\n✉ teresa.rodriguez@porveniragenciadigital.com"


def send_to_make(image_url: str, caption: str, hashtags: str):
    webhook_url = os.environ["MAKE_WEBHOOK_URL"]
    full_caption = f"{caption}\n.\n{CAPTION_FOOTER}\n.\n.\n.\n{hashtags}"

    r = requests.post(
        webhook_url,
        json={"image_url": image_url, "caption": full_caption},
        timeout=30,
    )
    r.raise_for_status()
    print(f"Make webhook OK: {r.status_code} — {r.text}")


def main():
    current = json.loads((BASE_DIR / "current_post.json").read_text())
    repo = os.environ.get("GITHUB_REPOSITORY", "porveniragenciadigital/instagram-bot")
    image_path = current["image_path"]
    image_url = f"https://raw.githubusercontent.com/{repo}/main/{image_path}"
    print(f"Image URL: {image_url}")

    caption, hashtags = generate_caption(current["topic"])
    print(f"\nCaption preview:\n{caption[:120]}...\n")

    send_to_make(image_url, caption, hashtags)


if __name__ == "__main__":
    main()
