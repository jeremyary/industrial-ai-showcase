# This project was developed with assistance from AI tools.
"""Modality config for nvidia/PhysicalAI-Robotics-GR00T-Teleop-G1 dataset.

The UNITREE_G1 embodiment tag expects base_height_command and navigate_command
(simulation locomotion data), but the Teleop-G1 dataset is real teleoperation
with direct 43-DOF joint positions. This config matches the dataset's actual
modality structure: left_leg, right_leg, waist, left_arm, left_hand,
right_arm, right_hand.
"""

from gr00t.data.embodiment_tags import EmbodimentTag
from gr00t.data.types import (
    ActionConfig,
    ActionFormat,
    ActionRepresentation,
    ActionType,
    ModalityConfig,
)

G1_TELEOP_MODALITY_CONFIG = {
    "video": ModalityConfig(
        delta_indices=[0],
        modality_keys=["rs_view"],
    ),
    "state": ModalityConfig(
        delta_indices=[0],
        modality_keys=[
            "left_leg",
            "right_leg",
            "waist",
            "left_arm",
            "left_hand",
            "right_arm",
            "right_hand",
        ],
    ),
    "action": ModalityConfig(
        delta_indices=list(range(16)),
        modality_keys=[
            "left_leg",
            "right_leg",
            "waist",
            "left_arm",
            "left_hand",
            "right_arm",
            "right_hand",
        ],
        action_configs=[
            ActionConfig(rep=ActionRepresentation.ABSOLUTE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.ABSOLUTE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.ABSOLUTE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.RELATIVE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.ABSOLUTE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.RELATIVE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
            ActionConfig(rep=ActionRepresentation.ABSOLUTE, type=ActionType.NON_EEF, format=ActionFormat.DEFAULT),
        ],
    ),
    "language": ModalityConfig(
        delta_indices=[0],
        modality_keys=["annotation.human.task_description"],
    ),
}


from gr00t.configs.data.embodiment_configs import register_modality_config

register_modality_config(G1_TELEOP_MODALITY_CONFIG, embodiment_tag=EmbodimentTag.NEW_EMBODIMENT)
