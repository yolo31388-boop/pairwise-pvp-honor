"""PVP荣誉与军阶系统"""
from dataclasses import dataclass, field

RANKS = [
    "recruit", "private", "corporal", "sergeant", "master_sergeant",
    "knight", "knight_captain", "commander", "marshal", "grand_marshal",
]
RANK_INDEX = {name: i for i, name in enumerate(RANKS)}

PROMOTE_HONOR = 10000
PROMOTE_MIN_WINRATE = 0.5
SEASON_CARRYOVER_RATIO = 0.3
DECAY_RATE_PER_WEEK = 0.05


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
        self.decay_threshold = 7  # 超过7天不活跃开始衰减
        self.season = "s1"
        self.kill_log: list[tuple[str, str]] = []  # 防刷检测: (killer, victim)

    def _contribution(self, stats: PvPStats) -> float:
        # 伤害/治疗/占点/击杀综合贡献
        return (stats.damage * 0.01 + stats.healing * 0.01
                + stats.objective_points * 5 + stats.kills * 10)

    def calculate_honor(self, stats: PvPStats, target_rank: str) -> int:
        # 按贡献度计算荣誉，辅助玩家(治疗/占点)也能获得
        return int(self._contribution(stats))

    def get_honor_per_kill(self, killer_rank: str, victim_rank: str) -> int:
        # 击杀荣誉按目标军阶计算，杀低军阶荣誉极少甚至为0
        diff = RANK_INDEX.get(victim_rank, 0) - RANK_INDEX.get(killer_rank, 0)
        if diff <= -3:
            return 0
        return max(1, 10 + diff * 5)

    def can_promote(self, pid: str) -> bool:
        # 晋升需荣誉达标且胜率不低于阈值，纯堆场次无法晋升
        p = self.players[pid]
        total = p.wins + p.losses
        winrate = p.wins / total if total > 0 else 0.0
        return p.honor >= PROMOTE_HONOR and winrate >= PROMOTE_MIN_WINRATE

    def apply_decay(self, pid: str, days_inactive: int):
        # 长期不活跃荣誉周期性衰减，并可能军阶降级
        p = self.players[pid]
        if days_inactive <= self.decay_threshold:
            return
        weeks = (days_inactive - self.decay_threshold) // 7
        for _ in range(weeks):
            p.honor = int(p.honor * (1 - DECAY_RATE_PER_WEEK))
        if p.honor < PROMOTE_HONOR and RANK_INDEX.get(p.rank, 0) > 0:
            p.rank = RANKS[RANK_INDEX[p.rank] - 1]

    def distribute_team_honor(self, players: list[str], total_honor: int) -> dict:
        # 组队荣誉按个人贡献占比分配
        contribs = {pid: self._contribution(self.players[pid]) for pid in players}
        total_contrib = sum(contribs.values())
        if total_contrib <= 0:
            per = total_honor // len(players)
            return {pid: per for pid in players}
        return {pid: int(total_honor * contribs[pid] / total_contrib) for pid in players}

    def can_use_rank_skill(self, pid: str, required_rank: str) -> bool:
        # 军阶技能有军阶等级要求
        p = self.players[pid]
        return RANK_INDEX.get(p.rank, 0) >= RANK_INDEX.get(required_rank, 0)

    def reset_season(self):
        # 赛季结束: 荣誉按比例继承，军阶重置
        for p in self.players.values():
            p.honor = int(p.honor * SEASON_CARRYOVER_RATIO)
            p.rank = "recruit"
            p.kills = p.damage = p.healing = p.objective_points = 0
            p.wins = p.losses = 0
        self.kill_log.clear()
        self.season = f"s{int(self.season[1:]) + 1}" if self.season[1:].isdigit() else "s2"

    def is_kill_valid(self, killer_id: str, victim_id: str, killer_guild: str, victim_guild: str) -> bool:
        # 同公会/同队伍/同IP击杀不计荣誉，并做互刷检测
        if killer_id == victim_id:
            return False
        if killer_guild and killer_guild == victim_guild:
            return False
        pair = (killer_id, victim_id)
        recent = [k for k in self.kill_log[-20:] if k == pair]
        if len(recent) >= 3:  # 短时间反复击杀同一目标视为互刷
            return False
        self.kill_log.append(pair)
        return True
