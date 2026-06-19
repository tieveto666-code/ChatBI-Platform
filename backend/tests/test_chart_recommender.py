"""图表类型推荐测试"""

from services.chart_recommender import recommend_chart, has_visual_chart


class TestChartRecommender:
    def test_line_for_time_series(self):
        result = {
            "columns": ["date", "count"],
            "rows": [["2024-01-01", 10], ["2024-01-02", 20], ["2024-01-03", 15]],
        }
        chart = recommend_chart(result)
        assert "line" in chart["available_types"]
        assert "bar" in chart["available_types"]
        assert "table" in chart["available_types"]
        assert chart["default_type"] == "line"
        assert len(chart["options"]["line"]["series"]) == 1
        assert chart["options"]["line"]["series"][0]["type"] == "line"

    def test_bar_for_category_metric(self):
        result = {
            "columns": ["category", "value"],
            "rows": [["A", 30], ["B", 50], ["C", 20]],
        }
        chart = recommend_chart(result)
        assert "bar" in chart["available_types"]
        assert "line" in chart["available_types"]
        assert chart["default_type"] == "bar"
        assert chart["options"]["bar"]["series"][0]["type"] == "bar"

    def test_bar_line_for_two_metrics(self):
        result = {
            "columns": ["month", "sales", "profit"],
            "rows": [
                ["Jan", 100, 10],
                ["Feb", 150, 18],
                ["Mar", 120, 12],
            ],
        }
        chart = recommend_chart(result)
        assert "bar_line" in chart["available_types"]
        assert chart["default_type"] == "bar_line"
        assert len(chart["options"]["bar_line"]["series"]) == 2
        assert chart["options"]["bar_line"]["series"][0]["type"] == "bar"
        assert chart["options"]["bar_line"]["series"][1]["type"] == "line"

    def test_table_for_no_numeric(self):
        result = {
            "columns": ["name", "grade"],
            "rows": [["Alice", "A"], ["Bob", "B"]],
        }
        chart = recommend_chart(result)
        assert chart["available_types"] == ["table"]
        assert chart["default_type"] == "table"
        assert not has_visual_chart(chart)

    def test_table_for_too_many_columns(self):
        result = {
            "columns": ["a", "b", "c", "d", "e"],
            "rows": [[1, 2, 3, 4, 5]],
        }
        chart = recommend_chart(result)
        assert chart["available_types"] == ["table"]

    def test_table_for_empty(self):
        chart = recommend_chart({"columns": [], "rows": []})
        assert chart["available_types"] == ["table"]

    def test_multiple_visual_types(self):
        result = {
            "columns": ["date", "count"],
            "rows": [["2024-01-01", 10], ["2024-01-02", 20]],
        }
        chart = recommend_chart(result)
        visual = [t for t in chart["available_types"] if t != "table"]
        assert len(visual) >= 2
        assert has_visual_chart(chart)
