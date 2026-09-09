"""언어 모델 단계가 공유하는 백엔드·묶음·재시도 장치."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel

from common import log

BatchT = TypeVar("BatchT", bound=BaseModel)
ItemT = TypeVar("ItemT", bound=BaseModel)


def pick_backend(name: str) -> str:
    if name != "auto":
        return name
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "sdk"
    if shutil.which("claude"):
        return "cli"
    raise SystemExit("ANTHROPIC_API_KEY 도 없고 claude CLI 도 없다. 둘 중 하나가 필요하다.")


def call_sdk(
    prompt: str,
    *,
    system: str,
    batch_type: type[BatchT],
    model: str,
    effort: str | None,
) -> tuple[BatchT, str]:
    import anthropic

    kwargs = {}
    if effort:
        kwargs["output_config"] = {"effort": effort}
    resp = anthropic.Anthropic().messages.parse(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=batch_type,
        **kwargs,
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {resp.stop_details}")
    if resp.parsed_output is None:
        raise RuntimeError(f"no parsed output (stop_reason={resp.stop_reason})")
    return resp.parsed_output, resp.model


def call_cli(
    prompt: str,
    *,
    system: str,
    batch_type: type[BatchT],
    model: str | None,
    effort: str | None,
) -> tuple[BatchT, str]:
    cmd = [
        "claude", "-p", "--no-session-persistence", "--tools", "",
        "--system-prompt", system,
        "--output-format", "json",
        "--json-schema", json.dumps(batch_type.model_json_schema()),
    ]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    cmd.append(prompt)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr.strip()[:400]}")
    data = json.loads(proc.stdout)
    if data.get("is_error") or data.get("structured_output") is None:
        raise RuntimeError(f"claude error: {str(data.get('result'))[:400]}")
    used = [m for m in data.get("modelUsage", {}) if not m.startswith("claude-haiku")]
    label = used[0] if used else (model or "claude-code-default")
    return batch_type.model_validate(data["structured_output"]), label


def call_codex(
    prompt: str,
    *,
    system: str,
    batch_type: type[BatchT],
    model: str | None,
) -> tuple[BatchT, str]:
    """Codex CLI에 JSON 스키마를 맡기고 마지막 응답만 읽는다.

    Codex는 Claude의 ``--effort`` 인자를 쓰지 않는다. 스키마 파일과 마지막
    메시지는 임시 디렉터리에만 두고, 모델에는 읽기 전용 sandbox를 준다.
    """
    with tempfile.TemporaryDirectory(prefix="german-sentences-codex-") as tmp:
        temp = Path(tmp)
        schema = temp / "schema.json"
        output = temp / "output.json"
        schema.write_text(json.dumps(batch_type.model_json_schema()), encoding="utf-8")
        cmd = [
            "codex", "exec", "--ephemeral", "--sandbox", "read-only", "--color", "never",
            "--output-schema", str(schema), "--output-last-message", str(output),
        ]
        if model:
            cmd += ["--model", model]
        cmd.append(f"{system}\n\n{prompt}\n\nJSON 외에는 아무것도 출력하지 마라.")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            detail = (proc.stderr.strip() or proc.stdout.strip())[:400]
            raise RuntimeError(f"codex exit {proc.returncode}: {detail}")
        if not output.exists():
            raise RuntimeError("codex가 마지막 JSON 응답을 쓰지 않았다")
        return batch_type.model_validate_json(output.read_text(encoding="utf-8")), (model or "codex-default")


def run_chunks(
    entries: list[dict],
    *,
    label: str,
    system: str,
    build_prompt: Callable[[list[dict]], str],
    batch_type: type[BatchT],
    valid_item: Callable[[ItemT], bool],
    save: Callable[[list[ItemT], str], None],
    backend: str,
    model: str | None,
    sdk_model: str,
    effort: str | None,
    workers: int,
    chunk_size: int,
) -> tuple[int, int]:
    """항목을 병렬로 보내고 누락·실패 항목을 한 번 더 보낸다."""
    chunks = [entries[i:i + chunk_size] for i in range(0, len(entries), chunk_size)]

    def work(chunk: list[dict]) -> tuple[list[ItemT], list[dict], str]:
        prompt = build_prompt(chunk)
        if backend == "sdk":
            batch, used = call_sdk(
                prompt, system=system, batch_type=batch_type,
                model=model or sdk_model, effort=effort,
            )
        elif backend == "cli":
            batch, used = call_cli(
                prompt, system=system, batch_type=batch_type,
                model=model, effort=effort,
            )
        elif backend == "codex":
            batch, used = call_codex(
                prompt, system=system, batch_type=batch_type, model=model,
            )
        else:
            raise ValueError(f"unknown backend: {backend}")
        wanted = {entry["id"]: entry for entry in chunk}
        got_by_id = {}
        for item in batch.items:
            if item.id in wanted and item.id not in got_by_id and valid_item(item):
                got_by_id[item.id] = item
        got = list(got_by_id.values())
        got_ids = {item.id for item in got}
        missing = [entry for entry in chunk if entry["id"] not in got_ids]
        return got, missing, used

    retry: list[dict] = []
    n_ok = n_fail = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, chunk): (i, chunk) for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            i, chunk = futures[future]
            try:
                got, missing, used = future.result()
                save(got, used)
                retry.extend(missing)
                n_ok += 1
                suffix = f", {len(missing)} missing" if missing else ""
                log(f"  chunk {i + 1}/{len(chunks)} ok{suffix}")
            except Exception as exc:  # noqa: BLE001 — 다른 묶음은 계속하고 실패분만 재시도한다.
                retry.extend(chunk)
                n_fail += 1
                log(f"  chunk {i + 1}/{len(chunks)} FAILED: {exc}")

    # 같은 id가 비정상 응답과 실패 양쪽에서 들어와도 한 번만 재시도한다.
    retry = list({entry["id"]: entry for entry in retry}.values())
    if retry:
        log(f"  retrying {len(retry)} missing or failed ids once")
        for i in range(0, len(retry), chunk_size):
            part = retry[i:i + chunk_size]
            try:
                got, still, used = work(part)
                save(got, used)
                if still:
                    log(f"    still missing: {[entry['id'] for entry in still]}")
            except Exception as exc:  # noqa: BLE001 — 다시 실행하면 남은 id부터 이어진다.
                log(f"    retry FAILED: {exc}")
    log(f"{label}: chunks ok {n_ok}, failed {n_fail}")
    return n_ok, n_fail
