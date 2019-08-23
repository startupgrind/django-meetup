#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PURPOSE: For testing meetup models
AUTHOR: dylangregersen
DATE: Mon Sep 15 00:52:58 2014
"""
# ########################################################################### #

# import modules

from __future__ import absolute_import, print_function, division, unicode_literals
import time
import unittest

from mock import MagicMock
from mock import Mock
from mock import patch
import requests
from six.moves.urllib_parse import urlparse, parse_qs

from meetup.api import MeetupClient


MEETUP_KEY = "abc123"


# ########################################################################### #


class MeetupClientTests(unittest.TestCase):
    """Tests that ensure GET requests function correctly.
    """

    def setUp(self):
        self.client = MeetupClient(api_key=MEETUP_KEY)
        self.json_body = MagicMock()
        self.response_headers = {
            'X-RateLimit-Remaining': "14",
            'X-RateLimit-Reset': "2"
        }
        self.mock_json = Mock(return_value=self.json_body)
        self.mock_response = Mock(
            headers=self.response_headers,
            json=self.mock_json
        )

    def assertGetCallMatches(self, called_url, expected_path, params_dict):
        parsed_url = urlparse(called_url)
        query_dict = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme, 'https')
        self.assertEqual(parsed_url.netloc, 'api.meetup.com')
        self.assertEqual(parsed_url.path, expected_path)

        self.assertDictEqual(
            params_dict,
            query_dict
        )

    @patch.object(requests, "get")
    @patch.object(requests, "post")
    @patch.object(requests, "delete")
    def test_oauth_requests(self, mock_delete, mock_post, mock_get):
        mock_get.return_value = self.mock_response
        self.client = MeetupClient(oauth_token=MEETUP_KEY)
        self.client.invoke(
            meetup_method="2/groups",
            params={"member_id": "12345"},
            method="GET"
        )

        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        headers = mock_get.call_args[1]['headers']
        self.assertEqual({'Authorization': 'Bearer abc123'}, headers)

        self.assertGetCallMatches(
            called_url,
            '/2/groups',
            {
                'page': ['1000'],
                'member_id': ['12345']
            }
        )

        mock_post.return_value = self.mock_response
        self.client.invoke(
            meetup_method="2/groups",
            params={"name": "Awesome Team"},
            method="POST"
        )
        mock_post.assert_called_once_with(
            "https://api.meetup.com/2/groups",
            data={
                "name": "Awesome Team"
            },
            headers={'Authorization': 'Bearer abc123'}
        )

        mock_delete.return_value = self.mock_response
        self.client.invoke(
            meetup_method="2/groups/awesome-team",
            params={"id": 72},
            method="DELETE"
        )
        mock_delete.assert_called_once_with(
            "https://api.meetup.com/2/groups/awesome-team",
            params={
                "id": 72
            },
            headers={'Authorization': 'Bearer abc123'}
        )

    @patch.object(requests, "get")
    def test_invoke_get_calls_requests(self, mock_get):
        mock_get.return_value = self.mock_response
        result = self.client.invoke(
            meetup_method="2/groups",
            params={
                "member_id": "12345"
            },
            method="GET"
        )
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]

        self.assertGetCallMatches(
            called_url,
            '/2/groups',
            {
                'page': ['1000'],
                'key': ['abc123'],
                'member_id': ['12345'],
            },
        )

        self.mock_json.assert_called_once_with()
        self.assertIs(self.json_body, result)

    @patch.object(requests, "patch")
    def test_invoke_patch_calls_requests(self, mock_patch):
        mock_patch.return_value = self.mock_response
        result = self.client.invoke(
            meetup_method="foo/events/1734824",
            params={
                "name": "Awesome Team Event"
            },
            method="PATCH"
        )
        mock_patch.assert_called_once_with(
            "https://api.meetup.com/foo/events/1734824",
            data={
                "key": "abc123",
                "name": "Awesome Team Event"
            }
        )
        self.mock_json.assert_called_once_with()
        self.assertIs(self.json_body, result)

    @patch.object(requests, "post")
    def test_invoke_post_calls_requests(self, mock_post):
        mock_post.return_value = self.mock_response
        result = self.client.invoke(
            meetup_method="2/groups",
            params={
                "name": "Awesome Team"
            },
            method="POST"
        )
        mock_post.assert_called_once_with(
            "https://api.meetup.com/2/groups",
            data={
                "key": "abc123",
                "name": "Awesome Team"
            }
        )
        self.mock_json.assert_called_once_with()
        self.assertIs(self.json_body, result)

    @patch.object(requests, "delete")
    def test_invoke_delete_calls_requests(self, mock_delete):
        mock_delete.return_value = self.mock_response
        result = self.client.invoke(
            meetup_method="2/groups/awesome-team",
            params={
                "id": 72
            },
            method="DELETE"
        )
        mock_delete.assert_called_once_with(
            "https://api.meetup.com/2/groups/awesome-team",
            params={
                "key": "abc123",
                "id": 72
            }
        )
        self.mock_json.assert_called_once_with()
        self.assertIs(self.json_body, result)

    @patch.object(time, "sleep")
    @patch.object(requests, "get")
    def test_hit_rate_limit_waits(self, mock_get, mock_sleep):
        mock_get.return_value = self.mock_response
        self.response_headers['X-RateLimit-Remaining'] = "0"
        self.response_headers['X-RateLimit-Reset'] = "4"
        self.client.invoke("2/groups/foo")

        self.response_headers['X-RateLimit-Reset'] = "2"
        self.client.invoke("2/groups/bar")
        self.assertEqual(2, len(mock_get.call_args_list))
        mock_sleep.assert_called_once_with(4)

        mock_sleep.reset_mock()
        self.client.invoke("2/groups/chew")
        mock_sleep.assert_called_once_with(2)

    @patch.object(requests, "get")
    def test_get_next_page_uses_meta_to_fetch_next(self, mock_get):
        mock_get.return_value = self.mock_response
        result = self.client.get_next_page(
            {
                "meta": {
                    "next": "http://meetup.foo.co/page-2"
                }
            }
        )
        mock_get.assert_called_once_with("http://meetup.foo.co/page-2")
        self.mock_json.assert_called_once_with()
        self.assertIs(self.json_body, result)

    def test_get_next_page_no_next_is_none(self):
        result = self.client.get_next_page(
            {
                "meta": {
                    "prev": "http://fifo.com/1"
                }
            }
        )
        self.assertIsNone(result)

    def test_get_next_page_no_meta_is_none(self):
        result = self.client.get_next_page({})
        self.assertIsNone(result)


class MeetupAPIEndpointsTests(MeetupClientTests):
    """Test cases for individual API endpoints.
    """

    @patch.object(MeetupClient, "invoke")
    def test_close_event_rsvps(self, mocked_invoke):
        self.client.close_event_rsvps("test-group", 2600)
        mocked_invoke.assert_called_with(
            'test-group/events/2600/rsvps/close/',
            method='POST'
        )

    @patch.object(MeetupClient, "invoke")
    def test_open_event_rsvps(self, mocked_invoke):
        self.client.open_event_rsvps("test-group", 2600)
        mocked_invoke.assert_called_with(
            'test-group/events/2600/rsvps/open/',
            method='POST'
        )


# ########################################################################### #
if __name__ == "__main__":
    unittest.main()
