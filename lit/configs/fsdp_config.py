from dataclasses import dataclass

from torch.distributed.fsdp import ShardingStrategy
from torch.distributed.fsdp.fully_sharded_data_parallel import StateDictType


@dataclass
class fsdp_config:
    use_fp16: bool = False
    sharding_strategy: ShardingStrategy = (
        ShardingStrategy.FULL_SHARD
    )  # HYBRID_SHARD "Full Shard within a node DDP cross Nodes", SHARD_GRAD_OP "Shard only Gradients and Optimizer States", NO_SHARD "Similar to DDP".
    hsdp: bool = (
        False  # Require HYBRID_SHARD to be set. This flag can extend the HYBRID_SHARD by allowing sharding a model on customized number of GPUs (Sharding_group) and Replicas over Sharding_group.
    )
    sharding_group_size: int = (
        0  # requires hsdp to be set. This specifies the sharding group size, number of GPUs that you model can fit into to form a replica of a model.
    )
    replica_group_size: int = (
        0  # requires hsdp to be set. This specifies the replica group size, which is world_size/sharding_group_size.
    )
    checkpoint_type: StateDictType = StateDictType.SHARDED_STATE_DICT
    fsdp_activation_checkpointing: bool = True
    fsdp_cpu_offload: bool = False
    pure_bf16: bool = False
    low_cpu_fsdp: bool = True
    optimizer: str = "AdamW"
