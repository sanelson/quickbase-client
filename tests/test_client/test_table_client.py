import json
from datetime import date

import pytest

from quickbase_client import ResponsePager
from quickbase_client.client.table_client import QuickbaseTableClient
from quickbase_client.query.query_base import QuickbaseQuery


class TestQuickbaseTableClient(object):
    @pytest.mark.parametrize(
        "http_method,url,cls_method,kwargs",
        [
            ("GET", "/apps/abcdefg", "get_app", {}),
            ("GET", "/tables?appId=abcdefg", "get_tables_for_app", {}),
            ("GET", "/tables/aaaaaa?appId=abcdefg", "get_table", {}),
            ("GET", "/fields?tableId=aaaaaa", "get_fields_for_table", {}),
            ("GET", "/fields/6?tableId=aaaaaa", "get_field", {"field": 6}),
            ("GET", "/reports?tableId=aaaaaa", "get_reports_for_table", {}),
            ("GET", "/reports/1?tableId=aaaaaa", "get_report", {"report": 1}),
            ("POST", "/reports/1/run?tableId=aaaaaa", "run_report", {"report": 1}),
        ],
    )
    def test_makes_api_request_to_correct_url(
        self, requests_mock, debugs_table, http_method, url, cls_method, kwargs
    ):
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        mock_json = {"foo": "bar"}
        requests_mock.request(
            http_method, f"https://api.quickbase.com/v1{url}", json=mock_json
        )
        resp = getattr(client, cls_method)(**kwargs)
        assert resp.ok
        assert resp.json() == mock_json

    @pytest.mark.parametrize(
        "header,val",
        [
            ("Content-Type", "application/json"),
            ("Authorization", "QB-USER-TOKEN myusertoken"),
            ("QB-Realm-Hostname", "dicorp.quickbase.com"),
        ],
    )
    def test_request_includes_proper_headers(self, mocker, debugs_table, header, val):
        client = QuickbaseTableClient(debugs_table, user_token="myusertoken")
        spy = mocker.spy(client.api.rf.session, "request")
        client.get_table()
        args, kwargs = spy.call_args
        headers = kwargs["headers"]
        assert header in headers
        assert headers[header] == val

    def test_add_record_posts_data_as_list(self, requests_mock, mocker, debugs_table):
        requests_mock.post(
            "https://api.quickbase.com/v1/records", json={"blah": "bleh"}
        )
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        spy = mocker.spy(client.api.rf.session, "request")
        record = debugs_table(some_basic_text_field="hi", some_checkbox=False)
        client.add_record(record)
        args, kwargs = spy.call_args
        posted_json = kwargs["json"]
        assert posted_json["to"] == "aaaaaa"
        assert posted_json["data"][0]["6"]["value"] == "hi"

    def test_serializes_dates(self, requests_mock, mocker, debugs_table):
        requests_mock.post(
            "https://api.quickbase.com/v1/records", json={"blah": "bleh"}
        )
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        spy = mocker.spy(client.api.rf.session, "request")
        record = debugs_table(
            some_basic_text_field="hi", just_a_date=date(year=2020, month=2, day=7)
        )
        client.add_record(record)
        args, kwargs = spy.call_args
        posted_json = kwargs["json"]
        assert "2020-02-07" in json.dumps(posted_json["data"])

    def test_add_record_does_not_post_null_values(self, mocker, debugs_table):
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        spy = mocker.spy(client.api.rf.session, "request")
        record = debugs_table(some_basic_text_field="hi", some_checkbox=False)
        client.add_record(record)
        args, kwargs = spy.call_args
        posted_json = kwargs["json"]
        assert posted_json["to"] == "aaaaaa"
        assert "7" not in posted_json["data"]

    def test_query_raw_response(self, debugs_table, qb_api_mock):
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        q = QuickbaseQuery(where="{'18'.EX.19}")
        r = client.query(q, raw=True)
        assert r.ok

    def test_query_deserialized_response(self, debugs_table, qb_api_mock):
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        recs = client.query()
        for rec in recs:
            assert isinstance(rec, debugs_table)
            assert rec.some_basic_text_field is not None

    def test_query_with_pager(self, debugs_table, qb_api_mock):
        client = QuickbaseTableClient(debugs_table, user_token="doesnotmatter")
        pager = ResponsePager()
        client.query(pager=pager)
        assert pager.total_records == 4
        assert not pager.more_remaining()
