"""Patient profile routes."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.memory_factory import MemoryFactory


# Semantic memory instance
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Get or create semantic memory instance."""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = MemoryFactory.create_semantic({"db_path": "./data/db/patient_profiles.db"})
    return _semantic_memory


router = APIRouter(tags=["patients"])


@router.get("/{patient_id}")
async def get_patient(patient_id: str) -> dict:
    """Get patient profile.

    Args:
        patient_id: Patient identifier.

    Returns:
        Patient profile data.

    Raises:
        HTTPException: If patient not found.
    """
    memory = get_semantic_memory()
    profile = memory.get(patient_id)

    if profile is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {"patient_id": patient_id, **profile}


@router.put("/{patient_id}")
async def upsert_patient(patient_id: str, data: dict) -> dict:
    """Create or update patient profile.

    Args:
        patient_id: Patient identifier.
        data: Patient profile data.

    Returns:
        Updated patient profile.
    """
    memory = get_semantic_memory()
    memory.upsert(patient_id, data)

    return {"patient_id": patient_id, **data}


@router.delete("/{patient_id}")
async def delete_patient(patient_id: str) -> dict:
    """Delete patient profile.

    Args:
        patient_id: Patient identifier.

    Returns:
        Success message.

    Raises:
        HTTPException: If patient not found.
    """
    memory = get_semantic_memory()
    profile = memory.get(patient_id)

    if profile is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    memory.delete(patient_id)

    return {"message": "Patient deleted"}


@router.get("")
async def list_patients(limit: int = 100) -> List[dict]:
    """List all patients (simplified listing).

    Note: SemanticMemory doesn't support listing all patients.
    This endpoint is a placeholder that returns an empty list.
    For full listing, use episodic memory for patient history.

    Args:
        limit: Maximum number of patients to return.

    Returns:
        Empty list (listing not implemented).
    """
    return []
