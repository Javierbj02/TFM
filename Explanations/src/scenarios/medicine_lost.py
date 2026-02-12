# /src/scenarios/medicine_lost.py
import os
from validator.runtime import ExperimentConfig, Step, run_experiment

file_name = os.path.splitext(os.path.basename(__file__))[0]

cfg_unexpected = ExperimentConfig(
    ontology_path="data/ontologies/MLO.owl",
    steps=[
        Step(
            name="Init",
            types=[
                ("Agent_Nurse", "DUL.Agent"),
                ("Agent_Shadow", "DUL.Agent"),
                ("PhysicalPlace_Hospital", "DUL.PhysicalPlace"),
                ("PhysicalPlace_Hall", "DUL.PhysicalPlace"),
                ("PhysicalPlace_Room101", "DUL.PhysicalPlace"),
                ("PhysicalPlace_Corridor1", "DUL.PhysicalPlace"),
                ("PhysicalObject_ShadowTray", "DUL.PhysicalObject"),
                ("PhysicalObject_Medicine1", "DUL.PhysicalObject"),
                ("Goal_DeliveryAssistance", "DUL.Goal"),
                ("Plan_DeliverMedicine", "DUL.Plan"),
                ("Collaboration_Collaborate", "ocra.Collaboration"),
                ("Task_PlaceMedicine", "SOMA.Task"),
                ("Task_FollowSupervisor", "DUL.Task"),
            ],
            asserts=[
                ("PhysicalPlace_Hall", "DUL.isPartOf", "PhysicalPlace_Hospital"),
                ("PhysicalPlace_Hall", "DUL.hasLocation", "PhysicalPlace_Hospital"),
                ("Agent_Nurse", "DUL.hasLocation", "PhysicalPlace_Hall"),
                ("Agent_Shadow", "DUL.hasLocation", "PhysicalPlace_Hall"),
                ("PhysicalObject_Medicine1", "DUL.hasLocation", "PhysicalPlace_Hall"),
                ("PhysicalPlace_Room101", "DUL.isPartOf", "PhysicalPlace_Hospital"),
                ("PhysicalPlace_Room101", "DUL.hasLocation", "PhysicalPlace_Hospital"),
                ("PhysicalPlace_Corridor1", "DUL.isPartOf", "PhysicalPlace_Hospital"),
                ("PhysicalPlace_Corridor1", "DUL.hasLocation", "PhysicalPlace_Hospital"),
                ("PhysicalObject_ShadowTray", "DUL.isPartOf", "Agent_Shadow"),
                ("PhysicalObject_ShadowTray", "DUL.hasLocation", "Agent_Shadow"),
                ("Plan_DeliverMedicine", "SOMA.isPlanFor", "Task_PlaceMedicine"),
                ("Plan_DeliverMedicine", "SOMA.isPlanFor", "Task_FollowSupervisor"),
                ("Plan_DeliverMedicine", "DUL.hasComponent", "Goal_DeliveryAssistance"),
                ("Collaboration_Collaborate", "ocra.executesPlan", "Plan_DeliverMedicine"),
                ("Collaboration_Collaborate", "DUL.hasParticipant", "Agent_Nurse"),
                ("Collaboration_Collaborate", "DUL.hasParticipant", "Agent_Shadow"),
                ("Agent_Nurse", "ocra.hasPlan", "Plan_DeliverMedicine"),
                ("Agent_Shadow", "ocra.hasPlan", "Plan_DeliverMedicine"),
                ("Agent_Nurse", "ocra.hasGoal", "Goal_DeliveryAssistance"),
                ("Agent_Shadow", "ocra.hasGoal", "Goal_DeliveryAssistance"),
            ]
        ),
        Step(
            name="Place_medicine",
            types=[("Action_PlaceMedicine", "DUL.Action")],
            asserts=[
                ("Action_PlaceMedicine", "DUL.hasParticipant", "Agent_Nurse"),
                ("Action_PlaceMedicine", "DUL.hasParticipant", "Agent_Shadow"),
                ("Action_PlaceMedicine", "DUL.hasParticipant", "PhysicalObject_Medicine1"),
                
                ("Action_PlaceMedicine", "DUL.executesTask", "Task_PlaceMedicine"),
            
            ],
            retracts=[],
            updates=[
                ("PhysicalObject_Medicine1", "DUL.hasLocation", "PhysicalPlace_Hall", "PhysicalObject_ShadowTray"),
            ]
        ),
        Step(
            name="Cleanup",
            types=[],
            asserts=[],
            retracts=[],
            updates=[],
            deletes=["Action_PlaceMedicine"]
        ),
        Step(
            name="Following",
            tags=["background"],
            types=[("Action_Follow", "DUL.Action")],
            asserts=[
                ("Action_Follow", "DUL.hasParticipant", "Agent_Shadow"),
                ("Action_Follow", "DUL.hasParticipant", "Agent_Nurse"),
                ("Action_Follow", "DUL.executesTask", "Task_FollowSupervisor"),
            ],
            retracts=[],
            updates=[]
        ),
        Step(
            name="Move_to_corridor",
            types=[],
            asserts=[],
            retracts=[],
            updates=[
                ("Agent_Nurse", "DUL.hasLocation", "PhysicalPlace_Hall", "PhysicalPlace_Corridor1"),
                ("Agent_Shadow", "DUL.hasLocation", "PhysicalPlace_Hall", "PhysicalPlace_Corridor1"),
            ],
        ),
        Step(
            name="Unexpected_event",
            types=[],
            asserts=[],
            retracts=[
                ("PhysicalObject_Medicine1", "DUL.hasLocation", "PhysicalObject_ShadowTray"),
            ],            
            updates=[]
        ),##################################################### ...
        Step(
            name="End",
            types=[],
            asserts=[],
            retracts=[],
            updates=[]
        )
    ]
)
cfg_unexpected.scenario_id = "medicine_lost"

if __name__ == "__main__":
    run_experiment(cfg_unexpected)
