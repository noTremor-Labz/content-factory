import pytest

from content_factory_pipeline.providers import (
    ProviderContractError,
    WorkflowPresetContract,
)
from content_factory_worker.providers import get_provider_registry


def test_provider_registry_exposes_default_adapters() -> None:
    registry = get_provider_registry()
    contract = WorkflowPresetContract(
        workflow_provider="comfyui",
        voice_provider="none",
        packaging_provider="ffmpeg",
        workflow_definition={
            "nodes": {
                "script_prompt": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "render a compliant host short"},
                }
            }
        },
        input_mapping={
            "script_text": {"source_type": "content_item", "source_field": "script"},
        },
        output_mapping={
            "video_file": {"artifact_type": "video", "output_path": "outputs.primary.video"},
        },
    )

    registry.validate_workflow_preset(contract)


def test_provider_registry_rejects_invalid_comfyui_definition() -> None:
    registry = get_provider_registry()
    contract = WorkflowPresetContract(
        workflow_provider="comfyui",
        voice_provider="none",
        packaging_provider="ffmpeg",
        workflow_definition={"graph": []},
        input_mapping={
            "script_text": {"source_type": "content_item", "source_field": "script"},
        },
        output_mapping={
            "video_file": {"artifact_type": "video", "output_path": "outputs.primary.video"},
        },
    )

    with pytest.raises(ProviderContractError, match="nodes"):
        registry.validate_workflow_preset(contract)
