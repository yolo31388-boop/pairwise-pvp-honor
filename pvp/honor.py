"""PVP荣誉与军阶系统 - 含8个bug"""
from dataclasses import dataclass, field

@dataclass
class PvPStats:
    pid: str
    kills: int = 0
    damage: float = 0
    healing: float = 0
    objective_points: int = 0
    wins: int = 0
    losses: int = 0
    honor: int = 0
    rank: str = "recruit"

class HonorSystem:
    def __init__(self):
        self.players: dict[str, PvPStats] = {}
        self.decay_threshold = 0  # bug4: 无衰减
        self.season = "s1"

    def calculate_honor(self, stats: PvPStats, target_rank: str) -> int:
        # bug1: 只看击杀
        return stats.kills * 10

    def get_honor_per_kill(self, killer_rank: str, victim_rank: str) -> int:
        # bug2: 不看目标军衔
        return 10

    def can_promote(self, pid: str) -> bool:
        # bug3: 只看荣誉不看胜率
        p = self.players[pid]
        return p.honor >= 10000

    def apply_decay(self, pid: str, days_inactive: int):
        # bug4: 无衰减
        pass

    def distribute_team_honor(self, players: list[str], total_honor: int) -> dict:
        # bug5: 平均分配
        per = total_honor // len(players)
        return {pid: per for pid in players}

    def can_use_rank_skill(self, pid: str, required_rank: str) -> bool:
        # bug6: 无军阶要求
        return True

    def reset_season(self):
        # bug7: 不重置
        pass

    def is_kill_valid(self, killer_id: str, victim_id: str, killer_guild: str, victim_guild: str) -> bool:
        # bug8: 同公会也给荣誉
        return True
