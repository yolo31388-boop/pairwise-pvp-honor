"""PVP荣誉与军阶系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pvp.honor import HonorSystem, PvPStats

class TestHonorByContribution:
    def test_healer_gets_honor_without_kills(self):
        hs = HonorSystem()
        stats = PvPStats("p1", kills=0, healing=5000, objective_points=100)
        honor = hs.calculate_honor(stats, "sergeant")
        assert honor > 0  # bug1: 0击杀=0荣誉

class TestKillByTargetRank:
    def test_killing_low_rank_gives_less_honor(self):
        hs = HonorSystem()
        h_high = hs.get_honor_per_kill("recruit", "grand_marshal")
        h_low = hs.get_honor_per_kill("recruit", "recruit")
        assert h_high > h_low  # bug2: 都是10

class TestPromotionRequiresWinrate:
    def test_promotion_checks_winrate(self):
        hs = HonorSystem()
        hs.players["p1"] = PvPStats("p1", honor=20000, wins=5, losses=95)
        assert hs.can_promote("p1") == False  # bug3: 胜率5%也能晋级

class TestDecay:
    def test_inactive_player_loses_honor(self):
        hs = HonorSystem()
        hs.players["p1"] = PvPStats("p1", honor=20000)
        hs.decay_threshold = 7
        hs.apply_decay("p1", 30)
        assert hs.players["p1"].honor < 20000  # bug4: 不变

class TestTeamDistribution:
    def test_carry_gets_more_honor(self):
        hs = HonorSystem()
        hs.players["p1"] = PvPStats("p1", damage=10000, kills=10)
        hs.players["p2"] = PvPStats("p2", damage=100, kills=0)
        result = hs.distribute_team_honor(["p1", "p2"], 1000)
        assert result["p1"] > result["p2"]  # bug5: 平均分

class TestRankSkillGate:
    def test_low_rank_cannot_use_high_skill(self):
        hs = HonorSystem()
        hs.players["p1"] = PvPStats("p1", rank="recruit")
        assert hs.can_use_rank_skill("p1", "grand_marshal") == False  # bug6: True

class TestSeasonReset:
    def test_season_reset_clears_honor(self):
        hs = HonorSystem()
        hs.players["p1"] = PvPStats("p1", honor=20000, rank="marshal")
        hs.reset_season()
        assert hs.players["p1"].honor < 20000  # bug7: 不变

class TestSameGuildKill:
    def test_same_guild_kill_no_honor(self):
        hs = HonorSystem()
        assert hs.is_kill_valid("p1", "p2", "G1", "G1") == False  # bug8: True
