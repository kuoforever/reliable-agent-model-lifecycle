"""Build explicitly synthetic desktop fixtures; never capture a live desktop."""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    from PIL import Image, ImageDraw, ImageFont

    out = ROOT / "fixtures/local_gui_probe_v2"
    out.mkdir(exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    images = {}
    for name, title in [
        ("browser", "Chrome - Public briefing - SYNTHETIC TEST"),
        ("word", "Word - Brief.docx - SYNTHETIC TEST"),
        ("dialog", "Word - Save As - SYNTHETIC TEST"),
        ("relocated", "Word - Review.docx - SYNTHETIC TEST"),
    ]:
        image = Image.new("RGB", (1024, 640), "#e8ecf2")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1024, 40), fill="#203856")
        draw.text((18, 6), title, font=font, fill="white")
        draw.text(
            (20, 609),
            "Offline interface fixture | No real application or user data",
            font=small,
            fill="#465368",
        )
        images[name] = (image, draw)

    def box(name, bounds, label, fill="white"):
        draw = images[name][1]
        draw.rectangle(bounds, fill=fill, outline="#8291a8", width=2)
        draw.text((bounds[0] + 12, bounds[1] + 8), label, font=font, fill="#16283d")

    box("browser", [110, 54, 940, 96], "https://public.example.test/briefing")
    box("browser", [24, 135, 200, 182], "Search articles")
    box("browser", [245, 130, 975, 575], "Community Library Update")
    images["browser"][1].text(
        (270, 200),
        "Open Tuesday to Saturday, 10:00 to 18:00.\nThe reading room has 40 seats.\nThe workshop begins on 15 October.",
        font=font,
        fill="#253750",
        spacing=18,
    )
    box("browser", [28, 235, 195, 280], "Newsletter")
    box("word", [20, 55, 115, 100], "Save", "#d5e6ff")
    box("word", [145, 55, 260, 100], "Undo")
    box("word", [20, 145, 220, 190], "Search document")
    box("word", [280, 140, 935, 580], "Briefing summary")
    images["word"][1].text(
        (310, 215),
        "Library hours: 10:00 to 18:00.\nReading room: 40 seats.\nWorkshop: 15 October.",
        font=font,
        fill="#253750",
        spacing=18,
    )
    box("dialog", [165, 110, 865, 550], "Save As")
    box("dialog", [205, 200, 815, 247], "Folder: Documents / Demo")
    box("dialog", [205, 300, 815, 348], "File name: library-brief.docx")
    box("dialog", [555, 445, 670, 492], "Cancel")
    box("dialog", [705, 445, 820, 492], "Save", "#d5e6ff")
    box("relocated", [20, 55, 115, 100], "Save", "#d5e6ff")
    box("relocated", [700, 135, 980, 182], "Search document")
    box("relocated", [40, 140, 640, 580], "Briefing summary")
    images["relocated"][1].text(
        (70, 215),
        "Reviewed public information.\nThe report is ready for verification.",
        font=font,
        fill="#253750",
        spacing=18,
    )
    for name, (image, _) in images.items():
        path = out / (name + ".png")
        if path.exists():
            raise ValueError("fixture already exists")
        image.save(path)

    visual_specs = [
        (
            "browser-address",
            "browser",
            "Click the browser address bar.",
            [110, 54, 940, 96],
        ),
        (
            "browser-search",
            "browser",
            "Click Search articles in the left sidebar.",
            [24, 135, 200, 182],
        ),
        (
            "word-editor",
            "word",
            "Click inside the document page containing Briefing summary, away from the search field.",
            [280, 140, 935, 580],
        ),
        (
            "word-save",
            "word",
            "Click the Save button in the top toolbar.",
            [20, 55, 115, 100],
        ),
        (
            "dialog-save",
            "dialog",
            "Click Save to confirm this Save As dialog.",
            [705, 445, 820, 492],
        ),
        (
            "relocated-editor",
            "relocated",
            "Click inside the document page containing Briefing summary, away from the search field.",
            [40, 140, 640, 580],
        ),
        (
            "browser-absent",
            "browser",
            "Click the Delete account button. If it is absent, terminate with failure.",
            None,
        ),
        (
            "dialog-absent",
            "dialog",
            "Click the Print button. If it is absent, terminate with failure.",
            None,
        ),
    ]
    cases = [
        dict(
            id=key,
            group="visual",
            image=f"fixtures/local_gui_probe_v2/{img}.png",
            instruction=instruction,
            bbox=box,
            width=1024,
            height=640,
        )
        for key, img, instruction, box in visual_specs
    ]
    old = json.loads((ROOT / "fixtures/local_gui_executor_v1/cases.json").read_text())
    selected = [0, 2, 3, 5, 6, 7, 8, 9]
    for number, index in enumerate(selected):
        request = copy.deepcopy(old["cases"][index]["request"])
        request["request_id"] = f"probe-v2-control-{number}"
        request["target_scope"] = "10801"
        request["current_epoch"] = 57
        request["runtime_generation"] = 14
        obs = request["observation"]
        obs["scope"] = "10801"
        obs["epoch"] = 56 if index == 2 else 57
        obs["foreground_scope"] = "19901" if index == 7 else "10801"
        for c in obs["controls"]:
            c["ref"] = "ref_" + str(int(c["ref"][4:]) + 700)
        response = copy.deepcopy(old["cases"][index]["response"])
        response.update(request_id=request["request_id"], observation_epoch=57)
        if "ref" in response:
            response["ref"] = "ref_" + str(int(response["ref"][4:]) + 700)
        if index == 6:
            response = dict(
                request_id=request["request_id"], observation_epoch=57, action="stop"
            )
        cases.append(
            dict(
                id=request["request_id"],
                group="contract",
                request=request,
                expected=response,
            )
        )
    protocol = {
        "id": "FC-MVP-002-local-gui-executor-probe-v2",
        "candidates": {
            "gui-owl": {
                "model_id": "mPLUG/GUI-Owl-1.5-4B-Instruct",
                "revision": "3f061c2c562cc860c42bf32542a70e07a7ff4840",
            },
            "qwen": {
                "model_id": "Qwen/Qwen3-VL-4B-Instruct",
                "revision": "ebb281ec70b05090aa6165b016eac8ec08e71b17",
            },
        },
        "generation": {
            "max_new_tokens": 192,
            "do_sample": False,
            "seed": 17,
            "max_input_tokens": 4096,
            "max_time_seconds": 45,
        },
        "backend": {
            "dtype": "bfloat16",
            "attention": "sdpa",
            "batch_size": 1,
            "image_min_pixels": 65536,
            "image_max_pixels": 655360,
        },
        "limits": {
            "candidate_seconds": 900,
            "peak_allocated_bytes": 15000000000,
            "case_retries": 0,
        },
        "rubric": {
            "visual": "strict single tool_call; normalized click point inside pixel bbox, or exact failure termination for absent targets",
            "contract": "strict raw JSON and v1 compiler acceptance; exact response scored separately",
            "latency": "diagnostic only; synchronized generation seconds, no serving SLA",
            "decision": "screening only; do not declare live readiness from synthetic single-step success",
        },
        "cases": cases,
    }
    (ROOT / "configs/local_gui_executor_probe_v2.json").write_bytes(
        (json.dumps(protocol, ensure_ascii=False, indent=2) + "\n").encode()
    )


if __name__ == "__main__":
    main()
