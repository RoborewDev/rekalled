import uuid

import pytest

from app.models import Card
from app.study.memory import memory_of


def test_a_draft_has_no_memory_to_read() -> None:
    # A plain Card, not an assert: the check must survive `python -O`.
    draft = Card(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        deck_id=uuid.uuid4(),
        question="Q",
        answer="A",
    )

    with pytest.raises(ValueError, match="drafts have no memory"):
        _ = memory_of(draft)
