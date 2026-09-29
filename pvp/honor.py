"""PVP荣誉与军阶系统"""
from dataclasses import dataclass

# 军阶阶梯（等级从低到高）
RANKS = [
    "recruit",
    "corporal",
    "sergeant",
    "master_sergeant",
    "knight",
    "knight_lieutenant",
    "knight_captain",
    "knight_champion",
    "lieutenant_commander",
    "commander",
    "marshal",
    "field_marshal",
    "grand_marshal",
]
RANK_LEVEL = {rank: i for i, rank in enumerate(RANKS)}

# 各军阶所需荣誉（用于衰减后的降级判定）
RANK_HONOR = {
    "recruit": 0,
    "corporal": 1000,
    "sergeant": 2000,
    "master_sergeant": 3500,
    "knight": 5000,
    "knight_lieutenant": 7000,
    "knight_captain": 9000,
    "knight_champion": 11500,
    "lieutenant_commander": 14000,
    "commander": 17000,
    "marshal": 20000,
    "field_marshal": 25000,
    "grand_marshal": 30000,
}

# fix1: 贡献度权重（伤害/治疗/占点）
DAMAGE_WEIGHT = 0.01
HEALING_WEIGHT = 0.005
OBJECTIVE_WEIGHT = 2
KILL_CONTRIB_WEIGHT = 10

# fix3: 晋升门槛
PROMOTION_HONOR = 10000
MIN_WINRATE = 0.5
MIN_GAMES = 10

# fix4: 衰减参数（每经过一个衰减周期，荣誉保留 DECAY_FACTOR）
DECAY_FACTOR = 0.9

# fix2: 击杀荣誉与防虐新手
KILL_RANK_WEIGHT = 2
RANK_GAP_NO_HONOR = 5

# fix7: 赛季重置后荣誉继承比例
SEASON_CARRYOVER = 0.1

# fix8: 同一凶手反复击杀同一受害者超过该次数即判定为刷荣誉
FARM_LIMIT = 5


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
        self.decay_threshold = 7  # 连续不活跃天数达到该值开始衰减
        self.season = "s1"
        self.kill_counts: dict[tuple[str, str], int] = {}
        self.farm_limit = FARM_LIMIT

    def _performance(self, stats: PvPStats) -> float:
        """伤害/治疗/占点构成的基础贡献（与击杀无关，辅助也能拿荣誉）。"""
        return (
            stats.damage * DAMAGE_WEIGHT
            + stats.healing * HEALING_WEIGHT
            + stats.objective_points * OBJECTIVE_WEIGHT
        )

    def _contribution(self, stats: PvPStats) -> float:
        """个人综合贡献度：伤害/治疗/占点/击杀。"""
        return self._performance(stats) + stats.kills * KILL_CONTRIB_WEIGHT

    def calculate_honor(self, stats: PvPStats, target_rank: str) -> int:
        # fix1: 荣誉按贡献度（伤害/治疗/占点/击杀）综合计算
        # fix2: 击杀部分荣誉取决于目标军阶
        kill_honor = stats.kills * self.get_honor_per_kill(stats.rank, target_rank)
        return int(self._performance(stats) + kill_honor)

    def get_honor_per_kill(self, killer_rank: str, victim_rank: str) -> int:
        # fix2: 荣誉按目标军阶计算；高军阶虐杀低军阶收益递减甚至为0
        killer_level = RANK_LEVEL.get(killer_rank, 0)
        victim_level = RANK_LEVEL.get(victim_rank, 0)
        base = victim_level * KILL_RANK_WEIGHT  # 低军阶目标给极少荣誉，recruit为0
        gap = killer_level - victim_level
        if gap >= RANK_GAP_NO_HONOR:
            return 0
        factor = max(0.25, 1 - 0.1 * gap)
        return int(base * factor)

    def can_promote(self, pid: str) -> bool:
        # fix3: 荣誉达标且胜率不低于阈值，堆场次无法晋级
        p = self.players[pid]
        games = p.wins + p.losses
        if games < MIN_GAMES:
            return False
        winrate = p.wins / games
        return p.honor >= PROMOTION_HONOR and winrate >= MIN_WINRATE

    def _rank_for_honor(self, honor: int) -> str:
        """按当前荣誉返回可保持的最高军阶。"""
        result = "recruit"
        for rank in RANKS:
            if honor >= RANK_HONOR[rank]:
                result = rank
        return result

    def apply_decay(self, pid: str, days_inactive: int):
        # fix4: 长期不活跃周期性衰减荣誉，并按剩余荣誉降级
        p = self.players[pid]
        if self.decay_threshold <= 0 or days_inactive < self.decay_threshold:
            return
        periods = days_inactive // self.decay_threshold
        p.honor = int(p.honor * (DECAY_FACTOR ** periods))
        p.rank = self._rank_for_honor(p.honor)

    def distribute_team_honor(self, players: list[str], total_honor: int) -> dict:
        # fix5: 按个人贡献占比分配，而非平均分配
        contributions = {}
        for pid in players:
            stats = self.players.get(pid)
            contributions[pid] = self._contribution(stats) if stats else 0.0
        total_contribution = sum(contributions.values())
        if total_contribution <= 0:
            share = total_honor // len(players)
            return {pid: share for pid in players}
        return {
            pid: int(total_honor * contributions[pid] / total_contribution)
            for pid in players
        }

    def can_use_rank_skill(self, pid: str, required_rank: str) -> bool:
        # fix6: 军阶技能有军阶等级要求，不达标不能使用
        p = self.players[pid]
        player_level = RANK_LEVEL.get(p.rank, 0)
        required_level = RANK_LEVEL.get(required_rank, len(RANKS))
        return player_level >= required_level

    def reset_season(self, carryover: float = SEASON_CARRYOVER):
        # fix7: 赛季结束荣誉按比例继承、军阶与战绩重置
        for p in self.players.values():
            p.honor = int(p.honor * carryover)
            p.rank = "recruit"
            p.wins = 0
            p.losses = 0
        self.kill_counts.clear()
        season_num = int(self.season[1:]) if self.season.startswith("s") else 1
        self.season = f"s{season_num + 1}"

    def record_kill(self, killer_id: str, victim_id: str):
        """记录一次击杀对，用于防刷检测。"""
        key = (killer_id, victim_id)
        self.kill_counts[key] = self.kill_counts.get(key, 0) + 1

    def is_kill_valid(
        self,
        killer_id: str,
        victim_id: str,
        killer_guild: str,
        victim_guild: str,
        killer_team: str | None = None,
        victim_team: str | None = None,
        killer_ip: str | None = None,
        victim_ip: str | None = None,
    ) -> bool:
        # fix8: 同公会/同队伍/同IP/自杀不计荣誉，并做防刷检测
        if killer_id == victim_id:
            return False
        if killer_guild and killer_guild == victim_guild:
            return False
        if killer_team and killer_team == victim_team:
            return False
        if killer_ip and killer_ip == victim_ip:
            return False
        if self.kill_counts.get((killer_id, victim_id), 0) >= self.farm_limit:
            return False
        return True
