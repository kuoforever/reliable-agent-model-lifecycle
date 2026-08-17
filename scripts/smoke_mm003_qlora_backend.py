"""Exercise the local QLoRA backend without using MM-002 evaluation data."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


SEED = 20260817
SYSTEM_PROMPT = "Compatibility smoke only. Never execute GUI actions."
USER_PROMPT = (
    "This blank synthetic image is unrelated to every evaluation case. "
    "Reply with exactly the word TRAINABLE."
)
TARGET = "TRAINABLE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-snapshot", type=Path, required=True)
    args = parser.parse_args()

    snapshot = args.model_snapshot.resolve(strict=True)
    if not snapshot.is_dir():
        raise RuntimeError("model snapshot must be a directory")

    started = time.perf_counter()
    (
        bitsandbytes,
        torch,
        image_class,
        lora_config_class,
        task_type,
        get_peft_model,
        prepare_model_for_kbit_training,
        processor_class,
        model_class,
        quantization_config_class,
    ) = _load_dependencies()
    _seed_all(torch)
    torch.cuda.reset_peak_memory_stats()

    quantization_config = quantization_config_class(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    processor = processor_class.from_pretrained(
        snapshot,
        local_files_only=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1280 * 28 * 28,
        use_fast=False,
    )
    model = model_class.from_pretrained(
        snapshot,
        quantization_config=quantization_config,
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    model = get_peft_model(
        model,
        lora_config_class(
            task_type=task_type.CAUSAL_LM,
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
        ),
    )
    model.train()
    model.config.use_cache = False

    image = image_class.new("RGB", (448, 448), color=(245, 245, 245))
    prefix_messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": USER_PROMPT},
            ],
        },
    ]
    full_messages = [
        *prefix_messages,
        {"role": "assistant", "content": TARGET},
    ]
    prefix = _encode(
        processor,
        prefix_messages,
        image,
        add_generation_prompt=True,
    )
    batch = _encode(
        processor,
        full_messages,
        image,
        add_generation_prompt=False,
    )
    prefix_length = int(prefix.input_ids.shape[1])
    sequence_length = int(batch.input_ids.shape[1])
    if prefix_length >= sequence_length:
        raise RuntimeError("assistant target has no trainable tokens")
    if not torch.equal(prefix.input_ids[0], batch.input_ids[0, :prefix_length].cpu()):
        raise RuntimeError("multimodal prompt prefix differs from full example")

    labels = batch.input_ids.clone()
    labels[:, :prefix_length] = -100
    labels[batch.attention_mask == 0] = -100
    trainable_tokens = int(labels.ne(-100).sum().item())
    if trainable_tokens <= 0:
        raise RuntimeError("assistant target has no trainable tokens")

    cuda_batch = {key: value.to("cuda") for key, value in batch.items()}
    output = model(**cuda_batch, labels=labels.to("cuda"))
    loss = float(output.loss.detach().cpu().item())
    if not math.isfinite(loss):
        raise RuntimeError("loss is not finite")
    output.loss.backward()

    trainable_parameters = 0
    finite_gradient_parameters = 0
    nonzero_gradient_parameters = 0
    gradient_l2_squared = 0.0
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            continue
        trainable_parameters += parameter.numel()
        if parameter.grad is None:
            continue
        if not bool(torch.isfinite(parameter.grad).all().item()):
            raise RuntimeError(f"non-finite LoRA gradient: {name}")
        finite_gradient_parameters += parameter.numel()
        gradient_norm = float(parameter.grad.detach().float().norm().cpu().item())
        gradient_l2_squared += gradient_norm * gradient_norm
        if gradient_norm > 0.0:
            nonzero_gradient_parameters += parameter.numel()
    if trainable_parameters <= 0:
        raise RuntimeError("LoRA injection produced no trainable parameters")
    if finite_gradient_parameters <= 0 or nonzero_gradient_parameters <= 0:
        raise RuntimeError("backward produced no nonzero finite LoRA gradient")

    linear_4bit_modules = sum(
        isinstance(module, bitsandbytes.nn.Linear4bit) for module in model.modules()
    )
    if linear_4bit_modules <= 0:
        raise RuntimeError("model contains no bitsandbytes Linear4bit modules")

    result = {
        "adapter_saved": False,
        "bitsandbytes": importlib.metadata.version("bitsandbytes"),
        "compute_capability": ".".join(
            str(part) for part in torch.cuda.get_device_capability(0)
        ),
        "cuda": torch.version.cuda,
        "device": torch.cuda.get_device_name(0),
        "elapsed_seconds": time.perf_counter() - started,
        "finite_gradient_parameters": finite_gradient_parameters,
        "gradient_l2_norm": math.sqrt(gradient_l2_squared),
        "gradient_checkpointing": True,
        "linear_4bit_modules": linear_4bit_modules,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "lora_rank": 16,
        "loss": loss,
        "nonzero_gradient_parameters": nonzero_gradient_parameters,
        "peak_cuda_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_cuda_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        "peft": importlib.metadata.version("peft"),
        "prefix_length": prefix_length,
        "quantization": {
            "compute_dtype": "bfloat16",
            "double_quant": True,
            "load_in_4bit": True,
            "type": "nf4",
        },
        "seed": SEED,
        "sequence_length": sequence_length,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
        "torch": torch.__version__,
        "trainable_parameters": trainable_parameters,
        "trainable_tokens": trainable_tokens,
        "transformers": importlib.metadata.version("transformers"),
        "valid": True,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def _encode(
    processor: Any,
    messages: list[dict[str, Any]],
    image: Any,
    *,
    add_generation_prompt: bool,
) -> Any:
    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
    )
    return processor(
        text=[text],
        images=[image],
        padding=True,
        return_tensors="pt",
    )


def _load_dependencies() -> tuple[Any, ...]:
    import bitsandbytes
    import torch
    from peft import (  # type: ignore[import-not-found]
        LoraConfig,
        TaskType,
        get_peft_model,
        prepare_model_for_kbit_training,
    )
    from PIL import Image
    from transformers import (  # type: ignore[import-untyped]
        AutoProcessor,
        BitsAndBytesConfig,
        Qwen2_5_VLForConditionalGeneration,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    return (
        bitsandbytes,
        torch,
        Image,
        LoraConfig,
        TaskType,
        get_peft_model,
        prepare_model_for_kbit_training,
        AutoProcessor,
        Qwen2_5_VLForConditionalGeneration,
        BitsAndBytesConfig,
    )


def _seed_all(torch: Any) -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


if __name__ == "__main__":
    raise SystemExit(main())
