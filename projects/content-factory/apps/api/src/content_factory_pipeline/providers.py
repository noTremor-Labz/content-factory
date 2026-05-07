from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderContractError(ValueError):
    """Raised when a workflow preset references an invalid provider contract."""


@dataclass(frozen=True)
class WorkflowPresetContract:
    workflow_provider: str
    voice_provider: str
    packaging_provider: str
    workflow_definition: dict[str, object]
    input_mapping: dict[str, dict[str, object]]
    output_mapping: dict[str, dict[str, object]]


class WorkflowEngineProvider(ABC):
    name: str

    @abstractmethod
    def validate_contract(self, contract: WorkflowPresetContract) -> None:
        """Validate a workflow contract for this provider."""


class VoiceProvider(ABC):
    name: str

    @abstractmethod
    def validate_contract(self, contract: WorkflowPresetContract) -> None:
        """Validate any voice-related contract constraints."""


class PackagingProvider(ABC):
    name: str

    @abstractmethod
    def validate_contract(self, contract: WorkflowPresetContract) -> None:
        """Validate any packaging-related contract constraints."""


@dataclass(frozen=True)
class ProviderRegistry:
    workflow_engines: dict[str, WorkflowEngineProvider]
    voice_providers: dict[str, VoiceProvider]
    packaging_providers: dict[str, PackagingProvider]

    def validate_workflow_preset(self, contract: WorkflowPresetContract) -> None:
        workflow_engine = self.workflow_engines.get(contract.workflow_provider)
        if workflow_engine is None:
            raise ProviderContractError(
                f"Unknown workflow provider '{contract.workflow_provider}'",
            )

        voice_provider = self.voice_providers.get(contract.voice_provider)
        if voice_provider is None:
            raise ProviderContractError(
                f"Unknown voice provider '{contract.voice_provider}'",
            )

        packaging_provider = self.packaging_providers.get(contract.packaging_provider)
        if packaging_provider is None:
            raise ProviderContractError(
                f"Unknown packaging provider '{contract.packaging_provider}'",
            )

        workflow_engine.validate_contract(contract)
        voice_provider.validate_contract(contract)
        packaging_provider.validate_contract(contract)


@dataclass(frozen=True)
class ComfyUIWorkflowEngineProvider(WorkflowEngineProvider):
    name: str = "comfyui"

    def validate_contract(self, contract: WorkflowPresetContract) -> None:
        nodes = contract.workflow_definition.get("nodes")
        if not isinstance(nodes, dict) or not nodes:
            raise ProviderContractError(
                "ComfyUI workflow_definition must contain a non-empty 'nodes' object",
            )


@dataclass(frozen=True)
class NoopVoiceProvider(VoiceProvider):
    name: str = "none"

    def validate_contract(self, contract: WorkflowPresetContract) -> None:
        if not contract.input_mapping:
            raise ProviderContractError("Workflow preset input_mapping must not be empty")


@dataclass(frozen=True)
class FfmpegPackagingProvider(PackagingProvider):
    name: str = "ffmpeg"

    def validate_contract(self, contract: WorkflowPresetContract) -> None:
        if not contract.output_mapping:
            raise ProviderContractError("Workflow preset output_mapping must not be empty")


def build_provider_registry() -> ProviderRegistry:
    return ProviderRegistry(
        workflow_engines={"comfyui": ComfyUIWorkflowEngineProvider()},
        voice_providers={"none": NoopVoiceProvider()},
        packaging_providers={"ffmpeg": FfmpegPackagingProvider()},
    )
