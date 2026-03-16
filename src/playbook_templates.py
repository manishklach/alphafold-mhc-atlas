from __future__ import annotations

from dataclasses import dataclass
from .playbook_schema import Playbook


@dataclass(frozen=True)
class PlaybookTemplate:
    template_id: str
    label: str
    description: str
    default_config: dict[str, object]


def load_playbook_templates() -> list[PlaybookTemplate]:
    # In Phase 17, we reuse the playbooks as templates
    from .playbook_schema import load_playbooks
    playbooks = load_playbooks()
    return [
        PlaybookTemplate(
            template_id=p.playbook_id,
            label=p.display_name,
            description=p.description,
            default_config=p.to_dict()
        ) for p in playbooks
    ]
