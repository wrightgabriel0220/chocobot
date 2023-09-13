from typing import Callable
import unittest
import dundle

mock_intern_card_1 = dundle.InternCard(
            name="Testguy A",
            competence=10,
            creativity=10,
            experience=10,
            obedience=10,
            pride=10,
        )
mock_intern_card_2 = dundle.InternCard(
            name="Testguy B",
            competence=50,
            creativity=50,
            experience=50,
            obedience=50,
            pride=50,
        )

class TestEstablishment(unittest.TestCase):
    def test_establishment_value_reflects_costs_and_profits():
        assert False

class TestRegion(unittest.TestCase):
    def test_can_generate_intern_applications():
        assert False

    def test_can_only_generate_local_intern_applications():
        assert False

class TestAsset(unittest.TestCase):
    def test_can_evalute_assets():
        assert False

class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.mock_player = dundle.Player()
        self.mock_region = dundle.Region(name="Test Region", plots=1)
        self.mock_region.local_intern_cards = [
            mock_intern_card_1,
            mock_intern_card_2,
        ]

    def test_can_buy_assets(
        self,
    ):
        for mock_asset in [self.mock_plot, self.mock_machine]:
            pre_buy_balance = self.mock_player.balance
            asset_cost = dundle.Asset.get_value(asset=mock_asset, region=self.mock_region)
            self.mock_player.buy(mock_asset)

            self.assertTrue(self.mock_player.owns(mock_asset)), f"The player should own the {type(mock_asset)} after purchase."
            self.assertEqual(
                self.mock_player.balance,
                pre_buy_balance - asset_cost,
                "The player's balance should reflect the expense of the purchase",
            )

    def test_can_sell_assets_to_market(
        self,
    ):
        for mock_asset in [self.mock_plot, self.mock_machine]:
            self.mock_player[f"{type(mock_asset)}s"].append(mock_asset)

            pre_sale_balance = self.mock_player.balance
            asset_value = dundle.Asset.get_value(asset=mock_asset, region=self.mock_region)
            self.mock_player.sell(mock_asset)

            self.assertFalse(self.mock_player.owns(mock_asset), f"The {type(mock_asset)} should no longer be owned after purchase.")
            self.assertEqual(
                self.mock_player.balance,
                pre_sale_balance + asset_value,
                "The player should have received the money for the sale.",
            )

    def test_can_sell_assets_to_another_player(self):
        for mock_asset in [self.mock_plot, self.mock_machine]:
            self.mock_player[f"{type(mock_asset)}s"].append(mock_asset)

            #TODO

    def test_machine_count_is_limited_by_plot_count(self, mock_player: dundle.Player, mock_plot: dundle.Plot, mock_machine: dundle.Machine):
        assert False

class TestWorld(unittest.TestCase):
    def test_leaderboard_is_accurate(self):
        assert False
    
    def test_world_save_data_formats_correctly(self):
        assert False
