from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import MUTATION_ROLES
from content_factory_api.modules.models import User, WorkflowPreset
from content_factory_api.modules.schemas import (
    WorkflowPresetCreateRequest,
    WorkflowPresetListResponse,
    WorkflowPresetRead,
)
from content_factory_api.modules.services import commit_or_409, get_by_id_or_404, write_audit_log
from content_factory_pipeline.providers import (
    ProviderContractError,
    WorkflowPresetContract,
    build_provider_registry,
)

router = APIRouter(prefix="/api/workflow-presets", tags=["workflows"])
provider_registry = build_provider_registry()


@router.post("", response_model=WorkflowPresetRead, status_code=status.HTTP_201_CREATED)
def create_workflow_preset(
    request: WorkflowPresetCreateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowPreset:
    contract = WorkflowPresetContract(
        workflow_provider=request.workflow_provider.value,
        voice_provider=request.voice_provider.value,
        packaging_provider=request.packaging_provider.value,
        workflow_definition=request.workflow_definition,
        input_mapping={
            key: binding.model_dump(mode="json")
            for key, binding in request.input_mapping.items()
        },
        output_mapping={
            key: binding.model_dump(mode="json")
            for key, binding in request.output_mapping.items()
        },
    )
    try:
        provider_registry.validate_workflow_preset(contract)
    except ProviderContractError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    current_version = db_session.scalar(
        select(func.max(WorkflowPreset.version)).where(WorkflowPreset.key == request.key)
    )
    workflow_preset = WorkflowPreset(
        key=request.key,
        version=(current_version or 0) + 1,
        name=request.name,
        description=request.description,
        workflow_provider=request.workflow_provider.value,
        voice_provider=request.voice_provider.value,
        packaging_provider=request.packaging_provider.value,
        workflow_definition=request.workflow_definition,
        input_mapping=contract.input_mapping,
        output_mapping=contract.output_mapping,
        created_by_user_id=current_user.id,
    )
    db_session.add(workflow_preset)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="workflow_preset.created",
        entity_type="workflow_preset",
        entity_id=workflow_preset.id,
        payload={"key": workflow_preset.key, "version": workflow_preset.version},
    )
    commit_or_409(db_session, "Workflow preset could not be created")
    return workflow_preset


@router.get("", response_model=WorkflowPresetListResponse)
def list_workflow_presets(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowPresetListResponse:
    workflow_presets = list(
        db_session.scalars(
            select(WorkflowPreset).order_by(
                WorkflowPreset.key.asc(),
                WorkflowPreset.version.desc(),
                WorkflowPreset.created_at.desc(),
            )
        )
    )
    return WorkflowPresetListResponse(
        items=[
            WorkflowPresetRead.model_validate(workflow_preset)
            for workflow_preset in workflow_presets
        ]
    )


@router.get("/{workflow_preset_id}", response_model=WorkflowPresetRead)
def get_workflow_preset(
    workflow_preset_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowPreset:
    return get_by_id_or_404(db_session, WorkflowPreset, workflow_preset_id, "Workflow preset")
