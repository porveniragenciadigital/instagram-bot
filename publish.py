"""
Reads current_post.json, generates a caption with Claude,
and publishes the post to Instagram via the Graph API.
"""
import json
import os
import time
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
- Maximo 2-3 emojis si encajan naturalmente
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


def publish_to_instagram(image_url: str, caption: str, hashtags: str):
    account_id = os.environ["INSTAGRAM_ACCOUNT_ID"]
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    full_caption = f"{caption}\n.\n.\n.\n{hashtags}"

    # Step 1: create media container
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{account_id}/media",
        data={"image_url": image_url, "caption": full_caption, "access_token": token},
        timeout=30,
    )
    r.raise_for_status()
    creation_id = r.json()["id"]
    print(f"Container: {creation_id}")

    # Step 2: wait for Instagram to process the image
    for attempt in range(6):
        time.sleep(5)
        status_r = requests.get(
            f"https://graph.facebook.com/v19.0/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        )
        status = status_r.json().get("status_code", "")
        print(f"  status: {status}")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram container error: {status_r.json()}")
    else:
        raise TimeoutError("Container did not reach FINISHED state in time")

    # Step 3: publish
    p = requests.post(
        f"https://graph.facebook.com/v19.0/{account_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    p.raise_for_status()
    post_id = p.json()["id"]
    print(f"Published! Post ID: {post_id}")
    return post_id


def main():
    current = json.loads((BASE_DIR / "current_post.json").read_text())
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    image_path = current["image_path"]
    image_url = f"https://raw.githubusercontent.com/{repo}/main/{image_path}"
    print(f"Image URL: {image_url}")

    caption, hashtags = generate_caption(current["topic"])
    print(f"\nCaption preview:\n{caption[:120]}...\n")

    publish_to_instagram(image_url, caption, hashtags)


if __name__ == "__main__":
    main()
